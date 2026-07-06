# Telegram ChatOps Local Bot Handler

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

- `/a` and `/r` without a number only act when **exactly one** pending capture exists.
- If multiple are pending, they refuse with a prompt to use `/p`.
- `/a latest` and `/r latest` require the explicit word `latest`.

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

## Not Implemented Yet

- `/link`, `/idea`, `/project` command routing
- File/photo attachment handling
- Unrecognized text inbox routing
- n8n integration
- Docker service or daemon mode
- AI Mirror enforcement
- Focus Locker
- Behavior blocking
