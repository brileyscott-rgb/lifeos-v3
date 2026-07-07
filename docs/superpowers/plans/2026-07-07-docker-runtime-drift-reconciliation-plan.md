# Docker Runtime Drift Reconciliation Plan

> **For agentic workers:** This is a docs-only planning document. No Docker, systemd, compose, or service state changes are authorized. Every phase explicitly lists what may and may not be executed.

**Goal:** Align LifeOS documentation and next-step planning with actual Docker runtime state without changing any runtime state.

**Architecture:** The unified Docker Compose baseline (`40_Services/compose/lifeos.yaml`) exists as a static definition but does not own the running containers. Three containers are active from two legacy compose projects plus one manual-start container. This plan categorizes each drift, documents the reconciliation path, and provides rollback-safe next steps.

**Tech Stack:** docker-compose v1.29.2, Docker engine, systemd user services.

## Global Constraints

- No Docker/systemd/service state changes in any phase unless explicitly listed as executable
- No broad `docker-compose down` or `docker-compose rm` without per-container approval
- No removal of n8n data volume (`n8n_n8n_data`)
- No breakage of Action API at `localhost:8788` — Telegram capture path must survive
- Telegram bot remains capture-first systemd user service (`--poll --interval 3`, no `--allow-review`)
- `30_Capture/` and `50_Event_Log/` must be preserved at all times
- Do not inspect secrets or `.env` contents
- n8n workflow activation status is NOT verified — do not claim workflows are active
- All documentation corrections distinguish historical claims (true at the time) from current-state claims

---

## A. Runtime Truth Table

| Component / Container | Current State | Origin / Owner | Compose Project | Compose File / Working Dir | Port Exposure | Restart Policy | Mounts / Data Access | Health Status | Matches Unified Compose Baseline? | Current Documentation Status | Risk Level | Recommended Handling |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `lifeos-status-api` | Running | Legacy `status_api` compose | `status_api` | `40_Services/status_api/docker-compose.yml` / `/home/lifeos/40_Services/status_api` | Container-only 8787/tcp (no host mapping) | `unless-stopped` | `30_Capture:ro`, `50_Event_Log:ro` | Internal healthy; `localhost:8787` unreachable | Partial — image/build differs; no `127.0.0.1:8787` mapping; similar mounts | Compose README says "Defined, not started" — contradicts running state | Medium — unreachable from host; no migration path | Tolerate temporarily; plan recreate with localhost mapping |
| `lifeos-action-api` | Running | Likely manual `docker run` (no compose labels) | (empty) | (empty) — no compose origin | `127.0.0.1:8788→8788/tcp` | `no` | `30_Capture:rw`, `50_Event_Log:rw` | `localhost:8788/health` returns `ok/read_write` | Partial — image name differs; no compose labels; manual start | Compose README says "Defined, not started" — contradicts running state | High — mutation surface; no restart policy; serves live Telegram path | Do not touch; leave untouched until n8n/Status drift reconciled |
| `n8n_n8n_1` | Running | Legacy `n8n` compose | `n8n` | `docker-compose.yml` / `/home/lifeos/40_Services/n8n` | `127.0.0.1:5678→5678/tcp` | `unless-stopped` | Docker volume `n8n_n8n_data` | Container running; workflow activation NOT verified | Matches compose structure; unified uses different project name (`lifeos-n8n`) | n8n README says "scaffold only — not production active" — contradicts running container | Medium — container is running but no verified active workflows | Decide stop vs tolerate; preserve data volume |
| `lifeos_internal` network | Exists | Created by first compose up | N/A | N/A | N/A | N/A | N/A | N/A | Matches — unified uses `external: true` | Documented correctly | Low — no action needed | Accept as-is |
| Telegram bot service | Active, enabled | systemd user service | N/A | `/home/lifeos/.config/systemd/user/lifeos-telegram-bot.service` | N/A | `enabled` (user session) | N/A | Active (`--poll --interval 3`) | Not in compose — correct | Documented correctly | Low — no action needed | Accept as-is |
| Unified compose baseline (`lifeos.yaml`) | Static definition only | Current task | N/A | `40_Services/compose/lifeos.yaml` | N/A | N/A | N/A | N/A | N/A — owns no containers | Created 2026-07-07; services listed as "Defined, not started" | Medium — documented state contradicts reality | Add drift warning; update current-state docs |

