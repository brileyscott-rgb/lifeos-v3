# LifeOS Observability Control Plane V2

> Scaffold-only. No services installed, started, stopped, or migrated.
> This document defines the observability policy before any implementation.

## Purpose

Observability V2 defines local-only monitoring and service visibility for
LifeOS before MCP, Qdrant, AI services, n8n automation expansion, or
public ingress. It establishes what to monitor, how to measure health,
and what alerting policy applies — all before installing any observability
services.

## Current Observability Sources

These read-only sources are available today without any new services:

| Source | Type | Access |
|--------|------|--------|
| Status API `/health` | HTTP endpoint | `curl -fsS http://localhost:8787/health` |
| Status API `/status` | HTTP endpoint | `curl -fsS http://localhost:8787/status` |
| Action API `/health` | HTTP endpoint | `curl -fsS http://localhost:8788/health` |
| `lifeos_services.py` | Python script | `python3 40_Services/scripts/lifeos_services.py --text` |
| `lifeos_observability.py` | Python script | `python3 40_Services/scripts/lifeos_observability.py --text` |
| `docker ps` | CLI | Docker daemon required |
| `systemctl --user status` | CLI | systemd user scope |
| Event log validity | Via Status API `/status` | `event_log_valid` field |
| Capture queue counts | Via Status API `/status` | `pending_captures`, `approved_unprocessed_captures` |

## Proposed Observability Stack

Documented for future activation. None are installed yet.

| Service | Purpose | Why | Status |
|---------|---------|-----|--------|
| **Homepage** | Dashboard landing page | Single pane linking all LifeOS services | Not installed |
| **Uptime Kuma** | Uptime checks and local alerts | HTTP health checks + notification rules | Not installed |
| **Dozzle** | Container logs viewer | Read-only log tailing, no Docker socket write | Not installed |
| Glances (optional later) | System metrics | CPU, memory, disk, network | Not installed |
| Prometheus/Grafana (optional later) | Metrics collection | Only after basic monitoring is stable | Not installed |

## Service Health Matrix

### API Health Checks

| Service | Health Source | Expected Healthy | Local URL | Alert Threshold | Risk |
|---------|--------------|-----------------|-----------|-----------------|------|
| `lifeos-status-api` | `GET /health` | `{"status": "ok", "mode": "read_only"}` | `http://localhost:8787/health` | Down for > 1m | Low |
| `lifeos-action-api` | `GET /health` | `{"status": "ok", "mode": "read_write"}` | `http://localhost:8788/health` | Down for > 1m | Medium |
| n8n | HTTP 200 on port 5678 | Responding on localhost | `http://localhost:5678` | Down for > 5m | Medium |

### System Health Checks

| Service | Health Source | Expected Healthy | Check Command | Alert Threshold | Risk |
|---------|--------------|-----------------|---------------|-----------------|------|
| Telegram bot | systemd status | active (running) | `systemctl --user status lifeos-telegram-bot.service` | Inactive > 1m | Low |
| ChromaDB | container status | Running | `docker ps` filter | Down for > 10m | Low |
| Git dirty | `git status --short` | Clean or known files | `lifeos_services.py` | Dirty > 10 files | Low |
| Disk usage | `df -h /` | < 90% | `lifeos_services.py` | >= 90% | Medium |
| Event log | Status API `event_log_valid` | `true` | `lifeos_observability.py` | Invalid | Medium |
| Capture pending | Status API `pending_captures` | < 10 | `lifeos_observability.py` | >= 10 | Low |

## Alert Policy

### Safe Alert Types (Allowed)

These alert conditions are safe to raise as notifications:

- **service_down** — A core service is unreachable
- **unhealthy_container** — Docker health check reports unhealthy
- **restart_loop** — Container restart count exceeds threshold
- **disk_usage_warning** — Root disk usage >= 90%
- **event_log_invalid** — Event log contains malformed entries
- **pending_capture_count_high** — Pending captures >= 10
- **n8n_unreachable** — n8n not responding on localhost:5678
- **action_api_unreachable** — Action API not responding
- **status_api_unreachable** — Status API not responding
- **telegram_inactive** — Telegram bot not running

### Forbidden Alert Behavior

- **No auto-restart** — Alerts must not trigger container/service restarts
- **No auto-delete** — Alerts must not trigger pruning or cleanup
- **No auto-prune** — Alerts must not trigger `docker prune`
- **No auto-commit** — Alerts must not trigger git commits
- **No direct vault writes** — Alerts must not write to `10_Vaults/`
- **No public notification** — Alerts must stay local until explicitly configured
- **No secrets in payloads** — Alert messages must not contain `.env` values, tokens, or keys

## Dashboard Policy

- **Local-only first** — All dashboards bind `127.0.0.1` only
- **No public dashboards** — No Cloudflare tunnel, no public port binding
- **No Cloudflare tunnel in this phase** — Tunnel activation is deferred
- **No admin UI exposure** — Admin panels bind localhost or are disabled
- **No Docker socket mounted** — No observability container gets `/var/run/docker.sock`
- **Tailscale-only later** — If remote access is needed, use Tailscale, not public tunnels

## Future Activation Plan

Observability service activation is a separate phase that requires:

1. **Scaffold creation** — Docker Compose observability service definitions
2. **Static validation** — `docker-compose config` check without starting
3. **Port review** — Verify all ports bind `127.0.0.1` only
4. **Security review** — No Docker socket, no secrets, no vault mounts
5. **No public ingress** — Confirm no Cloudflare, no public ports
6. **Single-service start** — Activate one service, verify, stabilize
7. **Health verification** — Confirm all health checks pass
8. **Backup/export policy** — Document backup needs before enabling persistence
9. **Rollback plan** — Document how to stop and remove observability services

Each step requires explicit approval. No batch activation.

## Current Observability Gaps

| Gap | Impact | Planned Fix |
|-----|--------|-------------|
| No container health monitoring | Unknown if services fail between manual checks | Uptime Kuma (future) |
| No alerting | Issues found only by manual inspection | Uptime Kuma notifications (future) |
| No dashboard | Must use CLI for all service status | Homepage (future) |
| No log aggregation | Must SSH and `docker logs` per container | Dozzle (future) |
| No disk monitoring | Could fill disk without warning | Uptime Kuma + script (future) |
| No service uptime history | Unknown restart patterns | Uptime Kuma (future) |

## Storage Pressure Integration

- Disk >= 90% is a **warning** — run `lifeos_observability.py` to confirm.
- Disk >= 95% is **critical** — execute safe cleanup from `Storage_Triage_Runbook.md`.
- Do not activate new observability services while disk is >= 95%.
- Storage Triage V3 (2026-07-08) improved disk from 97% to 91%. Observability V3 activation remains deferred while disk remains at or above 90%.
- See `40_Services/docs/Storage_Triage_Runbook.md` for safe cleanup procedures and forbidden actions.

## Deferrals

- Prometheus/Grafana/Loki — Heavy stack, needs separate evaluation
- Public dashboards — Never. Tailscale only if remote access needed
- Cloudflare tunnel for dashboards — Deferred, not needed for local monitoring
- Auto-remediation — Never. All remediation requires human review
- Kubernetes observability — Not applicable, no Kubernetes planned
- Homelab device monitoring — Not in scope for current single-host phase
