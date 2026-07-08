# LifeOS Uptime Kuma Monitor Plan

> Monitor definitions for the LifeOS Uptime Kuma instance at `127.0.0.1:3001`.
> All monitors are manual setup until Uptime Kuma exposes a safe CLI/API path.
> Monitors marked "Create now" should be configured immediately.
> Monitors marked "Create later" are placeholders for future services.

## Setup Method

Uptime Kuma does not currently have a reviewed safe CLI or API for automated
monitor creation in this environment. All monitors must be created manually
through the Uptime Kuma web UI at `http://127.0.0.1:3001`.

### Manual Setup Steps

1. Open `http://127.0.0.1:3001` in a local browser.
2. Complete first-run setup (create admin account and password).
3. For each monitor below, click "Add New Monitor" and fill in the fields
   as specified.
4. Verify the monitor shows "Up" (green) after creation.
5. Monitors are persisted in the `uptime_kuma_data` Docker volume and
   survive container restarts.

---

## Core Monitors

### 1. Status API Health

| Field | Value |
|-------|-------|
| **Monitor name** | `LifeOS Status API` |
| **Type** | HTTP(s) |
| **URL** | `http://lifeos-status-api:8787/health` |
| **Expected status code** | 200 |
| **Heartbeat interval** | 60 seconds |
| **Retries** | 3 |
| **Alert priority** | High |
| **Create** | **Now** |
| **Notes** | Core read-only service. If this is down, no system status is visible. Monitored via Docker DNS on `lifeos_internal` network. |
| **Expected response body** | `{"service":"lifeos-status-api","status":"ok","mode":"read_only"}` |

### 2. Action API Health

| Field | Value |
|-------|-------|
| **Monitor name** | `LifeOS Action API` |
| **Type** | HTTP(s) |
| **URL** | `http://lifeos-action-api:8788/health` |
| **Expected status code** | 200 |
| **Heartbeat interval** | 60 seconds |
| **Retries** | 3 |
| **Alert priority** | High |
| **Create** | **Now** |
| **Notes** | Core read-write service. Telegram captures and review commands fail if this is down. Monitored via Docker DNS on `lifeos_internal` network. |
| **Expected response body** | `{"service":"lifeos-action-api","status":"ok","mode":"read_write"}` |

### 3. n8n

| Field | Value |
|-------|-------|
| **Monitor name** | `LifeOS n8n` |
| **Type** | HTTP(s) |
| **URL** | `http://n8n_n8n_1:5678` |
| **Expected status code** | 200 |
| **Heartbeat interval** | 120 seconds |
| **Retries** | 2 |
| **Alert priority** | Medium |
| **Create** | **Now** |
| **Notes** | n8n may return a redirect (302) to the login page if Basic Auth is active but unauthenticated. Accept any response (2xx, 3xx) as "Up" by checking "Accepted Status Codes" and adding 200,302. Monitored via Docker DNS on `lifeos_internal` network. |

### 4. Dashboard Homepage

| Field | Value |
|-------|-------|
| **Monitor name** | `LifeOS Homepage` |
| **Type** | HTTP(s) |
| **URL** | `http://lifeos-homepage:3000` |
| **Expected status code** | 200 |
| **Heartbeat interval** | 120 seconds |
| **Retries** | 2 |
| **Alert priority** | Low |
| **Create** | **Now** |
| **Notes** | Dashboard landing page. Non-critical but useful to know if it's down. Monitored via Docker DNS on `dashboard_default` network. |

### 5. Uptime Kuma (self)

| Field | Value |
|-------|-------|
| **Monitor name** | `LifeOS Uptime Kuma` |
| **Type** | HTTP(s) |
| **URL** | `http://localhost:3001` |
| **Expected status code** | 200, 302 |
| **Heartbeat interval** | 300 seconds |
| **Retries** | 1 |
| **Alert priority** | Low |
| **Create** | **Now** |
| **Notes** | Self-check of the Uptime Kuma web UI from inside its own container. `localhost:3001` is correct for this monitor only, because the check runs inside the Uptime Kuma container itself. Accept 200/302. |

### 6. Dozzle

| Field | Value |
|-------|-------|
| **Monitor name** | `LifeOS Dozzle` |
| **Type** | HTTP(s) |
| **URL** | `http://lifeos-dozzle:8080` |
| **Expected status code** | 200 |
| **Heartbeat interval** | 120 seconds |
| **Retries** | 2 |
| **Alert priority** | Low |
| **Create** | **Now** |
| **Notes** | Container log viewer. Non-critical. If down, use `docker logs` as fallback. Uses internal Docker port 8080 (not host port 3002). Monitored via Docker DNS on `dashboard_default` network. |

---

## Infrastructure Monitors

### 7. Status API — Full Status Payload