---

## B. Drift Classification

### `lifeos-status-api`
- **Classification:** Accepted current runtime; requires future stop/recreate planning
- **Rationale:** Container is healthy and correct in behavior but unreachable from host. Documentation says not started.
- **Action:** Documentation correction first. Plan recreate with `127.0.0.1:8787` mapping. Do not recreate yet.

### `lifeos-action-api`
- **Classification:** Accepted current runtime; requires immediate action to never touch
- **Rationale:** Serving live Telegram capture path at `localhost:8788`. No compose ownership. No restart policy. High risk of disruption.
- **Action:** Do not touch. Document as manual/unlabeled container. Leave untouched until Status API and n8n drifts are reconciled.

### `n8n_n8n_1`
- **Classification:** Tolerated temporary drift; requires stop/defer decision
- **Rationale:** Container running from legacy compose. n8n README and compose README both say scaffold-only / not started. Workflow activation status not verified.
- **Action:** Decide whether to stop or tolerate. If stopped, preserve `n8n_n8n_data` volume. Do not stop in this plan — decide in Phase B.

### `lifeos_internal` network
- **Classification:** Accepted current runtime
- **Rationale:** Exists, contains all three containers. Matches unified baseline expectation.
- **Action:** No action needed.

### Telegram bot service
- **Classification:** Accepted current runtime
- **Rationale:** Correctly documented as systemd user service outside compose. Capture-first, no `--allow-review`.
- **Action:** No action needed.

### Unified compose baseline
- **Classification:** Documentation drift; ownership drift
- **Rationale:** Exists as static definition but does not own running containers. Compose README claims "Defined, not started" for all services — contradicts runtime.
- **Action:** Add drift warning. Update service status table. Do not attempt to claim ownership until per-container adoption plans are approved.

---

## C. Documentation Contradiction Review

### Contradictions found

| Document | Claim | Runtime Truth | Severity |
|---|---|---|---|
| `40_Services/compose/README.md` service table | `lifeos-status-api`: "Defined, not started" | Container is running (legacy compose) | High — current-state claim contradicts reality |
| `40_Services/compose/README.md` service table | `lifeos-action-api`: "Defined, not started" | Container is running (manual, no compose labels) | High — current-state claim contradicts reality |
| `Current_Working_State.md` line 122 | "No containers started, built, or pulled" (from baseline entry) | This was historically true at the time of baseline creation. Running containers pre-date or are independent of the unified baseline. | Does NOT contradict — this was a historical implementation claim about the baseline task. It did not assert no containers were running system-wide. However, it may be misinterpreted. |
| `40_Services/n8n/README.md` | "Status: scaffold only — not production active" | Container is running. Workflow activation status is not verified. | Medium — "scaffold only" implies not started. Container existence contradicts this. |
| `40_Services/n8n/README.md` line 27 | "Local-only binding by default" | Correct — `127.0.0.1:5678`. | No contradiction. |
| `40_Services/status_api/README.md` | "docker-compose up -d" as deployment instruction | Container is running via legacy compose; this instruction would create a second container. | Low — the README describes intended/possible deployment, not current state. Clear once drift is documented. |
| `40_Services/action_api/README.md` | Documents both localhost active path and Docker inactive path | Correct — `localhost:8788` active from container, Docker service DNS inactive. | No contradiction. Well-documented. |

### Key distinction

- **"No containers started, built, or pulled"** (Current_Working_State.md baseline entry) — This was an accurate description of the unified compose baseline creation task. The unified compose file was created, validated, and committed without starting containers. This does NOT claim that no Docker containers exist system-wide. However, the proximity of this claim to the compose README service table (which says "Defined, not started") creates an impression that nothing is running.

