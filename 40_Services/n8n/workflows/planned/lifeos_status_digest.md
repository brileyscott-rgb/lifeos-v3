# Planned Workflow: LifeOS Status Digest

## Status

**Not active.** Scaffold ready. Manual trigger only. No Telegram sending yet.

## Trigger

Manual trigger (n8n workflow editor "Workflow" → "Execute Workflow" button).

No schedule, no webhook, no Telegram trigger.

## Flow

```
Manual Trigger
  → Execute Command node
  → Command: python3 /home/lifeos/40_Services/scripts/lifeos_status.py --json
  → inspect returned JSON in n8n output panel
```

## Reads

- `30_Capture/` file counts via `lifeos_status.py`
- `50_Event_Log/events.jsonl` via `lifeos_status.py`
- Git status via `lifeos_status.py`
- Disk usage via `lifeos_status.py`
- Docker n8n container status via `lifeos_status.py`

## Writes

None. The status script is read-only.

## Future Steps

Only after explicit user approval:

- [ ] Schedule trigger (e.g., daily at 08:00)
- [ ] Telegram notification of status digest
- [ ] Dashboard panel in n8n
- [ ] Event log summary aggregation
- [ ] Capture queue alerts (pending count threshold)

## Implementation Notes

- The status script uses Python standard library only (no pip dependencies).
- JSON output is the canonical machine format.
- n8n can parse the JSON with a `Code` node or use the `Execute Command` node's built-in JSON parsing.
- The script does not need environment variables or secrets.
