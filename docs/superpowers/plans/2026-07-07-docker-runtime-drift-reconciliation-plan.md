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
| `lifeos-status-api` | **RESOLVED** — now unified-compose-owned | Unified compose `compose` project | `compose` | `40_Services/compose/lifeos.yaml` / `/home/lifeos/40_Services/compose` | `127.0.0.1:8787→8787/tcp` | `unless-stopped` | `30_Capture:ro`, `50_Event_Log:ro` | `localhost:8787/health` returns `ok/read_only` | Yes — owned by unified compose | Compose README now shows **Active (adopted)** | Low — resolved | Resolved via Phase 2 adoption |
| `lifeos-action-api` | **RESOLVED** — now unified-compose-owned | Unified compose `compose` project | `compose` | `40_Services/compose/lifeos.yaml` / `/home/lifeos/40_Services/compose` | `127.0.0.1:8788→8788/tcp` | `unless-stopped` (improved from `no`) | `30_Capture:rw`, `50_Event_Log:rw` | `localhost:8788/health` returns `ok/read_write` | Yes — owned by unified compose | Compose README now shows **Active (adopted)** | Low — resolved | Resolved via Phase 5 adoption |
| `n8n_n8n_1` | Running | Legacy `n8n` compose | `n8n` | `docker-compose.yml` / `/home/lifeos/40_Services/n8n` | `127.0.0.1:5678→5678/tcp` | `unless-stopped` | Docker volume `n8n_n8n_data` | Container running; workflow activation NOT verified | Matches compose structure; unified uses different project name (`lifeos-n8n`) | n8n README says "scaffold only — not production active" — contradicts running container | Medium — container is running but no verified active workflows | Decide stop vs tolerate; preserve data volume |
| `lifeos_internal` network | Exists | Created by first compose up | N/A | N/A | N/A | N/A | N/A | N/A | Matches — unified uses `external: true` | Documented correctly | Low — no action needed | Accept as-is |
| Telegram bot service | Active, enabled | systemd user service | N/A | `/home/lifeos/.config/systemd/user/lifeos-telegram-bot.service` | N/A | `enabled` (user session) | N/A | Active (`--poll --interval 3`) | Not in compose — correct | Documented correctly | Low — no action needed | Accept as-is |
| Unified compose baseline (`lifeos.yaml`) | Owns Status API and Action API | Drift reconciliation | `compose` | `40_Services/compose/lifeos.yaml` | N/A | N/A | N/A | N/A | N/A — now owns 2 of 3 services | Updated in Phases 2/5 documentation | Low — resolved for Status/Action API; n8n remains | Accept n8n as tolerated drift |

---

## B. Drift Classification

### `lifeos-status-api`
- **Classification:** **RESOLVED** — adopted under unified compose (Phase 2)
- **Rationale:** Legacy container stopped/removed. Unified compose container running with `127.0.0.1:8787:8787` mapping. Healthy on `localhost:8787/health`.
- **Action:** No further action. Monitor health.

### `lifeos-action-api`
- **Classification:** **RESOLVED** — adopted under unified compose (Phase 5)
- **Rationale:** Manual container stopped/removed. Unified compose container running with `127.0.0.1:8788:8788` and `restart: unless-stopped`. Telegram capture path intact.
- **Action:** No further action. Monitor health. Do not enable `--allow-review`.

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
- **Classification:** **RESOLVED** — now owns Status API and Action API
- **Rationale:** Status API and Action API adopted under unified compose in Phases 2 and 5. Compose README service table updated to reflect active ownership. n8n remains the only unowned container (tolerated temporary drift).
- **Action:** n8n ownership remains deferred. Do not attempt n8n adoption without separate plan and approval.

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

**Status: COMPLETE** (commit 23cecc3)

Steps:
- [x] Record this plan as `docs/superpowers/plans/2026-07-07-docker-runtime-drift-reconciliation-plan.md`
- [x] Add runtime drift entry to `Current_Working_State.md` with the verified runtime truth
- [x] Update `40_Services/compose/README.md` with Runtime Drift Warning section
- [x] Run static validation checks to confirm no unintended changes

