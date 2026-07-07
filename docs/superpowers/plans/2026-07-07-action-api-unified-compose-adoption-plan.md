# Action API Unified Compose Adoption Plan

> **For agentic workers:** This is a docs-only planning document. No Docker, systemd, compose, or service state changes are authorized. All future commands are clearly marked "do not run yet."

**Goal:** Plan how to safely adopt the currently running manual `lifeos-action-api` container under unified compose ownership without disrupting the live Telegram capture path.

**Architecture:** The `lifeos-action-api` currently runs as a manual Docker container (no compose labels, `restart: no`) and serves the live Telegram capture path at `localhost:8788`. The unified compose (`40_Services/compose/lifeos.yaml`) defines the same service with proper restart policy (`unless-stopped`), compose labels, and identical mount/network configuration. The manual container must be stopped and removed, then the unified container started in its place.

**Tech Stack:** docker-compose v1.29.2, Python 3.12-alpine (stdlib HTTP server), read-write container.

## Global Constraints

- No container stop/start/restart/build/pull/create/remove/recreate in this plan
- No container or service changes of any kind in this docs-only phase
- Do not touch Status API except health checks
- Do not touch n8n
- Do not restart Telegram
- Do not enable `--allow-review`
- Do not activate Telegram review commands
- Do not expose public ingress
- Do not use broad `docker-compose down`
- Do not use `docker-compose down -v`
- Do not remove Docker volumes, including `compose_n8n_data`
- Do not inspect secrets or `.env` contents
- Preserve `30_Capture/` and `50_Event_Log/`

---

## 1. Current Action API Runtime Truth

| Property | Value |
|---|---|
| Container name | `lifeos-action-api` |
| Image | `n8n_lifeos-action-api` |
| Status | Running |
| Started at | 2026-07-07T04:02:59Z |
| Restart policy | `no` — will not restart on host reboot |
| Port binding | `127.0.0.1:8788→8788/tcp` |
| Network | `lifeos_internal` |
| Compose labels | None — `ComposeProject=""`, `ComposeService=""`, `Labels={}` |
| Compose origin | None — manual `docker run` or equivalent |
| Mounts | `30_Capture:/lifeos/capture:rw`, `50_Event_Log:/lifeos/event-log:rw` |
| Health | `localhost:8788/health` → `{"service":"lifeos-action-api","status":"ok","mode":"read_write"}` |
| Current owner | None (unlabeled manual container) |
| Desired owner | Unified compose at `40_Services/compose/lifeos.yaml` |

## 2. Why Action API Is High Risk

1. **Live mutation path** — Action API is the write boundary. It creates capture files, modifies frontmatter, moves review files, and appends event log entries. Any disruption directly impacts Telegram capture functionality.
2. **Telegram capture depends on `localhost:8788`** — The Telegram polling bot (`telegram_capture_bot.py --poll --interval 3`) calls `POST /captures` at `http://localhost:8788`. If Action API goes down, Telegram replies with `"LifeOS capture unavailable. No action was taken."`
3. **Read-write mounts** — Unlike Status API (read-only), Action API mounts `30_Capture/` and `50_Event_Log/` as read-write. Incorrect mount configuration could lead to data integrity issues.
4. **No restart policy** — Current `restart: no` means the container does not survive host reboot. Adoption improves this to `unless-stopped`.
5. **No automated rollback safety** — The current container has no compose labels, so rollback requires reconstructing the manual `docker run` command precisely.

## 3. Desired Future State

| Property | Current | Desired |
|---|---|---|
| Owner | Manual (unlabeled) | Unified compose (`compose` project) |
| Restart policy | `no` | `unless-stopped` |
| Compose labels | None | Present (`com.docker.compose.project`, etc.) |
| Port | `127.0.0.1:8788:8788` | Same (unchanged) |
| Mounts | `30_Capture:rw`, `50_Event_Log:rw` | Same (unchanged) |
| Network | `lifeos_internal` | Same (unchanged) |
| `localhost:8788/health` | Working | Same (unchanged) |
| Security (`cap_drop: ALL`, `no-new-privileges`) | Not explicitly set at container level (may be inherited) | Explicitly enforced via compose |
| Telegram capture path | Working | Same (unchanged) |
| `--allow-review` | Disabled | Disabled (unchanged) |
| Public ingress | None | None (unchanged) |
| n8n | Tolerated localhost-only drift | Same (unchanged) |

