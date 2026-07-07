# Telegram ChatOps Local Bot Handler

> **Status: Fallback / manual-test tool.** The primary production Telegram
> path will use the n8n webhook workflow routing through the LifeOS Action API.
> This local polling bot is for development testing, offline validation, and
> manual capture testing when n8n is not running. Do not rely on this bot
> for production capture intake.

## Purpose

Local manual-test Telegram bot handler for LifeOS V3. Polls the Telegram API,
validates the sender, processes `/capture`, `/list_pending`, `/approve`,
`/reject`, `/help`, and `/status` commands.

**Capture and review flow:** `/capture <text>`, `/p`, `/list_pending`,
`/view`, `/a`, `/r`, `/approve`, and `/reject` all route through the
Action API (`http://localhost:8788`). The bot does not write capture files,
move review files, update frontmatter, or append event log entries directly
— it delegates all capture and review lifecycle operations to the Action API.

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

# Safe capture test (only /capture allowed, all other commands blocked)
python3 telegram_capture_bot.py --capture-test

# Process pending updates once
python3 telegram_capture_bot.py --once

# Poll every 3 seconds (foreground, Ctrl+C to stop)
python3 telegram_capture_bot.py --poll --interval 3
```

## Test a Real Capture

1. Ensure `TELEGRAM_BOT_TOKEN` and `TELEGRAM_ALLOWED_USER_ID` are set in
   `40_Services/config/telegram/.env`.
2. Run `python3 telegram_capture_bot.py --check` to verify.
3. Ensure the Action API is running on `http://localhost:8788`.
4. Send `/capture test message` to your bot on Telegram.
5. **Do NOT use raw `--once` for first `/capture` or `/p`/`/view`/`/a`/`/r` validation.** Use
   `--capture-test` for capture testing, or wait for a safe `--review-test` mode. Raw
   `--once` may process stale review commands that have accumulated in the
   Telegram update queue.
6. Run `python3 telegram_capture_bot.py --capture-test` to safely process
   the `/capture` command.
7. Bot replies with `Capture created: <capture_id>\nStatus: pending_review\nNo AI processing has started.`
8. If Action API is unavailable, bot replies:
   `LifeOS capture unavailable. No action was taken.`

## Review Lifecycle

After a capture is created, it sits in `30_Capture/pending_review/`.
You can review and close it from Telegram using numbered commands.

**All review commands route through the Action API (`http://localhost:8788`).**
The Telegram bot does not directly list, read, move, or mutate capture review
files. It only calls Action API endpoints and formats replies.

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
- **Direct filesystem safety**: The Telegram bot never directly lists `30_Capture/pending_review/`, never reads pending capture files, never moves review files, and never appends review lifecycle events. All review operations are delegated to the Action API.

### Action API endpoint mapping

| Command | Action API Endpoint | Method |
|---------|-------------------|--------|
| `/p` | `GET /captures/pending` | GET |
| `/list_pending` | `GET /captures/pending` | GET |
| `/view <n>` | `GET /captures/pending/<n>` | GET |
| `/view latest` | `GET /captures/pending/latest` | GET |
| `/view <capture_id>` | `GET /captures/<capture_id>` | GET |
| `/a <n>` or `/a latest` | `GET /captures/pending/<n>` then `POST /captures/<id>/approve` | GET + POST |
| `/a` (single pending) | `GET /captures/pending` then `POST /captures/<id>/approve` | GET + POST |
| `/r <n>` or `/r latest` | `GET /captures/pending/<n>` then `POST /captures/<id>/reject` | GET + POST |
| `/r` (single pending) | `GET /captures/pending` then `POST /captures/<id>/reject` | GET + POST |
| `/approve <capture_id>` | `POST /captures/<capture_id>/approve` | POST |
| `/reject <capture_id>` | `POST /captures/<capture_id>/reject` | POST |

### What the Action API owns

- Capture pending listing and file reads
- Capture approve/reject file moves between `pending_review/`, `approved/`, `rejected/`
- Capture frontmatter status updates (`status`, `processed_at`)
- Review lifecycle event logging to `50_Event_Log/events.jsonl`

### What the Telegram bot does not do

- Does not directly list `30_Capture/pending_review/`
- Does not directly read pending capture files
- Does not directly move capture files
- Does not directly update capture frontmatter
- Does not directly append capture review events
- Does not directly mutate `30_Capture/`
- Does not directly mutate `50_Event_Log/events.jsonl`

### Approval scope

Capture approval through the Action API only moves the capture from
`pending_review/` to `approved/`. It does **not** trigger AI extraction,
proposal generation, file processor execution, vault writes, n8n workflows,
or any automation beyond the file move and event log.

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

### What happens (Action API owns all mutation)

