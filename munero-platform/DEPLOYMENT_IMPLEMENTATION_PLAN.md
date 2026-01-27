# Munero Platform — Self‑Hosted Client Demo Deployment Implementation Plan

This document is a **self‑contained, end‑to‑end implementation plan** to deploy the Munero full‑stack dashboard + AI copilot (FastAPI + Next.js + Ollama) as a **private demo environment you operate**, so a client can access it easily for feedback while keeping their data inside your hosted stack.

---

## 0) Safety Rails (Prevent Regressions)

The goal is to make every phase **safe, reviewable, and reversible**, so deployment work can’t “ruin” the rest of the project.

### 0.1 Baseline snapshot (do once)
- Start from a clean working tree: `git status` should show no pending changes.
- Create a baseline commit + tag before any deployment work:
  - `git add -A && git commit -m "baseline: before deployment work"`
  - `git tag demo-baseline-YYYYMMDD`

### 0.2 One phase = one branch (recommended)
- Create a new branch for each phase (or use `git worktree` for even stronger isolation):
  - `git switch -c deploy/phase-1`
- Keep changes scoped:
  - Prefer adding new deploy artifacts under `munero-platform/deploy/`.
  - Only touch existing code for **env/config wiring** needed by that phase (avoid refactors and dependency upgrades).

### 0.3 Phase gates (must pass before moving on)
- Always review scope: `git diff --stat` should show only expected files.
- Run the automated gate:
  - `cd munero-platform && ./scripts/phase_gate.sh offline`
  - If services are running locally: `cd munero-platform && ./scripts/phase_gate.sh smoke`
- Commit after a green gate: `git add -A && git commit -m "phase X: <short description>"`

### 0.4 Rollback / recovery
- Abandon a phase entirely: `git switch main && git branch -D deploy/phase-X`
- Return to the known-good baseline: `git reset --hard demo-baseline-YYYYMMDD`

### 0.5 Codex phase prompt template (copy/paste)
```text
Implement Phase <X> only from munero-platform/DEPLOYMENT_IMPLEMENTATION_PLAN.md.

Constraints:
- Only implement Phase <X>; do not start Phase <X+1>.
- No unrelated refactors; no dependency upgrades.
- Keep deploy artifacts under munero-platform/deploy/ unless the phase explicitly requires otherwise.
- After changes: show `git diff --stat`, run `cd munero-platform && ./scripts/phase_gate.sh offline` (and `smoke` if backend is running), then STOP.
```

## 1) Goals, Constraints, and Definition of Done

### Goals
- Provide the client with a single URL (e.g., `https://demo-client1.yourdomain.com`) to access:
  - the dashboard UI
  - the AI assistant that generates SQL + charts based on private client data
- Ensure the LLM remains **fully self‑hosted** (no third‑party model API calls).
- Make the environment easy to stand up, reset, and tear down.

### Constraints (from requirements)
- **LLM must be fully self‑hosted** (Ollama).
- **Cannot deploy in the client’s environment** (you host it).
- No “high need” for strict security beyond preventing private client data from leaking outside the stack.

### Definition of Done (DoD)
- Client can log in and use the app via HTTPS from their network.
- Backend can reach Ollama and generate responses reliably.
- Database/data is isolated per client environment (at minimum: separate DB + volume).
- A “wipe/reset” procedure exists and works (removes client data + chat artifacts).
- Basic operational checks exist (health endpoints and a simple smoke test).

---

## 2) Recommended Deployment Shape (Fastest + Practical)

### Target architecture (single‑VM, containerized)
- **One VM** hosts all services via Docker Compose (**CPU‑first to minimize cost**, with a GPU upgrade path if needed):
  - `frontend` (Next.js)
  - `backend` (FastAPI)
  - `ollama` (local inference)
  - `caddy` (reverse proxy + TLS + Basic Auth)
- Only **ports 80/443** are reachable from the internet.
- Ollama is **never exposed publicly**; only the backend can talk to it on the private Docker network.

### Why this approach
- Minimal moving parts (no Kubernetes required).
- Simple for trials: copy data in, run, get feedback, wipe, repeat.
- Keeps private data and prompts inside your controlled environment.

---

## 3) Phase 0 — Locked Decisions (Recommended + Lowest Cost)

This plan is now “ready to execute” with the following default choices (you can change them later, but these are the recommended least‑cost defaults).

