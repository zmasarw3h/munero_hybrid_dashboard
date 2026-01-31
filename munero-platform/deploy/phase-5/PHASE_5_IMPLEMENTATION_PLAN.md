# Phase 5 — VM Provisioning + Deploy (Implementation Plan)

This file turns Phase 5 into an **operator-executable checklist** that is easy to run end-to-end and verify.

**Primary references**
- `munero-platform/DEPLOYMENT_IMPLEMENTATION_PLAN.md` (Phase 5 section)
- `munero-platform/deploy/phase-5/DEPLOY.md` (runbook)
- `munero-platform/deploy/phase-5/smoke.sh` (public smoke tests)

**Scope**
- Implements **Phase 5 only** (VM provisioning + deploy + public smoke tests + rollback snapshot guidance).
- Explicitly **out of scope**: Phase 6 wipe/reset procedures.

---

## A) Repo readiness (make Phase 5 shippable)

Goal: the repo contains everything needed to deploy the Phase 4 stack to a VM, without committing secrets.

- [ ] Clean working tree and review scope: `git diff --stat` (and `git status --porcelain` should be empty)
- [ ] Ensure secrets are not tracked:
  - [ ] `munero-platform/deploy/phase-4/.env` is **not** committed
  - [ ] `munero-platform/deploy/phase-4/.env.caddy` is **not** committed
  - [ ] `munero-platform/data/munero.sqlite` is **not** committed
- [ ] Ensure deploy helper artifacts are present and committed:
  - [ ] `munero-platform/.gitignore` (env + sqlite ignore rules)
  - [ ] `munero-platform/deploy/phase-5/smoke.sh` (recommended: `chmod +x`)
- [ ] (Recommended) Create a deterministic rollback tag for the VM deploy:
  - [ ] `git tag phase-5-deploy-YYYYMMDD`

Optional but recommended validation on your dev machine:
- [ ] `cd munero-platform && ./scripts/phase_gate.sh offline`

---

## B) Provision the VM (CPU-first; GPU optional)

Collect inputs:
- [ ] `DEMO_DOMAIN` (DNS name), `ACME_EMAIL`
- [ ] `OLLAMA_MODEL`
- [ ] Basic Auth credentials (`BASIC_AUTH_USER`, `BASIC_AUTH_PASSWORD`)
- [ ] VM public IP

VM sizing (RAM is driven by `OLLAMA_MODEL`):
- [ ] Choose a VM size that can run your model without OOM (see `munero-platform/deploy/phase-5/DEPLOY.md`).

Provisioning checklist:
- [ ] Create VM
- [ ] Configure firewall/security group:
  - [ ] Allow inbound `80/tcp` and `443/tcp` from the internet
  - [ ] Restrict SSH to your IP (or provider console)
  - [ ] Do **not** expose `3000`, `8000`, or `11434` publicly
- [ ] Install Docker + Docker Compose v2
- [ ] Confirm DNS:
  - [ ] `dig +short "$DEMO_DOMAIN"` returns the VM IP

GPU optional:
- [ ] If using a GPU VM: install NVIDIA drivers + NVIDIA Container Toolkit per provider docs

---

## C) Deploy to the VM (Phase 4 stack)

### C1) Copy repo onto the VM

Pick one:
- [ ] **Git clone** + pin a tag/commit:
  - [ ] `git clone <YOUR_REPO_URL> Munero_Hybrid_Dashboard`
  - [ ] `cd Munero_Hybrid_Dashboard`
  - [ ] `git checkout <DEPLOY_TAG_OR_COMMIT>`
- [ ] **Release artifact** (zip/tar) extracted so the VM has `munero-platform/` at repo root

### C2) Place the seed DB (host file; not committed)

- [ ] Place the DB at: `munero-platform/data/munero.sqlite`
- [ ] Confirm: `ls -lh munero-platform/data/munero.sqlite`

### C3) Configure VM-only env files (do not commit)

From repo root:
- [ ] `cd munero-platform/deploy/phase-4`

Create main env:
- [ ] `cp .env.example .env`
- [ ] `chmod 600 .env`
- [ ] Set at minimum in `.env`:
  - [ ] `DEMO_DOMAIN=<your domain>`
  - [ ] `ACME_EMAIL=<your email>`
  - [ ] `OLLAMA_MODEL=<your model>`
  - [ ] `CORS_ORIGINS=https://<your domain>`
  - [ ] `NEXT_PUBLIC_API_URL=https://<your domain>`

Create Caddy auth env:
- [ ] `cp .env.caddy.example .env.caddy`
- [ ] `chmod 600 .env.caddy`
- [ ] Set:
  - [ ] `BASIC_AUTH_USER=...`
  - [ ] `BASIC_AUTH_PASSWORD=...` (recommended; hash generated at container startup)

### C4) Seed the persistent client DB volume

From `munero-platform/deploy/phase-4`:
- [ ] `docker compose run --rm seed_db`

### C5) Start the stack

From `munero-platform/deploy/phase-4`:
- [ ] `docker compose up -d --build`
- [ ] Watch proxy/TLS logs until certificates are issued:
  - [ ] `docker compose logs -f caddy`

### C6) Pull the Ollama model

From `munero-platform/deploy/phase-4`:
- [ ] `docker compose exec -T ollama ollama pull "$OLLAMA_MODEL"`

---

## D) Public smoke tests (laptop → public URL)

Goal: validate the deployed VM is reachable over HTTPS, protected by Basic Auth, and serving the required endpoints.

From your laptop:
- [ ] Manual:
  - [ ] `curl -fsS -u "$BASIC_AUTH_USER:$BASIC_AUTH_PASSWORD" "https://$DEMO_DOMAIN/health"`
  - [ ] `curl -fsS -u "$BASIC_AUTH_USER:$BASIC_AUTH_PASSWORD" "https://$DEMO_DOMAIN/api/dashboard/test"`
  - [ ] `curl -fsS -u "$BASIC_AUTH_USER:$BASIC_AUTH_PASSWORD" "https://$DEMO_DOMAIN/api/chat/test"`
- [ ] Scripted:
  - [ ] `DEMO_DOMAIN=... BASIC_AUTH_USER=... BASIC_AUTH_PASSWORD=... bash munero-platform/deploy/phase-5/smoke.sh`

If these fail:
- [ ] Re-check DNS + firewall (`80/443`)
- [ ] `docker compose logs -f caddy backend frontend ollama`
- [ ] Confirm the model is pulled (`ollama pull`) and `ollama` has enough RAM/VRAM

---

## E) Rollback point (required before client onboarding)

After public smoke tests pass:
- [ ] Take a **VM snapshot** (preferred) and record snapshot ID
- [ ] Record the deployed repo identifier:
  - [ ] Tag/commit hash deployed
  - [ ] `DEMO_DOMAIN`, `OLLAMA_MODEL`

Phase 5 is considered complete when:
- [ ] The VM deploy runbook is accurate (`munero-platform/deploy/phase-5/DEPLOY.md`)
- [ ] Public smoke tests pass (manual or `munero-platform/deploy/phase-5/smoke.sh`)
- [ ] A rollback snapshot exists and is recorded
