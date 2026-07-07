# Status API localhost:8787 Mapping/Adoption Plan

> **For agentic workers:** This is a docs-only planning document. No Docker, systemd, compose, or service state changes are authorized. All future commands are clearly marked "do not run yet."

**Goal:** Plan how to safely reconcile the running `lifeos-status-api` container so it becomes reachable at `localhost:8787` and can eventually be owned by the unified compose baseline.

**Architecture:** The legacy `lifeos-status-api` runs from `status_api` compose project with no host port mapping. The unified compose (`40_Services/compose/lifeos.yaml`) defines the same container name with `127.0.0.1:8787:8787`. The legacy container must be stopped and removed, then the unified container can start on port 8787.

**Tech Stack:** docker-compose v1.29.2, Python 3.12-alpine (stdlib HTTP server), read-only container.

## Global Constraints

- No container stop/start/restart/build/pull/create/remove/recreate in this plan
- Do not touch `lifeos-action-api` — Telegram capture path depends on it
- No broad `docker-compose down` — only targeted `stop` + `rm` for the legacy Status API
- `30_Capture/` and `50_Event_Log/` must be preserved (read-only mounts, no data risk)
- `lifeos_internal` network must be preserved
- Telegram bot remains capture-first, no `--allow-review`
- Status API is read-only — lowest risk container to adopt

---

## Current Status API Runtime Truth

| Property | Value |
|---|---|
| Container name | `lifeos-status-api` |
| Image | `status_api_lifeos-status-api` |
| Status | Running (Up 16+ hours) |
| Compose project | `status_api` (legacy) |
| Compose file | `docker-compose.yml` at `/home/lifeos/40_Services/status_api` |
| Restart policy | `unless-stopped` |
| Port exposure | Container-only `8787/tcp` — no host mapping (`null`) |
| Network | `lifeos_internal` (172.20.0.2/16) |
| Mounts | `30_Capture:/lifeos/capture:ro`, `50_Event_Log:/lifeos/event-log:ro` |
| `read_only` | Yes (in Dockerfile/compose) |
| Internal health | Passes — `GET /health` returns `{"service":"lifeos-status-api","status":"ok","mode":"read_only"}` |
| `localhost:8787/health` | Fails — connection refused (no host port mapping) |
| `localhost:8787/status` | Fails — connection refused |
| Container name conflicts with unified compose? | Yes — both use `container_name: lifeos-status-api` |

## Why localhost:8787 Mapping Matters

- Telegram bot `/status` command expects `http://localhost:8787/status` — currently always falls back
- The Status API was designed to be reachable from the host (Telegram systemd service), not just from Docker-internal DNS
- Without host mapping, the Telegram bot cannot use Status API for `/status` replies; it relies on safe fallback
- Unified compose already defines the correct mapping: `127.0.0.1:8787:8787`
- Port 8787 is currently free on the host — no conflict

## Risk Classification

**Classification: Policy drift requiring planned recreate/adoption**

Evidence:
- Container is healthy and correct in behavior — no functional defect
- Port mapping is missing, making it unreachable from the host
- No public exposure risk — fix would add `127.0.0.1` mapping (local-only)
- Read-only container — no data loss risk during recreation
- Container name `lifeos-status-api` conflicts with unified compose definition, requiring explicit stop/remove before unified adoption
- Lowest-risk container to migrate because: read-only, no mutation surface, no Telegram capture dependency, simple rollback

---

## Decision Options

### Option A — Tolerate current legacy Status API temporarily

| Pros | Cons | Conditions | Required Docs | Next Follow-up |
|---|---|---|---|---|
| No disruption to running container | Telegram `/status` remains on fallback path | No urgent need for host-accessible Status API | Already documented in drift entry | After n8n toleration period ends (no deadline) |
| Simple — do nothing | Continues documentation-to-runtime gap | Port 8787 must remain free | None additional | Before unified compose ownership migration (Phase E) |
| Container is stable with `unless-stopped` | Manual intervention needed later | Status API internal health is fine | | |

### Option B — Controlled recreate under unified compose with localhost:8787 mapping (Recommended)

| Pros | Cons | Preconditions | Required Approval | Rollback | Expected Verification |
|---|---|---|---|---|---|
| Status API becomes reachable at `localhost:8787` | Brief outage during container swap | Action API remains untouched | Unified compose activation approval | Start legacy container from `status_api` compose | `curl localhost:8787/health` returns 200 |
| Telegram `/status` works without fallback | Legacy compose `status_api` project state changes | n8n toleration confirmed (done) | Separate explicit approval (not this plan) | `docker-compose -f 40_Services/compose/lifeos.yaml stop lifeos-status-api` | `curl localhost:8787/status` returns valid JSON |
| Unified compose owns the container | | `lifeos_internal` network exists (verified) | | Then start legacy: `docker-compose -f 40_Services/status_api/docker-compose.yml start lifeos-status-api` | Telegram `/status` command returns status data |
| Read-only — no data loss risk | | Port 8787 is free (verified) | | | Internal health unchanged |
| Same mounts, same security hardening | | No active captures in progress | | | |
| Rollback is simple and safe | | | | | |

### Option C — Keep legacy compose but add port mapping there

| Pros | Cons | Why Less Ideal |
|---|---|---|
| Minimal change — edit legacy `40_Services/status_api/docker-compose.yml` | Legacy compose remains active outside unified management | Perpetuates ownership drift — two compose files claim the same service |
| No container recreate — just `docker-compose up -d` to re-create with new mapping | No unified healthcheck, logging, or policy applied | Unified compose is the long-term target; this option delays convergence |
| Faster than unified adoption | Future migration still needed | Adds one more migration step instead of one direct move |

