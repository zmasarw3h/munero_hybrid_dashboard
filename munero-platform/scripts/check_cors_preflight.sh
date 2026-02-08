#!/usr/bin/env bash
set -euo pipefail

# Quick CORS preflight probe for the hosted backend.
#
# Example:
#   BACKEND="https://your-render-backend.onrender.com" \
#   ORIGIN="https://your-app.vercel.app" \
#   ENDPOINT="/api/dashboard/headline" \
#   METHOD="POST" \
#   bash munero-platform/scripts/check_cors_preflight.sh

BACKEND="${BACKEND:-}"
ORIGIN="${ORIGIN:-}"
ENDPOINT="${ENDPOINT:-/api/dashboard/headline}"
METHOD="${METHOD:-POST}"
REQ_HEADERS="${REQ_HEADERS:-content-type}"

if [[ -z "$BACKEND" || -z "$ORIGIN" ]]; then
  echo "Missing BACKEND/ORIGIN."
  echo "Usage: BACKEND=https://... ORIGIN=https://... [ENDPOINT=/api/dashboard/headline] [METHOD=POST] $0"
  exit 2
fi

backend="${BACKEND%/}"
endpoint="${ENDPOINT#/}"

curl -i -X OPTIONS "${backend}/${endpoint}" \
  -H "Origin: ${ORIGIN}" \
  -H "Access-Control-Request-Method: ${METHOD}" \
  -H "Access-Control-Request-Headers: ${REQ_HEADERS}"

