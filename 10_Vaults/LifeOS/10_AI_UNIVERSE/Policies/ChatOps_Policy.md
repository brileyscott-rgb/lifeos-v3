# ChatOps Policy

## Primary Channel

Telegram is the recommended primary approval and interaction channel.

## Later Alert Channel

Gotify or ntfy should be considered later for simple system alerts.

## Telegram Responsibilities

- approval requests
- agent summaries
- daily digest
- migration review prompts
- project update summaries

## Standard Commands

```text
/approve <request_id>
/reject <request_id>
/revise <request_id>
/defer <request_id>
/archive <request_id>
/status
```

## Secret Handling

Bot tokens are real secrets and must never be stored in the vault or event-log details.
