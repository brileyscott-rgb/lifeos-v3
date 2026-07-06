# System Registry

This registry describes intended services and governance status. Phase 1 does not deploy services.

## Vault

| Item | Path | Purpose | Status |
|---|---|---|---|
| LifeOS Vault | `/home/lifeos/10_Vaults/LifeOS` | Curated meaning layer | scaffolded |

## Filesystem Stores

| Store | Path | Purpose | Status |
|---|---|---|---|
| Inbox | `/home/lifeos/00_Inbox` | Raw capture landing zones | scaffold-only |
| Workspaces | `/home/lifeos/20_Workspaces` | Active technical work | scaffold-only |
| Documents | `/home/lifeos/30_Documents` | Formal document intake | scaffold-only |
| Services | `/home/lifeos/40_Services` | Future service definitions and data | scaffold-only |
| Event Log | `/home/lifeos/50_Event_Log` | Factual activity spine | scaffolded |
| AI Runtime | `/home/lifeos/60_AI_Runtime` | Prompts, agents, MCP, schemas | scaffolded |
| Archive | `/home/lifeos/99_Archive` | Old imports and migration staging | scaffold-only |

## Services

| Service | Category | Phase | Status | Compose Path | Config Path | Data Path | Backup Path | Health Check | Secrets Required | Event Types |
|---|---|---:|---|---|---|---|---|---|---|---|
| n8n | automation | 2 | planned | `40_Services/compose/automation/` | `40_Services/config/n8n/` | `40_Services/data/n8n/` | `70_Backups/services/n8n/` | planned | yes | `workflow.started`, `workflow.failed`, `workflow.completed` |
| Paperless-ngx | documents | 4 | planned | `40_Services/compose/documents/` | `40_Services/config/paperless/` | `40_Services/data/paperless/` | `70_Backups/services/paperless/` | planned | yes | `document.ingested`, `document.failed` |
| Uptime Kuma | monitoring | 9 | planned | `40_Services/compose/monitoring/` | `40_Services/config/uptime-kuma/` | `40_Services/data/uptime-kuma/` | `70_Backups/services/uptime-kuma/` | planned | yes | `monitor.alert`, `monitor.recovered` |
| Glances | monitoring | 9 | planned | `40_Services/compose/monitoring/` | `40_Services/config/glances/` | `40_Services/data/glances/` | `70_Backups/services/glances/` | planned | no | `host.metric.sampled`, `host.alert` |
| Ollama | ai | 6 | planned | `40_Services/compose/ai/` | `40_Services/config/ollama/` | `40_Services/data/ollama/` | `70_Backups/services/ollama/` | planned | no | `model.available`, `model.failed` |
| Qdrant | vector-store | 6 | planned | `40_Services/compose/ai/` | `40_Services/config/qdrant/` | `40_Services/data/qdrant/` | `70_Backups/services/qdrant/` | planned | no | `vector.collection.created`, `vector.query.failed` |
| MCP Filesystem | mcp | 6 | planned | `40_Services/compose/ai/` | `60_AI_Runtime/mcp/filesystem/` | none | `70_Backups/services/mcp/` | planned | no | `mcp.tool.called`, `mcp.tool.failed` |
| Telegram ChatOps Gateway | chatops | 3 | planned | `40_Services/compose/chatops/` | `40_Services/config/chatops/` | `40_Services/data/chatops/` | `70_Backups/services/chatops/` | planned | yes | `approval.requested`, `notification.sent` |
| Gotify or ntfy Alerts | alerts | 9 | planned | `40_Services/compose/monitoring/` | `40_Services/config/alerts/` | `40_Services/data/alerts/` | `70_Backups/services/alerts/` | planned | yes | `alert.sent`, `alert.failed` |
| SQLite Event Store | database | 1 | planned | `40_Services/compose/databases/` | `40_Services/config/sqlite/` | `40_Services/data/sqlite/` | `70_Backups/services/sqlite/` | planned | no | `event.persisted`, `event.validation_failed` |

## Responsibility Boundaries

- Vault: curated meaning, decisions, schemas, dashboards, project context, approved summaries.
- Outside vault: raw captures, source documents, code, Docker data, runtime logs, generated artifacts, old imports.

## Registry Rules

- `Status` values: `planned`, `scaffolded`, `staged`, `active`, `paused`, `deprecated`, `retired`.
- No service should be marked `active` until deployed and health-checked.
- Any service requiring credentials must use placeholders in Phase 1.
- Real secrets must never be stored in the vault.
