# n8n Stop/Tolerate Decision Plan

> **For agentic workers:** This is a docs-only planning document. No Docker, systemd, compose, or service state changes are authorized. All stop/start commands are clearly marked "do not run yet."

**Goal:** Decide whether the currently running `n8n_n8n_1` container should be temporarily tolerated as localhost-only drift or stopped in a later approved action.

**Architecture:** n8n is running from legacy `n8n` compose project at `/home/lifeos/40_Services/n8n`. Unified compose defines a separate `lifeos-n8n` service (profile `manual-start-disabled`). This plan determines the treatment of the legacy container only.

**Tech Stack:** Docker, n8n 2.28.7 (Alpine), legacy docker-compose v1.29.2.

## Global Constraints

- No container stop/start/restart in this plan
- n8n data volume `n8n_n8n_data` must never be removed
- No inspection of n8n credentials, database contents, or workflow JSON
- No `docker-compose down -v` ever
- n8n workflow activation status is NOT verified
- Telegram bot remains capture-first, no `--allow-review`

---

## Current n8n Runtime Truth

| Property | Value |
|---|---|
| Container name | `n8n_n8n_1` |
| Image | `n8nio/n8n:latest` (v2.28.7) |
| Status | Running (Up 10+ hours) |
| Restart policy | `unless-stopped` (survives host reboot) |
| Port binding | `127.0.0.1:5678→5678/tcp` |
| Network | `lifeos_internal` (172.20.0.3/16) |
| Compose project | `n8n` (legacy) |
| Compose file | `docker-compose.yml` at `/home/lifeos/40_Services/n8n` |
| Data volume | `n8n_n8n_data` (Docker named volume at `/var/lib/docker/volumes/n8n_n8n_data/_data`) |
| Workflow activation | Not verified — external inspection cannot confirm |
| HTTP surface | Responds HTTP 200 at `http://localhost:5678/` (n8n UI) |

## Public Exposure Check

| Check | Result |
|---|---|
| `ss -ltnp \| grep ':5678'` | `127.0.0.1:5678` only — no `0.0.0.0` |
| Unified compose `0.0.0.0` bind | None found |
| `WEBHOOK_URL` in unified compose | Not present |
| Cloudflare/cloudflared in unified compose | Not present |
| HTTP headers from `localhost:5678` | No `x-forwarded-*` headers, no public origin hints |

**Conclusion: No public exposure. n8n is localhost-only.**

## Risk Classification

**Classification: Tolerated temporary drift**

Evidence:
- Localhost-only binding (`127.0.0.1:5678`) — no public ingress
- No `WEBHOOK_URL` configured
- No Cloudflare tunnel or cloudflared active
- Restart policy `unless-stopped` — container persists across reboots (acceptable for localhost-only)
- Workflow activation not verified — no evidence of active automated workflows
- Legacy compose ownership — container is not under unified compose management
- Connected to `lifeos_internal` — can reach other LifeOS containers internally (acceptable for localhost-only, pre-existing architecture)
- Risk of unauthorized internal access is low — `lifeos_internal` is a bridge network not exposed externally
- Primary risk: undocumented drift; future operator unaware of running container

**Rationale for not classifying higher:** No public exposure path exists. No webhook or tunnel activation. The container is isolated to localhost. The main concern is documentation gap and ownership drift, not an active security threat.

---

## Decision Options

### Option A — Tolerate n8n temporarily (Recommended)

| Pros | Cons | Conditions | Required Docs | Next Follow-up |
|---|---|---|---|---|
| No risk of breaking n8n data or workflows | Container runs outside unified compose management | No public ingress present (verified) | Current_Working_State.md already updated | Before any future webhook/tunnel activation |
| No service disruption to Telegram or other APIs | n8n README says "scaffold only" (stale) | No WEBHOOK_URL or Cloudflare active (verified) | Compose README already updated | Before unified compose ownership migration (Phase E of reconciliation plan) |
| No need to re-provision n8n later | Workflow activation status unknown | Unified compose n8n remains `manual-start-disabled` | This decision plan documents the toleration decision | |
| n8n UI remains available for local manual development | Continued documentation-to-runtime gap | `n8n_n8n_data` volume must be preserved | | |
| `unless-stopped` restart policy ensures uptime | | No `--allow-review` on Telegram bot | | |

### Option B — Controlled stop of n8n

| Pros | Cons | Preconditions | Rollback | Data Volume Preservation | Verification Commands |
|---|---|---|---|---|---|
| Aligns runtime with "scaffold only" documentation | Loses n8n UI access for local manual development | Approval from LifeOS operator | `docker start n8n_n8n_1` (restart existing container) | `n8n_n8n_data` volume persists after `docker stop` — never run `docker-compose down -v` | `docker ps \| grep n8n` — expect no match |
| Eliminates drift between plan and runtime | Any running workflows would be interrupted (if any — unknown) | Verify no operator actively using n8n UI | Or `docker-compose -f 40_Services/n8n/docker-compose.yml start n8n` | Volume will be re-attached on container restart | `curl -sS http://localhost:5678/` — expect connection refused |
| Cleaner baseline for unified compose ownership later | Requires re-start before next n8n usage | Document the stop in Current_Working_State.md | No data loss — volume is preserved | Do not run: `docker volume rm n8n_n8n_data` | `docker volume ls \| grep n8n_n8n_data` — expect volume still present |
| | | Update n8n README to reflect actual state (stopped but container exists) | | | |

