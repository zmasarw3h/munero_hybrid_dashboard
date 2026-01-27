# Phase 0 Deployment Inputs (Fill In)

## Locked decisions
- Trial data policy: client data stored on demo VM volume; wipe within 24 hours of trial end (or on request).
- Tenancy: single client stack on a dedicated VM for the trial; tear down after trial.
- Model: qwen2.5-coder:3b (upgrade to 7b or GPU VM if needed).
- Access control: public HTTPS with Basic Auth via Caddy.
- Data format: prepared munero.sqlite mounted as client_data volume.

## Required inputs
- VM public IP: TBD
- Demo domain: demo-client1.yourdomain.com
- Chosen model: qwen2.5-coder:3b
- munero.sqlite location (host path): TBD (place under munero-platform/deploy/)