## 4. Preconditions for Future Action API Adoption

All must be met before Phase 5 execution:

- [ ] Status API healthy on `localhost:8787/health` → `ok/read_only`
- [ ] Current Action API healthy on `localhost:8788/health` → `ok/read_write`
- [ ] Telegram bot active: `systemctl --user is-active lifeos-telegram-bot.service`
- [ ] Unified compose config validates: `docker-compose -f 40_Services/compose/lifeos.yaml config`
- [ ] No public bind: `grep -n "0.0.0.0" /tmp/lifeos-compose-config.out` → no match
- [ ] No `WEBHOOK_URL`: `grep -n "WEBHOOK_URL" /tmp/lifeos-compose-config.out` → no match
- [ ] No Cloudflare: `grep -n "cloudflared\|cloudflare" /tmp/lifeos-compose-config.out` → no match
- [ ] Port 8788 is bound by current Action API: `ss -ltnp | grep ':8788'`
- [ ] Port 8787 is bound by Status API: `ss -ltnp | grep ':8787'`
- [ ] n8n unchanged on `5678`: `ss -ltnp | grep ':5678'`
- [ ] Rollback command confirmed and documented before stopping old container
- [ ] User gives exact approval phrase: **APPROVE PHASE 5 ACTION API ADOPTION**

---

## 5. Future Controlled Adoption Procedure

**FUTURE ONLY — DO NOT RUN UNTIL APPROVED**

```bash
# Step 0: Pre-adoption verification
echo "=== Pre-adoption state ==="
docker inspect lifeos-action-api --format 'Name={{.Name}} Image={{.Config.Image}} Status={{.State.Status}} RestartPolicy={{.HostConfig.RestartPolicy.Name}} Ports={{json .NetworkSettings.Ports}} ComposeProject={{index .Config.Labels "com.docker.compose.project"}}'
curl -sS --max-time 5 http://localhost:8788/health
curl -sS --max-time 5 http://localhost:8787/health
systemctl --user is-active lifeos-telegram-bot.service
ss -ltnp | grep -E ':5678|:8787|:8788'

# Step 1: Stop manual Action API only
docker stop lifeos-action-api

# Step 2: Remove manual Action API container only
docker rm lifeos-action-api

# Step 3: Build unified Action API only
docker-compose -f 40_Services/compose/lifeos.yaml build lifeos-action-api

# Step 4: Start unified Action API only
docker-compose -f 40_Services/compose/lifeos.yaml up -d lifeos-action-api

# Step 5: Post-adoption verification
echo "=== Post-adoption state ==="
docker inspect lifeos-action-api --format 'Name={{.Name}} Image={{.Config.Image}} Status={{.State.Status}} RestartPolicy={{.HostConfig.RestartPolicy.Name}} Ports={{json .NetworkSettings.Ports}} ComposeProject={{index .Config.Labels "com.docker.compose.project"}} ComposeService={{index .Config.Labels "com.docker.compose.service"}} ComposeConfigFiles={{index .Config.Labels "com.docker.compose.project.config_files"}}'
curl -sS --max-time 5 http://localhost:8788/health
curl -sS --max-time 5 http://localhost:8787/health
systemctl --user is-active lifeos-telegram-bot.service
ss -ltnp | grep -E ':5678|:8787|:8788'
echo "=== Runtime artifact check ==="
git status --short
echo "=== Public ingress check ==="
docker-compose -f 40_Services/compose/lifeos.yaml config | grep "0.0.0.0" && echo "ERROR" || echo "OK: no 0.0.0.0"
```

## 6. Rollback Procedure

