# LifeOS Docker Compose Baseline Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a safe, local-only unified Docker Compose baseline that documents and centralizes existing LifeOS Docker service definitions without starting containers, changing service state, or expanding public exposure.

**Architecture:** A single `40_Services/compose/lifeos.yaml` that defines Docker-capable services for Status API, Action API, and n8n scaffold. The unified file consolidates definitions from three existing compose files. No service migration occurs — the active Telegram bot contract remains `http://localhost:8788` and `http://localhost:8787` via host-mapped ports. No service activation occurs in this phase.

**Tech Stack:** Docker Compose (v1 baseline), Python 3.12-alpine (Status API, Action API), n8nio/n8n (scaffold-only).

> **Host tooling note:** Current host has `docker-compose` v1.29.2. The `docker compose` v2 plugin is not available. All validation commands in this plan use `docker-compose`. The unified `lifeos.yaml` is the validated baseline (no `name:` top-level key, v1-compatible). The legacy automation compose at `40_Services/compose/automation/compose.yaml` still contains `name:` and will fail under docker-compose v1; it is preserved as reference-only.

## Global Constraints

- No secrets committed — all config via `.env.example` only
- No public ingress — all ports bind `127.0.0.1` only
- No service activation in this phase — n8n uses `manual-start-disabled` profile
- All containers: `cap_drop: ALL`, `no-new-privileges: true`, non-root user
- All containers join `lifeos_internal` network only
- Runtime artifacts (30_Capture/*, 50_Event_Log/events.jsonl, n8n_data/) are never committed
- `lifeos_internal` network expected to already exist (`external: true`)
- No container build, pull, or start in baseline phase — static validation only
- Existing compose files are preserved as legacy/reference — not removed, not aggressively deprecated

---
## Current Service Inventory

| Service | Run method | Containerized? | Port | Status |
|---|---|---|---|---|
| Telegram bot | systemd user service | No | N/A | Active, capture-first, no `--allow-review` |
| Status API | Docker via compose | Yes — has Dockerfile + compose | 8787 | Previously built and validated |
| Action API | Docker via compose | Yes — has Dockerfile + compose | 8788 | Previously built and run via Docker |
| n8n | Compose scaffold only | Has Docker image | 5678 | Inactive — scaffold only, never started |
| Cloudflared | Compose example only | Has example compose | N/A | Inactive — template only |

---
## Unified Compose File Scope

**Single unified file:** `40_Services/compose/lifeos.yaml`

**Purpose:** Centralize all LifeOS Docker service definitions in one file. The unified file defines Docker-capable services for Status API, Action API, and n8n scaffold. It does not migrate or activate any service.

**Active Telegram contract remains unchanged:**
- Telegram bot calls `http://localhost:8788` (Action API) and `http://localhost:8787` (Status API)
- These host ports are mapped from Docker container ports by the compose definition
- No code changes to the Telegram bot
- No service migration occurs during baseline planning

**Existing compose files:** `40_Services/n8n/docker-compose.yml`, `40_Services/status_api/docker-compose.yml`, `40_Services/compose/automation/compose.yaml` are preserved as-is for reference. A legacy/reference notice is added to each. They remain valid for their original scope until the unified baseline is verified and explicitly activated.

---
## Proposed Service Definitions

### 1. `lifeos-status-api`

- **Build context:** `40_Services/status_api/`
- **Port:** `127.0.0.1:8787:8787`
- **Read-only:** `read_only: true`, `tmpfs: /tmp:noexec,nosuid,size=1m`
- **Bind mounts:** `../../30_Capture:/lifeos/capture:ro`, `../../50_Event_Log:/lifeos/event-log:ro`
- **Healthcheck:** `GET /health` → 200
- **Security:** `cap_drop: ALL`, `no-new-privileges`, non-root (uid 1001)

### 2. `lifeos-action-api`

- **Build context:** `40_Services/action_api/`
- **Port:** `127.0.0.1:8788:8788`
- **Bind mounts:** `../../30_Capture:/lifeos/capture:rw`, `../../50_Event_Log:/lifeos/event-log:rw`
- **Healthcheck:** `GET /health` → 200
- **Security:** `cap_drop: ALL`, `no-new-privileges`, non-root (uid 1001)

### 3. `lifeos-n8n` (scaffold-only, not started)

- **Image:** `n8nio/n8n:latest`
- **Profile:** `manual-start-disabled`
- **Port:** `127.0.0.1:5678:5678`
- **Named volume:** `n8n_data:/home/node/.n8n`
- **No `env_file` — all config via `${VAR:-default}` substitution**
- **No `WEBHOOK_URL` — no webhook activation**
- **Restart:** `no`
- **Security:** `cap_drop: ALL`, `no-new-privileges`, non-root via upstream image defaults (not explicitly set until activation review)

---
## Internal Network Model

- **Network name:** `lifeos_internal`
- **Scope:** `external: true` — the compose file expects the network to already exist
- **Service DNS (inactive until activation):** `lifeos-status-api:8787`, `lifeos-action-api:8788`, `lifeos-n8n:5678`
- **Activation prerequisite (not run in planning phase):**
  ```bash
  docker network inspect lifeos_internal || docker network create lifeos_internal
  ```
- **Current Telegram bot contract:** The systemd Telegram bot uses `http://localhost:8788` and `http://localhost:8787` (host-mapped ports). It does not join `lifeos_internal`. This is the correct interim design — the bot runs outside Docker and reaches APIs via host-mapped ports. When the bot is eventually containerized, it will join `lifeos_internal` and use service DNS.
- **No network recreation:** The existing `lifeos_internal` network is not replaced or auto-recreated. The `external: true` declaration prevents accidental network management by Docker Compose.

---
## Volume / Runtime Artifact Policy

| Path | Type | Git-tracked? | Notes |
|---|---|---|---|
| `30_Capture/` | Bind mount (rw for action, ro for status) | No — canonical operational records | Backup policy TBD |
| `50_Event_Log/events.jsonl` | Bind mount (rw for action, ro for status) | No — canonical operational records | Backup policy TBD |
| `n8n_data` | Named Docker volume | No — service runtime state | Destroyable, re-creatable |
| `.env` files | Host file | No — local operator config (tracked by exception via `.env.example`) | Per Runtime Artifact Policy |

---
## .env.example Strategy

**Single centralized `.env.example`:** `40_Services/compose/.env.example`

Consolidates env vars from existing `.env.example` files:
- `40_Services/n8n/.env.example`
- `40_Services/compose/automation/.env.example`

**Contents (example only — no real secrets):**

```bash
# =============================================================================
# LifeOS Docker Compose — Example Environment Variables
# =============================================================================
# This file is documentation only. The compose file uses ${VAR:-default}
# substitution — no env_file reference. docker-compose config works without
# a real .env file.
#
# .env is gitignored — do not commit secrets.
#
# NOTE: N8N_ENCRYPTION_KEY is a future activation placeholder. It is not
# consumed by the baseline compose unless explicitly added during n8n
# activation planning.
# =============================================================================

# n8n server configuration
N8N_HOST=localhost
N8N_PORT=5678
N8N_PROTOCOL=http
N8N_TIMEZONE=America/Chicago
N8N_USER_FOLDER=/home/node/.n8n
N8N_DIAGNOSTICS_ENABLED=false
N8N_PERSONALIZATION_ENABLED=false
N8N_VERSION_NOTIFICATIONS_ENABLED=false
N8N_ENCRYPTION_KEY=replace_with_real_secret_later

# Basic authentication for n8n
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=change_me
N8N_BASIC_AUTH_PASSWORD=change_me

# Action API
ACTION_API_PORT=8788

# Status API
STATUS_API_PORT=8787
```

**Per-service `.env.example` files** at `40_Services/n8n/.env.example`, `40_Services/secrets/.env.example` remain as reference for their respective modules.

**Important:** The n8n compose service uses `${VAR:-default}` environment substitution — no `env_file: .env` is used. This allows `docker-compose config` to validate successfully without a real `.env` file. The `.env.example` is documentation only.

---
## Action API Handling

**Service definition location:** The unified compose file defines the Action API as a Docker service. The Action API is already containerized (validated via Docker compose in prior phases).

**Active Telegram contract:** The Telegram bot calls the Action API at `http://localhost:8788`. Docker maps the container port `8788` to `127.0.0.1:8788` on the host. No code change to the Telegram bot is needed.

**Docker service DNS path** (`http://lifeos-action-api:8788`) is prepared in the compose definition but is **not the active contract** until a separate activation step confirms it.

**Action API Dockerfile** already exists at `40_Services/action_api/Dockerfile`. No changes needed.

**No service migration occurs in this phase.** The compose file is a documentation/centralization artifact only.

---
## Status API Handling

**Service definition location:** The unified compose file defines the Status API as a Docker service.

**Active Telegram contract:** The Telegram bot calls the Status API at `http://localhost:8787` — no code change needed.

**Status API Dockerfile** already exists at `40_Services/status_api/Dockerfile`. No changes needed.

---
## n8n Placeholder / Local-Only Handling

- n8n service uses `profiles: ["manual-start-disabled"]` — will not start on `docker-compose up`
- No `WEBHOOK_URL`, no Telegram webhook trigger, no public ingress
- `restart: "no"` — explicit manual start only
- **No `env_file: .env`** — all configuration via `${VAR:-default}` environment substitution
- **No image pull** is required for baseline validation. Image is pulled only when explicitly approved for activation.
- Workflows, security boundaries, activation checklist remain as-is (scaffold-only)
- n8n admin UI accessible only at `http://localhost:5678` with basic auth when manually started

---
## Healthchecks

```yaml
healthcheck:
  test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8787/health')"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s
```

Both `lifeos-status-api` and `lifeos-action-api` get healthchecks that call their `/health` endpoints. n8n does not get a healthcheck (scaffold-only, not started).

---
## Logging Policy

- Default Docker json-file driver
- `max-size: 10m`
- `max-file: 3`
- No logs committed to git
- Service logs are runtime state (per Runtime Artifact Tracking Policy)

---
## Security Boundaries

Applied uniformly across all services:

| Setting | Enforcement |
|---|---|
| `cap_drop: ALL` | All services |
| `security_opt: no-new-privileges:true` | All services |
| Non-root user | API services via Dockerfiles (uid 1001); n8n via upstream image defaults |
| `read_only: true` | Status API only (write-not-needed) |
| Network | `lifeos_internal` only — no `host` network mode |
| Port binding | `127.0.0.1` only — no `0.0.0.0` |
| No Docker socket | No `/var/run/docker.sock` mounts |
| No secrets in compose | `.env.example` only; `${VAR:-default}` substitution; no `env_file:` reference |
| No vault access | No `10_Vaults/` mounts |
| No shell execution | Python stdlib HTTP servers, no subprocess |

---
## Explicit Deferrals (Not in Compose)

The following are explicitly **not added** to the unified compose file:

1. **Cloudflare tunnel (cloudflared)** — Remains at `40_Services/n8n/cloudflared/docker-compose.cloudflared.example.yml`. Not merged into unified compose.
2. **Telegram webhook mode** — No webhook trigger, no `WEBHOOK_URL`, no public ingress.
3. **Public ingress** — All ports bound to `127.0.0.1`. No `0.0.0.0` exposure.
4. **AI proposal pipeline** — No AI worker, no proposal generation, no model nodes.
5. **Controlled file processor** — No file processor service, no vault-write authority.
6. **Kubernetes / homelab expansion** — No K8s manifests, no homelab service definitions.
7. **Telegram bot containerization** — Bot stays as systemd user service. Containerization is future work.
8. **n8n workflow activation** — n8n remains scaffold-only, not started, no workflows active.
9. **External secrets management** — No HashiCorp Vault, no Docker secrets, no external KMS.

---
## Step-by-Step Implementation Plan

All paths relative to `/home/lifeos`.

### Commit 1: Add unified Compose baseline file and .env.example only

#### Task 1.1: Create unified compose file `40_Services/compose/lifeos.yaml`

**Files:**
- Create: `40_Services/compose/lifeos.yaml`

**Interfaces:**
- Consumes: existing `40_Services/action_api/Dockerfile`, `40_Services/status_api/Dockerfile`, n8n image
- Produces: a single runnable compose file (static validation only — no container operations)

- [ ] **Step 1: Write `40_Services/compose/lifeos.yaml`**

```yaml
x-lifeos-boundary:
  status: baseline
  notes: >
    Unified Docker Compose baseline for LifeOS V3 local services.
    No public ingress, no secrets in config, no service activation without
    explicit approval. Telegram bot remains a systemd user service outside
    this compose. Cloudflare tunnel, Telegram webhook, AI proposal pipeline,
    and controlled file processor remain explicitly deferred.
    This file defines Docker-capable services. Active Telegram contract
    remains localhost:8788 and localhost:8787. No service migration occurs
    in the baseline phase.

services:
  lifeos-status-api:
    build: ../status_api
    container_name: lifeos-status-api
    restart: unless-stopped
    read_only: true
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    tmpfs:
      - /tmp:noexec,nosuid,size=1m
    networks:
      - lifeos_internal
    ports:
      - "127.0.0.1:${STATUS_API_PORT:-8787}:8787"
    volumes:
      - ../../30_Capture:/lifeos/capture:ro
      - ../../50_Event_Log:/lifeos/event-log:ro
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; exit(0 if urllib.request.urlopen('http://localhost:8787/health').status == 200 else 1)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    logging:
      driver: json-file
      options:
        max-size: 10m
        max-file: "3"

  lifeos-action-api:
    build: ../action_api
    container_name: lifeos-action-api
    restart: unless-stopped
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    networks:
      - lifeos_internal
    ports:
      - "127.0.0.1:${ACTION_API_PORT:-8788}:8788"
    volumes:
      - ../../30_Capture:/lifeos/capture:rw
      - ../../50_Event_Log:/lifeos/event-log:rw
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; exit(0 if urllib.request.urlopen('http://localhost:8788/health').status == 200 else 1)"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s
    logging:
      driver: json-file
      options:
        max-size: 10m
        max-file: "3"

  lifeos-n8n:
    image: n8nio/n8n:latest
    profiles:
      - manual-start-disabled
    restart: "no"
    environment:
      N8N_HOST: ${N8N_HOST:-localhost}
      N8N_PORT: ${N8N_PORT:-5678}
      N8N_PROTOCOL: ${N8N_PROTOCOL:-http}
      N8N_BASIC_AUTH_ACTIVE: ${N8N_BASIC_AUTH_ACTIVE:-true}
      N8N_BASIC_AUTH_USER: ${N8N_BASIC_AUTH_USER:-change_me}
      N8N_BASIC_AUTH_PASSWORD: ${N8N_BASIC_AUTH_PASSWORD:-change_me}
      GENERIC_TIMEZONE: ${GENERIC_TIMEZONE:-America/Chicago}
      TZ: ${TZ:-America/Chicago}
      N8N_DIAGNOSTICS_ENABLED: "false"
      N8N_PERSONALIZATION_ENABLED: "false"
      N8N_VERSION_NOTIFICATIONS_ENABLED: "false"
    networks:
      - lifeos_internal
    ports:
      - "127.0.0.1:${N8N_PORT:-5678}:5678"
    volumes:
      - n8n_data:/home/node/.n8n
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    logging:
      driver: json-file
      options:
        max-size: 10m
        max-file: "3"

volumes:
  n8n_data:

networks:
  lifeos_internal:
    external: true
```

- [ ] **Step 2: Verify compose syntax (static validation only)**

```bash
cd /home/lifeos/40_Services/compose
docker-compose -f lifeos.yaml config
```

Expected: Compose file is valid, config output shows resolved service definitions. No warnings about missing `.env` (n8n uses `${VAR:-default}` substitution only). No containers are built, pulled, or started.

#### Task 1.2: Create consolidated `.env.example`

**Files:**
- Create: `40_Services/compose/.env.example`

**Interfaces:**
- Consumed by: operators who want documentation of available env vars
- The compose file itself does NOT reference `.env` — n8n uses `${VAR:-default}` exclusively

- [ ] **Step 1: Write `40_Services/compose/.env.example`**

```bash
# =============================================================================
# LifeOS Docker Compose — Example Environment Variables
# =============================================================================
# This file is documentation only. The compose file uses ${VAR:-default}
# substitution — no env_file reference. docker-compose config works without
# a real .env file.
#
# .env is gitignored — do not commit secrets.
#
# NOTE: N8N_ENCRYPTION_KEY is a future activation placeholder. It is not
# consumed by the baseline compose unless explicitly added during n8n
# activation planning.
# =============================================================================

# n8n server configuration
N8N_HOST=localhost
N8N_PORT=5678
N8N_PROTOCOL=http
N8N_TIMEZONE=America/Chicago
N8N_USER_FOLDER=/home/node/.n8n
N8N_DIAGNOSTICS_ENABLED=false
N8N_PERSONALIZATION_ENABLED=false
N8N_VERSION_NOTIFICATIONS_ENABLED=false
N8N_ENCRYPTION_KEY=replace_with_real_secret_later

# Basic authentication for n8n
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=change_me
N8N_BASIC_AUTH_PASSWORD=change_me

# Action API
ACTION_API_PORT=8788

# Status API
STATUS_API_PORT=8787
```

- [ ] **Step 2: Verify `.env.example` is gitignored**

Check that `.env` (not `.env.example`) is in `.gitignore`:

```bash
grep -n '\.env' /home/lifeos/.gitignore
```

Expected: `.env` pattern exists (not `.env.example`). Confirm `.env.example` is NOT gitignored.

#### Task 1.3: Commit

- [ ] **Step 1: Stage and commit**

```bash
git add \
  40_Services/compose/lifeos.yaml \
  40_Services/compose/.env.example
git commit -m "feat: add unified Docker Compose baseline file and .env.example"
```

Note: Only stage these two files. Do not stage `30_Capture/`, `50_Event_Log/events.jsonl`, `.env`, `.gemini/`, `.config/opencode/opencode.json`, or any secrets.

---

### Commit 2: Add legacy/reference notices to old compose files and READMEs

#### Task 2.1: Add legacy/reference header to `40_Services/n8n/docker-compose.yml`

- [ ] **Step 1: Insert legacy notice comment at line 1**

```yaml
# LEGACY/REFERENCE: A unified compose file now exists at
#   40_Services/compose/lifeos.yaml
# This file is preserved as-is for reference and backward compatibility.
# New work should use the unified file. This file is not removed.
```

#### Task 2.2: Add legacy/reference header to `40_Services/status_api/docker-compose.yml`

- [ ] **Step 1: Insert legacy notice comment at line 1**

```yaml
# LEGACY/REFERENCE: A unified compose file now exists at
#   40_Services/compose/lifeos.yaml
# This file is preserved as-is for reference and backward compatibility.
# New work should use the unified file. This file is not removed.
```

#### Task 2.3: Add legacy/reference header to `40_Services/compose/automation/compose.yaml`

- [ ] **Step 1: Insert legacy notice comment at line 1**

```yaml
# LEGACY/REFERENCE: A unified compose file now exists at
#   40_Services/compose/lifeos.yaml
# This file is preserved as-is for reference and backward compatibility.
# New work should use the unified file. This file is not removed.
```

#### Task 2.4: Update `40_Services/compose/automation/README.md`

- [ ] **Step 1: Add a note referencing the unified compose file**

After line 1, insert:

```markdown
> **Note:** A unified compose file now exists at `40_Services/compose/lifeos.yaml`. This directory's compose file is preserved for reference and backward compatibility.
```

#### Task 2.5: Verify notices are present

- [ ] **Step 1: Check for legacy notice in each file**

```bash
grep -c "LEGACY/REFERENCE" \
  40_Services/n8n/docker-compose.yml \
  40_Services/status_api/docker-compose.yml \
  40_Services/compose/automation/compose.yaml
```

Expected: Each file has exactly 1 match.

#### Task 2.6: Commit

- [ ] **Step 1: Stage and commit**

```bash
git add \
  40_Services/n8n/docker-compose.yml \
  40_Services/status_api/docker-compose.yml \
  40_Services/compose/automation/compose.yaml \
  40_Services/compose/automation/README.md
git commit -m "docs: add legacy/reference notices to existing compose files"
```

---

### Commit 3: Update docs/current-state/gameplan references

#### Task 3.1: Fix stale Telegram button UX status in gameplan

**Files:**
- Modify: `docs/superpowers/specs/2026-07-07-lifeos-telegram-n8n-next-phase-gameplan.md`

- [ ] **Step 1: Update line 79**

Change:
```
- Telegram button review UX is not implemented.
```
To:
```
- Telegram Review Button UX V1 is implemented/offline-tested but not live-validated and not active in the live capture-first service.
```

#### Task 3.2: Commit

- [ ] **Step 1: Stage and commit**

```bash
git add docs/superpowers/specs/2026-07-07-lifeos-telegram-n8n-next-phase-gameplan.md
git commit -m "docs: update gameplan to reflect Telegram review button UX implementation status"
```

---

### Commit 4: Add static validation instructions/runbook

#### Task 4.1: Update `.gitignore` for unified compose (if needed)

- [ ] **Step 1: Verify `.gitignore` covers new paths**

```bash
grep -n "compose\|\.env$" /home/lifeos/.gitignore
```

Expected: `40_Services/compose/.env` is covered by existing `.env` rules. If not, add:

```gitignore
# Docker Compose runtime state
40_Services/compose/.env
```

#### Task 4.2: Create validation runbook or update verification section

- [ ] **Step 1: Verify compose syntax (static only — no build, no pull, no start)**

```bash
cd /home/lifeos/40_Services/compose
docker-compose -f lifeos.yaml config > /dev/null && echo "COMPOSE VALID"
```

Expected: exits 0, prints "COMPOSE VALID".

- [ ] **Step 2: Verify legacy/reference notices present**

```bash
grep -c "LEGACY/REFERENCE" \
  40_Services/n8n/docker-compose.yml \
  40_Services/status_api/docker-compose.yml \
  40_Services/compose/automation/compose.yaml
```

Expected: Each file has exactly 1 match.

- [ ] **Step 3: Verify no `.env` committed**

```bash
git check-ignore 40_Services/compose/.env 2>/dev/null && echo "OK (ignored)" || echo "NOT IGNORED"
```

Expected: `OK (ignored)`.

- [ ] **Step 4: Verify no runtime artifacts staged**

```bash
git status --short
```

Expected: Only expected files. No `30_Capture/`, `50_Event_Log/events.jsonl`, `.env` files.

- [ ] **Step 5: Verify all ports bound to 127.0.0.1 (no public exposure)**

```bash
docker-compose -f 40_Services/compose/lifeos.yaml config | grep -E "published.*\":" | grep -v "127.0.0.1" && echo "WARNING: non-localhost bind found" || echo "OK: all ports localhost-only"
```

Expected: `OK: all ports localhost-only`.

- [ ] **Step 6: Verify git diff is clean (only expected files)**

```bash
git diff --stat
```

Expected: Only files listed in the commits above.

- [ ] **Step 7: Verify `external: true` on network**

```bash
docker-compose -f 40_Services/compose/lifeos.yaml config | grep -A2 "lifeos_internal" | grep "external: true"
```

Expected: `external: true` is present.

- [ ] **Step 8: Verify n8n has no `env_file` reference**

```bash
docker-compose -f 40_Services/compose/lifeos.yaml config | grep -A30 "lifeos-n8n" | grep "env_file"
```

Expected: No matches. n8n uses `${VAR:-default}` only.

#### Task 4.3: Commit

- [ ] **Step 1: Stage and commit**

```bash
git add .gitignore
git commit -m "docs: add static validation runbook for Docker Compose baseline"
```

Note: If `.gitignore` needed no changes, this commit contains the validation instructions only (as documentation in the commit message).

---

## Verification Commands

Run after implementation, before claiming completion. These are static validation only — no container build, pull, or start:

```bash
# 1. Compose syntax (static validation)
docker-compose -f 40_Services/compose/lifeos.yaml config > /dev/null && echo "COMPOSE VALID"

# 2. Legacy/reference notices present
grep -c "LEGACY/REFERENCE" \
  40_Services/n8n/docker-compose.yml \
  40_Services/status_api/docker-compose.yml \
  40_Services/compose/automation/compose.yaml

# 3. No .env committed
git check-ignore 40_Services/compose/.env 2>/dev/null && echo "OK (ignored)" || echo "NOT IGNORED"

# 4. No runtime artifacts staged
git status --short

# 5. All ports bound to 127.0.0.1 (no public exposure)
docker-compose -f 40_Services/compose/lifeos.yaml config | grep -E "published.*\":" | grep -v "127.0.0.1" && echo "WARNING: non-localhost bind found" || echo "OK: all ports localhost-only"

# 6. Git diff is clean (only expected files)
git diff --stat

# 7. Network is external: true
docker-compose -f 40_Services/compose/lifeos.yaml config | grep -A2 "lifeos_internal" | grep "external: true"

# 8. No env_file in n8n service
docker-compose -f 40_Services/compose/lifeos.yaml config | grep -A30 "lifeos-n8n" | grep "env_file" || echo "OK: no env_file in n8n"
```

**Do NOT run in baseline phase:**
- `docker-compose build` — not approved until activation/build phase
- `docker-compose pull` — not approved until activation/build phase
- `docker-compose up` — not approved until activation phase
- `docker network inspect` / `docker network create` — not approved until activation phase

---
## Rollback Plan

If the unified compose introduces issues:

1. **Remove new files:**
   ```bash
   git rm 40_Services/compose/lifeos.yaml 40_Services/compose/.env.example
   ```

2. **Restore old compose file references (remove legacy headers):**
   ```bash
   git checkout \
     40_Services/n8n/docker-compose.yml \
     40_Services/status_api/docker-compose.yml \
     40_Services/compose/automation/compose.yaml \
     40_Services/compose/automation/README.md
   ```

3. **Restore gameplan:**
   ```bash
   git checkout docs/superpowers/specs/2026-07-07-lifeos-telegram-n8n-next-phase-gameplan.md
   ```

4. **Restore `.gitignore`:**
   ```bash
   git checkout .gitignore
   ```

5. **Verify pre-existing state:**
   ```bash
   docker-compose -f 40_Services/n8n/docker-compose.yml config > /dev/null
   docker-compose -f 40_Services/status_api/docker-compose.yml config > /dev/null
   ```

6. **No containers were ever started** in this phase, so no `docker-compose down` cleanup is needed.

---
## Risks / Open Questions

| Risk | Mitigation |
|---|---|
| Existing `lifeos_internal` network may not exist when activation happens | Activation prerequisite step checks with `docker network inspect lifeos_internal` and creates if missing. Not run in baseline phase. |
| Port conflicts if Status API or Action API are already running on host | Host-run instances must be stopped before Docker instances can bind the same ports. The plan does not start containers, so this is deferred to actual activation. |
| Legacy compose files still referenced by existing scripts or docs | Legacy/reference notices plus preserved files ensure backward compatibility. The unified file supplements, not replaces. |
| Action API Docker service DNS path (`lifeos-action-api:8788`) differs from localhost path | Active Telegram contract remains `localhost:8788`. Service DNS is prepared but inactive until a separate activation step. |
| `.env.example` falls out of sync with compose env vars | Both files are part of the same repo. Verification step 8 checks for env_file references. Manual review during activation. |


