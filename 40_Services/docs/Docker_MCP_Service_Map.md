# LifeOS Docker + MCP Service Map

> Read-only inventory of all LifeOS services, their Docker/MCP status, and risk levels.
> Updated: 2026-07-08 — Dashboard deployed; Capture API added

## Current Services

| Service | Runtime | Port | Health Check | Risk | MCP Exposure |
|---------|---------|------|-------------|------|-------------|
| `lifeos-status-api` | Docker (unified compose) | `127.0.0.1:8787` | `GET /health` | Low | Read-only planned |
| `lifeos-action-api` | Docker (unified compose) | `127.0.0.1:8788` | `GET /health` | Medium | Write-gated (future) |
| `n8n_n8n_1` | Docker (legacy compose) | `127.0.0.1:5678` | HTTP 200 on port | Medium-High | Deferred |
| `odysseus_chromadb_1` | Docker (legacy, not LifeOS) | `127.0.0.1:8100` | None | Low-Medium | No |
| `lifeos-telegram-bot` | systemd user service | None (outbound) | systemctl status | Low | No |
| **Dashboard Stack** | | | | | |
| `lifeos-homepage` | Docker (dashboard compose) | `127.0.0.1:3000` | HTTP 200 | Low | No |
| `lifeos-uptime-kuma` | Docker (dashboard compose) | `127.0.0.1:3001` | HTTP 200 | Low | No |
| `lifeos-dozzle` | Docker (dashboard compose) | `127.0.0.1:3002` | HTTP 200 | Low-Medium* | No |

## Planned Services

| Service | Phase | Port | Health Check | Risk | MCP Exposure |
|---------|-------|------|-------------|------|-------------|
| **MCP/mcpo** | Foundation (scaffold) | | | | |
| LifeOS MCP Server | Foundation (scaffold) | `127.0.0.1:TBD` | TBD | Medium | Self |
| mcpo Proxy | Foundation (scaffold) | `127.0.0.1:TBD` | TBD | Medium | Self |
| **OpenHands** | Foundation (scaffold) | | | | |
| OpenHands Sandbox | Foundation (scaffold) | `127.0.0.1:3003` | TBD | Medium-High | No |
| **Capture Pipeline** | V1 (roadmap) | | | | |
| Capture API | V1 (roadmap) | `127.0.0.1:8789` | `GET /health` | Medium | Read-only planned |
| **AI (Future)** | V2+ | | | | |
| Ollama | V2+ | `127.0.0.1:11434` | `GET /api/tags` | Medium | No |
| Open WebUI | V2+ | `127.0.0.1:8080` | HTTP 200 | Medium | mcpo consumer |
| LiteLLM | V2+ | `127.0.0.1:TBD` | TBD | Medium | No |
| **Memory (Future)** | V2+ | | | | |
| Qdrant | V2+ | `127.0.0.1:6333` | `GET /health` | Medium | Deferred |
| Search API | V2+ | `127.0.0.1:TBD` | TBD | Medium | Read-only planned |
| Indexer | V2+ | None (batch) | None | Medium | No |

*Dozzle has read-only Docker socket access — documented and controlled risk.

## Startup Methods

| Startup Method | Services |
|---------------|----------|
| **Docker Compose V1 (legacy)** | n8n, ChromaDB (odysseus) |
| **Docker Compose V1 (unified)** | Status API, Action API |
| **Docker Compose V1 (dashboard)** | Homepage, Uptime Kuma, Dozzle |
| **systemd user service** | Telegram bot |
| **Manual/CLI scripts** | lifeos_services.py, lifeos_observability.py |

## Port Map

```
127.0.0.1:3000  → Homepage (dashboard compose)
127.0.0.1:3001  → Uptime Kuma (dashboard compose)
127.0.0.1:3002  → Dozzle (dashboard compose)
127.0.0.1:3003  → OpenHands Sandbox (planned)
127.0.0.1:5678  → n8n (legacy compose)
127.0.0.1:8100  → ChromaDB (legacy, odysseus)
127.0.0.1:8787  → Status API (unified compose)
127.0.0.1:8788  → Action API (unified compose)
127.0.0.1:8789  → Capture API (planned, V1 roadmap)
```

## Volumes

