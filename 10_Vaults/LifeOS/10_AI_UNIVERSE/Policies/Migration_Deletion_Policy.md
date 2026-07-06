# Migration Deletion Policy

## Rule

All migration deletion requires manual A4 approval every time.

## Deletion Workflow

```text
candidate deletion detected
→ migration reviewer summarizes file
→ duplicate/conflict check
→ pre-action snapshot path recorded
→ deletion reason written
→ approval request created
→ human approves
→ event log records deletion
→ file moved to quarantine/archive first
→ hard delete only after later review
```

## Quarantine First

Use quarantine before hard deletion:

```text
delete recommendation
→ move to 99_Archive/migration-staging/deferred-delete/
→ keep for 30-90 days
→ delete later if still useless
```

## Required Record Fields

- source path
- proposed deletion reason
- duplicate/conflict evidence
- pre-action snapshot
- approval event ID
- human approver
- quarantine path
- hard-delete review date