**FUTURE ONLY — ROLLBACK IF ADOPTION FAILS**

Run only if `localhost:8788/health` fails after adoption:

```bash
# Step 1: Stop unified Action API only
docker-compose -f 40_Services/compose/lifeos.yaml stop lifeos-action-api || true
docker-compose -f 40_Services/compose/lifeos.yaml rm -f lifeos-action-api || true

# Step 2: Restore manual Action API from existing image n8n_lifeos-action-api
docker run -d \
  --name lifeos-action-api \
  --network lifeos_internal \
  -p 127.0.0.1:8788:8788 \
  -v /home/lifeos/30_Capture:/lifeos/capture:rw \
  -v /home/lifeos/50_Event_Log:/lifeos/event-log:rw \
  n8n_lifeos-action-api

# Step 3: Verify rollback
curl -sS --max-time 5 http://localhost:8788/health
docker ps --filter name=lifeos-action-api
```

## 7. Verification Strategy

After adoption, verify:

| Check | Command | Expected |
|---|---|---|
| Action API health | `curl -sS http://localhost:8788/health` | `{"service":"lifeos-action-api","status":"ok","mode":"read_write"}` |
| Status API still healthy | `curl -sS http://localhost:8787/health` | `{"service":"lifeos-status-api","status":"ok","mode":"read_only"}` |
| Telegram active | `systemctl --user is-active lifeos-telegram-bot.service` | `active` |
| Compose ownership | `docker inspect lifeos-action-api --format '{{index .Config.Labels "com.docker.compose.project"}}'` | `compose` |
| Restart policy | `docker inspect lifeos-action-api --format '{{.HostConfig.RestartPolicy.Name}}'` | `unless-stopped` |
| Port bindings | `ss -ltnp \| grep -E ':5678\|:8787\|:8788'` | All three ports on `127.0.0.1` |
| n8n unchanged | `curl -sS -I http://localhost:5678/ \| head -1` | `HTTP/1.1 200 OK` |
| No public ingress | `grep "0.0.0.0" /tmp/lifeos-compose-config.out` | No match |
| No runtime artifacts staged | `git status --short` | No `30_Capture/`, `50_Event_Log/`, `.env` |
| No secrets leakage | — | No `.env` or credential inspection |

## 8. Explicit Warnings

1. **Do not use broad `docker-compose down`** — Only targeted `stop` + `rm` for `lifeos-action-api`. Broad `down` could affect Status API and n8n.
2. **Do not use `docker-compose down -v`** — Would remove volumes including `n8n_data` and potentially `compose_n8n_data`.
3. **Do not remove Docker volumes** — Including `n8n_n8n_data` (legacy n8n data), `n8n_data` (compose volume definition), and `compose_n8n_data` (side-effect volume, empty but present).
4. **Do not remove `compose_n8n_data`** — Created as an empty/unused side-effect during Status API adoption. Harmless. Leave it.
5. **Do not touch n8n** — n8n remains tolerated localhost-only drift. No start, stop, restart, or workflow activation.
6. **Do not touch Status API except health checks** — Status API is now unified-compose-owned and working.
7. **Do not enable `--allow-review`** — Telegram must remain capture-first.
8. **Do not activate Telegram review commands** — Review command live validation is deferred.
9. **Do not activate n8n workflows** — Workflow activation status is not verified.
10. **Do not expose public ingress** — All ports must remain `127.0.0.1` only.
11. **Preserve `30_Capture/` and `50_Event_Log/`** — These are canonical operational records.
12. **Do not inspect secrets or `.env`** — No credential files, tokens, or secrets handling.

## 9. Documentation Updates

After successful adoption, update:
- `10_Vaults/LifeOS/10_AI_UNIVERSE/Current_Working_State.md` — record Action API adoption, verify Status API still healthy, confirm n8n unchanged
- `40_Services/compose/README.md` — update drift warning (remove Action API from list), update service table
- `40_Services/action_api/README.md` — update Docker section to reference unified compose

