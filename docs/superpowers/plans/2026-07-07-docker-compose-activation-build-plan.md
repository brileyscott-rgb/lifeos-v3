# Docker Compose Activation/Build Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan phase-by-phase. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Safely build and optionally activate the local Docker Compose baseline services (Status API first, Action API second) while keeping n8n deferred, public exposure unchanged, and Telegram capture-first polling intact.

**Architecture:** Single `docker-compose -f 40_Services/compose/lifeos.yaml` manages three services. Status API (read-only, port 8787) activates first as lowest-risk entry point. Action API (read-write, port 8788) activates only after Status API smoke test passes and explicit approval is granted. n8n uses `manual-start-disabled` profile and remains inactive. All services bind `127.0.0.1` only — no public ingress. `lifeos_internal` network is external (must pre-exist or be created). Telegram bot stays as systemd user service outside compose.

**Tech Stack:** docker-compose v1.29.2, Python 3.12-alpine base images, stdlib HTTP servers, no n8n upstream image pulled.

## Global Constraints

- No public ingress (`0.0.0.0` bind is forbidden in compose config)
- No `WEBHOOK_URL` in compose config
- No Cloudflare tunnel or cloudflared service in compose config
- n8n uses `manual-start-disabled` profile — never started without explicit separate plan
- n8n uses `${VAR:-default}` env substitution only — no `env_file` reference
- `lifeos_internal` network is `external: true` — must verify existence before start
- Do not run: `docker-compose up`, `start`, `restart`, `run`, `create`, `build`, `pull` outside of explicit approval gates
- Do not run: `docker run`, `docker build`, `docker pull`
- Do not inspect secrets, `.env`, tokens
- Do not stage runtime artifacts (`30_Capture/*`, `50_Event_Log/events.jsonl`, `.env`, `.gemini/`, `.config/opencode/opencode.json`, tokens/secrets, runtime offsets, Docker/n8n runtime data)
- Telegram bot remains `--poll --interval 3`, no `--allow-review`
- Do not stop existing host-run APIs without explicit migration decision
- Host-run Action API and Status API (if active) must be checked before proposing container replacement
- n8n remains entirely inactive — no build, pull, profile override, or start
- Rollback must be defined per phase before proceeding to next phase

---

## Pre-Activation Inventory

### Current Host Service State (verify in Phase A)

Before any activation, determine whether host-run Action API / Status API processes are currently bound to ports 8788 and 8787:

- `ss -ltnp | grep -E ':8787|:8788|:5678' || true`
- `systemctl --user status lifeos-telegram-bot.service | head -20`
- `curl -s http://localhost:8787/health` (if Status API host process is running)
- `curl -s http://localhost:8788/health` (if Action API host process is running)

### Network Readiness (verify in Phase B)

- `docker network inspect lifeos_internal` — must return network details
- If missing: `docker network create lifeos_internal` (create once before any compose start)
- Network creation is idempotent — safe to run if absent

### Static Compose Validation Re-Verification

Before Phase C, re-run:

```bash
docker-compose -f 40_Services/compose/lifeos.yaml config > /dev/null
```

Expected: exit 0, no warnings about unset variables (all have `${VAR:-default}` fallbacks).

---

## Phase A: Pre-Activation Inspection

**Goal:** Gather current state without touching any service.

- [ ] **Step A1: Check port bindings**

```bash
echo "=== Port bindings ==="
ss -ltnp | grep -E ':8787|:8788|:5678' || echo "No LifeOS services bound"
```

If ports 8787 or 8788 are bound, note the owning PID/process name. This determines whether host-run APIs need migration consideration.

- [ ] **Step A2: Check Telegram bot service status**

```bash
echo "=== Telegram bot service ==="
systemctl --user status lifeos-telegram-bot.service | head -20
```

Expected: active (running), capture-first (`--poll --interval 3`, no `--allow-review`).

- [ ] **Step A3: Health-check host-run APIs (if applicable)**

```bash
echo "=== Host API health ==="
curl -s http://localhost:8787/health || echo "Status API host process not responding"
curl -s http://localhost:8788/health || echo "Action API host process not responding"
```

- [ ] **Step A4: Record findings for activation decision**

If host-run Status API is bound to 8787 and healthy, the Docker Status API cannot start on the same port until the host process is stopped. The activation plan must account for this conflict.

If host-run Action API is bound to 8788 and healthy, Docker Action API activation on 8788 requires stopping the host process — which requires explicit approval and rollback planning.

If neither host-run API is running, ports are free and Docker containers can start directly.

---

## Phase B: Network Readiness

**Goal:** Ensure `lifeos_internal` Docker network exists before any container start.

- [ ] **Step B1: Inspect network**

```bash
docker network inspect lifeos_internal
```

