# LifeOS Docker Service Profiles V1

> Profiles define service groupings for controlled startup and risk management.
> No migration from current running state. Profiles are planning tooling only.

## Profile Definitions

### core

**Purpose:** Essential infrastructure required for LifeOS to function. These services must be running before any other profile.

**Candidate services:**
- `lifeos-status-api` — Read-only system status
- `lifeos-action-api` — Capture and review mutation boundary
- `lifeos-telegram-bot` — ChatOps intake (systemd, not Docker)

**When to start:** Always. These are the backbone of capture, review, and status.

**Risk level:** Low — status is read-only, action is single-purpose mutation boundary, Telegram is authorized-sender-only.

**Backup needs:** Capture files and event log through Git + restic.

**Dependencies:** `lifeos_internal` Docker network.

**Not allowed in this phase:**
- Public ingress or webhooks
- Cloudflare tunnel activation
- AI model containers
- n8n workflow automation

### automation

**Purpose:** Workflow automation and orchestration.

**Candidate services:**
- `lifeos-n8n` — n8n automation server
- `n8n_data` volume — workflow and credential storage

**When to start:** After core services are healthy. Requires explicit activation approval.

**Risk level:** Medium — hosts workflow logic, credentials, and potential Execute Command nodes.

**Backup needs:** High — n8n workflows, credentials, and execution data must be backed up before any activation.

**Dependencies:** Core profile, `lifeos_internal` network, n8n `.env` with reviewed secrets.

**Not allowed in this phase:**
- Telegram webhook triggers (compete with polling bot)
- Cloudflare/public tunnel
- Execute Command nodes pointing at production paths
- Direct vault-write workflow steps
- Direct git-commit workflow steps

### memory

**Purpose:** Semantic memory, vector storage, and knowledge retrieval.

**Candidate services:**
- `chromadb` — Vector database (already running, undocumented)
- `qdrant` — Future vector store (per architecture decision)

**When to start:** After core + automation are stable. Requires indexing strategy.

**Risk level:** Low-Medium — vector DB without mutation path is low risk; with AI write path becomes medium.

**Backup needs:** Medium — vector indexes are rebuildable but costly. Back up when embeddings are populated.

**Dependencies:** Core profile, automation profile (for indexing workflows).

**Not allowed in this phase:**
- AI model containers
- Automatic embedding/indexing of vault content
- Direct vault reads without explicit content policy

### ai

**Purpose:** AI model inference, worker agents, and proposal generation.

**Candidate services:**
- `ai-worker` — Implementer agent (currently dry-run scaffold)
- `semantic-janitor` — Knowledge organization agent (future)
- Local LLM inference (future)
- OpenCode execution worker (future)

**When to start:** After core + automation + memory are stable. Requires explicit A3 agent policy compliance.

**Risk level:** High — AI agents may read vault, propose changes, execute code.

**Backup needs:** High — job queue, prompts, and agent state.

**Dependencies:** Core, automation, memory profiles. A3 agent policy approval.

**Not allowed in this phase:**
- Real model API calls from ai-worker
- Direct vault writes without human approval
- OpenCode or shell execution from AI workers
- Automatic file edits or git commits
- Long-running AI inference containers

### observability

**Purpose:** Monitoring, alerting, logging, and system health visualization.

**Candidate services:**
- `gotify` or `ntfy` — Notification/alerting
- Container health dashboard (future)
- Disk usage monitor
- Capture queue alert
- Event log watcher
- MCP server

**When to start:** After core profile is stable. Read-only first.

**Risk level:** Low — read-only monitoring does not mutate state.

**Backup needs:** Low — log rotation and retention policy.

**Dependencies:** Core profile, Docker socket or healthcheck endpoints.

**Not allowed in this phase:**
- Heavy monitoring stacks (Prometheus, Grafana)
- Docker socket exposure to containers
- Alert fatigue triggers
- Public-facing dashboards

### experiments

**Purpose:** Sandbox services for testing new tools, workflows, and integrations.

**Candidate services:**
- `flowise` — Visual AI workflow builder
- `langflow` — LangChain workflow UI
- Test n8n instances
- Sandbox databases
- POC services

**When to start:** Never in production. Explicit approval per experiment.

**Risk level:** Variable — each experiment requires risk assessment.

**Backup needs:** None — experiments should be disposable.

**Dependencies:** None — isolated from production.

**Not allowed in this phase:**
- Access to production data or vault
- Production network attachment
- Real secrets or credentials
- Long-running background processes

## Current State Map

| Service | Current Profile | Current Status | Future Profile |
|---------|----------------|---------------|----------------|
| `lifeos-status-api` | core | Running (unified compose) | core |
| `lifeos-action-api` | core | Running (unified compose) | core |
| `lifeos-telegram-bot` | core | Running (systemd) | core |
| `n8n_n8n_1` | automation | Running (legacy compose) | automation |
| `odysseus_chromadb_1` | memory | Running (unknown owner) | memory |
| `ai-worker` | ai | Scaffold only | ai |
| MCP server | observability | Not started | observability |

## Profile Startup Order

```
core → automation → memory → ai
                  ↘ observability (parallel with memory/ai)
```

Experiments are always isolated and started manually.

## Docker Compose Profile Mapping (Future)

```yaml
# 40_Services/compose/lifeos.yaml (future enhancement)
services:
  lifeos-status-api:
    profiles: [core, all]

  lifeos-action-api:
    profiles: [core, all]

  lifeos-n8n:
    profiles: [automation, all]
    # Requires core profile already running

  chromadb:
    profiles: [memory, all]

  ai-worker:
    profiles: [ai, all]

  mcp-server:
    profiles: [observability, all]
```

Current `lifeos.yaml` uses `manual-start-disabled` profile for n8n only.
Profile assignment will be added in a future phase after n8n adoption.
