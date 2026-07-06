# Current Working State

## Active Milestone

Foundation Lock-In for LifeOS V3 under `/home/lifeos`.

## Current Environment

- User: `lifeos`
- Root: `/home/lifeos`
- Vault: `/home/lifeos/10_Vaults/LifeOS`
- Event log: `/home/lifeos/50_Event_Log/events.jsonl`
- OpenCode config: `/home/lifeos/.config/opencode/opencode.json`
- OpenCode binary: `/home/lifeos/.local/bin/opencode`

## Completed

- LifeOS V3 source-of-truth plan created.
- Phase 1 scaffold created.
- Phase 1B decisions encoded.
- New `lifeos` user created.
- Login password repaired.
- Scaffold copied into `/home/lifeos`.
- Event log contains scaffold, decision, and login repair events.
- OpenCode handoff/config package prepared for `lifeos`.
- OpenCode verified running as `lifeos` from `/home/lifeos`.
- Groups verified: `docker`, `video`, `render`.
- Git, Docker CLI, Node/npm, and OpenCode availability verified.
- Git initialized safely for `/home/lifeos`.
- Safe `.gitignore` added for secrets, service data, backups, raw imports, migration work, local state, and copied reference/vendor trees.
- Initial clean scaffold/control-plane commit created: `85acdb7 Initialize LifeOS V3 scaffold`.
- Git branch renamed to `main`.

## Current Decisions

- ChatOps: Telegram
- Alerts later: Gotify or ntfy
- Vault sync: Git first
- Capture sync later: Syncthing if needed
- AI strategy: hybrid local plus cloud
- Vector store: Qdrant
- Structured state: SQLite first
- A3 agents: Project Maintainer and Semantic Janitor only
- Migration deletion: manual A4 approval every time, quarantine first
- Backup strategy: Git plus restic later
- Service order: Git, n8n, Telegram, Paperless-ngx, Qdrant, monitoring, MCP

## Next Milestone

Foundation Lock-In:

1. Add a Git remote for `/home/lifeos` when the remote target is chosen.
2. Push branch `main` after remote verification.
3. Open Obsidian vault at `/home/lifeos/10_Vaults/LifeOS`.
4. Prepare n8n compose/config scaffolding only after Git remote backup exists.

## Do Not Do Yet

- Do not migrate old LifeOS files yet.
- Do not start Docker services yet.
- Do not configure real Telegram/n8n/Paperless/Qdrant secrets yet.
- Do not loosen `/home/lifeos/40_Services/secrets` permissions.

## Required First Reads

- `/home/lifeos/LifeOS_V3_Source_of_Truth.md`
- `/home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Current_Working_State.md`
- `/home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Decisions/Phase_1B_Foundation_Decisions.md`
- `/home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Policies/New_User_Account_Policy.md`
- `/home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Policies/Sync_And_Backup_Policy.md`
- `/home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Policies/A3_Agent_Policy.md`
- `/home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Policies/Migration_Deletion_Policy.md`
- `/home/lifeos/50_Event_Log/events.jsonl`