| Field | Value |
|-------|-------|
| **Monitor name** | `LifeOS Status — Full` |
| **Type** | HTTP(s) — Keyword |
| **URL** | `http://lifeos-status-api:8787/status` |
| **Keyword** | `"status": "ok"` |
| **Expected status code** | 200 |
| **Heartbeat interval** | 300 seconds |
| **Retries** | 2 |
| **Alert priority** | Medium |
| **Create** | **Now** |
| **Notes** | Verifies the full status endpoint returns valid JSON with `"status": "ok"`. Catches partial API failures that the `/health` endpoint might miss. Monitored via Docker DNS on `lifeos_internal` network. |

### 8. Docker Daemon Available

| Field | Value |
|-------|-------|
| **Monitor name** | `LifeOS Docker Daemon` |
| **Type** | TCP Port |
| **Hostname** | `localhost` |
| **Port** | Socket check via script (see notes) |
| **Heartbeat interval** | 300 seconds |
| **Alert priority** | High |
| **Create** | **Now (script/manual)** |
| **Notes** | Uptime Kuma cannot directly check Docker socket health without Docker socket access (which is not granted). Two options: (a) Create a custom monitor type in Uptime Kuma that calls `docker info` from a script, or (b) monitor all Docker-hosted services individually — if Status API, Action API, n8n, and Dozzle are all down simultaneously, Docker daemon is likely the cause. Option (b) is recommended for V1. |

### 9. Disk Pressure

| Field | Value |
|-------|-------|
| **Monitor name** | `LifeOS Disk Usage` |
| **Type** | HTTP(s) — Keyword |
| **URL** | `http://lifeos-status-api:8787/status` |
| **Keyword** | N/A — use custom script (see notes) |
| **Expected status code** | 200 |
| **Heartbeat interval** | 600 seconds |
| **Retries** | 2 |
| **Alert priority** | Medium |
| **Create** | **Now (via Push Monitor)** |
| **Notes** | Disk usage is not exposed by Status API in V1. Recommended approach: set up a Push Monitor in Uptime Kuma, then run `lifeos_observability.py` on a cron schedule and push the disk percentage. Or use a simple script: `df -h / | tail -1 | awk '{print $5}'` with a threshold check. Push monitor URL can be triggered with `curl`. See Observability Runbook for detailed disk alerting flow. |

### 10. Git Dirty State

| Field | Value |
|-------|-------|
| **Monitor name** | `LifeOS Git Dirty` |
| **Type** | Push Monitor |
| **Push URL** | Generated by Uptime Kuma |
| **Heartbeat interval** | 3600 seconds |
| **Alert priority** | Low |
| **Create** | **Later (push monitor)** |
| **Notes** | Push monitor: a cron job runs `git -C /home/lifeos status --short | wc -l` and pushes to Uptime Kuma. Alert if dirty count > expected threshold for >24h. |

### 11. Offsite Push Status

| Field | Value |
|-------|-------|
| **Monitor name** | `LifeOS Offsite Push` |
| **Type** | Push Monitor |
| **Push URL** | Generated by Uptime Kuma |
| **Heartbeat interval** | 86400 seconds (24h) |
| **Alert priority** | Medium |
| **Create** | **Later (push monitor)** |
| **Notes** | Push monitor: a daily cron job runs `git -C /home/lifeos fetch offsite --dry-run` or checks the last push timestamp and pushes to Uptime Kuma. Alert if no push in >24h. |

### 12. ChromaDB Container

| Field | Value |
|-------|-------|
| **Monitor name** | `LifeOS ChromaDB` |
| **Type** | TCP Port |
| **Hostname** | `odysseus_chromadb_1` |
| **Port** | 8000 |
| **Heartbeat interval** | 300 seconds |
| **Alert priority** | Low |
| **Create** | **Later** |
| **Notes** | ChromaDB is on the `odysseus_default` network, not `lifeos_internal`. Uptime Kuma does not currently attach to `odysseus_default` (ChromaDB is a legacy service, not LifeOS-owned). If intra-network monitoring is needed, add `odysseus_default` as an external network to Uptime Kuma. For now, verify ChromaDB availability from the host (`docker ps`) or use a Push Monitor from a host cron job. Low priority alert. |

---

## Future Monitors

Monitors in this section should be created when the corresponding service is
deployed and active. Do not create them now.

### Capture Pipeline

| Monitor | Type | URL/Method | When to Create |
|---------|------|------------|---------------|
| Capture API | HTTP | `http://localhost:8789/health` | When Capture API is deployed (planned port per `Capture_API_Roadmap.md`) |
| Queue Processor | Push | Cron push from queue monitor script | When queue processor is active |
| Pending Capture Count | HTTP — Keyword | Status API `pending_captures` | Already checkable via Status API full monitor |

### AI Stack

