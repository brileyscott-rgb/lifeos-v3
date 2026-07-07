# Action API Contract Hardening Spec

Status: implementation contract for Critical Phase 3  
Date: 2026-07-07  
Scope: LifeOS Action API capture/review lifecycle only

## Goal

Harden the Action API as the single mutation boundary for Telegram, future n8n ingress, and capture review lifecycle operations.

This phase keeps the current filesystem plus JSONL event-log architecture. It does not introduce a database, public ingress, AI proposals, controlled file processing, webhooks, tunnels, or service changes.

## Active Deployment Contract

Current active path:

```text
Telegram /capture
-> local systemd user polling service
-> telegram_capture_bot.py --poll --interval 3
-> Action API at http://localhost:8788
-> 30_Capture/pending_review
-> 50_Event_Log/events.jsonl
```

Current local Telegram bot contract:

- The host-run Telegram bot expects the Action API at `http://localhost:8788`.
- If Action API is unavailable or returns `success: false`, Telegram reports that no action was taken.
- Telegram compatibility requires preserving the existing top-level `success`, `capture_id`, `file_name`, `relative_path`, and `event_id` fields where already used.

Future Docker/n8n contract:

- n8n and Docker-internal callers may later call Docker service DNS such as `http://lifeos-action-api:8788`.
- That contract is not active until Docker Compose/n8n ingress is explicitly finalized.
- n8n, webhooks, Cloudflare tunnels, AI proposals, and controlled file processor remain inactive.

## Response Envelope

All mutation responses use a compatibility envelope:

Successful mutation minimum:

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

Error response minimum:

```json
{
  "success": false,
  "ok": false,
  "error": "capture_not_found",
  "data": null,
  "event_id": null
}
```

Rules:

- `success` remains the legacy compatibility boolean.
- `ok` mirrors `success` for the new contract.
- `error` remains a short symbolic string for Telegram compatibility.
- `data` contains structured response data on success and `null` on error.
- `event_id` is non-null only when the mutation event was durably appended.

## Event ID Semantics

- Every accepted mutation generates an `event_id` before or during the mutation.
- The returned `event_id` must match the event appended to `50_Event_Log/events.jsonl`.
- Capture creation frontmatter includes `capture_id` and `created_event_id`.
- Approval/rejection frontmatter records status and processing timestamp; when practical it also records the processing event ID.
- The API must not return success if the lifecycle mutation cannot be correlated to an appended event.

## Atomicity Strategy

This phase uses practical filesystem rollback, not a database transaction.

Capture creation:

1. Validate request size and text.
2. Generate `capture_id` and `event_id`.
3. Build a collision-resistant filename.
4. Write the pending review file using exclusive create semantics.
5. Append the event using the pre-generated `event_id`.
6. If event append fails, remove the newly-created pending file if it is still safe to remove.
7. Return success only after both file creation and event append succeed.

Approve/reject:

1. Validate capture ID.
2. Resolve a pending capture by ID only from `pending_review`.
3. Generate `event_id`.
4. Write the target approved/rejected file with updated frontmatter using exclusive create semantics.
5. Remove the pending source only after the target write succeeds.
6. Append the lifecycle event using the pre-generated `event_id`.
7. If event append fails, attempt rollback by restoring the original pending file and removing the target file.
8. Return success only when state mutation and event append both succeed.

If rollback cannot be completed, the API still returns a symbolic failure such as `mutation_failed` or `event_append_failed`; it must not pretend success.

## Filename Collision Strategy

- Capture IDs keep timestamp plus random entropy.
- Pending filenames include timestamp, a random suffix, and slug text.
- Approved/rejected target writes use exclusive create semantics.
- If a target filename already exists, the API chooses a collision-safe suffixed filename instead of overwriting.
- Existing captures are never moved, deleted, or overwritten as part of collision handling.

## Request Size Limits

Default internal limits:

```text
MAX_REQUEST_BYTES = 65536
MAX_CAPTURE_TEXT_CHARS = 20000
```

