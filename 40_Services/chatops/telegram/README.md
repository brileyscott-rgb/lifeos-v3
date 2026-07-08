# Telegram ChatOps Local Bot Handler

> **Status: Live — capture + review + proposal.** The Telegram bot is
> running as a local systemd user polling service (`--poll --interval 3 --allow-review`).
> Capture, review, and proposal commands are live-validated through Action API.
> Inline review button UX (approve/reject with confirmation, cancel, view full text)
> is active in live polling. Deterministic proposal v1 (`/proposal <n>`) is available
> as a read-only preview with no vault writes. Message cards are compact mobile-first
> plain-text format (no box-drawing characters, no age/countdown clutter).
>
> The future production path will use n8n webhook workflow routing through
> the LifeOS Action API, but is not yet active.

## Current Interim Operating Mode

```text
Active path:
Telegram /capture
→ local systemd user polling service
→ telegram_capture_bot.py --poll --interval 3 --allow-review
→ Action API (http://localhost:8788)
→ 30_Capture/pending_review/
→ 50_Event_Log/events.jsonl

Active review path:
Telegram /p, /view, /a, /r, /approve, /reject
→ Action API (http://localhost:8788)
→ approve/reject moves files, appends events

Active proposal path:
Telegram /proposal <n>
→ Action API (http://localhost:8788) for capture data
→ deterministic template-based classification
→ Telegram operator card reply only (no vault writes)

Active status path:
Telegram /status
→ Status API (http://localhost:8787)
→ read-only status card reply

Inactive/future paths (not started):
n8n Telegram workflows
Cloudflare tunnels
Telegram webhooks
AI proposal processing
Controlled file processor
```

**Live commands (2026-07-07):**
- `/capture <text>` — create pending capture via Action API
- `/p` — list pending captures (read-only)
- `/view <n>` — view capture details with inline review buttons
- `/a <n>` — approve capture via Action API
- `/r <n>` — reject capture via Action API
- `/approve <capture_id>` — approve by ID
- `/reject <capture_id>` — reject by ID
- `/list_pending` — alias for list pending
- `/status` — read-only status via Status API
- `/proposal <n>` — deterministic proposal preview (no vault writes)
- `/help` — command list

**Review commands are fully live and validated** through Action API.
All mutations use inline button confirmation (two-step approve/reject with HMAC callback tokens).

**Service facts:**
- Service name: `lifeos-telegram-bot.service`
- Scope: systemd user service
- Enabled on login: yes
- Linger: no
- Runs only during user session/login
- Does not run independently before login

**Action API dependency:** The Telegram bot expects Action API at
`http://localhost:8788`. If Action API is unavailable, `/capture` and review
mutation commands should fail safely with a no-action message.

**Status API dependency:** The `/status` command expects Status API at
`http://localhost:8787`.

**Bot event logging:** The Telegram bot should not write capture/review
lifecycle events directly. Some bot telemetry events may still be written
by legacy/local bot telemetry paths; this is a known boundary cleanup item.

## Next-Phase Gameplan

The next-phase roadmap is documented at
`docs/superpowers/specs/2026-07-07-lifeos-telegram-n8n-next-phase-gameplan.md`.
It keeps the system in capture-first local polling mode and prioritizes
runtime artifact policy, Telegram helper cleanup, Action API hardening,
`event_id` traceability, review-command risk handling, and offline tests
before buttons, n8n webhooks, Cloudflare tunnels, AI proposals, controlled
file processing, Docker expansion, homelab expansion, or Kubernetes.

## Purpose

Local active Telegram bot handler for LifeOS V3. Polls the Telegram API,
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

# Safe review test (only review commands allowed, all other commands blocked)
python3 telegram_capture_bot.py --review-test

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
   `--capture-test` for capture testing, and `--review-test` for review command testing. Raw
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
2. Run `python3 telegram_capture_bot.py --review-test` to process.
3. Send `/view 1` to inspect, then `/a 1` or `/r 1` to decide.
4. Run `python3 telegram_capture_bot.py --review-test` to process.

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
| `/view <n>` | `GET /captures/pending/<n>` | GET (summary + inline buttons) |
| View Full / Proposal (buttons) | `GET /captures/pending` → `GET /captures/<id>` | GET + GET (cap_ref resolved) |
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

The Telegram bot does not write capture files or review lifecycle events
directly. All capture file creation, event logging, and review lifecycle
operations are handled by the Action API (`http://localhost:8788`).

