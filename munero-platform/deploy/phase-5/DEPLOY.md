# Phase 5 — VM Provisioning + Deploy Runbook (CPU‑First; GPU Optional)

This runbook deploys the **Phase 4** Docker Compose stack (FastAPI + Next.js + Ollama) to a **public VM** behind **HTTPS + Basic Auth** (Caddy).

**Artifacts used (Phase 4):**
- `munero-platform/deploy/phase-4/docker-compose.yml`
- `munero-platform/deploy/phase-4/Caddyfile`
- `munero-platform/deploy/phase-4/.env.example`
- `munero-platform/deploy/phase-4/.env.caddy.example`
- `munero-platform/deploy/phase-4/seed-db.sh`
- `munero-platform/deploy/phase-4/caddy-entrypoint.sh`

## 0) Inputs (collect these first)
- VM public IP
- `DEMO_DOMAIN` (example: `demo-client1.yourdomain.com`) + DNS A record pointing to the VM IP
- `ACME_EMAIL` (for Let’s Encrypt)
- `OLLAMA_MODEL` (example: `qwen2.5-coder:3b` or `qwen2.5-coder:7b`)
- `CORS_ORIGINS` (recommended: `https://$DEMO_DOMAIN`)
- `NEXT_PUBLIC_API_URL` (recommended: `https://$DEMO_DOMAIN`)
- Basic Auth credentials (`BASIC_AUTH_USER` + `BASIC_AUTH_PASSWORD`)
- Seed DB file on the VM: `munero-platform/data/munero.sqlite` (**do not commit**)

## 1) VM sizing guidance (CPU‑first)
Rule of thumb: **model size drives RAM**, and CPU inference can be slow on tiny VMs.

- **Baseline (recommended)**: 8 vCPU / **16 GB RAM** / 100 GB disk.
- **Smaller model (`...:3b`)**: often usable with ~8–12 GB RAM (plus OS + app overhead).
- **Larger model (`...:7b`)**: plan for **16–24 GB RAM** on CPU to avoid OOM/restarts.
- **GPU (optional)**: if latency is unacceptable, move to a GPU VM; ensure VRAM can hold the model.

## 2) VM provisioning checklist
On a fresh Ubuntu VM (or similar):

1. Install Docker + Docker Compose v2.
2. Firewall / security group:
   - inbound `80/tcp` and `443/tcp` from the internet
   - do **not** expose `8000`, `3000`, or `11434` to the internet
   - SSH restricted to your IP (or provider console access)
3. Ensure the VM has enough disk for:
   - `ollama_models` volume (model files)
   - `client_data` volume (SQLite DB copy)
   - `caddy_data` (certificates)
4. Confirm DNS is correct before deploy:
   - `dig +short "$DEMO_DOMAIN"` should return the VM IP

Provisioning helpers (repo artifacts):
- `munero-platform/deploy/phase-5/VM_PROVISION.md` (provider-agnostic checklist + Ubuntu examples)
- `munero-platform/deploy/phase-5/vm-bootstrap-ubuntu.sh` (Docker + Compose v2 install helper)
- `munero-platform/deploy/phase-5/vm-preflight.sh` (DNS + basic readiness checks)

GPU optional:
- Install NVIDIA drivers + NVIDIA Container Toolkit per your provider’s guidance.

## 3) Copy the repo to the VM
Pick one:

**Option A: git clone**
```bash
git clone <YOUR_REPO_URL> Munero_Hybrid_Dashboard
cd Munero_Hybrid_Dashboard
# Optional but recommended: pin a tag/commit for rollback
# git checkout <DEPLOY_TAG_OR_COMMIT>
```

**Option B: release artifact**
- Copy a tarball/zip to the VM and extract it (result should contain `munero-platform/` at the repo root).

## 4) Place the client seed DB (host file; not committed)
1. Create the directory if needed:
```bash
mkdir -p munero-platform/data
```

2. Place the DB at:
- `munero-platform/data/munero.sqlite`

3. Confirm:
```bash
ls -lh munero-platform/data/munero.sqlite
```

## 5) Configure env files (VM-only; do not commit secrets)
All commands below assume:
- `cd munero-platform/deploy/phase-4`

1. Create the main env file:
```bash
cp .env.example .env
chmod 600 .env
```

Update at minimum in `.env`:
- `DEMO_DOMAIN=demo-client1.yourdomain.com`
- `ACME_EMAIL=admin@yourdomain.com`
- `OLLAMA_MODEL=qwen2.5-coder:3b` (or `...:7b`)
- `CORS_ORIGINS=https://demo-client1.yourdomain.com`
- `NEXT_PUBLIC_API_URL=https://demo-client1.yourdomain.com`

Notes:
- `CORS_ORIGINS` supports comma-separated origins or a JSON list (see `backend/app/core/config.py`).
- Keep `NEXT_PUBLIC_API_URL` as **https** to avoid mixed-content issues behind Caddy.

2. Create the Caddy Basic Auth env file:
```bash
cp .env.caddy.example .env.caddy
chmod 600 .env.caddy
```

Set:
- `BASIC_AUTH_USER`
- `BASIC_AUTH_PASSWORD` (recommended; the container generates a bcrypt hash at startup)

## 6) First-time seed (populate the `client_data` volume)
From `munero-platform/deploy/phase-4`:

```bash
docker compose run --rm seed_db
```

This copies `../../data/munero.sqlite` into the persistent named volume `client_data` at `/data/munero.sqlite`.

## 7) Bring up the stack
From `munero-platform/deploy/phase-4`:

```bash
docker compose up -d --build
```

Watch logs if TLS or routing looks wrong:
```bash
docker compose logs -f caddy
```

## 8) Pull the Ollama model on the VM
The `ollama` container does not auto-pull models. Pull the model explicitly:

```bash
MODEL="$(grep -E '^OLLAMA_MODEL=' .env | cut -d= -f2-)"
docker compose exec -T ollama ollama pull "$MODEL"
```

## 9) Public smoke tests (from your laptop)
All routes require Basic Auth.

Manual (replace variables):
```bash
curl -fsS -u "$BASIC_AUTH_USER:$BASIC_AUTH_PASSWORD" "https://$DEMO_DOMAIN/health"
curl -fsS -u "$BASIC_AUTH_USER:$BASIC_AUTH_PASSWORD" "https://$DEMO_DOMAIN/api/dashboard/test"
curl -fsS -u "$BASIC_AUTH_USER:$BASIC_AUTH_PASSWORD" "https://$DEMO_DOMAIN/api/chat/test"
```

Scripted:
- See `munero-platform/deploy/phase-5/smoke.sh`
  - Example:
    ```bash
    DEMO_DOMAIN=demo-client1.yourdomain.com \
    BASIC_AUTH_USER=... \
    BASIC_AUTH_PASSWORD=... \
    bash munero-platform/deploy/phase-5/smoke.sh
    ```

## 10) Rollback point (before client onboarding)
After smoke tests pass:

1. **Snapshot the VM** (recommended) so you can roll back instantly.
2. Record a rollback identifier in your notes:
   - VM snapshot name/ID
   - repo tag/commit deployed
   - `OLLAMA_MODEL` used

If you can’t snapshot, at least deploy from a **pinned tag/commit** so a redeploy is deterministic.

---

Out of scope for Phase 5:
- Wipe/reset procedures (Phase 6).
