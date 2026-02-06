# Phase 5 — VM Provisioning (CPU‑First; GPU Optional)

This document makes **Part B (Provision the VM)** of `PHASE_5_IMPLEMENTATION_PLAN.md` operator-executable.

Scope:
- VM provisioning only (no deploy steps).
- Provider-agnostic, with concrete Ubuntu examples.

Non-goals:
- Terraform/Pulumi automation (out of scope for Phase 5).
- Phase 6 wipe/reset procedures.

---

## 0) Collect inputs

You will need:
- `DEMO_DOMAIN` (DNS name) and `ACME_EMAIL`
- `OLLAMA_MODEL`
- `BASIC_AUTH_USER` and `BASIC_AUTH_PASSWORD`
- VM public IP

---

## 1) Choose VM sizing (CPU-first)

Model size drives RAM:
- Baseline (recommended): **8 vCPU / 16 GB RAM / 100 GB disk**
- Smaller model (`...:3b`): often usable with ~8–12 GB RAM
- Larger model (`...:7b`): plan for **16–24 GB RAM** on CPU

If latency is unacceptable, upgrade to a GPU VM (see GPU section below).

---

## 2) Create the VM

Provider-agnostic guidance:
- OS image: **Ubuntu 22.04 LTS** (or similar)
- Attach enough disk for:
  - Docker images
  - `ollama_models` volume (models can be multiple GB)
  - `client_data` volume (SQLite DB + growth)
  - `caddy_data` (TLS certificates)

---

## 3) Configure firewall / security group

Required:
- Allow inbound `80/tcp` and `443/tcp` from the internet
- Restrict SSH (`22/tcp`) to your IP (or use provider console access)
- Do **not** expose `3000`, `8000`, or `11434` publicly

### Ubuntu example (UFW)

Run on the VM (adjust `YOUR_IP`):
```bash
YOUR_IP="<your.public.ip.addr>"

sudo ufw default deny incoming
sudo ufw default allow outgoing

sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow from "${YOUR_IP}" to any port 22 proto tcp

sudo ufw enable
sudo ufw status verbose
```

Safety note: enabling a firewall can lock you out if the SSH rule is wrong. Prefer keeping a provider console session open while applying rules.

---

## 4) Install Docker + Docker Compose v2

On Ubuntu, the repo includes a helper script that installs:
- Docker Engine
- Compose v2 plugin (`docker compose ...`)

From the repo root on the VM:
```bash
bash munero-platform/deploy/phase-5/vm-bootstrap-ubuntu.sh
```

Then verify:
```bash
docker version
docker compose version
```

If the script adds your user to the `docker` group, log out/in (or start a new SSH session) for it to take effect.

---

## 5) Confirm DNS

From your laptop (or from the VM), verify the A record resolves to the VM IP:
```bash
DEMO_DOMAIN="demo-client1.yourdomain.com"
EXPECTED_IP="<vm.public.ip>"
bash munero-platform/deploy/phase-5/vm-preflight.sh
```

---

## 6) GPU optional (only if using a GPU VM)

Install per provider docs:
- NVIDIA drivers
- NVIDIA Container Toolkit

Suggested verification:
```bash
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.3.2-base-ubuntu22.04 nvidia-smi
```

---

## 7) Provisioning checklist (Part B)

- [ ] Create VM (CPU-first; GPU optional)
- [ ] Firewall/security group configured (`80/443` open; SSH restricted; no `3000/8000/11434`)
- [ ] Docker + Docker Compose v2 installed
- [ ] DNS A record points to VM IP (`DEMO_DOMAIN` resolves correctly)
- [ ] (GPU only) NVIDIA drivers + container toolkit installed and verified