- **Approve**: Telegram bot calls `POST /captures/<id>/approve` on Action API.
  Action API moves file from `pending_review/` to `approved/`, updates
  frontmatter (`status`, `processed_at`), and appends event to the event log.
- **Reject**: Telegram bot calls `POST /captures/<id>/reject` on Action API.
  Action API moves file from `pending_review/` to `rejected/`, updates
  frontmatter (`status`, `processed_at`), and appends event to the event log.

**Note**: Approve/reject only moves the review file. It does **not** trigger
AI extraction, proposal generation, file processor execution, vault writes,
n8n workflows, or any automation beyond the file move and event log.

## What Gets Written

The Telegram bot no longer writes files directly. All capture file creation,
event logging, and review lifecycle operations are handled by the Action API
(`http://localhost:8788`).

| Path | Writer | Description |
|------|--------|-------------|
| `30_Capture/pending_review/YYYYMMDD_HHMMSS_*.md` | Action API | Pending review file with frontmatter |
| `30_Capture/approved/YYYYMMDD_HHMMSS_*.md` | Action API | Approved capture (moved from pending_review) |
| `30_Capture/rejected/YYYYMMDD_HHMMSS_*.md` | Action API | Rejected capture (moved from pending_review) |
| `50_Event_Log/events.jsonl` | Action API | Appended event for each action |

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

1. `/capture` and all review commands now route through the Action API
2. Add a safe `--review-test` mode or perform tightly scoped controlled validation of `/p`, `/view`, `/a`, `/r` through Action API without raw `--once`
3. Proceed step by step through the Telegram Control Plane roadmap
4. Only after stable local command handling: plan n8n webhook path (requires Cloudflare tunnel approval)

## Capture Test Mode (`--capture-test`)

### Purpose

Safe capture-only validation mode for live `/capture` testing. Prevents the
bot from accidentally dispatching `/status`, `/approve`, `/reject`, `/view`,
`/p`, `/a`, `/r`, `/list_pending`, or any unknown command when processing
a real Telegram update.

### Warning: Do Not Use Raw `--once` for First `/capture` Validation

Raw `--once` calls the normal `process_update()` dispatcher, which handles
ALL commands. If the Telegram update queue contains stale review commands
(e.g., an older `/approve` or `/reject` that was typed but never processed),
`--once` will execute them against the filesystem. This is unsafe during
live capture validation.

**Always use `--capture-test` for the first `/capture` validation.**

### Behavior

- Loads environment normally.
- Fetches at most one update from Telegram using the existing offset.
- Validates sender authorization before any action.
- Only allows `/capture <text>`.
- If the update is not `/capture <text>`, replies:
  `LifeOS capture-test mode is active. No action was taken.`
- If the update is `/capture` without text, replies:
  `Usage: /capture <text>`
- If authorized and is `/capture <text>`, calls `handle_capture()` which
  routes through the Action API.
- Never calls `process_update()` — normal command dispatch is completely bypassed.
- Always updates offset for the one processed update.
- Exits immediately after one update.

### Commands Blocked by `--capture-test`

- `/status`
- `/pending`
- `/view`
- `/approve`
- `/reject`
- `/p`
- `/a`
- `/r`
- `/list_pending`
- Any unknown or unrecognized command

### Boundaries Preserved

- **Telegram bot does not write capture files.** Only the Action API creates
  capture files under `30_Capture/pending_review/` and appends entries to
  `50_Event_Log/events.jsonl`.
- **No AI processing or proposal generation** is triggered by `--capture-test`.
- **No controlled file processor** is invoked.
- **No n8n, Docker, tunnels, or webhooks** are started.
- **No service restart** occurs.

### How to Use

1. Ensure `40_Services/config/telegram/.env` has `TELEGRAM_BOT_TOKEN` and
   `TELEGRAM_ALLOWED_USER_ID`.
2. Run `python3 telegram_capture_bot.py --check` to verify configuration.
3. Ensure the LifeOS Action API is running on `http://localhost:8788`.
4. Send `/capture test message` to the bot on Telegram.
5. Run `python3 telegram_capture_bot.py --capture-test`.
6. Bot replies with `Capture created: <capture_id>\nStatus: pending_review\nNo AI processing has started.`
7. If Action API is unreachable, bot replies:
   `LifeOS capture unavailable. No action was taken.`

### Note on Offset

`--capture-test` updates the Telegram offset for the single processed update,
same as `--once` and `--receive-test`. This prevents re-processing the same
update in subsequent test runs.

## Not Implemented Yet

- `/link`, `/idea`, `/project` command routing
- File/photo attachment handling
- Unrecognized text inbox routing
- n8n integration
- Docker service or daemon mode
- AI Mirror enforcement
- Focus Locker
- Behavior blocking