Expected output includes network name, driver (bridge), scope (local), and connected containers (none initially).

- [ ] **Step B2: Create network if missing**

Run only if Step B1 fails with "network not found":

```bash
docker network create lifeos_internal
```

Verify: `docker network inspect lifeos_internal` now succeeds.

- [ ] **Step B3: Record network state**

Note for documentation update: the network was either verified as existing or was created during activation.

---

## Phase C: Status API Build → Start → Smoke Test

**Goal:** Build and start only the Status API container. This is the lowest-risk entry point — read-only, least privilege, no mutation surface. Requires explicit approval before execution.

### Pre-Flight Approval

Before Phase C, obtain explicit approval from the reviewer/operator.

Approval request message:

```
Ready to activate Docker Status API.

Pre-activation inspection shows:
- Port 8787: [free|bound by host PID X]
- lifeos_internal network: [exists|needs creation]
- Telegram service: [active capture-first]
- Host-run APIs: [Status: running/not running] [Action: running/not running]

Phase C will:
1. docker-compose build lifeos-status-api
2. docker-compose up -d lifeos-status-api  (only if port is free)
3. Verify /health and /status endpoints

> Note: host-run Status API on port 8787 [must be stopped first|port is free].

Approve Phase C? [y/N]
```

### Execution Steps

- [ ] **Step C1: Build Status API image**

```bash
docker-compose -f 40_Services/compose/lifeos.yaml build lifeos-status-api
```

Expected: build succeeds, image `lifeos-lifeos-status-api` (or similar) created.

Verification: `docker images | grep lifeos-status-api`

- [ ] **Step C2: Start Status API container**

```bash
docker-compose -f 40_Services/compose/lifeos.yaml up -d lifeos-status-api
```

Expected: container `lifeos-status-api` starts, exits 0.

Verification: `docker ps --filter name=lifeos-status-api` shows status `Up` and port `127.0.0.1:8787->8787/tcp`.

- [ ] **Step C3: Verify health endpoint**

```bash
curl -s http://localhost:8787/health
```

Expected:
```json
{"service": "lifeos-status-api", "status": "ok", "mode": "read_only"}
```

- [ ] **Step C4: Verify status endpoint**

```bash
curl -s http://localhost:8787/status
```

Expected: JSON with capture queue counts, event log state, and path status.

- [ ] **Step C5: Verify read-only mount enforcement**

The Status API container uses `read_only: true`. Verify that write attempts fail:

```bash
docker exec lifeos-status-api touch /lifeos/capture/test_write || echo "Read-only enforced (expected)"
```

Expected: `touch: /lifeos/capture/test_write: Read-only file system` or similar.

- [ ] **Step C6: Verify Telegram bot still works with Status API**

Send `/status` via Telegram (capture-first mode allows `/status`). Bot should reply with status data. Use `--review-test` or check Telegram.

Alternatively, verify with curl against Action API Status API contract:

```bash
curl -s http://localhost:8787/health > /dev/null && echo "Status API healthy"
```

---

## Phase D: Status API Decision — Stop or Leave Running

**Goal:** Decide whether the Status API container stays active after smoke test. This decision must be made before proceeding to Action API activation.

- [ ] **Step D1: Present decision prompt**

Present these options to the operator:

1. **Leave Status API running** — Status API continues as Docker container. Host-run Status API (if any) remains stopped. This is the normal path for baseline activation.
2. **Stop Status API** — Run `docker-compose -f 40_Services/compose/lifeos.yaml stop lifeos-status-api`. Container is stopped but not removed. Can be restarted later with `docker-compose start lifeos-status-api`.
3. **Remove Status API** — Run `docker-compose -f 40_Services/compose/lifeos.yaml down lifeos-status-api`. Container and network reference removed. Image retained.

- [ ] **Step D2: Execute decision**

If leaving running, verify Telegram `/status` still works:

```bash
systemctl --user status lifeos-telegram-bot.service | head -5
curl -s http://localhost:8787/health
```

- [ ] **Step D3: Document Status API state**

Record in Current_Working_State.md and compose README that Status API is now active as a Docker container (or stopped, depending on decision).

---

## Phase E: Action API Build → Start → Migration Plan

**Goal:** Build and start Action API as Docker container. This is higher risk because:
- Action API has read-write mounts (capture/event-log mutation surface)
- Port 8788 may be bound by a host-run Action API process
- Telegram bot depends on `http://localhost:8788` — must continue working

**Requires separate explicit approval after Phase D is resolved.**

### Pre-Flight Approval

Before Phase E, present:

