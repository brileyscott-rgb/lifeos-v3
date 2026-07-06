# Planned Workflow: LifeOS Status Digest

## Trigger

Manual trigger or schedule (e.g., daily at 08:00).

## Flow

```
Manual trigger or schedule
  → execute safe status script
  → collect metrics:
     - pending captures count
     - approved unprocessed count
     - last event timestamp
     - git dirty/clean status
     - disk space
  → format summary message
  → send Telegram notification (future)
```

## Reads

- `30_Capture/pending_review/` — file count
- `30_Capture/approved/` — file count
- `50_Event_Log/events.jsonl` — last event timestamp
- `git status --short` — dirty/clean
- `df -h /` — disk space

## Writes

None yet. Future: Telegram message only.

## Status

**Not active.** No Telegram send credentials configured. No schedule enabled.
