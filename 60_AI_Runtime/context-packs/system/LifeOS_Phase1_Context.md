# LifeOS Phase 1 Context

## Root

`/home/lifeos/`

## Source of Truth

`/home/lifeos/LifeOS_V3_Source_of_Truth.md`

## Phase 1 Scope

Create inert control-plane scaffold, governance docs, schemas, templates, event logs, runtime definitions, and migration safety structures.

## Not Active In Phase 1

- live services
- Docker deployment
- ChatOps bot
- MCP runtime
- old LifeOS migration
- real secrets
- Linux user creation

## Safety Rules

- A4 always requires explicit human approval.
- Migration deletion is A4 and requires audit trail.
- AI Mirror observes only and must not enforce.
- Direct mutation requires role, path, approval tier, and logging.
