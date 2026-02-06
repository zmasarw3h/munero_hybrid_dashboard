# Phase 6 — Data Handling & Reset Workflow

## Data retention policy (practical)
- Keep only the data required for the demo.
- Wipe within **24 hours** of trial end (or immediately on request).

## Wipe/reset procedure (VM)
This resets the environment back to a clean state and removes the client dataset from the VM.

From the repo root on the VM:
- `./deploy/phase-6/wipe_client_data.sh`

Non-interactive:
- `./deploy/phase-6/wipe_client_data.sh --yes`

If you intentionally want to keep `munero-platform/data/munero.sqlite` on disk (not recommended for retention):
- `./deploy/phase-6/wipe_client_data.sh --keep-host-seed --yes`

After wiping:
- Re-upload the client DB file to `munero-platform/data/munero.sqlite`
- Re-seed and restart:
  - `cd deploy/phase-4 && docker compose run --rm seed_db`
  - `cd deploy/phase-4 && docker compose up -d --build`

