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

- n8n local Docker instance running under `40_Services/n8n/`.
- AI worker dry-run scaffold added under `40_Services/ai_worker/`.
- Planned workflows documented under `40_Services/n8n/workflows/planned/`.
- No public webhooks configured.
- No direct vault writes allowed.
- No model API calls active.
- No n8n production workflows active yet.

Completed:
- Read-only LifeOS Status API created at `40_Services/status_api/`.
- Python stdlib HTTP server on port 8787, joins shared `lifeos_internal` Docker network.
- Endpoints: `GET /health` and `GET /status` returning JSON.
- Reads only `30_Capture/` and `50_Event_Log/events.jsonl` via read-only mounts.
- Hardened container: `read_only: true`, `cap_drop: ALL`, `no-new-privileges`, non-root user.
- No Docker socket, no vault access, no secrets access, no shell commands.
- Unit tests cover capture counting, event log parsing, and path checks.
- n8n direct filesystem mounts removed; n8n now routes status queries through the API on `lifeos_internal` network.
- n8n planned workflow `lifeos_status_digest.md` updated with HTTP Request step.
- Activation checklist updated with HTTP Request workflow instructions.
- **First manual n8n status workflow test passed**: Manual Trigger → HTTP Request → GET `http://lifeos-status-api:8787/status`. Returned JSON valid and read-only (`status: ok`, `mode: read_only`, `event_log_valid: true`, all `limitations` fields present). Workflow saved as inactive. No schedule, Telegram, webhook, Execute Command, AI/model node, or file-write nodes added.
- **LifeOS Action API created at `40_Services/action_api/`**: Read-write sibling to Status API. Python stdlib HTTP server on port 8788, joins `lifeos_internal` network. Endpoints for capture create, pending list, approve, reject. Event log append for all operations. Mounts `30_Capture/` and `50_Event_Log/` as read-write. Hardened container: `cap_drop: ALL`, `no-new-privileges`, non-root user. 32 unit tests pass. Added to n8n compose stack. No shell execution, no Docker socket, no vault access, no secrets.

- **Telegram Operator capture vision locked in design doc**: Telegram Operator will become LifeOS mobile capture intake. `/capture` supports immediate text/link capture and future capture mode (multi-message, timeout, /cancel). Initially supported payloads: text, links, thoughts, ideas, notes. Planned later: photos, voice memos, documents/files. Review flow remains `/pending`, `/view`, `/approve`, `/reject`. Future AI extraction will produce approval-gated proposals, not direct writes. File creation will go through a controlled processor — never from n8n or AI directly. All captures land in `pending_review` first. Separation of capture, extraction, and file creation is enforced architecturally.

- **Phase B1 Cloudflare Tunnel scaffold/runbook created at `40_Services/n8n/cloudflared/`**:
  - `config.example.yml` with placeholder tunnel ID and domain
  - `docker-compose.cloudflared.example.yml` — safe template, no real secrets
  - `README.md` — setup outline, generic webhook test plan, Telegram webhook docs (later), Cloudflare Access warning, rollback steps
  - No tunnel activated yet.
  - No Telegram webhook registered.
  - No n8n Telegram workflow created or activated.
  - Security boundaries and activation checklist updated with Cloudflare Tunnel prerequisites.
  - Next step after Phase B1: user-provided Cloudflare/domain readiness, then controlled implementation of active tunnel config.

Next:
1. Phase B2: User provides Cloudflare domain readiness and tunnel credentials (out of band).
2. Phase B3: Controlled activation of cloudflared with real config (token-free validation first).
3. Phase C: Create n8n Telegram bot webhook workflow in UI.
4. Phase D: Register Telegram webhook, end-to-end testing, documentation closeout.
5. All phases require explicit step-by-step approval.
6. Do not implement AI extraction or file creation processor until raw capture/review flow is stable.

## Do Not Do Yet

- Do not migrate old LifeOS files yet.
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
