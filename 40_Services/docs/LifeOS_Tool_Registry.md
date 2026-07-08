# LifeOS Tool Registry

Status: V1 operator utility bundle (2026-07-08).

Every tool, script, API, and service in LifeOS V3. Use this alongside `LifeOS_Tool_Permission_Tiers.md`.

---

## APIs

| Tool | Owner | Status | Risk Tier | Allowed Inputs | Allowed Outputs | Forbidden Paths | Auth | Logging | Activation |
|------|-------|--------|-----------|---------------|----------------|----------------|------|---------|------------|
| `lifeos-status-api` | LifeOS | **Live** (Docker) | A0 | `GET /health`, `GET /status` | JSON status | Canonical vault | None (read-only) | Event log | Running |
| `lifeos-action-api` | LifeOS | **Live** (Docker) | A4 | `POST /captures`, `POST /approve`, `POST /reject` | JSON, capture files | Canonical vault | None (localhost) | Event log | Running |
| `lifeos-capture-api` | LifeOS | **Live** (systemd) | A2 | `POST /captures` (JSON, ≤65KB) | JSONL queue, event log | Canonical vault | Bearer token | Event log (metadata) | Running |
| `n8n` | Legacy | **Live** (Docker) | A4 (inactive) | HTTP, cron triggers | Workflow outputs | Vault, Docker socket | Basic auth | n8n logs | Running (inactive workflows) |

## CLI Scripts

| Tool | Owner | Status | Risk Tier | Allowed Inputs | Allowed Outputs | Forbidden Paths | Auth | Logging | Activation |
|------|-------|--------|-----------|---------------|----------------|----------------|------|---------|------------|
| `lifeos_services.py` | LifeOS | **Live** (script) | A1 | `docker ps`, `systemctl`, `git status` | `--text` / `--json` | None | None (read-only) | stdout | On-demand |
| `lifeos_status.py` | LifeOS | **Live** (script) | A1 | Filesystem paths, `git status` | `--text` / `--json` | None | None (read-only) | stdout | On-demand |
| `lifeos_observability.py` | LifeOS | **Live** (script) | A1 | Status API, Action API, `docker ps`, `systemctl` | `--text` / `--json` | None | None (read-only) | stdout | On-demand |
| `lifeos_goal_prompt.py` | LifeOS | **Live** (script) | A1 | `--goal`, `--risk-tier` | Prompt text | .env, secrets | None | stdout | On-demand |
| `lifeos_capture_summary.py` | LifeOS | **Live** (script) | A1 | JSONL queue path, processed dir | `--text` / `--json` (metadata only) | Canonical vault | None (read-only) | stdout | On-demand |

## Capture Processors

| Tool | Owner | Status | Risk Tier | Allowed Inputs | Allowed Outputs | Forbidden Paths | Auth | Logging | Activation |
|------|-------|--------|-----------|---------------|----------------|----------------|------|---------|------------|
| `init_capture_buffer.py` | LifeOS | **Live** (script) | A2 | `--buffer-root`, `--media-root` | Directory trees + READMEs | Canonical vault, `/`, `/home` | None | stdout | On-demand |
| `queue_to_markdown.py` | LifeOS | **Live** (script) | A2 | JSONL queue | Buffer Markdown files | Canonical vault | None | stderr (malformed) | On-demand |
| `review_packet_builder.py` | LifeOS | **Live** (script) | A3 | Buffer processed Markdown | Buffer review packets | Canonical vault | None | stdout | On-demand |

## Dashboard

| Tool | Owner | Status | Risk Tier | Allowed Inputs | Allowed Outputs | Forbidden Paths | Auth | Logging | Activation |
|------|-------|--------|-----------|---------------|----------------|----------------|------|---------|------------|
| `lifeos-uptime-kuma` | LifeOS | **Live** (Docker) | A1 | Manual monitor config | Web UI, status history, alerts | Docker socket | Local UI auth | Volume | Running |
| `lifeos-homepage` | LifeOS | **Live** (Docker) | A1 | `services.yaml`, `bookmarks.yaml` | Web dashboard | Docker socket | None (localhost) | Container logs | Running |
| `lifeos-dozzle` | LifeOS | **Live** (Docker) | A1 | Docker socket (read-only) | Container log viewer | Write operations | None (localhost) | Container logs | Running |

## Future / Scaffold

| Tool | Owner | Status | Risk Tier | Activation |
|------|-------|--------|-----------|------------|
| `mcpo` | LifeOS | **Scaffold** | A2 (planned) | **Not active** |
| `openhands` | LifeOS | **Scaffold** | A3 (planned) | **Not active** |
| `mcp/*` | LifeOS | **Scaffold** | A1-A2 | **Not active** |
| `chromadb` (odysseus) | Legacy | **Live** (Docker) | A1 | Running (legacy) |

---

## Cross-References

- [Permission Tiers](LifeOS_Tool_Permission_Tiers.md)
- [MCP Security Policy](MCP_Security_Policy.md)
- [MCP Candidate Catalog](../mcp/catalog/MCP_Candidate_Catalog.md)
- [Capture API Roadmap](Capture_API_Roadmap.md)
- [Uptime Kuma Monitor Plan](Uptime_Kuma_Monitor_Plan.md)
- [Docker + MCP Service Map](Docker_MCP_Service_Map.md)
- [Dashboard README](../dashboard/README.md)
