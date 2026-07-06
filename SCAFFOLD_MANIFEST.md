# LifeOS V3 Scaffold Manifest

Root: `/home/lifeos`

## Phase

Phase 1: Control Plane Foundation

## Created Layers

- `00_Inbox/` - raw capture landing zones.
- `10_Vaults/LifeOS/` - curated Obsidian meaning layer.
- `20_Workspaces/` - active work/project filesystem layer.
- `30_Documents/` - formal document intake and category folders.
- `40_Services/` - future Docker Compose, config, data, secrets, and backup layout.
- `50_Event_Log/` - append-only factual system activity spine.
- `60_AI_Runtime/` - prompts, agents, schemas, MCP definitions, context packs, evals, memory.
- `70_Backups/` - future versioned backup targets.
- `99_Archive/` - old imports, deprecated workflows, migration staging.

## Phase 1 Constraint

This scaffold is inert by default. It does not start services, create users, install packages, migrate old files, or write secrets.

Later-phase folders are marked scaffold-only until their phase is explicitly approved.