### 3.1 Trial mode parameters (chosen)
- **Trial data policy (easiest):** use the client dataset “as provided” (no anonymization workflow), store it only on the demo VM volume, and **wipe it within 24 hours of trial end (or immediately on request)**.
- **Tenancy:** **1 stack for this client** (single Docker Compose project) on **1 dedicated VM** for the duration of the trial; tear down the VM after the trial to stop costs.
- **Model (cost-first):** default to a smaller CPU-friendly model, `qwen2.5-coder:3b` via `OLLAMA_MODEL`. If quality is insufficient, bump to `qwen2.5-coder:7b`. If latency is still too high, switch the VM to a GPU instance.
- **Access control (least friction/cost):** public HTTPS + **Basic Auth in Caddy** (no VPN requirement for client users).
- **Data format (easiest):** ship a prepared `munero.sqlite` and mount it as the `client_data` volume (no ingestion step during deploy).

### 3.2 Hosting provider & VM size (chosen)
- **Provider (cost-first):** use the lowest‑cost reputable VPS provider you’re comfortable with (monthly billing), in a region close to the client.
- **VM type:** CPU VM to start (lowest cost).
- **CPU/RAM:** 8 vCPU / 16GB RAM (good baseline for API + Next.js + a small Ollama model).
- **Disk:** 100GB (models + SQLite + logs).
- **Upgrade trigger:** if the client experience is too slow, switch to a GPU VM (NVIDIA T4 16GB is a common “cheapest usable” baseline).

### 3.3 DNS + domain (chosen)
- Use `demo-client1.yourdomain.com` (or similar) pointing to the VM public IP.
- Use Caddy auto‑HTTPS (Let’s Encrypt) for certificates.

Deliverable of Phase 0:
- A short “deployment inputs” note: VM public IP, demo domain, chosen model, and the location of the `munero.sqlite` file to mount.

### Phase 0 gate (stop here)
- Review scope: `git diff --stat` (ideally doc-only changes at this point).
- Commit Phase 0 documentation decisions: `git add -A && git commit -m "phase 0: lock demo decisions"`

---

## 4) Phase 1 — Repo Changes (Make the App Container‑Ready)

This phase is about removing assumptions that only work on your laptop and making configuration fully environment‑driven.

### 4.1 Backend configuration hardening (env‑first)
Add/confirm environment variables and ensure the code actually uses them:
- `OLLAMA_BASE_URL` (container: `http://ollama:11434`)
- `OLLAMA_MODEL` (e.g., `qwen2.5-coder:7b`)
- `CORS_ORIGINS` (include the demo domain)
- `DB_FILE` or `DB_PATH` (path inside container volume, not a local absolute path)
- `DEBUG` (false in demo)

**Known codebase note:** `munero-platform/backend/app/core/database.py` currently builds `DB_PATH` from the filesystem relative path and prints it; update this to use the settings/env value so containers can mount data consistently.

### 4.2 Logging policy (private data)
Even if you’re not doing “strict security”, you should ensure private data isn’t accidentally stored long‑term:
- Avoid logging full prompts and full query results.
- Keep operational logs (errors, timings) only.
- If you need troubleshooting, add an explicit `DEBUG_LOG_PROMPTS=false` toggle and keep it off by default.

### 4.3 Health checks & smoke tests
Ensure these endpoints work without special setup:
- `GET /health` returns DB + LLM status (already present per README).
- `GET /api/chat/test` (or equivalent) verifies Ollama connectivity.

Deliverables of Phase 1:
- Backend uses env vars for DB + Ollama consistently.
- Logging defaults do not persist private prompts/responses.
- Health checks/smoke tests are reliable.

Acceptance criteria:
- Backend runs locally with `OLLAMA_BASE_URL` set to a non‑localhost URL (simulating container networking).

### Phase 1 gate (must be green before Phase 2)
- Review scope: `git diff --stat` (only config/env wiring + docs).
- Run: `cd munero-platform && ./scripts/phase_gate.sh offline`
- Commit: `git add -A && git commit -m "phase 1: container-ready config"`

---

## 5) Phase 2 — Containerize the Stack

### 5.1 Backend Dockerfile
Create a Dockerfile that:
- installs Python deps from `backend/requirements.txt`
- runs `uvicorn main:app --host 0.0.0.0 --port 8000`
- reads `.env` or container env vars

### 5.2 Frontend Dockerfile
Create a Dockerfile (multi‑stage recommended) that:
- installs Node deps
- builds the Next.js app
- runs `next start` on port `3000`

### 5.3 Add `.dockerignore`
Ensure you’re not copying local caches into images:
- `.next/`, `node_modules/`, `venv/`, `__pycache__/`, `.mypy_cache/`, etc.

Deliverables of Phase 2:
- `backend` and `frontend` can be built as images locally.

Acceptance criteria:
- `docker build` succeeds for both images without manual steps.

### Phase 2 gate (must be green before Phase 3)
- Review scope: `git diff --stat` (Docker + deploy files; minimal code changes).
- Run: `cd munero-platform && ./scripts/phase_gate.sh offline`
- Commit: `git add -A && git commit -m "phase 2: containerize backend + frontend"`

