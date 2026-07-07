# Event Log and Capture Privacy Policy

## Purpose

Define how LifeOS handles private data in event logs and capture files, and what users should know about the privacy implications of system telemetry.

## Scope

This policy covers:

- `50_Event_Log/events.jsonl` — structured event records
- `30_Capture/` — raw capture files (pending_review, approved, rejected, notes)
- Any future capture intake (Telegram, web, file drop, voice, photo)

## Privacy Principles

1. **Assumption of private data** — Runtime logs and captures may contain personal information, thoughts, ideas, links, messages, or other private content. Treat all capture and event data as potentially sensitive.

2. **Event logs are not fully redacted** — Event details may include capture text previews, file paths, user IDs, and action descriptions. Do not store secrets, credentials, or tokens in event details.

3. **Captures contain raw user content** — Capture files store the unmodified text, metadata, or file references sent by the user. No automatic redaction is applied.

4. **Access is bounded by permission tier** — Only authorized components and users can read event logs and capture directories (see Approval Tiers in the LifeOS architecture).

5. **No secrets in events** — Events must never contain Telegram bot tokens, Cloudflare credentials, API keys, passwords, or private keys. Event logging code must exclude token/credential fields.

6. **No credentials in capture content** — Capture files must not contain credentials, tokens, or secrets that would compromise system security. Users should avoid sending such content. If credentials are accidentally captured, they should be deleted from the capture and a quarantine event logged.

## Data Classification

| Data Type | Sensitivity | Examples |
|---|---|---|
| Event metadata | Low | event_id, timestamp, event type, source |
| Event details | Medium | capture_id, file_path, text_preview, user_id |
| Capture text | Medium to High | personal thoughts, ideas, notes, links |
| Capture file references | Medium | file paths, attachment metadata |
| Telegram sender ID | Medium | numeric user ID (not username) |
| Credentials/tokens | Critical | must never appear in events or captures |

## Retention

- Event logs and captures are retained indefinitely unless a specific cleanup or archival policy is defined.
- Users may request deletion of specific event entries or capture files. Deletion must follow the Migration Deletion Policy (manual A4 approval every time, quarantine first).
- No automatic cleanup or expiration is configured.

## Redaction Guidance

When reviewing event logs:

- Redact user IDs if sharing logs externally
- Redact capture text previews if they reveal sensitive personal information
- Never share event logs containing credentials or tokens

## Access Control

| Resource | Read Access | Write Access |
|---|---|---|
| `50_Event_Log/events.jsonl` | Status API (read-only), Action API (append), authorized users | Action API (append only) |
| `30_Capture/pending_review/` | Action API | Action API (create) |
| `30_Capture/approved/` | Action API | Action API (move) |
| `30_Capture/rejected/` | Action API | Action API (move) |

No component outside the specific API containers should read or write these paths directly.

## Incident Response

If private data is found in an event or capture that should not be there:

1. Do not delete without A4 review and quarantine.
2. Log a quarantine event with the original event_id or capture_id.
3. Review whether the data needs to be removed or the event/capture deleted.
4. Document the incident for future policy improvement.

## Policy Updates

This policy may be updated as the system grows. All updates require review and approval via the standard LifeOS decision process.

---

**Document Version**: 1.0
**Date**: 2026-07-06
**Status**: Locked
