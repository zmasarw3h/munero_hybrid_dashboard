#!/bin/sh
set -eu

DB_FILE="${DB_FILE:-/data/munero.sqlite}"
SEED_SRC="/seed/munero.sqlite"

if [ -f "$DB_FILE" ]; then
  echo "seed_db: DB already exists at $DB_FILE"
  exit 0
fi

if [ ! -f "$SEED_SRC" ]; then
  echo "seed_db: missing seed DB at $SEED_SRC" >&2
  echo "seed_db: create host file at munero-platform/data/munero.sqlite before running compose" >&2
  exit 1
fi

mkdir -p "$(dirname "$DB_FILE")"
cp -f "$SEED_SRC" "$DB_FILE"
echo "seed_db: copied $SEED_SRC -> $DB_FILE"