---

## 6) Phase 3 — Compose the Demo Environment (Local First)

### 6.1 Compose services
Create a `docker-compose.yml` (typically in a `deploy/` folder) with:
- `ollama` (internal only, persistent model volume)
- `backend` (connects to `ollama`, mounts the client DB volume)
- `frontend` (served behind reverse proxy)
- `caddy` (only public entrypoint: `80/443`)

### 6.2 Private networking
- All services in one private Compose network.
- Do **not** publish Ollama’s port to the host.

### 6.3 Persistent volumes
At minimum:
- `ollama_models` → `/root/.ollama`
- `client_data` → where the SQLite DB lives (or where you ingest CSVs)

### 6.4 Environment files
Create:
- `.env.example` with placeholders
- `.env.client1` (not committed) with real values for that client trial

Deliverables of Phase 3:
- `docker compose up -d` boots all services locally.

Acceptance criteria:
- Visiting `http://localhost` (via Caddy) serves frontend.
- AI endpoint works and returns a valid response using Ollama.

### Phase 3 gate (must be green before Phase 4)
- Review scope: `git diff --stat` (Compose + proxy config + env templates).
- Run: `cd munero-platform && ./scripts/phase_gate.sh offline`
- If you brought services up locally: `cd munero-platform && ./scripts/phase_gate.sh smoke`
- Commit: `git add -A && git commit -m "phase 3: local docker compose demo stack"`

---

## 7) Phase 4 — Edge Routing + HTTPS + Basic Auth

### 7.1 Reverse proxy routing
Recommended routing rules:
- `/api/*` → `backend:8000`
- everything else → `frontend:3000`

### 7.2 TLS certificates
With Caddy:
- Provide email and domain.
- Caddy obtains/renews certs automatically.

### 7.3 Basic Auth (fastest)
- Use Basic Auth to restrict access to client users.
- Rotate passwords as needed.

Deliverables of Phase 4:
- A Caddyfile (or Nginx config) that enforces HTTPS + auth and routes correctly.

Acceptance criteria:
- Client hits `https://demo-client1.yourdomain.com` and is prompted for credentials.

### Phase 4 gate (must be green before Phase 5)
- Review scope: `git diff --stat` (proxy/auth config only).
- Run: `cd munero-platform && ./scripts/phase_gate.sh offline`
- Commit: `git add -A && git commit -m "phase 4: https + basic auth routing"`

---

## 8) Phase 5 — Provision the VM and Deploy (CPU‑First; GPU Optional)

### 8.1 VM provisioning checklist
- Install Docker + Docker Compose v2.
- If using a GPU VM: install NVIDIA drivers and NVIDIA Container Toolkit (for GPU access).
- Open firewall/security group:
  - allow inbound `80/443`
  - allow SSH only from your IP (or via provider console)
- Attach enough disk space.

### 8.2 Deploy procedure (manual runbook)
1. Copy repo (or a release artifact) to the VM.
2. Create `.env.client1` on the VM (do not commit secrets).
3. Bring up the stack:
   - `docker compose up -d --build`
4. Pull the model (if not automatic):
   - run `ollama pull <model>` inside the `ollama` container (or an init step).
5. Run smoke tests:
   - `GET /health`
   - `POST /api/chat/` with a simple prompt

### 8.3 Data load procedure
**Chosen:** ship a prepared SQLite DB and mount it as the `client_data` volume.

Optional alternative (if you need to rebuild DB on the VM):
- Ship CSV to the VM and run the ingestion script in the backend container.

Deliverables of Phase 5:
- Deployed demo environment reachable from the internet (HTTPS + Basic Auth).
- Client data loaded and validated.

Acceptance criteria:
- Dashboard endpoints return data from the client dataset.
- AI endpoint returns chart suggestions/SQL on real client data.

### Phase 5 gate (before sharing with client)
- Confirm the VM deploy runbook is accurate and complete.
- Run smoke tests against the deployed URL (not just localhost): `GET /health`, `GET /api/dashboard/test`, `GET /api/chat/test`.
- Snapshot a rollback point (tag or VM snapshot) before onboarding the client.

---

## 9) Phase 6 — Data Handling & Reset Workflow

### 9.1 Data retention policy (practical)
- Keep only the data required for the demo.
- **Chosen:** wipe within **24 hours** of trial end (or immediately on request).

### 9.2 Wipe/reset procedure (must-have)
Implement a repeatable reset:
- Stop the stack.
- Remove/replace the `client_data` volume (or delete the SQLite file).
- Optionally wipe any uploaded files or cached query history.

