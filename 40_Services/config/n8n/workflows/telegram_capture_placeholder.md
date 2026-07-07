# Telegram Capture Workflow Placeholder

## Future n8n Workflow

When activated, this workflow will connect Telegram to the LifeOS capture intake system via the **LifeOS Action API** (not direct filesystem writes).

## Planned Flow

```
Telegram Trigger / Webhook
-> validate sender against TELEGRAM_ALLOWED_USER_ID
-> parse command text (/capture, /pending, /view, /approve, /reject, /status)
-> HTTP Request to Action API endpoint (GET/POST to lifeos-action-api:8788)
-> parse Action API JSON response
-> send reply to Telegram
```

### Capture Creation (Example)

```
/capture <text>
  → HTTP Request POST http://lifeos-action-api:8788/captures
    Body: {"text": "<capture content>", "source": "telegram", "sender_id": <id>}
  → Action API creates file in 30_Capture/pending_review/
  → Action API appends event to 50_Event_Log/events.jsonl
  → Returns JSON receipt with capture_id, event_id
  → n8n formats reply to Telegram
```

### Review Lifecycle

```
/pending
  → HTTP Request GET http://lifeos-action-api:8788/captures/pending
  → Action API returns numbered pending capture list
  → n8n formats reply

/approve 1
  → HTTP Request POST http://lifeos-action-api:8788/captures/<id>/approve
  → Action API moves file to 30_Capture/approved/
  → Action API appends event
  → n8n sends confirmation
```

## Key Constraint

**n8n must NOT write files directly.** All capture and review operations route through the Action API, which enforces bounded writes to `30_Capture/` and `50_Event_Log/` only — no vault access, no shell execution, no Docker socket.

## Current Status

- No active workflow
- No credentials configured
- No webhook exposed
- No n8n service started
- Action API is implemented and hardened (test count: 91/91)

## Activation Prerequisites

- [ ] n8n Docker service is running
- [ ] Action API container is running on `lifeos_internal`
- [ ] Cloudflare Tunnel (or approved ingress) is active and reachable
- [ ] Telegram bot token is stored in n8n credential store (not in workflow JSON)
- [ ] Telegram webhook is registered via setWebhook
- [ ] `telegram_allowed_user_ids` n8n variable is set
- [ ] No Execute Command nodes, no Docker socket, no vault writes
- [ ] Approved by LifeOS user

## Notes

- Do not store bot tokens in workflow JSON fields. Use n8n credential variables.
- Do not add Execute Command, git commit, or Docker socket nodes.
- n8n is the orchestrator — Action API is the data layer.
- Test with a simple echo/status webhook before enabling capture routing.
