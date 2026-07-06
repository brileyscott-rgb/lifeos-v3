# Project Schema

## Required Fields

- `type`
- `status`
- `domain`
- `priority`
- `created`
- `updated`
- `workspace_path`
- `approval_tier`

## Required Project Files

- `index.md`
- `AI_Context.md`
- `Decisions.md`
- `Tasks.md`
- `Logs.md`
- `References.md`

## Valid Statuses

- active
- paused
- dormant
- completed
- archived

## Example YAML

```yaml
type: project
status: active
domain: Systems
priority: P1
created: 2026-07-04
updated: 2026-07-04
workspace_path: /home/lifeos/20_Workspaces/Engineering/example
approval_tier: A3
```