Deliverables of Phase 6:
- A script/runbook: `wipe_client_data.sh` (or `make wipe`) and instructions.

Acceptance criteria:
- After wipe, the system returns to a clean state and requires data re-ingest.

### Phase 6 gate (must be green before Phase 7)
- Validate wipe/reset end-to-end (stop → wipe → restart → clean state).
- Commit: `git add -A && git commit -m "phase 6: wipe/reset workflow"`

---

## 10) Phase 7 — Minimal Observability & Supportability

Even for a demo, you need basic visibility so you can respond quickly.

### 10.1 Logs
- `docker compose logs -f` should show:
  - backend request errors
  - ollama failures/timeouts
  - proxy errors

### 10.2 Monitoring (lightweight)
**Chosen (free/minimal):**
- Provider VM monitoring for CPU/RAM/disk.
- A free external uptime check that pings `/health`.

### 10.3 Performance knobs
Document how to tune:
- model choice
- context size (if applicable)
- timeouts (`LLM_TIMEOUT`)
- concurrency limits (Uvicorn workers, etc.)

Deliverables of Phase 7:
- Short “Ops Quickstart” section: common commands, restart, view logs.

Acceptance criteria:
- You can detect and diagnose: “Ollama down”, “DB missing”, “frontend not reachable”.

### Phase 7 gate (must be green before Phase 8)
- Confirm logs + restart procedures work in one copy/paste runbook.
- Commit: `git add -A && git commit -m "phase 7: demo ops runbook"`

---

## 11) Phase 8 — Client Trial Workflow

### 11.1 Onboarding
Provide the client:
- URL
- credentials
- a short “how to use” guide (example questions + expected outputs)

### 11.2 Feedback capture
**Chosen (least effort/cost):** a dedicated email (or Slack) thread for feedback + a weekly check-in.

### 11.3 Change management
For trial stability:
- Prefer scheduled updates (e.g., daily at 6pm).
- Keep a changelog of trial tweaks.

Deliverables of Phase 8:
- Client onboarding message/template.
- Feedback intake mechanism.

Acceptance criteria:
- Client can complete a scripted set of 5–10 queries without assistance.

### Phase 8 gate (before sending access)
- Send a test onboarding message to yourself and verify the steps are complete.
- Confirm credentials rotation + revoke process is documented.

---

## 12) Phase 9 — Teardown / End of Trial

At trial end:
- Export any approved, non-sensitive feedback/metrics.
- Wipe client data (per your policy).
- Shut down or re-purpose the VM.
- Document lessons learned and next steps for production readiness.

Deliverables of Phase 9:
- Teardown checklist completed (including wipe confirmation).

### Phase 9 gate (done)
- Confirm client data wiped per policy and VM is stopped/deleted to stop billing.

---

## 13) Suggested Timeline (Fast Path)

Assuming one engineer and minimal surprises:
- Phase 0: 0.5 day
- Phase 1: 0.5–1 day
- Phase 2: 0.5–1 day
- Phase 3–4: 0.5–1 day
- Phase 5: 0.5 day
- Phase 6–8: 0.5–1 day

**Total:** ~3–5 working days for a solid client demo.

---

## 14) Risks & Mitigations

### Latency / cost surprises
- Mitigation: start with smaller model or a stronger GPU; test with client‑like query volume.

### Model pull / network restrictions
- Mitigation: pre-pull models; bake model into volume snapshot; keep a documented “model bootstrap” step.

### Data leakage via logs
- Mitigation: default to not logging prompts/results; scrub exception traces if they include payloads.

### Container path mismatches for SQLite
- Mitigation: make DB path configurable and mount consistently via volume.

---

## 15) Deliverables Checklist (What You Should End Up With in Repo)

Recommended new/updated items:
- `deploy/docker-compose.yml`
- `deploy/Caddyfile`
- `deploy/.env.example`
- `deploy/DEPLOY.md` (VM setup + runbook)
- `deploy/wipe_client_data.sh`
- `scripts/phase_gate.sh` (per-phase regression gate)
- `.gitignore` updated to prevent committing `.env.*` (while allowing `.env.example`)
- Backend updates to use env for DB path + Ollama URL
- Frontend configured for production API base path (ideally same origin via proxy)

---

## 16) “Good Enough” Security Baseline (Low Friction)

Given your stated constraints, this is the minimum sensible baseline:
- HTTPS everywhere (Caddy).
- Basic Auth access only (no VPN requirement).
- No public Ollama port.
- Minimal logging + short retention.
- Per-client isolated DB/volume and a wipe procedure.

If later you want to harden without major architecture changes:
- Move auth into the app (JWT/SSO).
- Add IP allowlisting.
- Encrypt volumes at rest (provider-managed).
- Add audit logging (without prompt content).