**Known exception:** Some bot telemetry events may still be written by
legacy/local bot telemetry paths in the Telegram bot process. This is a
known boundary cleanup item — the intended design is for the Action API
to own all capture/review event logging.

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

See `10_Vaults/LifeOS/10_AI_UNIVERSE/Policies/Runtime_Artifact_Tracking_Policy.md`
for the full classification of Git-tracked vs runtime vs backup-only vs
never-committed files.

## Code Boundary Hygiene

Legacy direct-filesystem review helpers were removed from
`telegram_capture_bot.py`. Active capture and review handlers delegate to the
Action API for capture creation, pending listing, review file reads,
approve/reject file moves, frontmatter updates, and review lifecycle event
logging.

Offline stdlib `unittest` coverage protects safe modes and mutation
boundaries under `40_Services/chatops/telegram/tests/`. The Telegram bot still
has limited telemetry logging paths; review lifecycle events remain
Action-API-owned.

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
2. `--review-test` mode is available for safe validation of `/p`, `/view`, `/a`, `/r`, `/approve`, `/reject` without raw `--once`
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

### Inline Review Buttons (V1)

When review mode is active (`--allow-review` or `TELEGRAM_ALLOW_REVIEW=1`),
`/view <n>` now sends a summary with inline keyboard buttons instead of the
full capture content:

```text
Capture 1
Title: My quick note
Type: note
Status: pending_review

Preview: My quick note about...

[View Full] [Proposal]
[Approve]  [Reject]
```

Button flow (all stateless, HMAC-signed callback tokens, 10-minute expiry):

- **[View Full]** — sends the complete capture content as a separate
  message with no approve/reject buttons.
- **[Approve]** — shows a confirmation prompt with [Confirm Approve] and
  [Cancel]. No mutation occurs at this stage.
- **[Reject]** — same confirmation pattern with [Confirm Reject] and [Cancel].
- **[Confirm Approve]** — calls `POST /captures/<id>/approve` on the Action
  API and shows the result with `event_id`.
- **[Confirm Reject]** — calls `POST /captures/<id>/reject` on the Action API
  and shows the result with `event_id`.
- **[Cancel]** — removes the inline keyboard, no mutation.

**Boundary enforcement:**
- Every button path calls `answerCallbackQuery` exactly once.
- Stale buttons tapped after review mode is disabled receive:
  `Review mode is disabled. Please /p to refresh.`
- Expired or invalid tokens receive:
  `Invalid or expired button. Please /p to refresh.`
- Captures that are no longer pending receive:
  `Capture no longer pending. Please /p to refresh.`
- All mutations route through the Action API — the Telegram bot never
  directly reads, moves, or writes capture files.
- Callback tokens are sender-bound (different user → MAC mismatch) and
  action-bound (approve token cannot be reused as reject).

## Review Test Mode (`--review-test`)

### Purpose

Safe review-only validation mode for live `/p`, `/view`, `/a`, `/r`,
`/approve`, and `/reject` testing. Prevents the bot from accidentally
dispatching `/capture`, `/status`, `/help`, or any unknown command when
processing a real Telegram update.

### Warning: Do Not Use Raw `--once` for First Review Command Validation

Raw `--once` calls the normal `process_update()` dispatcher, which handles
ALL commands. If the Telegram update queue contains stale or unexpected
commands, `--once` will execute them. This is unsafe during live review
validation.

**Always use `--review-test` for first review command validation.**

### Behavior

- Loads environment normally.
- Fetches at most one update from Telegram using the existing offset.
- Validates sender authorization before any action.
- Only allows review commands (`/p`, `/list_pending`, `/view`, `/a`, `/r`,
  `/approve`, `/reject`).
- If the update is not a review command, replies:
  `LifeOS review-test mode is active. No action was taken.`
- Allowed review commands route through the Action API — the Telegram bot
  does not directly list, read, move, or mutate review files.
- Never calls `process_update()` — normal command dispatch is completely bypassed.
- Always updates offset for the one processed update.
- Exits immediately after one update.

### Commands Allowed

- `/p`
- `/list_pending`
- `/view <n|latest|capture_id>`
- `/a <n|latest|capture_id>`
- `/r <n|latest|capture_id>`
- `/approve <capture_id>`
- `/reject <capture_id>`

### Commands Blocked

- `/capture`
- `/status`
- `/help`
- Any unknown or unrecognized command

### Boundaries Preserved

