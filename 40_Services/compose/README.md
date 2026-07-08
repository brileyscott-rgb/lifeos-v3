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

Actual Docker runtime may include legacy/manual containers not owned by this compose file. Run a provenance audit before activation or recreate.

**Do not run build/start/stop/recreate commands from this runbook without a separate approved activation plan.**

Current known drift:

- ~~Legacy `status_api` compose owned `lifeos-status-api` without `localhost:8787` mapping — **RESOLVED**. Status API now owned by this unified compose with `127.0.0.1:8787:8787`.~~
- ~~Manual/unlabeled Action API (no compose labels) — **RESOLVED**. Action API now owned by this unified compose with `127.0.0.1:8788:8788` and `restart: unless-stopped`.~~
- Legacy `n8n` compose project (`40_Services/n8n/docker-compose.yml`) owns a running `n8n_n8n_1` container on `localhost:5678`. n8n workflow activation status is not verified.
- `lifeos_internal` Docker network exists and contains all running containers.

See `docs/superpowers/plans/2026-07-07-docker-runtime-drift-reconciliation-plan.md` for full reconciliation plan.

## Services

| Service | Role | Status (defined in this compose) | Runtime Status |
|---------|------|----------------------------------|----------------|
| `lifeos-status-api` | Read-only status endpoint | **Active** (adopted) | Running from this unified compose — `localhost:8787/health` reachable, read-only |
| `lifeos-action-api` | Capture/review mutation API | **Active** (adopted) | Running from this unified compose — `localhost:8788/health` reachable, read-write |
| `lifeos-n8n` | Workflow automation scaffold | `manual-start-disabled` profile | Running from legacy `n8n` compose — `localhost:5678`, workflow activation not verified |

## Network

- `lifeos_internal` uses `external: true`.
- Activation must later verify/create the network, but this review phase must not run that command.

## Related Control Plane Docs

- `40_Services/docs/Docker_Service_Map.md` — Complete service inventory with ports, data paths, healthchecks, backup needs, risk levels, and future MCP exposure.
- `40_Services/docs/Service_Profiles.md` — Profile definitions (core, automation, memory, ai, observability, experiments) with start order, dependencies, and phase restrictions.
- `40_Services/docs/MCP_Roadmap.md` — MCP server roadmap with read-only-first tools, deny-by-default policy, and V1/V2/V3 tool catalog.
- `40_Services/docs/Observability_Control_Plane.md` — Observability V2 policy defining local-only monitoring, health matrix, alert policy, and dashboard policy. No services installed yet.
- `40_Services/docs/Observability_Runbook.md` — Manual read-only health checks, failure triage steps, activation checklist, and rollback model.

## Observability Status

Observability services (Homepage, Uptime Kuma, Dozzle) are **not yet installed or started**. The Observability Control Plane and Runbook are scaffold-only policy docs. Future activation requires:
- A separate approved activation plan
- Observability compose scaffold creation
- Single-service start with verification
- No Docker socket, no public ingress, no secrets exposure

## Deferrals

- Cloudflare tunnel
- Telegram webhook
- Public ingress
- n8n workflow activation
- AI proposal pipeline
- Controlled file processor
- Telegram bot containerization
- Kubernetes/homelab expansion
