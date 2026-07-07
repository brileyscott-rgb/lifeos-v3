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

- **Root-level review zip cleanup completed (2026-07-06)**: Deleted `/home/lifeos/lifeos_files_20260706_220619.zip` (910M). Moved `/home/lifeos/backups/lifeos_backup_20260706_220113.zip` (935M) into `/home/lifeos/70_Backups/review_zips/`. Removed now-empty `/home/lifeos/backups/`. Updated `.gitignore` to block future root-level `lifeos_files_*.zip`, `lifeos_structure_review_*.zip`, `lifeos_backup_*.zip`, and `/backups/`. No deeper stale candidates touched. Commit: `da0dd41`.

- **Telegram receive-test planning completed (2026-07-06)**: Documented receive-test plan in `40_Services/chatops/telegram/README.md`. Recommends polling (`--once` mode) as first test — avoids webhook, tunnel, and public ingress. Forbidden behaviors documented. Commit: `0436bea`.

- **Safe Telegram receive-test guard added (2026-07-06)**: Added `--receive-test` mode to `telegram_capture_bot.py`. Safe handler bypasses all normal command dispatch (`/capture`, `/status`, `/approve`, `/reject`, `/list_pending`, `/p`, `/view`, `/a`, `/r`). Sends fixed acknowledgement: `LifeOS receive test OK. No action was taken.` Updated README.md to recommend `--receive-test` over raw `--once` for first receive testing. No live Telegram test run. No `/status` or `/capture` implementation.

- **Telegram sender authorization guard and read-only `/status` command added (2026-07-06)**: Extracted `extract_sender_id()`, `is_authorized_sender()`, and `reject_unauthorized()` helper functions. All command handlers and `--receive-test` mode now enforce sender allowlist before replying. Replaced local filesystem `handle_status()` with HTTP call to the internal Status API (`http://localhost:8787/status`) with safe fallback on unavailable. `/status` is read-only — no captures created, no files moved, no vault writes, no event log append, no AI/n8n/Docker invoked. Authorization is centralized and reusable for future commands. Documentation updated.

- **Telegram `/status` made fully read-only (2026-07-06)**: Removed the `append_event('chatops.telegram.status_requested')` call from `handle_status()` in `telegram_capture_bot.py`. `/status` no longer mutates the event log from the Telegram bot side. README corrected to state "No event log mutation" instead of "Appends event".

- **Telegram receive-test live validation passed (2026-07-06)**: Validated `--receive-test` end-to-end against live Telegram bot `@my_lifeOS_08bot`. Sent `/receive_test` from Telegram mobile. `--receive-test` safely acknowledged the update without dispatching normal commands (`/capture`, `/status`, `/approve`, `/reject`, `/list_pending`, etc.). Bot replied: `LifeOS receive test OK. No action was taken.` `30_Capture/` file list unchanged (0 diff). `50_Event_Log/events.jsonl` stayed at 25 lines — no capture files created, no event log entries appended. `--check` and `py_compile` passed. No `/capture`, `/status`, n8n, Docker, tunnel, webhook, AI, proposal, or file processor actions invoked. Commit: `46e1f0c`.

- **Capture-only receive validation mode added (2026-07-06)**: Added `--capture-test` mode to `telegram_capture_bot.py`. `process_capture_test_update()` only allows `/capture <text>`, blocks all other commands with a safe no-action reply. `cmd_capture_test()` fetches one update, routes through the capture-test handler, updates offset, and exits. Raw `--once` is intentionally avoided for capture validation because it dispatches all commands including filesystem-based review handlers. Normal `process_update()` is never called. README updated with `--capture-test` usage, warning against raw `--once`, and documentation of blocked commands and preserved boundaries. Next step: controlled live `/capture` validation through `--capture-test`.

- **Telegram `/capture` live validation passed using `--capture-test` (2026-07-06)**: Validated end-to-end live `/capture` through `--capture-test` mode. Bot received `/capture validation test from safe capture-test mode` from Telegram mobile. `--capture-test` fetched exactly one update, routed `/capture` through Action API `POST /captures`. Action API created capture file `30_Capture/pending_review/20260707_040421_validation-test-from-safe-capture-test-m.md` with `capture_id: cap_20260707_040421_e1b68f_validation-test-from-safe-capture-test-m` and appended event `evt_20260707T040421Z_telegram_capture_created` (actor: `lifeos-action-api`). Event log increased from 25 to 26 lines. Telegram replied: `Capture created: cap_20260707_040421_e1b68f_validation-test-from-safe-capture-test-m` / `Status: pending_review` / `No AI processing has started.` No files created in `approved/` or `rejected/`. No normal `process_update()` dispatch, no review commands, no n8n, no tunnel, no webhook, no AI, no proposal, no file processor actions. Action API run via Docker with port mapping; all other services unchanged.

