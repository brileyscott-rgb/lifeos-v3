# Planned Workflow: AI Job Intake Placeholder

## Trigger

Future: Telegram command, OpenCode CLI, or webhook.

## Flow

```
Telegram/OpenCode/CLI command
  → create job file in 40_Services/ai_worker/jobs/pending/
  → classify risk level
  → set approval_state: not_requested
  → notify user via Telegram (future)
  → no automatic implementation
```

## Reads

- User input (command arguments)

## Writes

- `40_Services/ai_worker/jobs/pending/` — new job file (Markdown)

## Status

**Not active.** No trigger implemented. Job creation is CLI-based via `ai_worker.py` only.