- **Correction needed:** The compose README service table needs current-state status. The baseline entry in Current_Working_State.md needs a clarifying follow-up entry that runtime drift exists.

---

## D. Reconciliation Phases

### Phase A: Docs-only correction of actual runtime truth

**Goal:** Record current Docker runtime drift without any service changes.

**Executable now — docs/planning only.**

Steps:
- [ ] Record this plan as `docs/superpowers/plans/2026-07-07-docker-runtime-drift-reconciliation-plan.md`
- [ ] Add runtime drift entry to `Current_Working_State.md` with the verified runtime truth
- [ ] Update `40_Services/compose/README.md` with Runtime Drift Warning section
- [ ] Run static validation checks to confirm no unintended changes

**Do NOT execute:**
- `docker-compose up/start/restart/build/pull/create`
- `docker run/build/pull/stop/start/restart/rm`
- `docker network create/rm`
- `systemctl --user stop/start/restart`
- Any container or service modification

### Phase B: n8n stop/defer decision plan

**Goal:** Decide whether running localhost-only n8n container is tolerated temporarily or should be stopped.

**Not executable yet — requires separate decision.**

Decision options:
1. **Tolerate (recommended unless risk is clear):** Leave n8n running localhost-only. Document that workflow activation is not verified. No container changes. Low risk if `127.0.0.1:5678` remains local-only.
2. **Stop n8n container:** Stop the legacy `n8n_n8n_1` container. Requires rollback notes and data volume preservation.

If future stop is chosen:
```bash
# Stop n8n container (do NOT run without approval)
docker stop n8n_n8n_1

# Do NOT remove — preserve the n8n_n8n_data volume
# docker rm n8n_n8n_1  # NOT authorized
```

Rollback (if stopped):
```bash
# Restart n8n from legacy compose
cd /home/lifeos/40_Services/n8n
docker-compose start n8n
# Or from unified compose with profile override
docker-compose -f 40_Services/compose/lifeos.yaml --profile manual-start-disabled up -d lifeos-n8n
```

**Data safety:**
- n8n data volume `n8n_n8n_data` must never be removed without explicit backup + approval
- Stopping the container does not remove the volume
- Workflow JSON exports in `40_Services/n8n/workflows/exported/` are git-tracked or will be added separately

**Do NOT:**
- Claim n8n workflows are active (not verified)
- Delete or export n8n workflows during stop
- Remove the n8n data volume

### Phase C: Status API localhost mapping adoption/recreate plan

**Goal:** Plan how to make Status API reachable on `localhost:8787`.

**Not executable yet — requires separate plan after Phase A is approved.**

Current state: Legacy `lifeos-status-api` container is healthy internally (`lifeos_internal`) but has no `127.0.0.1:8787` host port mapping. `localhost:8787` is free.

Future options:
1. **Recreate via unified compose:** `docker-compose -f 40_Services/compose/lifeos.yaml up -d lifeos-status-api` — would start a new container with `127.0.0.1:8787:8787` mapping. The existing legacy container must be stopped first to avoid port conflict (it uses internal-only 8787, so technically no port conflict exists on host).
2. **Adopt existing container:** Modify the legacy container to add port mapping. Less clean than recreate.
3. **Combined approach:** Stop the legacy `lifeos-status-api` container (no data loss — read-only container), then start the unified compose Status API.

**Important:** The legacy `lifeos-status-api` and the unified `lifeos-status-api` have different image names and compose project labels. They are distinct containers that cannot both claim the name `lifeos-status-api` on the same network.

**Do NOT recreate in this phase.**

### Phase D: Action API adoption plan

**Goal:** Plan how to bring Action API under compose ownership.

**Not executable yet — deferred until Phase B and Phase C are resolved.**

Current state: `lifeos-action-api` is serving live Telegram capture path at `localhost:8788`. No compose labels. No restart policy (`restart: no`).

