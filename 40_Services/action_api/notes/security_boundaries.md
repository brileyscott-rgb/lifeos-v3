# Action API Security Boundaries

## Hard Boundaries

1. **No shell execution** — Uses Python standard library exclusively. No subprocess, no shell=True.
2. **No Docker socket** — Container does not mount /var/run/docker.sock.
3. **No vault access** — Container cannot access 10_Vaults/.
4. **No secrets access** — Container does not read .env, secrets files, or n8n credential/database files.
5. **No arbitrary paths** — All path operations resolve within /lifeos/capture/ subdirectories only.
6. **Path traversal prevention** — Absolute paths and `../` sequences are rejected.
7. **Read-write scope limited** — Container writes only to 30_Capture/ and appends to 50_Event_Log/events.jsonl. No other write targets.
8. **No ambiguous mutation success** — Capture creation, approval, and rejection return success only after the capture file mutation and event log append both succeed.
9. **No silent overwrite** — Capture and review lifecycle writes use collision-resistant names and exclusive create semantics where practical.

## Container Hardening

| Setting | Value |
|---|---|
| `cap_drop` | `ALL` |
| `security_opt` | `no-new-privileges:true` |
| User | uid 1001 (non-root) |
| Restart | `unless-stopped` |
| Network | `lifeos_internal` only |

## Mount Scope

| Host Path | Container Path | Mode |
|---|---|---|
| `30_Capture/` | `/lifeos/capture` | `rw` |
| `50_Event_Log/` | `/lifeos/event-log` | `rw` |

## Current Deployment Contract

The active local Telegram polling service calls the Action API at `http://localhost:8788` from the host/user session.

Docker-internal callers such as future n8n workflows may later use service DNS such as `http://lifeos-action-api:8788`, but that ingress contract is not active until Docker Compose and n8n workflow activation are explicitly finalized.

n8n workflows, Telegram webhooks, Cloudflare tunnels, AI proposal generation, and controlled file processor execution remain inactive.

## Mutation Integrity Contract

- `POST /captures` generates `capture_id` and `event_id`, writes a pending capture file, appends the event, then returns the compatibility envelope.
- Pending capture frontmatter includes `capture_id` and `created_event_id`.
- `POST /captures/<capture_id>/approve` and `/reject` resolve only pending captures, write a collision-safe target file, remove the pending file, append the event, then return `event_id`.
- If event append fails after a file mutation, the API attempts rollback and returns `event_append_failed` instead of success.
- If rollback or file mutation cannot be completed safely, the API returns a symbolic failure and does not expose stack traces or host paths.

## Request Limits

| Limit | Value |
|---|---:|
| `MAX_REQUEST_BYTES` | `65536` |
| `MAX_CAPTURE_TEXT_CHARS` | `20000` |

Oversized bodies return `payload_too_large`. Oversized capture text returns `capture_text_too_large`.

## Error Contract

Errors are stable symbolic strings in a safe envelope. They must not include exception text, stack traces, filesystem paths, tokens, or secrets.

Current mutation error codes include `invalid_json`, `payload_too_large`, `capture_text_required`, `capture_text_too_large`, `invalid_capture_id`, `capture_not_found`, `write_error`, `event_append_failed`, `mutation_failed`, `method_not_allowed`, and `not_found`.

## Not Mounted

- `/home/lifeos` (root)
- `10_Vaults/`
- `40_Services/secrets/`
- `40_Services/n8n/.env`
- `/var/run/docker.sock`
- `.git/`
- n8n database or credential files

## Operates Only On

- `30_Capture/pending_review/`
- `30_Capture/approved/`
- `30_Capture/rejected/`
- `30_Capture/processed/`
- `50_Event_Log/events.jsonl`

## Out of Scope

The Action API does not handle proposals. Proposal creation, storage, versioning, viewing, and approval are the responsibility of the future AI Processing Pipeline and Controlled File Processor. The Action API's capture lifecycle (create, list, view, approve, reject) ends when a capture is marked `approved` — it does not generate, store, or route proposals.
