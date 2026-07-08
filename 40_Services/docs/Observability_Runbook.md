# LifeOS Observability Runbook V2

> Read-only manual checks and failure triage. No services installed or started.
> All mutation actions require separate approval.

## Manual Read-Only Checks

Run these commands to verify LifeOS health without installing any observability services.

### Service Inventory

```bash
python3 40_Services/scripts/lifeos_services.py --text
```

### API Health Checks

```bash
# Status API health
curl -fsS http://localhost:8787/health

# Status API full status (capture counts, event log)
curl -fsS http://localhost:8787/status

# Action API health
curl -fsS http://localhost:8788/health
```

### Container Status

```bash
docker ps
```

### Telegram Bot Status

```bash
systemctl --user status lifeos-telegram-bot.service --no-pager
```

### Observability Report Script

```bash
# Human-readable
python3 40_Services/scripts/lifeos_observability.py --text

# JSON (for scripts/tools)
python3 40_Services/scripts/lifeos_observability.py --json
```

## Failure Triage

### Status API Unavailable

**Symptom:** `curl http://localhost:8787/health` fails or times out.

**Safe first steps:**
1. Check container status: `docker ps --filter name=lifeos-status-api`
2. Check container health: `docker inspect lifeos-status-api -f '{{.State.Health.Status}}'`
3. Check container logs: `docker logs lifeos-status-api --tail 50`
4. Verify Docker network: `docker network inspect lifeos_internal`
5. Run `python3 40_Services/scripts/lifeos_services.py --text`

**Do not restart the container without separate approval.**

### Action API Unavailable

**Symptom:** `curl http://localhost:8788/health` fails or times out. Telegram `/capture` commands fail.

**Safe first steps:**
1. Check container status: `docker ps --filter name=lifeos-action-api`
2. Check container health: `docker inspect lifeos-action-api -f '{{.State.Health.Status}}'`
3. Check container logs: `docker logs lifeos-action-api --tail 50`
4. Verify `30_Capture/` and `50_Event_Log/` are mounted and writable

**Do not restart the container without separate approval.** The Action API is the single mutation boundary for captures.

### n8n Unavailable

**Symptom:** `curl http://localhost:5678` fails. n8n web UI not reachable.

**Safe first steps:**
1. Check container status: `docker ps --filter name=n8n`
2. Check container logs: `docker logs n8n_n8n_1 --tail 50`
3. Verify `lifeos_internal` network reachability from n8n container
4. Run `python3 40_Services/scripts/lifeos_services.py --text`

**Note:** n8n is tolerated legacy drift. Its unavailability does not block core capture/review flow. Telegram bot and Action API operate independently.

### Telegram Bot Inactive

**Symptom:** `systemctl --user status lifeos-telegram-bot.service` shows `inactive` or `failed`.

**Safe first steps:**
1. Check service status: `systemctl --user status lifeos-telegram-bot.service --no-pager`
2. Check recent logs: `journalctl --user -u lifeos-telegram-bot.service --since "10 minutes ago" --no-pager`
3. Verify Action API is reachable: `curl -fsS http://localhost:8788/health`
4. Verify `.env` exists and has correct permissions: `stat -c '%a %U %G' 40_Services/config/telegram/.env`

**Do not restart the service without checking for duplicate process/offset issues.** Restarting while the Telegram update queue has unprocessed messages may cause duplicate processing.

### Event Log Invalid

**Symptom:** Status API returns `"event_log_valid": false`.

**Safe first steps:**
1. Check event log size: `wc -l 50_Event_Log/events.jsonl`
2. Check for JSON errors: `python3 -c "import json; [json.loads(l) for l in open('50_Event_Log/events.jsonl') if l.strip()]"`
3. Find the first malformed line
4. Run `python3 40_Services/scripts/lifeos_observability.py --text`

**Do not edit the event log without separate approval.**

### Docker Unavailable

**Symptom:** `docker ps` fails with permission denied or connection refused.

**Safe first steps:**
1. Check Docker daemon: `systemctl status docker --no-pager`
2. Check user is in docker group: `groups | grep docker`
3. Check socket permissions: `ls -la /var/run/docker.sock`

### ChromaDB Unknown/Unhealthy

**Symptom:** `odysseus_chromadb_1` container is down or restarting.

**Safe first steps:**
1. Check container status: `docker ps -a --filter name=chromadb`
2. Check restart count: `docker inspect odysseus_chromadb_1 -f '{{.RestartCount}}'`
3. Check container logs: `docker logs odysseus_chromadb_1 --tail 50`

**Note:** ChromaDB is a legacy service from the old `odysseus` project. It is not LifeOS-owned. Do not attempt to repair or migrate this container.

### Disk Usage High

**Symptom:** `df -h /` shows usage >= 90%.

**Safe first steps:**
1. Check largest directories: `du -sh /home/lifeos/*/ | sort -rh | head -10`
2. Check Docker disk usage: `docker system df`
3. Check for large log files or orphaned volumes
4. Run `python3 40_Services/scripts/lifeos_observability.py --text`

**Do not run `docker system prune` or delete files without separate approval.**

## Observability Activation Checklist

For a future phase after explicit approval. Do not execute now.

- [ ] Choose observability services to install (Homepage, Uptime Kuma, Dozzle)
- [ ] Create Docker Compose scaffold at `40_Services/compose/observability/`
- [ ] Define service profiles (observability)
- [ ] Review ports — all must bind `127.0.0.1` only
- [ ] Verify no public exposure — no Cloudflare, no 0.0.0.0 bind
- [ ] Verify no Docker socket mount
- [ ] Verify no secrets committed — `.env.example` only
- [ ] Static validate compose: `docker-compose config`
- [ ] Get explicit approval to start
- [ ] Start one service (e.g., Uptime Kuma) only
- [ ] Verify health and local binding
- [ ] Configure first health checks
- [ ] Test notification channel (local only)
- [ ] Stabilize before adding next service
- [ ] Document rollback plan

## Rollback Model

- **Scaffold docs only** — This runbook and the Observability Control Plane
  doc can be reverted with `git revert`. No running services to roll back.
- **Future containers** — If observability services are activated in a later
  phase, they must have their own rollback plan. Containers must be stoppable
  without affecting core services.
- **No runtime damage possible now** — Nothing is installed or started.
  Rollback is not needed in this V2 scaffold phase.