Constraints:
- `localhost:8788` must remain functional throughout — Telegram polling depends on it
- Do not touch Action API until Status API and n8n drifts are reconciled
- Any restart or replacement risks a gap in Telegram capture service

Future options:
1. **Adopt via unified compose:** Stop the manual container, start the unified compose Action API. Risk of brief capture outage during swap.
2. **Leave as-is indefinitely:** Manual container with no restart policy is fragile. A host reboot would leave Action API down until manually started.
3. **Add `--restart unless-stopped` to existing container:** Minimal change, no outage. Requires `docker update`.

**Do NOT touch Action API in this plan. Future plans must include:**
- Rollback steps (restore manual container)
- Telegram capture verification after any change
- Event log continuity check

### Phase E: Unified compose ownership migration plan

**Goal:** Unified compose baseline should eventually own all LifeOS Docker services.

**Not executable yet — depends on Phase C and Phase D.**

Issues to resolve:
- **Name conflicts:** Legacy `lifeos-status-api` (from `status_api` project) conflicts with unified `lifeos-status-api` (from unified compose). The unified container name `lifeos-status-api` cannot be created while the legacy one exists with the same name.
- **Legacy project `status_api`:** `docker-compose -f 40_Services/status_api/docker-compose.yml down` would stop the legacy Status API. This is the cleanest way to free the name.
- **Manual Action API:** No compose project commands apply. Must be stopped individually.
- **Legacy n8n project:** `docker-compose -f 40_Services/n8n/docker-compose.yml down` would stop n8n. Use carefully — preserves volume.
- **Network:** `lifeos_internal` already exists and is used by all containers. Unified compose uses `external: true`. No network change needed.

**Do NOT execute broad `docker-compose down` until per-container ownership is clearly understood.**

### Phase F: Documentation closeout

**Goal:** Update all documentation to reflect current runtime reality after approved changes.

- Update `Current_Working_State.md` after each phase
- Update `40_Services/compose/README.md` status table
- Update `40_Services/status_api/README.md` if Status API is recreated
- Update `40_Services/action_api/README.md` if Action API is adopted
- Update `40_Services/n8n/README.md` if n8n is stopped or configuration changes

---

## E. Rollback Principles

1. **No broad `docker-compose down` or `docker-compose rm`** without explicit per-container approval. The unified compose must never run `docker-compose down` while it does not own the containers — this would have no effect on legacy containers, but the command should not be normalized.

2. **Do not remove n8n data volume** — `n8n_n8n_data` contains workflow state and credentials. It must be preserved even if the container is stopped.

3. **Do not break `localhost:8788` Action API path** — Telegram capture depends on it. Any Action API change must include verification that Telegram capture still works.

4. **Telegram bot remains capture-first** — `--poll --interval 3`, no `--allow-review`. Documentation and service state must stay in sync.

5. **Preserve `30_Capture/` and `50_Event_Log/`** at all times. No container operation should delete, move, or reformat these directories.

6. **If a container change fails mid-operation:**
   - Stop and assess. Do not proceed to next step.
   - If the legacy container is stopped but the unified container failed to start, restart the legacy container.
   - If mounts are wrong, stop the unified container and restore legacy mounts.
   - If Telegram capture is broken after Action API change, restore the manual Action API container and verify capture.

---

## F. Recommended Next Step

1. **Docs-only correction first (Phase A)** — Record the runtime drift truth. This covers the current task. No service changes.

2. **Then decide whether to stop or tolerate n8n (Phase B)** — As a separate plan/decision. Localhost-only n8n with no verified active workflows is low risk. Stopping it is optional.

3. **Then plan Status API localhost:8787 mapping (Phase C)** — Status API is read-only, lowest risk for actual migration. Requires stopping the legacy container and starting the unified one. Simple rollback.

4. **Leave Action API untouched (Phase D)** — Do not touch the live Telegram capture path until all other drifts are reconciled. This is the last container to adopt.

5. **Pause unified compose activation** — Do not run `docker-compose up` or `docker-compose build` until the drift reconciliation plan is reviewed and each per-container adoption is separately approved.