**Do NOT execute:**
- `docker-compose up/start/restart/build/pull/create`
- `docker run/build/pull/stop/start/restart/rm`
- `docker network create/rm`
- `systemctl --user stop/start/restart`
- Any container or service modification

### Phase B: n8n stop/tolerate decision plan

**Goal:** Decide whether running localhost-only n8n container is tolerated temporarily or should be stopped.

**Status: COMPLETE** (commit ab5d18c) — Decision: **tolerate temporarily**

Decision: **Tolerate n8n temporarily** (Option A per decision plan). See `docs/superpowers/plans/2026-07-07-n8n-stop-tolerate-decision-plan.md` for full analysis.

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

**Goal:** Plan and execute Status API adoption under unified compose with `localhost:8787` mapping.

**Status: COMPLETE** (commit d6f7757 — execution; preceded by plan at 96062cd)

Adoption executed via Phase 2:
1. Legacy `lifeos-status-api` from `status_api` compose was stopped and removed.
2. Unified compose `lifeos-status-api` was built and started.
3. `localhost:8787/health` now returns `ok/read_only`.
4. `localhost:8787/status` now returns valid JSON.
5. No data loss — read-only container. No other services affected.

### Phase D: Action API adoption plan

**Goal:** Plan and execute Action API adoption under unified compose.

**Status: COMPLETE** (commit 16699bf — execution; preceded by plan at 1e3f727)

Adoption executed via Phase 5:
1. Manual `lifeos-action-api` container (no compose labels, `restart: no`) was stopped and removed.
2. Unified compose `lifeos-action-api` was built and started with `restart: unless-stopped`.
3. `localhost:8788/health` still returns `ok/read_write` — Telegram capture path intact.
4. Status API remained healthy throughout.
5. Telegram was not restarted. No capture outage.

### Phase E: Unified compose ownership migration plan

**Goal:** Unified compose baseline should eventually own all LifeOS Docker services.

**Status: PARTIALLY COMPLETE** — Status API and Action API adopted. n8n remains.

Status:
- `lifeos-status-api` — adopted (Phase 2). No name conflict remaining.
- `lifeos-action-api` — adopted (Phase 5). No restart policy issue remaining.
- `n8n_n8n_1` — **not adopted.** Remains under legacy `n8n` compose project. Tolerated temporary drift.
- `lifeos_internal` network — preserved. Unified compose uses `external: true`.

**Do NOT execute broad `docker-compose down`.** Only adopt n8n via a separate approved plan.

### Phase F: Documentation closeout

**Goal:** Update all documentation to reflect current runtime reality after approved changes.

**Status: COMPLETE** (current commit)

Updates performed:
- `Current_Working_State.md` — runtime drift entry added (23cecc3); Status API adoption recorded (d6f7757); Action API adoption recorded (16699bf); final closeout entry (current commit)
- `40_Services/compose/README.md` — drift warning added (23cecc3); Status API resolved (d6f7757); Action API resolved (16699bf)
- `40_Services/status_api/README.md` — unified compose ownership documented (d6f7757)
- `40_Services/action_api/README.md` — unified compose ownership documented (16699bf)
- `40_Services/n8n/README.md` — stale "scaffold only" claim corrected (current commit)
- `docs/superpowers/plans/2026-07-07-docker-runtime-drift-reconciliation-plan.md` — phases marked complete (current commit)

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

## F. Recommended Next Step (Update — Post Reconciliation)

**Docker runtime drift reconciliation is complete for Status API and Action API.**

Current state:
1. **Status API** — Unified-compose-owned, `localhost:8787`, healthy read-only.
2. **Action API** — Unified-compose-owned, `localhost:8788`, healthy read-write, Telegram capture intact.
3. **n8n** — Tolerated localhost-only drift. No public ingress, no WEBHOOK_URL, no Cloudflare. Workflow activation not verified.
4. **Telegram** — Active, capture-first, no `--allow-review`.

Next deferred phases (no timeline):
- **n8n ownership/adoption** — Requires separate plan and approval if/when desired.
- **Telegram review command live validation** — Requires `--allow-review` test.
- **Cloudflare/webhooks** — Requires domain readiness and separate activation plan.
- **AI proposal pipeline** — Requires controlled file processor design.
- **Controlled file processor** — Requires proposal/approval architecture.
