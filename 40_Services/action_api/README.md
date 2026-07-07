# LifeOS Action API

Read-write HTTP API for LifeOS capture operations. It is the single mutation boundary for the current Telegram capture/review lifecycle and future n8n ingress.

## Architecture

```text
Current active path:
Telegram /capture
-> local systemd user polling service
-> telegram_capture_bot.py --poll --interval 3
-> http://localhost:8788
-> 30_Capture/pending_review/
-> 50_Event_Log/events.jsonl

Future inactive path:
n8n → HTTP Request → lifeos-action-api:8788 → capture create/approve/reject
```

Current local Telegram bot contract: `http://localhost:8788`.

Docker/n8n internal access may later use Docker service DNS such as `http://lifeos-action-api:8788`. Until the Docker Compose/n8n contract is finalized, localhost host-run Action API remains the active local contract for Telegram polling. n8n workflows, webhooks, Cloudflare tunnels, AI proposals, and controlled file processor remain inactive.

## Endpoints

### GET /health

Health check.

```json
{"service": "lifeos-action-api", "status": "ok", "mode": "read_write"}
```

### GET /captures/pending

List pending review captures with 1-based indexes, sorted oldest-first.

### GET /captures/pending/<index>

Get a specific pending capture by index (numeric) or `latest`.

### GET /captures/<id>

Get a specific pending capture by capture_id.

### GET /captures/approved

List approved capture files.

### POST /captures

Create a new capture. Accepts JSON body: `{"text": "..."}`. Writes a markdown capture file to `pending_review/` and appends an event.

Successful mutation responses preserve legacy fields and add the hardened envelope:

```json
{
  "success": true,
  "ok": true,
  "capture_id": "cap_...",
  "status": "pending_review",
  "event_id": "evt_...",
  "data": {
    "capture_id": "cap_...",
    "status": "pending_review"
  },
  "error": null
}
```

Request limits:

- `MAX_REQUEST_BYTES = 65536`
- `MAX_CAPTURE_TEXT_CHARS = 20000`

Oversized request bodies return `payload_too_large`. Oversized capture text returns `capture_text_too_large`.

### POST /captures/<id>/approve

Move a pending capture to `approved/` and update frontmatter.

Returns `event_id` after both file mutation and event append succeed.

### POST /captures/<id>/reject

Move a pending capture to `rejected/` and update frontmatter.

Returns `event_id` after both file mutation and event append succeed.

## Contract Hardening

- Capture filenames include timestamp, random suffix, and slug text to avoid same-second same-text collisions.
- Capture files are created with exclusive create semantics and are never silently overwritten.
- Capture frontmatter includes `capture_id` and `created_event_id`.
- Approve/reject writes a collision-safe target file and updates status/frontmatter before event append.
- If event append fails after a mutation, the API attempts rollback and returns failure instead of ambiguous success.
- Success is returned only when the filesystem mutation and JSONL event append both succeed.

## Error Contract

Errors use symbolic strings and safe response envelopes:

```json
{
  "success": false,
  "ok": false,
  "error": "capture_not_found",
  "data": null,
  "event_id": null
}
```

Current symbolic errors include `invalid_json`, `payload_too_large`, `capture_text_required`, `capture_text_too_large`, `invalid_capture_id`, `capture_not_found`, `write_error`, `event_append_failed`, `mutation_failed`, `method_not_allowed`, and `not_found`.

## Docker

Added to `40_Services/n8n/docker-compose.yml` as `lifeos-action-api`, but Docker/n8n ingress is not the active Telegram contract yet.

## Security

See `notes/security_boundaries.md`.
