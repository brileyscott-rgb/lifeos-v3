# Telegram ChatOps Local Bot Handler

> **Status: Fallback / manual-test tool.** The primary production Telegram
> path will use the n8n webhook workflow routing through the LifeOS Action API.
> This local polling bot is for development testing, offline validation, and
> manual capture testing when n8n is not running. Do not rely on this bot
> for production capture intake.

## Purpose

Local manual-test Telegram bot handler for LifeOS V3. Polls the Telegram API,
validates the sender, processes `/capture`, `/list_pending`, `/approve`,
`/reject`, `/help`, and `/status` commands, writes capture files, moves
reviewed files to approved/rejected folders, and appends events.

## Prerequisites

- Python 3.12+
- Bot token and allowed user ID in `40_Services/config/telegram/.env`
- `.env` is gitignored (never committed)

## Usage

```bash
# Check connectivity and configuration
python3 telegram_capture_bot.py --check

# Safe receive test (acknowledges one update, no commands executed)
python3 telegram_capture_bot.py --receive-test

# Process pending updates once
python3 telegram_capture_bot.py --once

# Poll every 3 seconds (foreground, Ctrl+C to stop)
python3 telegram_capture_bot.py --poll --interval 3
```

## Test a Real Capture

1. Ensure `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_USER_ID` are set in
   `40_Services/config/telegram/.env`.
2. Run `python3 telegram_capture_bot.py --check` to verify.
3. Send `/capture test message` to your bot on Telegram.
4. Run `python3 telegram_capture_bot.py --once` to process it.

## Review Lifecycle

After a capture is created, it sits in `30_Capture/pending_review/`.
You can review and close it from Telegram using numbered commands:

### Quick commands (phone-friendly)

```text
/p           — list pending captures (numbered, oldest first)
/view 1      — view full details of pending item #1
/a 1         — approve pending item #1
/r 1         — reject pending item #1
/a latest    — approve the newest pending item
/r latest    — reject the newest pending item
/a           — safe shortcut (only works with exactly 1 pending)
/r           — safe shortcut (only works with exactly 1 pending)
```

### Workflow

1. Send `/p` to your bot to see the numbered pending queue.
2. Run `python3 telegram_capture_bot.py --once` to process.
3. Send `/view 1` to inspect, then `/a 1` or `/r 1` to decide.
4. Run `python3 telegram_capture_bot.py --once` to process.

### Long-form commands (still supported)

```text
/list_pending
/approve cap_<capture_id>
/reject cap_<capture_id>
```

### Safety behavior

- **Authorization**: Every command handler validates the sender against `TELEGRAM_ALLOWED_USER_ID`. Unauthorized senders receive `Unauthorized` and are logged without revealing internal details.
- **Receive-test auth**: `--receive-test` mode also enforces sender authorization before acknowledging.
- `/a` and `/r` without a number only act when **exactly one** pending capture exists.
- If multiple are pending, they refuse with a prompt to use `/p`.
- `/a latest` and `/r latest` require the explicit word `latest`.

## `/status` Command

### Behavior

- **Authorization required**: Only the configured `TELEGRAM_ALLOWED_USER_ID` can invoke `/status`.
- **Read-only**: Calls the LifeOS Status API via HTTP (`http://localhost:8787/status`).
- **No side effects**: Does not create captures, move files, write vault content, invoke AI, n8n, or Docker.
- **Safe fallback**: If the Status API is unreachable, replies: `LifeOS status unavailable. No action was taken.`
- **No event log mutation**: Does not append events to the event log. The internal Status API may read the event log, but the Telegram bot does not write to it.

### Response format

```text
LifeOS Status
Capture queue:
- pending_review: N
- approved: N
- rejected: N

Event log: N entries
Last event: <type> at <timestamp>

Safety:
- no action taken
```

### Note

`/status` is the first real Telegram command after the receive-test guard. `/capture` is still not the next command unless separately implemented. Live bot execution still requires explicit manual approval.

### What happens

- **Approve**: pending file moves to `30_Capture/approved/`, frontmatter
  `status` set to `approved`, `processed_at` timestamp added, event logged.
- **Reject**: pending file moves to `30_Capture/rejected/`, frontmatter
  `status` set to `rejected`, `processed_at` timestamp added, event logged.

**Note**: Approve/reject only moves the review file. It does **not** write
into the main vault (`10_Vaults/LifeOS/`). Approval means queued for later
processing, not automatic vault integration.

## What Gets Written

| Path | Description |
|------|-------------|
| `30_Capture/notes/YYYYMMDD_HHMMSS_*.md` | Source capture file |
| `30_Capture/pending_review/YYYYMMDD_HHMMSS_*.md` | Pending review file with frontmatter |
| `30_Capture/approved/YYYYMMDD_HHMMSS_*.md` | Approved capture (moved from pending_review) |
| `30_Capture/rejected/YYYYMMDD_HHMMSS_*.md` | Rejected capture (moved from pending_review) |
| `50_Event_Log/events.jsonl` | Appended event for each action |

