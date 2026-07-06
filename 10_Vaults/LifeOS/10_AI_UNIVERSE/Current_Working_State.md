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

1. Verify OpenCode runs as `lifeos` from `/home/lifeos`.
2. Verify groups include `docker`, `video`, and `render`.
3. Verify Git, Docker, Node/npm, and OpenCode availability.
4. Initialize Git safely for `/home/lifeos`.
5. Exclude secrets, service data, backups, raw imports, and migration working folders.
6. Commit the clean scaffold.
7. Open Obsidian vault at `/home/lifeos/10_Vaults/LifeOS`.

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
