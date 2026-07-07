# Telegram Review Button UX Design

**Status:** Final / Implemented
**Date:** 2026-07-07
**Phase:** Telegram / Action API — Review Button UX (V1)

## 1. Overview

Add inline keyboard buttons to the Telegram review flow so users can approve/reject pending captures without typing command text. V1 is pull-based (user-initiated via `/view`), capture-first by default, uses HMAC stateless callback tokens, and routes all mutations through the Action API.

## 2. Pull-Based V1 Flow

```
/p
→ numbered pending list (text-only, no per-item buttons)

/view 1  (or /view latest, /view <capture_id>)
→ capture summary with inline buttons:
   [View Full Text]  [Approve]  [Reject]

[Approve] tap → confirmation message with new buttons:
   [Confirm Approve]  [Cancel]

[Confirm Approve] → mutation via Action API POST → result with event_id

[Reject] / [Confirm Reject] — same pattern as approve
[View Full Text] → sends full capture content as separate message
[Cancel] → removes buttons, no mutation
```

No auto-send review cards. No per-item buttons on `/p` list. Capture intake remains separate from review.

## 3. Callback Token System

### Token Format

```
rv1|a|cap_ref|exp_hex|mac
```

| Field | Description | Length |
|---|---|---|
| `rv1` | Review token version 1 | 3 |
| `\|` | Separator | 1 |
| `a` | Action (see below) | 1–2 |
| `\|` | Separator | 1 |
| `cap_ref` | First 12 hex chars of SHA256(capture_id) | 12 |
| `\|` | Separator | 1 |
| `exp_hex` | Expiration unix timestamp, hex-encoded | 8 |
| `\|` | Separator | 1 |
| `mac` | First 12 hex chars of HMAC-SHA256 | 12 |

**Maximum: 3+1+2+1+12+1+8+1+12 = 41 bytes** — within Telegram's 64-byte callback_data limit.

### Actions

| Action | Char(s) | Purpose |
|---|---|---|
| `v` | 1 | View full text of a specific capture |
| `a` | 1 | Initial approve intent — shows confirmation |
| `r` | 1 | Initial reject intent — shows confirmation |
| `ca` | 2 | Confirm approve — triggers Action API mutation |
| `cr` | 2 | Confirm reject — triggers Action API mutation |
| `n` | 1 | Cancel/no-op — removes buttons |

### HMAC Payload (signed)

```
{version}|{action}|{sender_id}|{cap_ref}|{exp_hex}
```

Example: `rv1|a|12345|a1b2c3d4e5f6|690f2a10`

The `sender_id` is NOT stored in the visible callback_data. It is only in the signed payload. Verification reconstructs the payload using the Telegram callback query sender's ID — a different sender will produce a different MAC and fail verification without revealing why.

### Key Derivation

```python
import hashlib, hmac

# Never logged, never stored in vault, never committed.
HMAC_KEY = hashlib.sha256(BOT_TOKEN.encode("utf-8")).digest()
```

This is deterministic (same bot token → same key), requires no extra config, and is never exposed in logs, vaults, or docs.

### Token Generation

```python
import time, hashlib, hmac

TOKEN_VERSION = "rv1"
TOKEN_TTL = 600  # 10 minutes
MAC_TRUNC = 12   # hex chars

def _make_token(action, sender_id, cap_ref):
    exp_ts = int(time.time()) + TOKEN_TTL
    exp_hex = format(exp_ts, "x")
    payload = f"{TOKEN_VERSION}|{action}|{sender_id}|{cap_ref}|{exp_hex}"
    mac = hmac.new(HMAC_KEY, payload.encode("utf-8"), hashlib.sha256).hexdigest()[:MAC_TRUNC]
    return f"{TOKEN_VERSION}|{action}|{cap_ref}|{exp_hex}|{mac}"
```

### Token Verification (fail-closed)

```python
def _verify_token(callback_sender_id, callback_data):
    parts = callback_data.split("|")
    if len(parts) != 5:
        return None
    version, action, cap_ref, exp_hex, mac = parts

    if version != TOKEN_VERSION:
        return None
    if action not in ("v", "a", "r", "ca", "cr", "n"):
        return None

    try:
        exp_ts = int(exp_hex, 16)
    except ValueError:
        return None
    if time.time() > exp_ts:
        return None

    payload = f"{version}|{action}|{callback_sender_id}|{cap_ref}|{exp_hex}"
    expected = hmac.new(HMAC_KEY, payload.encode("utf-8"), hashlib.sha256).hexdigest()[:MAC_TRUNC]
    if not hmac.compare_digest(mac, expected):
        return None

    return {"action": action, "cap_ref": cap_ref, "version": version}
```

Returns `None` for ALL failure cases (expired, sender mismatch, MAC mismatch, malformed, unknown action). No distinction leaked.

## 4. Capture Reference Resolution

The `cap_ref` is the first 12 hex chars of SHA256(capture_id). To resolve it back to a capture:

