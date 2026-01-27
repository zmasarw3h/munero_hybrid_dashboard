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
  - Verifies backend health and dashboard connectivity on http://localhost:8000
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
  local base_url="http://localhost:8000"

  echo "============================================================"
  echo "✅ Phase Gate (smoke)"
  echo "============================================================"

  offline_gate

  require_cmd curl
  require_cmd "${PYTHON_BIN}"

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