Rules:

- Requests with `Content-Length` over `MAX_REQUEST_BYTES` return `payload_too_large`.
- Invalid `Content-Length` returns `invalid_json`.
- Capture text longer than `MAX_CAPTURE_TEXT_CHARS` returns `capture_text_too_large`.
- Empty or missing text returns `capture_text_required`.

## Symbolic Error Codes

Stable errors for this phase:

```text
invalid_json
payload_too_large
capture_text_required
capture_text_too_large
invalid_capture_id
capture_not_found
capture_not_pending
mutation_failed
method_not_allowed
not_found
```

Errors must not expose stack traces, absolute internal filesystem paths, tokens, secrets, or raw exception strings.

## Endpoint Contracts

### POST /captures

Current behavior:

- Accepts JSON body with `text`.
- Creates a pending capture file.
- Appends a `telegram.capture_created` event.

Desired hardened behavior:

- Enforces request and text size limits.
- Requires string non-empty text.
- Creates collision-safe pending file with exclusive create.
- Writes `capture_id` and `created_event_id` frontmatter.
- Returns `event_id` and compatibility envelope.
- Returns failure if event append fails and attempts safe rollback.

### GET /captures/pending

Current behavior:

- Lists pending captures with 1-based indexes, oldest first.

Desired contract:

- Remains read-only.
- Preserves existing `success`, `pending`, and `count` fields.
- Does not mutate event log or capture files.

### GET /captures/pending/<n>

Current behavior:

- Returns pending capture by numeric index.

Desired contract:

- Remains read-only.
- Invalid or missing index returns symbolic `capture_not_found`.

### GET /captures/pending/latest

Current behavior:

- Returns newest pending capture.

Desired contract:

- Remains read-only.
- Empty queue returns symbolic `capture_not_found`.

### GET /captures/<capture_id>

Current behavior:

- Returns a pending capture by ID.

Desired contract:

- Reject malformed capture IDs consistently.
- Return symbolic `capture_not_found` if not pending.
- Remain read-only.

### POST /captures/<capture_id>/approve

Current behavior:

- Moves pending capture to approved.
- Updates frontmatter status.
- Appends `telegram.capture_approved`.

Desired hardened behavior:

- Reject malformed capture IDs consistently.
- Return `capture_not_found` or `capture_not_pending` for duplicates/non-pending captures.
- Use collision-safe target write; never overwrite.
- Return `event_id` and compatibility envelope.
- Return failure if event append fails and attempt rollback.

### POST /captures/<capture_id>/reject

Current behavior:

- Moves pending capture to rejected.
- Updates frontmatter status.
- Appends `telegram.capture_rejected`.

Desired hardened behavior:

- Same as approve, with `status: rejected` and `telegram.capture_rejected`.

## Telegram Compatibility Notes

- Telegram currently checks `result.get("success")` and reads top-level `capture_id`.
- This phase must not require Telegram code changes.
- New `ok`, `data`, and `event_id` fields are additive.
- Existing no-action fallback behavior remains valid for all symbolic errors.

## n8n Future Compatibility Notes

- n8n will treat the Action API as the single mutation boundary.
- n8n must not directly write `30_Capture/` or `50_Event_Log/events.jsonl`.
- n8n can use `event_id` for correlation once ingress is activated later.
- Webhook replay/idempotency is not implemented in this phase and remains a future ingress hardening item.

## Tests Required

- Capture creation returns `event_id`.
- Capture creation envelope preserves legacy fields and adds `ok`, `data`, `error`, `event_id`.
- Same-second same-text captures create distinct files and do not overwrite.
- Oversized request body returns `payload_too_large`.
- Oversized capture text returns `capture_text_too_large`.
- Malformed capture IDs are rejected consistently.
- Approve returns `event_id`.
- Reject returns `event_id`.
- Approve/reject cannot silently succeed if event append fails.
- Capture creation cannot silently succeed if event append fails.
- Errors are symbolic and safe.
- Telegram offline tests continue to pass without live Telegram access.
