# Telegram Capture Workflow Placeholder

## Future n8n Workflow

When activated, this workflow will connect Telegram to the LifeOS capture intake system.

## Planned Flow

```
Telegram Trigger / Webhook
-> validate sender against TELEGRAM_ALLOWED_USER_ID
-> classify command (/capture, /link, /idea, /project, /approve, /reject, /status)
-> parse message content
-> write raw capture file to 30_Capture/<type>/
-> create pending_review capture with frontmatter
-> append event to 50_Event_Log/events.jsonl
-> send confirmation reply to Telegram
```

## Current Status

- No active workflow
- No credentials configured
- No webhook exposed
- No n8n service started

## Activation Checklist

- [ ] n8n Docker service is running
- [ ] Telegram bot token is stored in secrets (not in workflow JSON)
- [ ] Workflow credentials are configured via n8n credential store
- [ ] Webhook URL is registered with Telegram via setWebhook (or polling is enabled)
- [ ] `TELEGRAM_ALLOWED_USER_ID` is set
- [ ] `30_Capture/` directories exist
- [ ] Events log is writable
- [ ] Approved by LifeOS user

## Notes

- Do not store bot tokens in workflow JSON fields. Use n8n credential variables.
- Workflow JSON exports must be reviewed before committing to ensure no secrets are embedded.
- Test with a simple echo workflow before enabling capture routing.
