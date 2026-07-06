# Runtime Loadout

## Local Tools

- Obsidian: planned curated vault interface
- Git: planned versioning layer
- Docker Compose: planned service runtime
- OpenCode: planned terminal AI assistant interface

## Automation

- n8n: planned, inactive in Phase 1
- Telegram: planned primary ChatOps approval channel
- Gotify or ntfy: planned later system-alert channel

## AI Runtime

- local models: planned for classification, simple summarization, tagging, routing suggestions, daily cleanup, privacy-sensitive first pass, and offline work
- remote APIs: planned for complex reasoning, architecture design, migration judgment, code review, difficult debugging, long synthesis, and final quality pass
- prompts: scaffolded
- agents: scaffolded
- context packs: scaffolded
- evals: scaffolded

## Storage and Retrieval

- SQLite: planned first structured state store
- Postgres: later option if service complexity justifies it
- Qdrant: planned vector database and semantic retrieval store
- filesystem: scaffolded
- vault: scaffolded

## MCP Layer

MCP access must be path-bounded and role-aware.

Candidate servers: filesystem, git, sqlite/postgres, browser/search, Docker wrapper, Obsidian/local vault, memory, sequential-thinking.

## Status

All runtime entries are scaffold-only until a later phase activates them.

See [[Policies/AI_Model_Routing_Policy]], [[Policies/Retrieval_And_Vector_Store_Policy]], [[Policies/ChatOps_Policy]], and [[Policies/Service_Activation_Order]].
