# Planned Workflow: Approved Capture Reminder

## Trigger

Schedule (e.g., daily at 09:00, 14:00, 19:00).

## Flow

```
Schedule trigger
  → count files in 30_Capture/approved/
  → if count > 0:
      → list filenames with timestamps
      → send reminder via Telegram (future)
  → if count == 0:
      → silent exit
```

## Reads

- `30_Capture/approved/` — file listing and count

## Writes

None. Read-only workflow.

## Status

**Not active.** No schedule enabled. No Telegram configured.