### Option D — Remove Status API until later

| Pros | Cons | Why Not Recommended |
|---|---|---|
| Eliminates drift entirely | Loss of Status API availability for Telegram and n8n | Status API is read-only, no risk, provides value (health/status endpoint) |
| Clean state for future adoption | Requires re-build when needed | Telegram `/status` would permanently fall back |
| | Any n8n workflows referencing `lifeos-status-api:8787` would fail | n8n is tolerated but could be locally developed; breaking Status API is unnecessary |

---

## Recommendation

**Plan controlled recreate/adoption under unified compose (Option B) as a future approved action.**

Rationale:
1. `localhost:8787` is currently free — no port conflict
2. Unified compose already defines the desired `127.0.0.1:8787:8787` mapping
3. Status API is read-only — zero data loss risk during any container operation
4. Telegram `/status` will work without fallback after adoption
5. Container name/resource conflict is explicit and manageable (stop legacy → start unified)
6. Rollback is simple: restart the legacy container, stop the unified one
7. This is the lowest-risk migration of all drift items — safe to prioritize
8. Aligns with the reconciliation plan's Phase C recommendation

**No action should happen in this task.** This plan documents the future procedure only.

---

## Future Controlled Procedure

**Do not run these commands now. This is for future approved execution only.**

### Preconditions

Before execution, verify:
- [ ] `lifeos-action-api` is running and healthy at `localhost:8788`
- [ ] Telegram bot is active and capture-first
- [ ] Port 8787 is free: `ss -ltnp | grep ':8787' || echo "free"`
- [ ] `lifeos_internal` network exists: `docker network inspect lifeos_internal`
- [ ] Legacy container `lifeos-status-api` is running: `docker ps --filter name=lifeos-status-api`
- [ ] Unified compose validates: `docker-compose -f 40_Services/compose/lifeos.yaml config`

### Execution Steps

```bash
# Step 1: Stop legacy Status API container
docker-compose -f 40_Services/status_api/docker-compose.yml stop lifeos-status-api

# Step 2: Remove legacy Status API container (frees container name for unified compose)
docker-compose -f 40_Services/status_api/docker-compose.yml rm -f lifeos-status-api

# Step 3: Build unified Status API image
docker-compose -f 40_Services/compose/lifeos.yaml build lifeos-status-api

# Step 4: Start unified Status API with localhost mapping
docker-compose -f 40_Services/compose/lifeos.yaml up -d lifeos-status-api
```

### Verification

```bash
# Verify container is running
docker ps --filter name=lifeos-status-api

# Verify localhost health
curl -sS http://localhost:8787/health
# Expected: {"service": "lifeos-status-api", "status": "ok", "mode": "read_only"}

# Verify localhost status
curl -sS http://localhost:8787/status
# Expected: valid JSON with capture counts and event log state

# Verify port mapping
ss -ltnp | grep ':8787'
# Expected: 127.0.0.1:8787

# Verify internal container health (via docker exec)
docker exec lifeos-status-api python3 -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8787/health', timeout=3).read().decode())"

# Verify Telegram bot can reach Status API (send /status via Telegram or check logs)
systemctl --user status lifeos-telegram-bot.service --no-pager -l | tail -5

# Verify Action API unaffected
curl -sS http://localhost:8788/health
```

---

## Rollback Procedure

If the unified Status API fails or causes issues:

```bash
# Stop unified Status API
docker-compose -f 40_Services/compose/lifeos.yaml stop lifeos-status-api
docker-compose -f 40_Services/compose/lifeos.yaml rm -f lifeos-status-api

# Restart legacy Status API
docker-compose -f 40_Services/status_api/docker-compose.yml up -d lifeos-status-api

# Verify legacy container is running
docker ps --filter name=lifeos-status-api

# Verify no host port mapping (expected — legacy behavior)
ss -ltnp | grep ':8787' || echo "Port 8787 free (expected)"

# Verify internal health
docker exec lifeos-status-api python3 -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8787/health', timeout=3).read().decode())"
```

**Rollback is safe because:**
- Status API is read-only — no data written during unified runtime
- `30_Capture/` and `50_Event_Log/` are host-mounted — unaffected by container state
- No Telegram capture dependency on Status API — Telegram only uses Status API for `/status` command
- Action API continues serving captures regardless of Status API state

---

## Explicit Warnings

1. **Do not touch Action API** — `lifeos-action-api` serves the live Telegram capture path on `localhost:8788`. Do not stop, restart, or modify it during Status API work.

2. **Do not use broad `docker-compose down`** — Never run `docker-compose -f 40_Services/compose/lifeos.yaml down` (would attempt to manage all services). Use targeted `stop` + `rm` for `lifeos-status-api` only.

3. **Preserve `30_Capture/` and `50_Event_Log/`** — Status API uses read-only mounts. No data loss risk. Confirm mounts are `ro` after adoption.

4. **`lifeos_internal` network must survive** — The unified compose uses `external: true`. Do not remove or recreate the network.

5. **No public exposure** — Verify `127.0.0.1` mapping, not `0.0.0.0`, after adoption.

6. **No n8n workflow activation** — Status API adoption does not change n8n status. n8n remains tolerated temporary drift.

---

## Explicit Note

Status API is **read-only**. It exposes `GET /health` and `GET /status` endpoints with no mutation surface. It does not write to `30_Capture/`, `50_Event_Log/`, or any other path. It has no Docker socket, no vault access, no secrets, and no subprocess execution. This is the lowest-risk container in the LifeOS stack for migration.
