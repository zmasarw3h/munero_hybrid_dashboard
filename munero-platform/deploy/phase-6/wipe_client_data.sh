#!/bin/sh
set -eu

usage() {
  cat <<'EOF'
Usage: wipe_client_data.sh [--compose-dir PATH] [--keep-host-seed] [--yes]

Wipes client demo data for the Phase 4 Compose stack:
  - stops the stack (docker compose down)
  - wipes the persistent client_data volume contents (/data)
  - optionally deletes the host seed DB file (munero-platform/data/munero.sqlite)

Options:
  --compose-dir PATH   Path to the Phase 4 compose directory (default: ../phase-4 relative to this script)
  --keep-host-seed     Do NOT delete the host seed DB file (default: delete it)
  --yes                Skip interactive confirmation
  -h, --help           Show this help

Notes:
  - This script is intended to run on the demo VM.
  - After wiping, re-upload the client DB file and re-seed before restarting the stack.
EOF
}

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
COMPOSE_DIR="${SCRIPT_DIR}/../phase-4"
KEEP_HOST_SEED="false"
ASSUME_YES="false"

while [ "${#}" -gt 0 ]; do
  case "${1}" in
    --compose-dir)
      COMPOSE_DIR="${2:-}"
      shift 2
      ;;
    --keep-host-seed)
      KEEP_HOST_SEED="true"
      shift 1
      ;;
    --yes)
      ASSUME_YES="true"
      shift 1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: ${1}" >&2
      echo "" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [ -z "${COMPOSE_DIR}" ] || [ ! -d "${COMPOSE_DIR}" ]; then
  echo "Missing/invalid --compose-dir: ${COMPOSE_DIR}" >&2
  exit 1
fi

COMPOSE_DIR="$(CDPATH= cd -- "${COMPOSE_DIR}" && pwd)"
COMPOSE_FILE="${COMPOSE_DIR}/docker-compose.yml"
HOST_SEED_DB="${COMPOSE_DIR}/../../data/munero.sqlite"

if [ ! -f "${COMPOSE_FILE}" ]; then
  echo "Missing compose file: ${COMPOSE_FILE}" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Missing required command: docker" >&2
  exit 1
fi

echo "============================================================"
echo "Munero Demo Wipe/Reset (Phase 6)"
echo "============================================================"
echo "Compose dir: ${COMPOSE_DIR}"
echo "Compose file: ${COMPOSE_FILE}"
echo "Will:"
echo "  - docker compose down"
echo "  - wipe contents of client_data volume (/data) via seed_db service"
if [ "${KEEP_HOST_SEED}" = "true" ]; then
  echo "  - keep host seed DB: ${HOST_SEED_DB}"
else
  echo "  - delete host seed DB if present: ${HOST_SEED_DB}"
fi
echo ""

if [ "${ASSUME_YES}" != "true" ]; then
  printf "Type WIPE to continue: "
  read -r CONFIRM
  if [ "${CONFIRM}" != "WIPE" ]; then
    echo "Aborted."
    exit 1
  fi
fi

(
  cd "${COMPOSE_DIR}"
  docker compose down
)

(
  cd "${COMPOSE_DIR}"
  docker compose run --rm --no-deps --entrypoint sh seed_db -c '
    set -eu
    if [ ! -d /data ]; then
      echo "wipe: missing /data (client_data volume not mounted?)" >&2
      exit 1
    fi
    # Delete all contents (including hidden files) in /data.
    find /data -mindepth 1 -maxdepth 1 -exec rm -rf {} +
    echo "wipe: client_data volume contents removed."
  '
)

if [ "${KEEP_HOST_SEED}" != "true" ]; then
  if [ -f "${HOST_SEED_DB}" ]; then
    rm -f "${HOST_SEED_DB}"
    echo "wipe: deleted host seed DB at ${HOST_SEED_DB}"
  else
    echo "wipe: host seed DB not present at ${HOST_SEED_DB} (nothing to delete)"
  fi
fi

echo ""
echo "Next steps:"
echo "  1) Upload/restore the client DB file to: ${HOST_SEED_DB}"
echo "  2) Re-seed the volume: (cd \"${COMPOSE_DIR}\" && docker compose run --rm seed_db)"
echo "  3) Start the stack:    (cd \"${COMPOSE_DIR}\" && docker compose up -d --build)"