```
Ready to activate Docker Action API.

Pre-activation state:
- Port 8788: [free|bound by host PID X]
- Host-run Action API: [running|not running]
  [If running: process name, PIDs]
- Telegram bot contract: http://localhost:8788
- Status API Docker container: [running|stopped]

Phase E will:
1. [If host-run Action API on 8788: stop host-run process]
2. docker-compose build lifeos-action-api
3. docker-compose up -d lifeos-action-api
4. Verify /health and offline capture test
5. Verify Telegram capture still works

> WARNING: If Telegram bot restarts or /capture breaks, rollback
> via Phase E rollback steps.

Approve Phase E? [y/N]
```

### Execution Steps

- [ ] **Step E1: Check Action API host process (if applicable)**

```bash
ss -ltnp | grep ':8788'
```

If a host-run Action API is using 8788, identify the process owner. If it's the Telegram bot or another LifeOS service, note the PID.

- [ ] **Step E2: Stop host-run Action API (if port conflict)**

**Requires explicit approval before running.**

```bash
# If Action API is running directly from a terminal:
kill <PID>

# If Action API is a system service:
systemctl --user stop lifeos-action-api.service  || true

# Verify port is free:
ss -ltnp | grep ':8788' || echo "Port 8788 is free"
```

- [ ] **Step E3: Build Action API image**

```bash
docker-compose -f 40_Services/compose/lifeos.yaml build lifeos-action-api
```

Expected: build succeeds.

Verification: `docker images | grep lifeos-action-api`

- [ ] **Step E4: Start Action API container**

```bash
docker-compose -f 40_Services/compose/lifeos.yaml up -d lifeos-action-api
```

Expected: container `lifeos-action-api` starts, exits 0.

Verification: `docker ps --filter name=lifeos-action-api` shows status `Up` and port `127.0.0.1:8788->8788/tcp`.

- [ ] **Step E5: Verify /health**

```bash
curl -s http://localhost:8788/health
```

Expected:
```json
{"service": "lifeos-action-api", "status": "ok", "mode": "read_write"}
```

- [ ] **Step E6: Verify Action API endpoints**

```bash
# GET /captures/pending (empty queue)
curl -s http://localhost:8788/captures/pending
```

Expected: `{"success": true, "ok": true, "captures": [], "count": 0, "error": null}`

- [ ] **Step E7: Offline capture test (create and clean up)**

This step creates a real capture file and event log entry. It is the true functional test.

```bash
# Create a test capture
CAPTURE_RESPONSE=$(curl -s -X POST http://localhost:8788/captures \
  -H "Content-Type: application/json" \
  -d '{"text": "Docker activation smoke test — will be rejected"}')
echo "$CAPTURE_RESPONSE" | python3 -m json.tool

# Extract capture_id
CAPTURE_ID=$(echo "$CAPTURE_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('capture_id',''))")
echo "Created capture_id: $CAPTURE_ID"

# Verify it appears in pending
curl -s http://localhost:8788/captures/pending | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Pending count: {data[\"count\"]}')
assert data['count'] > 0, 'No pending captures found'
print('OK: capture created successfully')
"
```

Wait for decision: does the operator want the test capture rejected now, or kept for later review?

```bash
# Option A: Reject the test capture
curl -s -X POST "http://localhost:8788/captures/${CAPTURE_ID}/reject"
```

```bash
# Option B: Leave for later manual review
echo "Test capture $CAPTURE_ID left for manual review"
```

- [ ] **Step E8: Verify Telegram capture still functional (if Telegram bot is running)**

Send `/capture docker-action-api-smoke-test` from Telegram mobile, then:

```bash
python3 40_Services/chatops/telegram/telegram_capture_bot.py --capture-test
```

Expected: Bot replies with capture_id and pending_review status.

Or, if `--capture-test` is not desired, just wait for the polling service to process it automatically and check Telegram.

- [ ] **Step E9: Document Action API state**

Record in Current_Working_State.md that Action API is now active as a Docker container.

---

## Phase F: n8n Remains Deferred

**No activation steps for n8n.**

`lifeos-n8n` uses `profiles: ["manual-start-disabled"]` and `restart: "no"`. It will not start unless explicitly overridden with `--profile manual-start-disabled`. Do not override this profile.

Confirmation check:

```bash
docker-compose -f 40_Services/compose/lifeos.yaml ps
```

The `lifeos-n8n` service should show as `Created` or not appear at all (depending on whether it was started). If it shows as `Up`, stop immediately:

```bash
docker-compose -f 40_Services/compose/lifeos.yaml stop lifeos-n8n
```

No build, pull, start, or workflow activation for n8n. Document in Current_Working_State.md that n8n remains deferred and inactive.

---

## Phase G: Documentation Closeout

- [ ] **Step G1: Update `40_Services/compose/README.md`**

Change "Defined, not started" to "Defined, active" for services that were started. Update the state/status section to reflect current running state. Add activation date and operator notes.