1. Call `GET /captures/pending` on the Action API
2. For each pending capture, compute SHA256(capture_id)[:12]
3. Match against `cap_ref`

### Resolution Results

| Matches | Behavior |
|---|---|
| 0 | "Capture no longer pending. Please /p to refresh." |
| 1 | Resolve to full capture_id, proceed |
| >1 | "Ambiguous capture reference. Please /p to refresh." |

12 hex chars = 48 bits of hash, collision probability among N pending captures is negligible for practical N (< 100).

## 5. Callback Query Handler

A new top-level handler in `process_update()`:

```python
def process_callback_query(update):
    cb = update.get("callback_query", {})
    sender_id = cb.get("from", {}).get("id")
    chat_id = cb.get("message", {}).get("chat", {}).get("id")
    msg_id = cb.get("message", {}).get("message_id")
    callback_data = cb.get("data", "")
    cb_id = cb.get("id")

    # 1. Authorization gate
    if not is_authorized_sender(sender_id):
        tg_api("answerCallbackQuery", {"callback_query_id": cb_id})
        return

    # 2. Review-mode guard — protects against stale buttons
    if not ALLOW_REVIEW_COMMANDS:
        tg_api("answerCallbackQuery", {
            "callback_query_id": cb_id,
            "text": "Review mode is disabled. Please /p to refresh."
        })
        return

    # 3. Token verification (handles expiry, sender mismatch, etc.)
    token = _verify_token(sender_id, callback_data)
    if token is None:
        tg_api("answerCallbackQuery", {
            "callback_query_id": cb_id,
            "text": "Invalid or expired button. Please /p to refresh."
        })
        return

    # 4. Answer the callback (no text) to stop the loading spinner.
    #    Every success path answers exactly once here, then edits/sends.
    tg_api("answerCallbackQuery", {"callback_query_id": cb_id})

    action = token["action"]
    cap_ref = token["cap_ref"]

    if action == "n":
        _handle_cancel(chat_id, msg_id)
    elif action == "v":
        _handle_view_full(chat_id, cap_ref)
    elif action == "a":
        _handle_approve_intent(chat_id, msg_id, sender_id, cap_ref)
    elif action == "r":
        _handle_reject_intent(chat_id, msg_id, sender_id, cap_ref)
    elif action == "ca":
        _handle_confirm_approve(chat_id, msg_id, sender_id, cap_ref)
    elif action == "cr":
        _handle_confirm_reject(chat_id, msg_id, sender_id, cap_ref)
```

### Answering Callback Queries

Every callback path must answer the callback query **exactly once**:
- Error paths (unauthorized, review disabled, token invalid/expired): answer with short `text` and return. No mutation, no message edit.
- Success paths (all valid action tokens): answer with no text to stop the loading spinner, then edit or send the relevant message.
- Never call `answerCallbackQuery` twice for the same callback query ID.

## 6. View Handler Modifications

Current `handle_view()` sends full capture content. For V1 with buttons:

```
handle_view is split:
1. Call GET /captures/pending/<index> or /captures/<capture_id>
2. Format short summary (metadata + preview line, no full body)
3. Generate three tokens: v (view full), a (approve intent), r (reject intent)
4. Send message with summary + inline keyboard:
   Row 1: [View Full Text]
   Row 2: [Approve]  [Reject]
```

The summary message includes: capture index, capture_id, status, created_at, source, and a single preview line (first non-empty content line, truncated to 120 chars).

[View Full Text] sends the complete capture content as a SEPARATE new text message with no approve/reject buttons.

## 7. Approve / Reject Confirmation Flow

### Initial Intent (a/r tokens)

User taps [Approve]:
1. Bot verifies `a` token
2. Bot resolves cap_ref → capture_id via GET /captures/pending
3. Bot edits the original summary message (editMessageText) to show:
   ```
   Confirm approval?
   
   capture_id: cap_20260707_120000_a1b2c3_slug
   Preview: My quick note about...
   ```
4. Bot generates new `ca` (confirm approve) and `n` (cancel) tokens
5. Bot sets inline keyboard: [Confirm Approve] [Cancel]

[Reject] tap follows the same pattern with `r` → `cr` tokens.

No mutation occurs at this stage.

### Confirmed Mutation (ca/cr tokens)

User taps [Confirm Approve]:
1. Bot verifies `ca` token
2. Bot resolves cap_ref → capture_id via GET /captures/pending
3. If not found or not pending: error message, no mutation
4. Bot calls POST /captures/<capture_id>/approve on Action API
5. Bot edits the original message to show:
   ```
   ✅ Approved
   
   capture_id: cap_20260707_120000_a1b2c3_slug
   event_id: evt_20260707T120500Z_telegram_capture_approved
   ```
6. Keyboard removed (empty inline_keyboard or editMessageReplyMarkup with no keyboard)

### Cancel (n token)

User taps [Cancel]:
1. Bot verifies `n` token
2. Bot edits message to remove buttons: "Cancelled."

## 8. Error Handling (all fail-closed)

