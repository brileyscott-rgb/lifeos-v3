# Planned Workflow: Event Log Watcher

## Trigger

Schedule (e.g., every 15 minutes).

## Flow

```
Schedule trigger
  → check 50_Event_Log/events.jsonl
  → detect new events since last check
  → summarize new event types
  → notify via Telegram (future)
```

## Reads

- `50_Event_Log/events.jsonl` — new events since last cursor

## Writes

- Future: cursor/tracking state (local file or n8n variable)

## Status

**Not active.** No schedule enabled. No Telegram configured.