| Monitor | Type | URL/Method | When to Create |
|---------|------|------------|---------------|
| Ollama | HTTP | `http://localhost:11434/api/tags` | When Ollama is deployed |
| Open WebUI | HTTP | `http://localhost:8080` | When Open WebUI is deployed |
| LiteLLM | HTTP | `http://localhost:TBD/health` | When LiteLLM is deployed |
| MCP Gateway / mcpo | HTTP | `http://localhost:TBD/health` | When MCP server or mcpo is active |
| LifeOS MCP Server | HTTP | `http://localhost:TBD/health` | When custom LifeOS MCP is active |

### Memory Stack

| Monitor | Type | URL/Method | When to Create |
|---------|------|------------|---------------|
| Qdrant | HTTP | `http://localhost:6333/health` | When Qdrant is deployed |
| Search API | HTTP | `http://localhost:TBD/health` | When Search API is deployed |
| Indexer | Push | Cron push from index job status | When indexer is active |

### Sandboxes

| Monitor | Type | URL/Method | When to Create |
|---------|------|------------|---------------|
| OpenHands | HTTP | `http://localhost:3003` | When OpenHands is activated |

### Agent Pipeline (Future)

| Monitor | Type | URL/Method | When to Create |
|---------|------|------------|---------------|
| Agentic Capture Pipeline | HTTP | `http://localhost:TBD/health` | When agentic pipeline is active |

---

## Alert Priority Definitions

| Priority | Response | Examples |
|----------|----------|----------|
| **High** | Investigate immediately | Status API down, Action API down, Docker daemon down |
| **Medium** | Fix within 1 day | n8n down, disk >= 90%, git dirty > 10 files > 24h, offsite push missed |
| **Low** | Fix when convenient | Homepage down, Dozzle down, ChromaDB down, git dirty < 10 files |

## Notification Channels

Uptime Kuma supports these notification methods. Choose based on LifeOS
alerting preferences:

| Channel | Setup Complexity | Recommendation |
|---------|-----------------|----------------|
| Gotify | Low | Recommended — self-hosted, simple |
| ntfy | Low | Recommended alternative — no server needed |
| Telegram | Medium | Use a separate bot from the main LifeOS bot |
| Email | Low | SMTP config needed |
| Webhook | Medium | Can push to n8n for custom workflow routing |

**V1 recommendation:** Start with Gotify or ntfy as a separate local-only
notification channel. Do not route alerts through the main LifeOS Telegram
bot to avoid mixing operations alerts with capture/review traffic.

## Alert Policy

- **No auto-remediation** — Alerts inform, they do not trigger restarts, prunes, or mutations.
- **No public notification** — All alerts stay local until a notification channel is explicitly configured.
- **No secret leakage** — Monitor names, URLs, and response bodies must not contain tokens, API keys, or credentials.
- **No alert fatigue** — Heartbeat intervals are chosen to avoid noise. Start with defaults and tune based on false-positive rate.
- **No Docker socket monitors** — Docker daemon health is inferred from individual service monitors. No Uptime Kuma container receives Docker socket access.

---

## Post-Setup Verification

After creating all "Now" monitors:

1. Open Uptime Kuma status page (`http://127.0.0.1:3001`).
2. Verify all monitors are green ("Up").
3. Wait 2 heartbeat intervals to confirm stability.
4. If any monitor is red:
   - Verify the URL is reachable from the Uptime Kuma container: `docker exec lifeos-uptime-kuma curl -s http://lifeos-status-api:8787/health`
   - Check that the target service is running: `docker ps`
   - Verify network membership: Uptime Kuma is on both `dashboard_default` and `lifeos_internal` Docker networks. Core services (Status API, Action API, n8n) are on `lifeos_internal`. Dashboard services (Homepage, Dozzle) are on `dashboard_default`. Ensure the monitor URL uses the correct container DNS name, not `localhost`.
   - `localhost` inside the Uptime Kuma container points to the Uptime Kuma container itself, not the host and not other containers. Use Docker DNS names (e.g., `lifeos-status-api`, `lifeos-action-api`, `n8n_n8n_1`, `lifeos-homepage`, `lifeos-dozzle`) for cross-container monitors.
   - Uptime Kuma does NOT have Docker socket access. Docker daemon health is inferred from individual service monitors.

## Backup

Uptime Kuma monitor definitions are stored in the `uptime_kuma_data` Docker volume.
To back up:

```bash
# Export monitor list (manual — no CLI)
# Monitor definitions persist in the Docker volume across restarts.
# For disaster recovery, recreate monitors from this plan document.

# Backup the volume data
docker run --rm -v uptime_kuma_data:/data -v $(pwd):/backup alpine tar czf /backup/uptime_kuma_backup.tar.gz -C /data .
```

## References

- Uptime Kuma docs: `https://github.com/louislam/uptime-kuma`
- LifeOS Observability Control Plane: `40_Services/docs/Observability_Control_Plane.md`
- LifeOS Observability Runbook: `40_Services/docs/Observability_Runbook.md`
- Docker MCP Service Map: `40_Services/docs/Docker_MCP_Service_Map.md`