| Condition | User-visible response | Does not |
|---|---|---|
| Malformed callback_data | "Invalid or expired button. Please /p to refresh." | Leak structure details |
| Expired token | Same as above | Distinguish from other failures |
| Sender mismatch | Same as above (MAC fails) | Reveal sender_id mismatch |
| MAC mismatch | Same as above | Reveal what part failed |
| 0 matches resolving cap_ref | "Capture no longer pending. Please /p to refresh." | Mutate anything |
| >1 matches | "Ambiguous capture reference. Please /p to refresh." | Mutate anything |
| Action API unavailable | "LifeOS review unavailable. No action was taken." | Store partial state |
| Action API mutation fails | Show Action API error message or "Mutation failed. No action was taken." | Commit partial state |

## 9. Security Model

| Property | Mechanism |
|---|---|
| Sender-bound | sender_id is in the signed HMAC payload |
| Capture-bound | cap_ref (SHA256 of capture_id) is in the signed payload |
| Action-bound | Action char is in the signed payload — a token cannot be reused for a different action |
| Short-lived | exp_hex expiration checked before any action |
| Tamper-proof | HMAC-SHA256 with key derived from bot token |
| Stateless | No runtime token storage needed |
| No direct filesystem | All mutations go through Action API |
| No raw paths in callback_data | cap_ref is a hash, not a file path |

## 10. Gating

Inline buttons respect `ALLOW_REVIEW_COMMANDS`:
- In capture-first default mode (`ALLOW_REVIEW_COMMANDS=False`): the `process_update` guard blocks review commands before they reach handler dispatch, including `/view`. Buttons are never shown.
- When review mode is active (`--allow-review` or `TELEGRAM_ALLOW_REVIEW=1`): `/view` works and inline buttons appear.
- `process_callback_query` also checks `ALLOW_REVIEW_COMMANDS` as a redundant safety net. If review mode is disabled, the callback handler answers the callback query once with "Review mode is disabled. Please /p to refresh." and returns with no mutation. This protects against stale buttons tapped after review mode was disabled.

## 11. Test Requirements

All tests offline via `unittest.mock.patch`:

### Token Tests
- Token generation produces valid format
- Token verification accepts valid token
- Token verification rejects expired token (mock time)
- Token verification rejects malformed callback_data (wrong parts, wrong version)
- Token verification rejects unknown action
- Token verification rejects wrong sender (MAC mismatch)
- Token for action `a` fails verification when used as action `r` (action-bound)

### Capture Resolution Tests
- cap_ref resolves to one capture from GET /captures/pending response
- cap_ref with 0 matches returns fail-closed error
- cap_ref with >1 matches returns fail-closed error

### Button Flow Tests
- Initial approve tap (`a`) does NOT call Action API approve endpoint
- Initial reject tap (`r`) does NOT call Action API reject endpoint
- Confirm approve (`ca`) resolves cap_ref, verifies pending, calls POST approve, shows event_id
- Confirm reject (`cr`) resolves cap_ref, verifies pending, calls POST reject, shows event_id
- Cancel (`n`) removes buttons, does not mutate
- View full (`v`) sends full content as new message
- View full does not add approve/reject buttons

### Error Tests
- Expired token on confirm approve does not mutate
- Capture no longer pending on confirm approve does not mutate
- Action API unavailable on confirm shows safe message

### Boundary Tests
- `process_callback_query` does NOT directly open/move/write capture files or event log
- `process_callback_query` enforces sender authorization before token verification
- Callback query is answered (answerCallbackQuery called) for all paths
- callback_data stays under 64 bytes for all action types
- Callback tapped while `ALLOW_REVIEW_COMMANDS=False` answers callback and performs no mutation

## 12. Files Changed

| File | Change |
|---|---|
| `40_Services/chatops/telegram/telegram_capture_bot.py` | Add callback token functions, callback query handler, /view modification (summary + buttons), approve/reject intent/confirm handlers, cancel handler, view_full handler |
| `40_Services/chatops/telegram/tests/test_telegram_bot.py` | Add all button flow + token tests |
| `40_Services/chatops/telegram/README.md` | Document button flow, callback tokens, test modes |
| `docs/superpowers/specs/2026-07-07-telegram-review-button-ux-design.md` | This design doc |

Action API — No changes needed. Existing endpoints are sufficient.

## 13. What Stays the Same

- `/p` stays text-only in V1
- No auto-send review cards for new captures
- No `/capture` from review flow
- Capture-first default mode unchanged
- `--allow-review` flag still required for review in poll mode
- Action API stays the same
- No n8n, Docker, Cloudflare, AI, file processor changes
- No new environment variables (HMAC key derived from BOT_TOKEN)

## 14. Open Questions / V2 Candidates

- Per-item [View] button on `/p` list (V2)
- Auto-send review cards on new capture (V2)
- One-time-use token enforcement (V2, using runtime state)
- Token revocation (V2)
- Embedded preview with expand/collapse instead of separate [View Full Text]