- **Telegram review commands routed through Action API (2026-07-07)**: All review commands (`/p`, `/list_pending`, `/view`, `/a`, `/r`, `/approve`, `/reject`) now call the Action API instead of directly accessing the filesystem. Telegram bot no longer lists `30_Capture/pending_review/` directly, reads pending capture files, moves review files, updates frontmatter, or appends review lifecycle events. Action API owns capture listing, file reads, approve/reject file moves, frontmatter updates, and event logging for the review lifecycle. Helpers added: `action_api_unavailable_reply()`, `_extract_preview_line()`. No AI, proposals, file processor, or n8n actions are triggered by capture approval. Next step: controlled validation of `/p`, `/view`, `/a`, `/r` through Action API.

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
- **LifeOS Action API created at `40_Services/action_api/`**: Read-write sibling to Status API. Python stdlib HTTP server on port 8788, joins `lifeos_internal` network. Endpoints for capture create, pending list, approve, reject. Event log append for all operations. Mounts `30_Capture/` and `50_Event_Log/` as read-write. Hardened container: `cap_drop: ALL`, `no-new-privileges`, non-root user. Hardened Action API test suite passes per d5a0042; latest reported count 91/91. Added to n8n compose stack. No shell execution, no Docker socket, no vault access, no secrets.

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

- **Long-term Telegram Control Plane roadmap locked**: `docs/superpowers/specs/2026-07-06-lifeos-telegram-control-plane-roadmap.md`. Defines 7 modules (Capture Operator, Review Operator, AI Processing Pipeline, Controlled File Processor, Retrieval Operator, Drift Auditor, Private Ops Dashboard), phased build plan (B3 through I2), safety model, permission tiers (A0-A5), and future features. Complements the existing Telegram Operator architecture design. No implementation performed in this step.

- **Final documentation/security drift cleanup completed**: Root status docs (README.md, Source_of_Truth.md) updated to reflect current implemented state. n8n access model updated to allow Cloudflare Tunnel scaffold while requiring activation approval. Old Telegram workflow placeholder now routes through Action API instead of direct n8n filesystem writes. Local Telegram polling bot marked as fallback/manual tool, not production path. Event/capture privacy policy created at `10_Vaults/LifeOS/10_AI_UNIVERSE/Policies/Event_Capture_Privacy_Policy.md`. `.gitignore` updated to ignore `.lesshst`, `.xsession-errors.old`, `.opencode/`. Cloudflare runbook updated with Docker Compose v1/v2 note. All documentation now reflects the current implemented state without implementation creep.

- **Temporary Cloudflare Quick Tunnel POC completed (2026-07-06)**:
  - Cloudflared Docker image pulled (`cloudflare/cloudflared:latest`).
  - Quick Tunnel started via `docker run --rm --network host cloudflare/cloudflared:latest tunnel --url http://127.0.0.1:5678`.
  - Temporary `trycloudflare.com` URL obtained (ephemeral, no credentials).
  - Generic n8n webhook test at `/webhook/test` returned HTTP 200 with `{"message":"Workflow was started"}` — confirms tunnel + n8n webhook end-to-end.
  - Root (`/`) exposed n8n UI — confirmed and acceptable only for temporary POC.
  - Tunnel stopped immediately after test.
  - Runbook created at `40_Services/n8n/cloudflared/quick_tunnel_poc.md`.
  - Helper script created at `40_Services/n8n/cloudflared/start_quick_tunnel_example.sh`.
  - **Not production. No Telegram webhook registered. No domain-based tunnel activated.**
  - Next step: user-optional Respond to Webhook node refinement, then proceed to Phase B3 (domain-based) when user has Cloudflare domain.

- **Exact proposal packet requirement locked in design docs**: All architecture and security docs now explicitly require exact proposal packets with version locking before any file creation/update approval. Hard boundaries 11-13 added to design doc Section 12 (no stale proposal, no unseen content approval, no direct AI vault writes). Section 20 updated with `proposal_version` field, proposal packet requirements table, version-locked approval rules, and Telegram display commands for proposals. Section 21 updated with version enforcement in processor requirements. n8n security boundaries extended with proposal approval boundaries and workflow review check item. Activation checklist extended with proposal viewing and version-locked approval items. Action API security boundaries document proposal scope exclusion. Documentation-only — no code, workflow, API, webhook, processor, or automation changes.

- **Telegram `/capture` routed through Action API (2026-07-06)**: `handle_capture()` in `telegram_capture_bot.py` no longer writes capture files directly. Calls `POST /captures` on the Action API (`http://localhost:8788`). Bot no longer writes to `30_Capture/notes/`, `30_Capture/pending_review/`, or `50_Event_Log/events.jsonl`. Action API handles capture file creation, event logging, and capture_id generation. Unavailable Action API returns safe message: `LifeOS capture unavailable. No action was taken.` Success response includes `capture_id` and `pending_review` status. No AI, n8n, file processor, proposals, or review commands implemented.

Next:
1. Phase B2 readiness cleanup is complete. Temporary tunnel POC passed — confirms n8n webhook reachability via Cloudflare tunnel.
2. Phase B3: Controlled domain-based Cloudflare Tunnel setup — requires user-provided Cloudflare domain, tunnel token, or credentials JSON. Quick Tunnel is not a substitute for production.
3. Controlled validation of `/p`, `/view`, `/a`, `/r` through Action API (add safe `--review-test` mode or perform tightly scoped validation without raw `--once`).
4. Phase C: n8n Telegram command workflow design/build in n8n UI.
5. Phase D: Telegram webhook registration and end-to-end test.
6. Later: capture mode, photos/voice/documents, AI extraction, controlled file creation processor (now with exact proposal packet requirement documented).
7. All phases require explicit step-by-step approval.

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