| Volume | Type | Service | Backup Need |
|--------|------|---------|-------------|
| `n8n_data` | Named volume | n8n | High |
| `odysseus_chromadb-data` | Named volume | ChromaDB | Unknown |
| `homepage_icons` | Named volume (dashboard) | Homepage | Low |
| `homepage_data` | Named volume (dashboard) | Homepage | Low |
| `uptime_kuma_data` | Named volume (dashboard) | Uptime Kuma | Medium |

## Config Paths

| Config | Path | Purpose |
|--------|------|---------|
| Unified compose | `40_Services/compose/lifeos.yaml` | Status API, Action API, n8n (future) |
| Legacy n8n compose | `40_Services/n8n/docker-compose.yml` | n8n (active) |
| Dashboard compose | `40_Services/dashboard/docker-compose.yml` | Homepage, Uptime Kuma, Dozzle |
| mcpo scaffold | `40_Services/mcpo/docker-compose.example.yml` | mcpo (scaffold) |
| OpenHands scaffold | `40_Services/openhands/docker-compose.example.yml` | OpenHands (scaffold) |
| MCP config | `40_Services/mcp/` | MCP server (scaffold) |
| Telegram config | `40_Services/config/telegram/.env` | Bot token (gitignored) |
| n8n .env | `40_Services/n8n/.env` | n8n credentials (gitignored) |

## Health Check Methods

| Service | Health Check | Check Command |
|---------|-------------|---------------|
| Status API | `GET /health` | `curl -fsS http://localhost:8787/health` |
| Action API | `GET /health` | `curl -fsS http://localhost:8788/health` |
| n8n | HTTP 200 on port | `curl -fsS -o /dev/null -w '%{http_code}' http://localhost:5678` |
| Telegram bot | systemd status | `systemctl --user status lifeos-telegram-bot.service` |
| Homepage | HTTP 200 | `curl -fsS -o /dev/null -w '%{http_code}' http://localhost:3000` |
| Uptime Kuma | HTTP 200 | `curl -fsS -o /dev/null -w '%{http_code}' http://localhost:3001` |
| Dozzle | HTTP 200 | `curl -fsS -o /dev/null -w '%{http_code}' http://localhost:3002` |
| ChromaDB | Container running | `docker ps --filter "name=chromadb"` |

## MCP Exposure Decision Map

| Service | MCP Exposure | Decision | Reason |
|---------|-------------|----------|--------|
| Status API | Read-only | Allow (planned) | Read-only system status, no secrets |
| Action API | Write-gated | Defer to V3 | Requires approval tier gating |
| n8n | Deferred | Defer | Requires API key scope management |
| ChromaDB | No | Reject | Not LifeOS-owned. Access via Search API. |
| Telegram Bot | No | Reject | ChatOps front-end, not a tool |
| Docker daemon | No | **Permanently reject** | Socket = system compromise |
| Vault | No | **Permanently reject** | Always via capture pipeline |
| Git (write) | No | Reject (V1) | Read-only git status OK. Write requires A4. |
| Ollama | No | Defer (V2+) | Model access via Open WebUI, not MCP |

## Risk Levels

| Level | Definition | Example |
|-------|-----------|---------|
| **Low** | Read-only, no secrets, no mutation, localhost | Status API, Homepage |
| **Low-Medium** | Read-only with socket access, controlled risk | Dozzle |
| **Medium** | Read-write with path boundaries, API gated | Action API, MCP read-only |
| **Medium-High** | Read-write, credential storage, workflow execution | n8n, OpenHands sandbox |
| **High** | Broad filesystem access, external API write, secrets access | (none active in V1) |
| **Critical** | Docker socket, shell execution, full vault access | Permanently rejected |

## Related Docs

- [Dashboard README](../dashboard/README.md) — dashboard stack startup and security notes
- [Uptime Kuma Monitor Plan](Uptime_Kuma_Monitor_Plan.md) — monitor definitions
- [N8N Automation Roadmap](N8N_Automation_Roadmap.md) — n8n phases and activation
- [MCP Security Policy](MCP_Security_Policy.md) — MCP tool allowlist and sandbox rules
- [Agentic Capture Pipeline](Agentic_Capture_Pipeline.md) — capture pipeline architecture
- [Capture API Roadmap](Capture_API_Roadmap.md) — Tailscale-only capture intake API
- [Capture Processor Roadmap](Capture_Processor_Roadmap.md) — Dockerized processors catalog
- [Observability Control Plane](Observability_Control_Plane.md) — observability policy and runbook
