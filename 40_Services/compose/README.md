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

## Services

| Service | Role | Status |
|---------|------|--------|
| `lifeos-status-api` | Read-only status endpoint | Defined, not started |
| `lifeos-action-api` | Capture/review mutation API | Defined, not started |
| `lifeos-n8n` | Workflow automation scaffold | `manual-start-disabled` profile |

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
