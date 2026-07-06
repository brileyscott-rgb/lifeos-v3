# Telegram ChatOps Local Bot Handler

## Purpose

Local manual-test Telegram bot handler for LifeOS V3. Polls the Telegram API,
validates the sender, processes `/capture`, `/help`, and `/status` commands,
writes capture files, and appends events.

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

## What Gets Written

| Path | Description |
|------|-------------|
| `30_Capture/notes/YYYYMMDD_HHMMSS_*.md` | Source capture file |
| `30_Capture/pending_review/YYYYMMDD_HHMMSS_*.md` | Pending review file with frontmatter |
| `50_Event_Log/events.jsonl` | Appended event for each action |

Runtime state (gitignored):

| Path | Description |
|------|-------------|
| `40_Services/config/telegram/runtime/update_offset.json` | Last processed update_id |

## Token Safety

- Token is read from the ignored `.env` file
- `--check` prints bot username only (never the token)
- `.env` is in `.gitignore` and must never be staged

## Not Implemented Yet

- `/approve` and `/reject` commands
- `/link`, `/idea`, `/project` command routing
- File/photo attachment handling
- Unrecognized text inbox routing
- n8n integration
- Docker service or daemon mode
- AI Mirror enforcement
- Focus Locker
- Behavior blocking
