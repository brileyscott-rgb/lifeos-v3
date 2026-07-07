# LifeOS Docker Compose Baseline — Static Validation Runbook

## Purpose

Unified local-only Docker Compose baseline for LifeOS services.

## Current Host Tooling

- `docker-compose` v1.29.2 is available on this host.
- `docker compose` v2 plugin is **not** available on this host.

## Allowed Static Validation Command

```bash
docker-compose -f 40_Services/compose/lifeos.yaml config
```

## Explicitly Forbidden in Baseline Phase

```bash
docker-compose build
docker-compose pull
docker-compose up
docker-compose start
docker-compose restart
docker-compose run
docker-compose create
docker run
docker build
docker pull
```

## State

This baseline defines Docker-capable services only. It does not start, build, pull, create, or migrate services. Active Telegram bot remains a systemd user service. Active Telegram contract remains `localhost:8788` / `localhost:8787` until a separate activation plan.

## Runtime Drift Warning

Actual Docker runtime may include legacy/manual containers not owned by this compose file. Unified compose is not yet the owner of existing containers. Run a provenance audit before activation or recreate.

**Do not run build/start/stop/recreate commands from this runbook without a separate approved activation plan.**

Current known drift:

- Legacy `status_api` compose project (`40_Services/status_api/docker-compose.yml`) owns a running `lifeos-status-api` container that lacks `127.0.0.1:8787` host mapping — internal-only on port 8787/tcp.
- A manual/unlabeled Action API container (no compose labels) serves `localhost:8788` and processes live Telegram captures. No restart policy. Do not touch.
- Legacy `n8n` compose project (`40_Services/n8n/docker-compose.yml`) owns a running `n8n_n8n_1` container on `localhost:5678`. n8n workflow activation status is not verified.
- `lifeos_internal` Docker network exists and contains all three containers.

See `docs/superpowers/plans/2026-07-07-docker-runtime-drift-reconciliation-plan.md` for full reconciliation plan.

## Services

| Service | Role | Status (defined in this compose) | Runtime Status |
|---------|------|----------------------------------|----------------|
| `lifeos-status-api` | Read-only status endpoint | Defined, not started | Running from legacy `status_api` compose — no `localhost:8787` mapping |
| `lifeos-action-api` | Capture/review mutation API | Defined, not started | Running from manual container (no compose labels) — serves `localhost:8788` |
| `lifeos-n8n` | Workflow automation scaffold | `manual-start-disabled` profile | Running from legacy `n8n` compose — `localhost:5678`, workflow activation not verified |

## Network

- `lifeos_internal` uses `external: true`.
- Activation must later verify/create the network, but this review phase must not run that command.

## Deferrals

- Cloudflare tunnel
- Telegram webhook
- Public ingress
- n8n workflow activation
- AI proposal pipeline
- Controlled file processor
- Telegram bot containerization
- Kubernetes/homelab expansion