- **Telegram bot does not list, read, move, or mutate review files directly.**
  All review operations are delegated to the Action API.
- **No AI processing or proposal generation** is triggered by `--review-test`.
- **No controlled file processor** is invoked.
- **No n8n, Docker, tunnels, or webhooks** are started.
- **No service restart** occurs.
- **Do not use `--poll` until review commands are validated** through `--review-test`.

### How to Use

1. Ensure `40_Services/config/telegram/.env` has `TELEGRAM_BOT_TOKEN` and
   `TELEGRAM_ALLOWED_USER_ID`.
2. Run `python3 telegram_capture_bot.py --check` to verify configuration.
3. Ensure the LifeOS Action API is running on `http://localhost:8788`.
4. Send a review command (e.g., `/p`) to the bot on Telegram.
5. Run `python3 telegram_capture_bot.py --review-test`.
6. Bot replies with the pending queue listing or review result.
7. If Action API is unreachable, bot replies:
   `LifeOS review unavailable. No action was taken.`

### Note on Offset

`--review-test` updates the Telegram offset for the single processed update,
same as `--capture-test`. This prevents re-processing the same update in
subsequent test runs.

## Local Polling Service

### Purpose

Run the Telegram bot locally as a systemd user service so that messages are
processed automatically without manual intervention.

### Safety

- **Local-only**: No n8n, tunnel, webhook, AI, proposal, or file processor.
- All capture and review lifecycle operations still route through the Action API
  (`http://localhost:8788`).
- The Status API (`http://localhost:8787`) handles `/status` queries.
- The bot never writes directly to `30_Capture/`, `50_Event_Log/`, or any vault path.
- No Docker, no Cloudflare, no public ingress — purely local polling.

### Prerequisites

- Action API running on `http://localhost:8788` for `/capture` and review mutation commands.
- Status API running on `http://localhost:8787` for `/status`.

### Install

Copy the user service template:

```bash
mkdir -p ~/.config/systemd/user/
cp 40_Services/chatops/telegram/systemd/lifeos-telegram-bot.service ~/.config/systemd/user/
```

### Commands

```bash
systemctl --user daemon-reload
systemctl --user start lifeos-telegram-bot.service
systemctl --user status lifeos-telegram-bot.service
systemctl --user stop lifeos-telegram-bot.service
systemctl --user enable lifeos-telegram-bot.service
systemctl --user disable lifeos-telegram-bot.service
```

### Status

The service is **currently active and enabled on login**.

- `/capture` automatic polling is validated through Action API.
- `/p` was validated through `--review-test`.
- `/view`, `/a`, and `/r` live validation remains deferred by user decision.
  Review commands are API-backed in code but have not been live-tested.
  If they fail in practice, they may be fixed later.

### Caveat

Do not enable n8n Telegram webhook triggers while local polling is active.
They would compete for the same Telegram update queue.

## Stale Helpers Removed

The following stale direct-filesystem helper functions were removed from
`telegram_capture_bot.py` during Phase 2 cleanup. They were unused by all
active code paths — all capture and review operations route through the
Action API.

```text
parse_frontmatter          — read frontmatter from pending files directly
find_pending_capture       — search pending_review/ by capture_id
get_first_line_content     — extract first content line from markdown
load_pending_capture_summary — build summary dict from filesystem file
list_pending_review_files  — list pending_review/ directory directly
format_pending_queue       — format queue text from filesystem data
resolve_pending_index      — resolve index from in-memory items
list_pending_captures      — list captures by scanning pending_review/
update_capture_frontmatter — write status/processed_at to frontmatter
move_capture_file          — os.rename between capture subdirectories
```

## Offline Tests

Offline unit tests are available under `40_Services/chatops/telegram/tests/`.
Run them with:

```bash
python3 -m unittest discover -s 40_Services/chatops/telegram/tests
```

These tests mock Telegram API calls and never connect to live services.
They verify:
- Safe modes do not dispatch unsafe paths
- Capture-test blocks non-capture commands
- Review-test blocks non-review commands
- Active capture/review handlers call Action API (not filesystem)
- Unauthorized sender is rejected before any action
- No active handler directly moves, renames, or writes capture/review files
- No active review path appends lifecycle events directly

## Not Implemented Yet

- `/link`, `/idea`, `/project` command routing
- File/photo attachment handling
- Unrecognized text inbox routing
- n8n integration
- Docker service or daemon mode
- AI Mirror enforcement
- Focus Locker
- Behavior blocking
