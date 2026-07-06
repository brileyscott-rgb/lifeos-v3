# Agent Run Schema

## Required Fields

- `type`
- `agent`
- `approval_tier`
- `started`
- `completed`
- `status`
- `input_refs`
- `output_refs`
- `event_ids`

## Valid Statuses

- started
- completed
- failed
- blocked
- pending_approval

## Required Logging

- meaningful actions
- file changes
- approval requests
- failures

## Example YAML

```yaml
type: agent_run
agent: Knowledge Curator
approval_tier: A2
started: 2026-07-04T00:00:00Z
completed: 2026-07-04T00:01:00Z
status: completed
input_refs: []
output_refs: []
event_ids: []
```
