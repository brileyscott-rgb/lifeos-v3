---
type: decision
status: accepted
date: 2026-07-04
decision_owner: user
supersedes: null
---

# Phase 1B Foundation Decisions

## Accepted Decisions

| Decision | Choice | Rationale |
|---|---|---|
| New user | `lifeos` | Dedicated clean LifeOS environment with hard separation from old account drift. |
| Final root | `/home/lifeos/` | Cleaner than nesting under `LifeOS_V3_Fresh_Start` after promotion. |
| Primary ChatOps | Telegram | Fast mobile approval loop, simple bot API, good n8n fit. |
| System alerts later | Gotify or ntfy | Lightweight alert channel for service health and backup notifications. |
| Vault sync | Git first | Best audit trail, rollback, and agent accountability for Markdown/control-plane files. |
| Capture sync later | Syncthing if needed | Useful for device-to-device raw capture movement after Git foundation is stable. |
| AI strategy | Hybrid local + cloud | Local for routine/private first pass; cloud for high-value reasoning and synthesis. |
| Vector store | Qdrant | Strong local Docker fit, simpler than Milvus, more durable than prototype-only stores. |
| Structured state | SQLite first | Simple local event/workflow state; Postgres later if service complexity justifies it. |
| A3 agents | Project Maintainer and Semantic Janitor only | Limited direct mutation surface until trust is proven. |
| Migration deletion | A4 manual approval every time | Old content may contain hidden context; deletion must be deliberate. |
| Deletion style | Quarantine first | Move to deferred-delete/quarantine before hard deletion. |
| Backup strategy | Git plus restic later | Git for text/config history; restic for encrypted full backups. |
| Obsidian plugins | Minimal core set first | Avoid plugin sprawl before workflows are stable. |
| Service order | Git, n8n, Telegram, Paperless, Qdrant, monitoring, MCP | Protect source first, then automate, then enrich. |

## Explicit Non-Decisions

- No live service deployment in Phase 1B.
- No old LifeOS migration in Phase 1B.
- No real secrets in Phase 1B.
- No AI Mirror enforcement.
