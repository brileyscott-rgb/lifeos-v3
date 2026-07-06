# Planned Workflow: LifeOS Status Digest

## Status

**Verified — inactive.** Manual workflow test passed. The workflow is created, saved as inactive, and produces valid read-only JSON output. No schedule, Telegram, webhook, or Execute Command nodes.

## Trigger

Manual trigger (n8n workflow editor "Workflow" → "Execute Workflow" button).

No schedule, no webhook, no Telegram trigger.

## Flow

```
Manual Trigger
  → HTTP Request node
  → GET http://lifeos-status-api:8787/status
  → inspect returned JSON in n8n output panel
```

## Reads

- `30_Capture/` file counts via Status API
- `50_Event_Log/events.jsonl` via Status API

## Writes

None. The Status API is read-only.

## Future Steps

Only after explicit user approval:

- [ ] Schedule trigger (e.g., daily at 08:00)
- [ ] Telegram notification of status digest
- [ ] Dashboard panel in n8n
- [ ] Event log summary aggregation
- [ ] Capture queue alerts (pending count threshold)

## Implementation Notes

- The Status API uses Python standard library only (no pip dependencies).
- JSON output is the canonical machine format.
- n8n parses the JSON automatically with the HTTP Request node.
- The Status API does not need environment variables or secrets.
- The API runs in a separate container on the shared `lifeos_internal` Docker network.

## Verification

- [x] Manual Trigger → HTTP Request → GET `http://lifeos-status-api:8787/status` returns 200
- [x] Returned JSON is valid and read-only
- [x] Workflow saved as inactive (no activation toggle)
- [ ] Future schedule trigger (requires explicit user approval)
- [ ] Future Telegram notification (requires explicit user approval)
