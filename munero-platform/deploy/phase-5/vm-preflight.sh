#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  DEMO_DOMAIN=demo-client1.yourdomain.com EXPECTED_IP=<vm.public.ip> ./vm-preflight.sh

What it checks:
  - DEMO_DOMAIN resolves (and matches EXPECTED_IP if provided)
  - Docker + Docker Compose v2 are available (if installed)
  - Common "should not be exposed" ports are not listening locally (best-effort)

Notes:
  - DNS propagation can take time; re-run until it matches.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ -z "${DEMO_DOMAIN:-}" ]]; then
  echo "Missing required env var: DEMO_DOMAIN" >&2
  usage >&2
  exit 2
fi

resolve_ipv4() {
  local host="$1"
  if command -v dig >/dev/null 2>&1; then
    dig +short A "${host}" | head -n 1
    return 0
  fi
  if command -v getent >/dev/null 2>&1; then
    getent ahostsv4 "${host}" 2>/dev/null | awk '{print $1}' | head -n 1
    return 0
  fi
  if command -v nslookup >/dev/null 2>&1; then
    nslookup "${host}" 2>/dev/null | awk '/^Address: /{print $2}' | tail -n 1
    return 0
  fi
  return 1
}

echo "== Munero Phase 5 VM preflight ==" >&2
echo "DEMO_DOMAIN=${DEMO_DOMAIN}" >&2

resolved_ip="$(resolve_ipv4 "${DEMO_DOMAIN}" || true)"
if [[ -z "${resolved_ip}" ]]; then
  echo "❌ Unable to resolve DEMO_DOMAIN (missing dig/getent/nslookup, or DNS not propagated)." >&2
  exit 1
fi

echo "Resolved IP: ${resolved_ip}" >&2

if [[ -n "${EXPECTED_IP:-}" ]]; then
  if [[ "${resolved_ip}" != "${EXPECTED_IP}" ]]; then
    echo "❌ DNS mismatch: EXPECTED_IP=${EXPECTED_IP} resolved=${resolved_ip}" >&2
    exit 1
  fi
  echo "DNS OK (matches EXPECTED_IP)." >&2
fi

echo "" >&2
echo "== Docker (optional) ==" >&2
if command -v docker >/dev/null 2>&1; then
  docker --version >&2
  if docker compose version >/dev/null 2>&1; then
    docker compose version >&2
  else
    echo "⚠️  docker compose not available (Compose v2 plugin missing?)." >&2
  fi
else
  echo "⚠️  docker not installed." >&2
fi

echo "" >&2
echo "== Local listening ports (best-effort) ==" >&2
if command -v ss >/dev/null 2>&1; then
  ss -lnt | awk 'NR==1 || $4 ~ /:(22|80|443|3000|8000|11434)$/ {print}'
else
  echo "⚠️  ss not available; skipping listening port check." >&2
fi

echo "" >&2
echo "✅ Preflight complete." >&2