Runtime state (gitignored):

| Path | Description |
|------|-------------|
| `40_Services/config/telegram/runtime/update_offset.json` | Last processed update_id |

## Token Safety

- Token is read from the ignored `.env` file
- `--check` prints bot username only (never the token)
- `.env` is in `.gitignore` and must never be staged

## Secret Scan Rule

Never scan or print `40_Services/config/telegram/.env`.

Use these safe checks only:

```bash
git check-ignore -v /home/lifeos/40_Services/config/telegram/.env
stat -c '%a %U %G %n' /home/lifeos/40_Services/config/telegram/.env
```

For tracked-file secret scans, explicitly scan tracked paths or use
`--exclude='.env'`:

```bash
git ls-files 40_Services/chatops/telegram \
  40_Services/config/telegram \
  30_Capture \
  50_Event_Log/events.jsonl \
  .gitignore \
| grep -v '40_Services/config/telegram/.env$' \
| xargs grep -nE "([0-9]{8,}:[A-Za-z0-9_-]{20,}|ghp_|sk-|xox[baprs]-|AKIA|BEGIN OPENSSH|BEGIN RSA|BEGIN PRIVATE|TELEGRAM_BOT_TOKEN=[0-9])" 2>/dev/null || true
```

## Receive Test Plan (Next Step)

### Purpose

Confirm Telegram messages can reach the local polling bot and produce a harmless acknowledgement — before any n8n webhook, Cloudflare tunnel, or production path.

### Test Mode Decision: **Polling (`--receive-test`)**

The bot now supports `--receive-test` mode. **Always use `--receive-test` for the first test** because:

- No public webhook registration required
- No Cloudflare tunnel required
- No public n8n ingress
- No daemon or foreground process needed
- **Regular command handlers are completely bypassed** — `/capture`, `/status`, `/approve`, `/reject`, `/list_pending`, `/p`, `/view`, `/a`, `/r` are never dispatched
- The safe handler sends a fixed acknowledgement: `LifeOS receive test OK. No action was taken.`
- Even dangerous commands like `/capture attempt123` are harmlessly acknowledged
- Each test is an explicit action: send message → run script → see result

### Allowed Behavior

- Run `python3 telegram_capture_bot.py --check` to verify config and connectivity
- Send any message to the bot via Telegram (mobile or desktop) — the content does not matter
- Run `python3 telegram_capture_bot.py --receive-test` to fetch and safely acknowledge the message
- The bot replies with: `LifeOS receive test OK. No action was taken.`
- The test logs to stdout what was received (first 80 chars only)

### Forbidden Behavior

- No `/capture` command processing (would create files in `30_Capture/`)
- No file writes to `30_Capture/`, `50_Event_Log/`, or any other path
- No Action API calls
- No capture/review/approve/reject lifecycle operations
- No AI extraction
- No proposal generation
- No webhook registration
- No Cloudflare tunnel
- No n8n workflow activation
- **Do not use raw `--once` for first receive testing** unless you have verified the Telegram update queue contains only safe `/help` messages and no stale `/capture`, `/approve`, or `/reject` commands

### How to Perform

1. Ensure `40_Services/config/telegram/.env` has `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_USER_ID`
2. Run `python3 telegram_capture_bot.py --check` — confirms bot identity and connectivity
3. From Telegram mobile, send any test message to the bot
4. Run `python3 telegram_capture_bot.py --receive-test` — fetches the message, sends safe acknowledgement
5. Check stdout for log lines (no errors, no file writes)
6. Check Telegram client for the bot's reply: `LifeOS receive test OK. No action was taken.`

### Success Criteria

- `--check` exits 0 with bot identity confirmed
- `--receive-test` processes the update without errors
- Bot replies with the safe fixed acknowledgement
- No files created in `30_Capture/`
- No events appended to `50_Event_Log/`
- No mutation of any LifeOS state

### Rollback / Stop Rule

- `--receive-test` is inherently ephemeral — no persistent state is created
- If the bot processes a command instead of acknowledging it, stop immediately and review `process_receive_test_update()` to ensure it does not call `process_update()`
- If the bot connects to the wrong environment, remove/rotate the token
- If the bot leaks the token in logs, check `.env` is gitignored and fix the leak source

### Next Step After Success

1. Confirm `/capture` command works safely (run with `--once` after verifying update queue is safe)
2. Plan the `/capture` test with explicit file-creation approval
3. Proceed step by step through the Telegram Control Plane roadmap
4. Only after stable local command handling: plan n8n webhook path (requires Cloudflare tunnel approval)

## Not Implemented Yet

- `/link`, `/idea`, `/project` command routing
- File/photo attachment handling
- Unrecognized text inbox routing
- n8n integration
- Docker service or daemon mode
- AI Mirror enforcement
- Focus Locker
- Behavior blocking
