#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  DEMO_DOMAIN=demo-client1.yourdomain.com \
  BASIC_AUTH_USER=... \
  BASIC_AUTH_PASSWORD=... \
  ./smoke.sh

Optional env:
  BASE_URL=https://demo-client1.yourdomain.com   # overrides DEMO_DOMAIN
  INSECURE=true                                  # pass -k to curl (not recommended)
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required env var: ${name}" >&2
    usage >&2
    exit 2
  fi
}

require_env BASIC_AUTH_USER
require_env BASIC_AUTH_PASSWORD

if [[ -z "${BASE_URL:-}" ]]; then
  require_env DEMO_DOMAIN
  BASE_URL="https://${DEMO_DOMAIN}"
fi

curl_args=(-fsS --connect-timeout 5 --max-time 30 -u "${BASIC_AUTH_USER}:${BASIC_AUTH_PASSWORD}")
if [[ "${INSECURE:-false}" == "true" ]]; then
  curl_args+=(-k)
fi

echo "== Munero Phase 5 smoke tests ==" >&2
echo "BASE_URL=${BASE_URL}" >&2

echo "" >&2
echo "== /health ==" >&2
curl "${curl_args[@]}" "${BASE_URL}/health" >/dev/null
echo "OK" >&2

echo "" >&2
echo "== /api/dashboard/test ==" >&2
curl "${curl_args[@]}" "${BASE_URL}/api/dashboard/test" >/dev/null
echo "OK" >&2

echo "" >&2
echo "== /api/chat/test ==" >&2
curl "${curl_args[@]}" "${BASE_URL}/api/chat/test" >/dev/null
echo "OK" >&2

echo "" >&2
echo "✅ Smoke tests passed." >&2
