# Current Working State

## Active Milestone

Foundation Lock-In for LifeOS V3 under `/home/lifeos`.

## Current Environment

- User: `lifeos`
- Root: `/home/lifeos`
- Vault: `/home/lifeos/10_Vaults/LifeOS`
- Event log: `/home/lifeos/50_Event_Log/events.jsonl`
- OpenCode config: `/home/lifeos/.config/opencode/opencode.json`
- OpenCode binary: `/home/lifeos/.local/bin/opencode`

## Completed

- Minimal local Telegram bot handler created under `40_Services/chatops/telegram/telegram_capture_bot.py`.
- Supports `--check`, `--once`, and `--poll` CLI modes.
- Supports `/capture`, `/help`, and `/status` commands.
- Reads ignored local `.env` for bot token and allowed user ID.
- Source notes written to `30_Capture/notes/`, pending review files to `30_Capture/pending_review/`.
- Events appended to `50_Event_Log/events.jsonl`.
- Local Telegram capture bot security hardening completed:
  - `.env` verified ignored and mode `600`
  - Previous run printed old token during bad secret scan (now excluded from future scans)
  - Capture frontmatter `event_id` now matches appended event exactly
  - Event ID format standardized to `evt_YYYYMMDDTHHMMSSZ_<slug>` with UTC timestamps
  - JSONL append collision detection added
  - Unauthorized sender logging hardened (no raw text logged)
  - Secret scan guidance added to README
  - No token committed, no n8n activation, no Docker service started.
- Next step: first real `/capture` test after cleanup commit.

- Telegram review lifecycle commands added: `/list_pending`, `/approve`, `/reject`.
- Approve/reject moves pending review files to `approved/` or `rejected/` folders.
- Frontmatter `status` updated to `approved` or `rejected` with `processed_at` timestamp.
- Events logged: `chatops.telegram.approval_received`, `chatops.telegram.rejection_received`, `chatops.telegram.pending_list_requested`.
- All operations stay in `30_Capture/` and `50_Event_Log/`. No direct vault writes.
- No n8n activation, no Docker services started.
- LifeOS V3 source-of-truth plan created.
- Phase 1 scaffold created.
- Phase 1B decisions encoded.
- New `lifeos` user created.
- Login password repaired.
- Scaffold copied into `/home/lifeos`.
- Event log contains scaffold, decision, and login repair events.
- OpenCode handoff/config package prepared for `lifeos`.
- OpenCode verified running as `lifeos` from `/home/lifeos`.
- Groups verified: `docker`, `video`, `render`.
- Git, Docker CLI, Node/npm, and OpenCode availability verified.
- Git initialized safely for `/home/lifeos`.
- Safe `.gitignore` added for secrets, service data, backups, raw imports, migration work, local state, and copied reference/vendor trees.
- Initial clean scaffold/control-plane commit created: `85acdb7 Initialize LifeOS V3 scaffold`.
- Git branch renamed to `main`.
- Local bare Git backup remote created at `/home/lifeos/70_Backups/git/lifeos.git` and `main` pushed.
- Obsidian Flatpak removed and official AppImage downloaded to ignored local path `/home/lifeos/Applications/Obsidian-1.12.7.AppImage`; user reported launch appears good.
- Agency Agents reference updated from `https://github.com/msitarzewski/agency-agents.git` to commit `6f8d5e5`.
- Curated Agency OpenCode subagents installed under `/home/lifeos/.config/opencode/agents/`.
- Off-machine Git backup explicitly deferred by user approval so inert service scaffolding may proceed.
- Inert n8n compose/config scaffold created without starting services, pulling images, or configuring real secrets.
- Dedicated SSH key created locally for off-machine Git backup; private key remains under ignored `/home/lifeos/.ssh/`.
- Off-machine Git remote `offsite` configured for GitHub repo `brileyscott-rgb/lifeos-v3` and `main` pushed.
- Telegram ChatOps capture scaffold created under `40_Services/config/telegram/` with message contracts, routing rules, approval format, security notes, and BotFather setup instructions.
- Capture intake folder structure created under `30_Capture/` with typed subdirectories and README conventions.
- Inert n8n Telegram capture workflow placeholder created under `40_Services/config/n8n/workflows/telegram_capture_placeholder.md`.
- `.gitignore` updated to protect Telegram local secrets and capture working files.
- All scaffold-only: no real Telegram token, no Docker services, no live bot.

