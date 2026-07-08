# LifeOS Docker Service Map V1

> Read-only inventory. No migration, no activation, no service changes.
> This map documents what exists today and what is planned for future phases.

## Running Containers (2026-07-07)

| Container | Compose Project | Purpose | Port | Status |
|-----------|----------------|---------|------|--------|
| `lifeos-status-api` | unified (`lifeos.yaml`) | Read-only status endpoint | `127.0.0.1:8787` | healthy |
| `lifeos-action-api` | unified (`lifeos.yaml`) | Capture/review mutation API | `127.0.0.1:8788` | healthy |
| `n8n_n8n_1` | legacy (`n8n/docker-compose.yml`) | n8n automation server | `127.0.0.1:5678` | running, not verified |
| `odysseus_chromadb_1` | odysseus (legacy, not LifeOS) | ChromaDB vector store | `127.0.0.1:8100` | running, partially known |

## Service Inventory

### lifeos-status-api

| Field | Value |
|-------|-------|
| **Service name** | `lifeos-status-api` |
| **Purpose** | Read-only HTTP API exposing LifeOS health and capture/event log counts |
| **Startup method** | Docker Compose (unified `40_Services/compose/lifeos.yaml`) |
| **Port** | `127.0.0.1:8787` (container port 8787) |
| **Config path** | `40_Services/compose/lifeos.yaml` (service definition) |
| **Source path** | `40_Services/status_api/app.py` |
| **Data path** | `30_Capture/` (read-only mount), `50_Event_Log/events.jsonl` (read-only mount) |
| **Healthcheck** | `GET /health` returns `{"status": "ok", "mode": "read_only"}` |
| **Backup need** | No persistent data — stateless. Container logs only. |
| **Risk level** | Low — read-only, no Docker socket, no secrets, no mutation |
| **Future MCP exposure** | `read-only` — expose `/status` endpoint for system health queries |
| **Runtime owner** | Unified compose (`lifeos.yaml`) |
| **Security** | `read_only: true`, `cap_drop: ALL`, `no-new-privileges`, `tmpfs /tmp` |

### lifeos-action-api

| Field | Value |
|-------|-------|
| **Service name** | `lifeos-action-api` |
| **Purpose** | Read-write HTTP API for capture creation, listing, approve/reject mutations |
| **Startup method** | Docker Compose (unified `40_Services/compose/lifeos.yaml`) |
| **Port** | `127.0.0.1:8788` (container port 8788) |
| **Config path** | `40_Services/compose/lifeos.yaml` (service definition) |
| **Source path** | `40_Services/action_api/server.py` |
| **Data path** | `30_Capture/` (read-write mount), `50_Event_Log/events.jsonl` (read-write mount) |
| **Healthcheck** | `GET /health` returns `{"status": "ok", "mode": "read_write"}` |
| **Backup need** | Capture files and event log — backed up via Git + restic (future) |
| **Risk level** | Medium — read-write, single mutation boundary for captures |
| **Future MCP exposure** | `write-gated` — expose capture creation and review operations with approval tier gating |
| **Runtime owner** | Unified compose (`lifeos.yaml`) |
| **Security** | `cap_drop: ALL`, `no-new-privileges`, path traversal protection, request size limits |

### n8n

| Field | Value |
|-------|-------|
| **Service name** | `n8n_n8n_1` (legacy) / `lifeos-n8n` (future unified) |
| **Purpose** | Local n8n workflow automation server |
| **Startup method** | Legacy Docker Compose (`40_Services/n8n/docker-compose.yml`) |
| **Port** | `127.0.0.1:5678` |
| **Config path** | `40_Services/n8n/docker-compose.yml` (legacy), `40_Services/compose/lifeos.yaml` (future) |
| **Data path** | Docker volume `n8n_data` (workflows, credentials, database) |
| **Healthcheck** | Not configured in legacy compose |
| **Backup need** | High — n8n workflows, credentials, and workflow execution data |
| **Risk level** | Medium-High — running from legacy compose, workflow activation not verified |
| **Future MCP exposure** | `write-gated` — n8n may expose workflow status and trigger endpoints |
| **Runtime owner** | Legacy `n8n` compose — adoption into unified compose deferred |
| **Security** | No public webhooks, no Cloudflare tunnel active, Basic Auth enabled |