**Execution (do not run yet — requires separate approval):**
```bash
# Stop n8n container (not approved in this plan)
docker stop n8n_n8n_1

# Verify stop
docker ps --filter name=n8n_n8n_1

# Verify volume preserved
docker volume ls | grep n8n_n8n_data
```

### Option C — Adopt n8n later under unified compose

| Pros | Cons | Preconditions | Why Not Now |
|---|---|---|---|
| Single source of truth for all LifeOS containers | Unified compose n8n has different service name (`lifeos-n8n`) and profile (`manual-start-disabled`) | Status API localhost mapping resolved (Phase C of reconciliation plan) | Status API and Action API drifts must be reconciled first |
| Unified logging, healthchecks, security settings | Legacy container must be stopped before unified one can start on port 5678 | Action API drift resolved or adoption deferred plan approved | Action API cannot be touched until its drift is reconciled |
| Consistent restart policy and network config | Data volume naming may differ (`n8n_n8n_data` vs `n8n_data`) | n8n toleration/stop decision made (this plan) | This is Phase E of the reconciliation plan — not yet reached |
| | Requires migration of data volume reference | Unified compose n8n can use same volume by referencing `n8n_n8n_data` as `external: true` | |

---

## Recommendation

**Tolerate n8n temporarily (Option A).**

Rationale:
1. No public exposure exists — `127.0.0.1:5678` only, no `WEBHOOK_URL`, no Cloudflare.
2. No urgent security threat — internal bridge network only, no tunnel, no webhook.
3. Stopping n8n provides no immediate benefit — it does not consume external resources, does not expose a public surface, and does not conflict with any active service.
4. Stopping n8n would lose local n8n UI access for manual testing/development (e.g., the Status API manual-trigger workflow test).
5. The priority order from the reconciliation plan is: Status API mapping first, then Action API adoption, then unified compose ownership. n8n toleration is the least urgent drift.
6. The documentation gap has already been addressed in `Current_Working_State.md` and `40_Services/compose/README.md`.

Conditions for revisiting this decision:
- If a future plan activates webhooks, tunnels, or public ingress for n8n
- If unified compose ownership migration (Phase E) begins
- If n8n becomes a blocker for Status API or Action API work (unlikely — different ports)

---

## Future Controlled Stop Procedure

**Do not run these commands in this plan. Included for future reference only.**

```bash
# 1. Pre-stop verification
docker ps --filter name=n8n_n8n_1
echo "Verify n8n_n8n_data volume exists:"
docker volume ls | grep n8n_n8n_data

# 2. Stop n8n container
docker stop n8n_n8n_1

# 3. Verify stop
docker ps --filter name=n8n_n8n_1

# 4. Verify volume preserved
docker volume ls | grep n8n_n8n_data

# 5. Verify port is free
ss -ltnp | grep ':5678' || echo "Port 5678 is free"
```

Never run:
```bash
docker-compose -f 40_Services/n8n/docker-compose.yml down -v  # destroys volume
docker volume rm n8n_n8n_data                                   # destroys data
```

---

## Future Rollback Procedure

If n8n was stopped and needs to be restarted:

```bash
# Option A: Restart existing container (preferred — preserves all state)
docker start n8n_n8n_1

# Option B: Start via legacy compose
docker-compose -f 40_Services/n8n/docker-compose.yml start n8n

# Verify
docker ps --filter name=n8n_n8n_1
curl -sS http://localhost:5678/ | head -5
```

---

## Data-Volume Preservation Warning

- `n8n_n8n_data` is a Docker named volume at `/var/lib/docker/volumes/n8n_n8n_data/_data`
- It contains n8n workflow state, credentials (encrypted), and configuration
- **Never remove this volume** without explicit backup + approval
- `docker stop` does not remove volumes — safe
- `docker-compose down` (without `-v`) does not remove named volumes — safe
- `docker-compose down -v` removes volumes — **never run this**
- `docker volume rm n8n_n8n_data` — **never run this**
- Volume will be re-attached automatically when the container restarts

---

## Public Exposure Guardrails

If any future plan proposes activating n8n webhooks, tunnels, or public ingress:

- [ ] Verify no `0.0.0.0` bind in compose config before start
- [ ] Verify `WEBHOOK_URL` is only set when tunnel/webhook is explicitly approved
- [ ] Cloudflare tunnel config must restrict to `/webhook/*` only (n8n UI never public)
- [ ] n8n basic auth must stay active for localhost UI access
- [ ] n8n activation checklist must be fully reviewed before any public exposure
- [ ] Separate approval required per Phase B3+ of the Telegram Control Plane roadmap

---

## Explicit Note

n8n workflow activation status is **not verified**. No claim is made about whether any n8n workflows are active, scheduled, or have ever been executed. This plan does not inspect n8n credentials, database, or workflow definitions. The container is running; the workflow state is unknown.
