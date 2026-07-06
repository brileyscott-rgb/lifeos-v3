# System Status

## Vault Structure

Phase 1 scaffold created for review.

## AI Universe

Registry, roles, approval tiers, schemas, prompts, and logs are scaffolded.

## External Systems

- n8n: planned, inactive
- Paperless-ngx: planned, inactive
- ChatOps: planned, inactive
- MCP: planned, inactive
- Monitoring: planned, inactive

## Accepted Phase 1B Decisions

- Fresh account name: `lifeos`
- Final root: `/home/lifeos/`
- Primary ChatOps channel: Telegram
- System alerts later: Gotify or ntfy
- AI model strategy: hybrid local plus cloud
- Vector database: Qdrant
- Structured state: SQLite first
- Vault sync: Git first
- Capture sync later: Syncthing if needed
- A3-capable agents: Project Maintainer and Semantic Janitor only
- Migration deletion: manual A4 approval every time, quarantine first
- Backup strategy: Git plus restic later
- Service order: Git, n8n, Telegram, Paperless-ngx, Qdrant, monitoring, MCP

## Known Gaps

No services are deployed in Phase 1.

The new `lifeos` account setup requires running the privileged script at `00_SETUP/create_lifeos_user_and_install_phase1.sh` with sudo from the current account.
