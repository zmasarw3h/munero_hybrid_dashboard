#!/bin/bash

# Munero Platform - Phase Gate
# Run this after each deployment phase to catch regressions early.
#
# Usage:
#   ./scripts/phase_gate.sh offline   # no running services required
#   ./scripts/phase_gate.sh smoke     # assumes backend running on localhost:8000
#
# Optional env vars:
#   PYTHON_BIN=python3
#   BASE_URL=http://localhost:8000
#   REQUIRE_OLLAMA=true   # smoke mode: fail if Ollama isn't available

set -euo pipefail

MODE="${1:-}"

usage() {
  cat <<'EOF'
Usage: ./scripts/phase_gate.sh <offline|smoke>

offline:
  - Python compile check for backend
  - SmartRender unit-style test
  - Frontend lint + build

smoke:
  - Runs offline gate first
  - Verifies backend health and dashboard connectivity on $BASE_URL (default: http://localhost:8000)
  - Verifies Ollama availability via /api/chat/test (optional; see REQUIRE_OLLAMA)
EOF
}

if [[ -z "${MODE}" || "${MODE}" == "-h" || "${MODE}" == "--help" ]]; then
  usage
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MUNERO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -z "${PYTHON_BIN:-}" && -x "${MUNERO_ROOT}/venv/bin/python" ]]; then
  PYTHON_BIN="${MUNERO_ROOT}/venv/bin/python"
else
  PYTHON_BIN="${PYTHON_BIN:-python3}"
  if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    PYTHON_BIN="python"
  fi
fi

require_cmd() {
  local cmd="${1}"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "❌ Missing required command: ${cmd}" >&2
    exit 1
  fi
}

run() {
  echo "+ $*" >&2
  "$@"
}

offline_gate() {
  echo "============================================================"
  echo "✅ Phase Gate (offline)"
  echo "============================================================"

  require_cmd "${PYTHON_BIN}"
  require_cmd npm

  echo ""
  echo "== Backend: compile check =="
  run "${PYTHON_BIN}" -m compileall "${MUNERO_ROOT}/backend" >/dev/null

  echo ""
  echo "== Backend: SmartRender test =="
  run "${PYTHON_BIN}" "${MUNERO_ROOT}/scripts/test_smart_render.py"

  echo ""
  echo "== Frontend: lint + build =="
  (
    cd "${MUNERO_ROOT}/frontend"
    run npm run lint
    run npm run build -- --webpack
  )

  echo ""
  echo "✅ Offline gate passed."
}

smoke_gate() {
  local base_url="${BASE_URL:-http://localhost:8000}"

  echo "============================================================"
  echo "✅ Phase Gate (smoke)"
  echo "============================================================"

  offline_gate

  require_cmd curl
  require_cmd "${PYTHON_BIN}"

  echo ""
  echo "== Backend: reachability check =="
  set +e
  local reachability_out
  reachability_out="$("${PYTHON_BIN}" - "${base_url}" <<'PY'
import socket
import sys
from urllib.parse import urlparse

base_url = sys.argv[1]
u = urlparse(base_url)
host = u.hostname or "localhost"
port = u.port or (443 if u.scheme == "https" else 80)

try:
    sock = socket.create_connection((host, port), timeout=1.0)
    sock.close()
    print("OK")
    sys.exit(0)
except PermissionError:
    print("PERMISSION")
    sys.exit(2)
except Exception as e:
    print(f"{type(e).__name__}: {e}")
    sys.exit(1)
PY
)"
  local reachability_rc=$?
  set -e

  if [[ ${reachability_rc} -eq 2 ]]; then
    echo "❌ Cannot connect to ${base_url} (network is blocked in this environment)." >&2
    echo "   Run this smoke gate from your local terminal, or re-run with network access enabled." >&2
    exit 1
  fi

  if [[ ${reachability_rc} -ne 0 ]]; then
    echo "❌ Backend not reachable at ${base_url} (${reachability_out})." >&2
    echo "   Start the backend (example): cd munero-platform/backend && ./../scripts/start_backend.sh" >&2
    echo "   Or set BASE_URL to the correct address/port: BASE_URL=http://127.0.0.1:8000 ./scripts/phase_gate.sh smoke" >&2
    exit 1
  fi

  echo ""
  echo "== Backend: /health (requires DB) =="
  run curl -fsS "${base_url}/health" | run "${PYTHON_BIN}" -c \
    "import json,sys; d=json.load(sys.stdin); assert d.get('database_connected') is True, d; print('OK')"

  echo ""
  echo "== Backend: /api/dashboard/test (requires DB) =="
  run curl -fsS "${base_url}/api/dashboard/test" | run "${PYTHON_BIN}" -c \
    "import json,sys; d=json.load(sys.stdin); assert d.get('status')=='ok', d; print('OK')"

  echo ""
  echo "== Backend: /api/chat/test (optional) =="
  if run curl -fsS "${base_url}/api/chat/test" | run "${PYTHON_BIN}" -c \
    "import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get('llm_available') is True else 1)"; then
    echo "OK (Ollama available)"
  else
    if [[ "${REQUIRE_OLLAMA:-false}" == "true" ]]; then
      echo "❌ Ollama not available (REQUIRE_OLLAMA=true)" >&2
      exit 1
    fi
    echo "⚠️  Skipping LLM smoke checks (Ollama not available)."
  fi

  echo ""
  echo "✅ Smoke gate passed."
}

case "${MODE}" in
  offline) offline_gate ;;
  smoke) smoke_gate ;;
  *)
    usage
    exit 2
    ;;
esac
