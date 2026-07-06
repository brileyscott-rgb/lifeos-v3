# LifeOS OpenCode Workflow

This OpenCode environment is dedicated to LifeOS V3 under `/home/lifeos`.

## Required First Reads

Before meaningful LifeOS work, read:

1. `/home/lifeos/LifeOS_V3_Source_of_Truth.md`
2. `/home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Current_Working_State.md`
3. `/home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Decisions/Phase_1B_Foundation_Decisions.md`
4. `/home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Policies/New_User_Account_Policy.md`
5. `/home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Policies/Sync_And_Backup_Policy.md`
6. `/home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Policies/A3_Agent_Policy.md`
7. `/home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Policies/Migration_Deletion_Policy.md`
8. `/home/lifeos/50_Event_Log/events.jsonl`

## Current Milestone

Foundation Lock-In.

## Hard Boundaries

- Do not migrate old LifeOS files yet.
- Do not start Docker services yet.
- Do not write real secrets into the vault, config files, prompts, logs, or event details.
- Preserve AI Mirror as observation-only.
- Preserve migration deletion as A4 manual approval every time with quarantine first.
- Keep work rooted in `/home/lifeos` unless explicitly asked otherwise.

## Quality Workflow

- Use Superpowers skills when relevant.
- Use agents when parallel specialist work improves quality.
- Verify before claiming completion.
- Keep Phase 1 and Phase 1B decisions as the source of truth until superseded by a new decision record.