- [ ] **Step G2: Update `10_Vaults/LifeOS/10_AI_UNIVERSE/Current_Working_State.md`**

Add entries documenting:
- Status API Docker activation (date, build+start outcome, smoke test results)
- Action API Docker activation (date, build+start outcome, smoke test results)
- n8n remains deferred
- Telegram bot remains capture-first systemd user service

- [ ] **Step G3: Update service README files (if applicable)**

- `40_Services/status_api/README.md` — if not already updated to reflect Docker activation
- `40_Services/action_api/README.md` — if not already updated to reflect Docker activation

- [ ] **Step G4: Verify all compose services still validate**

```bash
docker-compose -f 40_Services/compose/lifeos.yaml config > /dev/null
```

- [ ] **Step G5: Commit documentation updates**

```bash
git add docs/superpowers/plans/2026-07-07-docker-compose-activation-build-plan.md
git add 40_Services/compose/README.md
git add 10_Vaults/LifeOS/10_AI_UNIVERSE/Current_Working_State.md
git commit -m "docs: document Docker Compose activation build phase"
```

---

## Rollback Strategy

### Per-Phase Rollback

| Phase | Rollback Action | Side Effects |
|-------|----------------|--------------|
| A | No state changed — nothing to roll back | None |
| B | `docker network rm lifeos_internal` (if created) — only if no containers use it | None |
| C | `docker-compose -f 40_Services/compose/lifeos.yaml stop lifeos-status-api` then `down` to remove container. Or just `stop` to keep container. | Status API unavailable until restarted. No data loss (read-only container). |
| D | If Status API was stopped: restart with `docker-compose start lifeos-status-api`. | None |
| E | `docker-compose -f 40_Services/compose/lifeos.yaml stop lifeos-action-api` then `down`. Restore host-run Action API if it was stopped. | Any captures created during Docker Action API runtime remain in filesystem. Event log entries remain. Telegram bot will get "LifeOS capture unavailable" until Action API is restored. |
| F | n8n never started — nothing to roll back. | None |

### Full Rollback (revert all Docker activation)

```bash
docker-compose -f 40_Services/compose/lifeos.yaml down
# Restore host-run APIs if they were stopped:
# <restore commands per previous state>
```

### Data Safety During Rollback

- Status API is read-only — no data at risk.
- Action API writes to `30_Capture/` and `50_Event_Log/` from within the container using host-mounted volumes. If the container is stopped or removed, the files remain on the host. No data loss.
- Telegram bot offset (`update_offset.json`) is on the host filesystem — unaffected by container state.

### Telegram Service During Rollback

- If Action API container is stopped and no host-run Action API takes over, Telegram bot will fail to create captures. Bot replies with:
  `LifeOS capture unavailable. No action was taken.`
- To restore full service, either:
  - Restart the Docker Action API container
  - Restore the host-run Action API process
- No Telegram bot restart is needed — it reconnects on the next polling cycle.

---

## Risk Analysis

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Port conflict with host-run API | Medium — host-run Action API may be active | High — Docker container fails to start on same port | Phase E pre-check; explicit stop of host process before Docker start |
| `lifeos_internal` network missing | Low — compose validation passes without it | Medium — container fails to attach to network | Phase B creates network if absent |
| Docker build fails due to missing files | Low — Dockerfiles are simple COPY of single files | Low — no service disruption, fix and retry | Build-only step isolated from running services |
| Action API container writes to wrong paths | Low — read-write mounts are explicit | Medium — capture/event-log corruption | Verify with smoke test in Phase E |
| Telegram bot breaks due to Action API host migration | Low — localhost:8788 contract same regardless of Docker/host | Medium — capture creation fails until restored | Rollback defined; Telegram fallback message present |
| Container restart loses state | Low — host volumes persist data | Low — container is ephemeral but data lives on host | Document in README that containers are disposable |
| n8n accidentally activated | Low — uses `manual-start-disabled` profile | High — could start workflows, pull images, expose ingress | Never override profile; add to Do Not Do list |

---

## Recommendation

1. **Approve Phase A + B first** — inspection and network readiness are safe, no service impact. This is the recommended first step.
2. **Then approve Phase C** — Status API build/start/smoke test. Lowest risk. Read-only, hardened container, no mutation surface.
3. **Decide Phase D after C** — decide whether to keep Status API running.
4. **Separate approval for Phase E** — Action API migration requires host-process check, explicit stop approval if needed, and full verification before declaring success.

### Minimum Viable First Activation

If only one container must be activated, choose **Status API only** (Phase C). It:
- Is read-only (lowest risk)
- Provides Telegram `/status` command support
- Validates the compose build pipeline
- Validates the `lifeos_internal` network
- Validates healthcheck mechanism
- Can run alongside host-run Action API without conflict (different ports)
- Easy rollback with no data loss