### chromadb

| Field | Value |
|-------|-------|
| **Service name** | `odysseus_chromadb_1` |
| **Purpose** | Vector database (legacy app, not LifeOS-owned) |
| **Startup method** | Docker Compose V1 (`docker-compose.yml` from `/home/bdoss08/odysseus`, old user) |
| **Port** | `127.0.0.1:8100` (container port 8000) |
| **Config path** | Unknown — compose project `odysseus` from old user home |
| **Data path** | Docker volume `odysseus_chromadb-data` |
| **Image** | `docker.io/chromadb/chroma:latest` |
| **Healthcheck** | None configured |
| **Backup need** | Unknown — depends on legacy `odysseus` app |
| **Risk level** | Low-Medium — not LifeOS-owned, no known mutation path to LifeOS data |
| **Future MCP exposure** | `no` — vector DB access should go through semantic janitor, not MCP |
| **Runtime owner** | Legacy `odysseus` compose — not a LifeOS service |

### lifeos-telegram-bot

| Field | Value |
|-------|-------|
| **Service name** | `lifeos-telegram-bot.service` |
| **Purpose** | Local Telegram ChatOps bot — capture intake, review, status |
| **Startup method** | systemd user service (`--poll --interval 3`) |
| **Port** | None — outbound HTTP only |
| **Config path** | `40_Services/config/telegram/.env` (gitignored) |
| **Source path** | `40_Services/chatops/telegram/telegram_capture_bot.py` |
| **Data path** | Reads/writes through Action API (localhost:8788), Status API (localhost:8787) |
| **Healthcheck** | `systemctl --user status lifeos-telegram-bot.service` |
| **Backup need** | No persistent data — stateless (captures via Action API) |
| **Risk level** | Low — capture-first, no direct filesystem writes, authorized sender only |
| **Future MCP exposure** | `no` — ChatOps bot is a front-end, not an MCP tool |
| **Runtime owner** | systemd user service — not containerized |

### ai-worker (scaffold)

| Field | Value |
|-------|-------|
| **Service name** | N/A (not running) |
| **Purpose** | Dry-run AI implementer worker scaffold |
| **Startup method** | Not running — CLI scaffold only (`40_Services/ai_worker/ai_worker.py`) |
| **Port** | None |
| **Config path** | `40_Services/ai_worker/prompts/` |
| **Data path** | `40_Services/ai_worker/jobs/` |
| **Healthcheck** | N/A |
| **Backup need** | Low — scaffold only, no real data |
| **Risk level** | Low — dry-run only, no model calls, no file edits |
| **Future MCP exposure** | `write-gated` — job submission with approval gating |

## Network

| Network | Type | Purpose |
|---------|------|---------|
| `lifeos_internal` | Docker bridge (external) | Shared network for all LifeOS containers |

## Host Tooling

| Tool | Version | Notes |
|------|---------|-------|
| `docker` | (available) | Docker Engine |
| `docker-compose` | 1.29.2 | Compose V1 — no `docker compose` V2 plugin |
| `systemd` | (user scope) | Telegram bot service |

## Current Risks

1. **n8n running from legacy compose** — Not owned by unified compose. Workflow activation status unverified.
2. **ChromaDB undocumented** — No known compose project, purpose, or data path.
3. **No backup strategy active** — Docker volumes and n8n data have no automated backup.
4. **No monitoring/alerting** — Container health depends on Docker restart policies only.
5. **No MCP or observability layer** — This V1 map is the first step.

## Future Plan

- V1 (this map): Read-only service inventory
- V2: Observability (container health, disk usage, capture queue alerts)
- V3: MCP read-only tools (status, git, projects)
- V4: MCP write-gated tools (capture creation, job submission)
- V5: AI worker activation, semantic janitor, n8n workflow automation

## Files Not To Touch

- Real `.env` files under `40_Services/config/`, `40_Services/n8n/`, `40_Services/secrets/`
- Running Docker containers (no stop/start/restart/recreate)
- `docker-compose.yml` files (no migration yet)
- `30_Capture/`, `50_Event_Log/` (production data)
- `10_Vaults/` (Obsidian vault)
