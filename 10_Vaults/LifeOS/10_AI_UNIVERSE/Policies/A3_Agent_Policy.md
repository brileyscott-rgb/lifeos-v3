# A3 Agent Policy

## Initial A3 Agents

Only these agents should begin with A3 direct modification capability:

- Project Maintainer
- Semantic Janitor

## Project Maintainer A3 Scope

Allowed paths:

- `10_Vaults/LifeOS/02_PROJECTS/<approved_project>/`
- `20_Workspaces/<approved_domain>/<approved_project>/`
- `50_Event_Log/`

Allowed actions:

- update project index
- update `AI_Context.md`
- update `Decisions.md` after approval
- update `Tasks.md`
- update `Logs.md`
- update `References.md`
- record event IDs

Prohibited actions:

- delete project files
- modify unrelated projects
- touch secrets
- publish externally
- change system configs
- perform financial, credential, or system-level actions

## Semantic Janitor A3 Scope

Allowed paths:

- `10_Vaults/LifeOS/01_INBOX/`
- `10_Vaults/LifeOS/04_KNOWLEDGE/`
- `10_Vaults/LifeOS/05_RESOURCES/`
- `10_Vaults/LifeOS/09_DASHBOARDS/`
- `50_Event_Log/maintenance/`

Allowed actions:

- fix broken links
- normalize metadata
- add cross-links
- update indexes
- mark stale notes
- move low-risk notes within approved areas

Prohibited actions:

- delete notes
- rewrite canonical notes without approval
- merge notes destructively
- modify projects outside scope
- touch secrets
- enforce behavioral rules

## All Other Agents

All other agents remain A0-A2 until proven safe and explicitly upgraded.