- **Number-first pending review queue with safe phone-friendly commands**: Added `/p`, `/view`, `/a`, `/r` with numbered index (1‑based, oldest-first), `latest` keyword, and safe no-arg shortcuts. Existing `/list_pending`, `/approve <capture_id>`, `/reject <capture_id>` preserved. Helper functions: `list_pending_review_files()`, `load_pending_capture_summary()`, `format_pending_queue()`, `resolve_pending_index()`. Test payloads added for all new commands. Docs updated in README, approval_format.md, message_contract.md.

- **Read-only LifeOS status script created**: `40_Services/scripts/lifeos_status.py` reports capture queue counts, event log status, git dirty state, disk usage, n8n container status, and scaffold presence. Supports `--text` and `--json` output. n8n planned workflow `lifeos_status_digest.md` updated with manual-trigger Execute Command step. Activation checklist updated with first-workflow steps.

## Active Deferrals

- None active. The earlier off-machine Git backup deferral was superseded by GitHub remote setup at `2026-07-06T02:11:21Z`.

## Current Decisions

- ChatOps: Telegram (local bot handler created)
- Alerts later: Gotify or ntfy
- Vault sync: Git first
- Capture sync later: Syncthing if needed
- AI strategy: hybrid local plus cloud
- Vector store: Qdrant
- Structured state: SQLite first
- A3 agents: Project Maintainer and Semantic Janitor only
- Migration deletion: manual A4 approval every time, quarantine first
- Backup strategy: Git plus restic later
- Service order: Git, n8n, Telegram, Paperless-ngx, Qdrant, monitoring, MCP

## Next Milestone

Foundation Lock-In:

1. Test the new numbered review queue end-to-end: send `/p`, `/view 1`, `/a 1`, `/r 1` via Telegram.
2. Run `python3 40_Services/chatops/telegram/telegram_capture_bot.py --once` after each command.
3. Test edge cases: `/a` with zero/one/multiple pending; `/a 999`; `/a abc`.
4. Verify approved/rejected files under `30_Capture/approved/` or `30_Capture/rejected/`.
5. Verify approval/rejection events in `50_Event_Log/events.jsonl`.
6. Verify GitHub off-machine remote during routine backup checks.
7. Continue manual Obsidian vault verification at `/home/lifeos/10_Vaults/LifeOS` from the AppImage launcher.
8. Review n8n compose/config scaffold before any service activation.

## Active Milestone

LifeOS V3 Automation Foundation Setup:

- n8n local Docker scaffold added under `40_Services/n8n/`.
- AI worker dry-run scaffold added under `40_Services/ai_worker/`.
- Planned workflows documented under `40_Services/n8n/workflows/planned/`.
- No public webhooks configured.
- No direct vault writes allowed.
- No model API calls active.
- No n8n production workflows active yet.

Completed:
- Read-only LifeOS status script created at `40_Services/scripts/lifeos_status.py`.
- Supports `--text` (default) and `--json` output modes.
- Reports capture queue counts, event log status, git dirty state, disk usage,
  n8n container status, and scaffold presence.
- Read-only by design: no file modification, no git writes, no secret reads.
- n8n planned workflow `lifeos_status_digest.md` updated with explicit manual-trigger
  Execute Command step calling `python3 /home/lifeos/40_Services/scripts/lifeos_status.py --json`.
- Activation checklist updated with first-workflow steps.
- n8n verified running in Docker.

Next:
1. Manual test: `python3 40_Services/scripts/lifeos_status.py --json`
2. Open n8n UI, create manual-trigger Execute Command workflow.
3. Capture queue processing (approved captures remain unprocessed).
4. After status workflow verified, discuss schedule/notification additions.

## Do Not Do Yet

- Do not migrate old LifeOS files yet.
- Do not start Docker services yet (n8n scaffold is ready but inactive).
- Do not configure real Telegram/n8n/Paperless/Qdrant secrets yet.
- Do not loosen `/home/lifeos/40_Services/secrets` permissions.
- Do not treat the local bare Git remote as a substitute for off-machine backup.
- Do not install the full Agency roster into OpenCode unless the OpenCode agent registration limit is resolved or the selection remains below the known limit.
- Do not enable n8n Telegram webhook triggers.
- Do not give n8n or AI worker direct vault-write or git-commit authority.

## Required First Reads

- `/home/lifeos/LifeOS_V3_Source_of_Truth.md`
- `/home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Current_Working_State.md`
- `/home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Decisions/Phase_1B_Foundation_Decisions.md`
- `/home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Policies/New_User_Account_Policy.md`
- `/home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Policies/Sync_And_Backup_Policy.md`
- `/home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Policies/A3_Agent_Policy.md`
- `/home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Policies/Migration_Deletion_Policy.md`
- `/home/lifeos/50_Event_Log/events.jsonl`
