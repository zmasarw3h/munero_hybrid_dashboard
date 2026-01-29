#!/bin/sh
set -eu

if [ -z "${BASIC_AUTH_USER:-}" ]; then
  echo "BASIC_AUTH_USER is required for Caddy Basic Auth" >&2
  exit 1
fi

if [ -z "${BASIC_AUTH_HASH:-}" ]; then
  if [ -z "${BASIC_AUTH_PASSWORD:-}" ]; then
    echo "Set BASIC_AUTH_PASSWORD (recommended) or BASIC_AUTH_HASH for Caddy Basic Auth" >&2
    exit 1
  fi

  BASIC_AUTH_HASH="$(caddy hash-password --algorithm bcrypt --plaintext "$BASIC_AUTH_PASSWORD")"
  export BASIC_AUTH_HASH
fi

exec caddy run --config /etc/caddy/Caddyfile --adapter caddyfile
