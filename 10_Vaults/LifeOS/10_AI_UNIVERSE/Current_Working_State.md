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

- **Telegram safe review-test mode added (2026-07-07)**: Added `--review-test` mode to `telegram_capture_bot.py`. `process_review_test_update()` only allows review commands (`/p`, `/list_pending`, `/view`, `/a`, `/r`, `/approve`, `/reject`), blocks all other commands with a safe no-action reply. `cmd_review_test()` fetches one update, routes through the review-test handler, updates offset, and exits. Review commands route through the Action API — the Telegram bot does not directly list, read, move, or mutate review files. Normal `process_update()` is never called. Raw `--once` is intentionally avoided for review validation. README updated with `--review-test` usage. Next step: controlled validation of `/p`, `/view`, `/a`, `/r` through `--review-test`.

- **Telegram review-command partial validation recorded (2026-07-07)**: `/p` was live-validated using `--review-test` through Action API-backed handlers with no file mutation and no new event-log entry. Controlled validation captures were identified for future approve/reject testing: `cap_20260707_040421_e1b68f_validation-test-from-safe-capture-test-m` and `cap_20260707_061632_1b4b64_validation-review-reject-path-test`. Full live validation of `/view`, `/a`, and `/r` was intentionally deferred by user decision. No raw `--once`, `--poll`, n8n, tunnel, webhook, AI, proposal, or file processor actions were run. No approve/reject mutation was performed.

- **Phase 2 — Telegram helper cleanup + offline tests completed (2026-07-07)**: Removed 10 stale direct-filesystem helper functions from `telegram_capture_bot.py` (`parse_frontmatter`, `find_pending_capture`, `get_first_line_content`, `load_pending_capture_summary`, `list_pending_review_files`, `format_pending_queue`, `resolve_pending_index`, `list_pending_captures`, `update_capture_frontmatter`, `move_capture_file`). All active handlers route through Action API only. Added offline `unittest` suite under `40_Services/chatops/telegram/tests/` covering safe-mode isolation, test-mode command blocking, Action API delegation, unauthorized sender rejection, direct-filesystem write prohibition, and lifecycle event boundary. Staleness confirmed by `grep` scan and test assertions. All verification commands pass. No Action API, live Telegram, or service changes.

- **Action API mutation contract hardened (2026-07-07)**: ca41db0 — event_id envelope added, capture filename collision safety added, request size limits added, symbolic errors added, best-effort rollback added. event_id response contract is partly resolved at API level. Telegram receipts still need to display event_id if not already done. Action API tests: 103 passing.

- **Telegram bot event_id receipts added (2026-07-07)**: Successful mutation responses from Action API display the returned `event_id` receipt in Telegram bot replies for `/capture`, `/approve`, `/reject`, `/a`, and `/r` commands. Offline tests cover presence and absence of event_id.

- **Telegram bot telemetry boundary cleaned up (2026-07-07)**: Centralized local logging via `append_event` in the bot to enforce local operational/telemetry logging only (unauthorized sender rejected, help requested), raising `ValueError` on mutation events. Extracted co_names assertion tests to ensure no active command handler calls `append_event` directly.

- **Telegram polling mode decision implemented (2026-07-07)**: Enforced capture-first default polling mode. Added `ALLOW_REVIEW_COMMANDS` guard (default: False) and `--allow-review` CLI flag. In default mode, all review commands are blocked with a safe no-action message. Added offline tests verifying review command blocking by default and authorization when explicitly enabled.

- **Telegram review commands /view, /a, /r offline validation complete (2026-07-07)**: Validated `/view`, `/a`, and `/r` commands using controlled offline tests. Verified safe display of pending capture info, API-only approve/reject mutations, safe handling of invalid IDs/missing captures, and filepath exposure prevention. All tests added to `test_telegram_bot.py` pass.

- **Telegram stabilization activation complete (2026-07-07)**: Restarted `lifeos-telegram-bot.service` after HEAD `6aeabd2` — all 5 reviewed commits (bf79a53, 0f1cff9, 9785064, b9e075f, 6aeabd2) are now active in the live polling service. Service remains capture-first (`--poll --interval 3`, no `--allow-review`). Review commands are blocked in live polling by default. Event_id receipt code is active on successful mutation responses. No live `/view`, `/a`, `/r` review command validation performed. n8n/Docker/Cloudflare remain deferred. 189 offline tests passing. All preflight checks clean.

- **Telegram Review Button UX V1 implemented and offline-tested (2026-07-07)**: Inline keyboard buttons added to the Telegram review flow. `/view <n>` now sends a summary with inline buttons ([View Full Text], [Approve], [Reject]) instead of full capture content. Button flow uses stateless HMAC-signed callback tokens (10-minute expiry, sender-bound, action-bound, capture-bound) embedded in `callback_data` under 64 bytes. All mutations route through the Action API — the Telegram bot never directly reads, moves, or writes capture files. Implemented across 4 commits:
  - `de76015` — stateless callback token helpers (`_hmac_key`, `_make_cap_ref`, `_make_token`, `_verify_token`) with 13 offline tests
  - `797c127` — callback query dispatch (`process_callback_query`) with auth, review-mode guard, cancel handler, and 6 dispatch tests + 2 boundary tests
  - `22616fb` — `/view` summary + buttons and view-full flow with 7 UI tests
  - `f382bb9` — approve/reject confirmation intent and confirm mutation flow with 11 intent/confirm tests
  - `210dd83` — README docs documenting inline review button flow
  - Design spec: `docs/superpowers/specs/2026-07-07-telegram-review-button-ux-design.md` (status: Final/Implemented)
  - Implementation plan: `docs/superpowers/plans/2026-07-07-telegram-review-button-ux-v1.md`
  - Offline tests: 107/107 Telegram bot tests passing (17 new for buttons, 90 existing still passing)
  - **Not live-validated.** Not active in the running capture-first service (`--poll --interval 3`, no `--allow-review`). Review commands and callback buttons are blocked in default capture-first mode. Live polling remains capture-first. Activating review mode requires `--allow-review` flag or `TELEGRAM_ALLOW_REVIEW=1` plus service restart.
  - No n8n, Docker, Cloudflare, webhook, AI proposal, controlled file processor, or service changes performed.

- **Unified Docker Compose baseline created (2026-07-07)**: Single `40_Services/compose/lifeos.yaml` consolidates Status API, Action API, and n8n (scaffold-only) service definitions. Healthchecks, logging limits, `.env.example`, and security hardening applied uniformly across all services. n8n uses `manual-start-disabled` profile and `${VAR:-default}` env substitution — no `env_file`, no `WEBHOOK_URL`. Network uses `external: true` — existing `lifeos_internal` is preserved. Existing compose files at `40_Services/n8n/`, `40_Services/status_api/`, and `40_Services/compose/automation/` marked as legacy/reference. Static validation runbook at `40_Services/compose/README.md`. No containers started, built, or pulled. No service migration. Telegram bot remains systemd user service outside compose. Cloudflare tunnel, Telegram webhook, AI proposal pipeline, controlled file processor, n8n workflow activation, Telegram bot containerization, and Kubernetes/homelab expansion remain explicitly deferred.

- **Docker runtime drift discovered during provenance audit (2026-07-07)**: The actual Docker runtime is ahead of the documented Compose activation plan. No Docker/systemd/service action was taken during the audit.
  - `lifeos-status-api` is running from legacy `status_api` compose project (`40_Services/status_api/docker-compose.yml`), container-only 8787/tcp with no `127.0.0.1:8787` host mapping. `localhost:8787` is free and health check fails. Restart policy: `unless-stopped`.
  - `lifeos-action-api` is running as a likely manual Docker container with no compose labels (compose project/name are empty). Healthy on `localhost:8788/health` returning `ok/read_write`. No restart policy (`restart: no`). This currently serves the live Telegram capture path.
  - `n8n_n8n_1` is running from legacy `n8n` compose project, bound to `127.0.0.1:5678`. Restart policy: `unless-stopped`. n8n workflow activation status was not verified.
  - `lifeos_internal` Docker network exists and contains all three containers: `lifeos-status-api` (172.20.0.2), `n8n_n8n_1` (172.20.0.3), `lifeos-action-api` (172.20.0.4).
  - Ports: `127.0.0.1:5678` (n8n), `127.0.0.1:8788` (Action API) are bound. `127.0.0.1:8787` is free.
  - Telegram bot remains capture-first systemd user service (`--poll --interval 3`, no `--allow-review`). Active and enabled on login.
  - Unified compose baseline (`40_Services/compose/lifeos.yaml`) exists but does not yet own the running containers.
  - **Action:** Do not build/start/stop/recreate any container until the drift reconciliation plan (`docs/superpowers/plans/2026-07-07-docker-runtime-drift-reconciliation-plan.md`) is reviewed and approved. Docs-only correction recorded in this entry and compose README.

- **Status API adopted under unified compose with localhost:8787 mapping (2026-07-07)**: Legacy `lifeos-status-api` (from `status_api` compose project) was stopped, removed, and replaced with a unified compose container built from `40_Services/compose/lifeos.yaml`. Status API is now reachable at `localhost:8787/health` and `localhost:8787/status`. Action API was not touched. n8n remains tolerated localhost-only drift. Telegram bot remained capture-first and was not restarted. No public ingress, no WEBHOOK_URL, no Cloudflare. Unified compose now owns Status API. Action API adoption remains a future gated phase requiring separate approval.

- **Action API adopted under unified compose (2026-07-07)**: Manual `lifeos-action-api` container was stopped, removed, and replaced with a unified compose container built from `40_Services/compose/lifeos.yaml`. `localhost:8788/health` returns `ok/read_write`. Restart policy improved from `no` to `unless-stopped`. Status API remains healthy on `localhost:8787`. Telegram bot remained capture-first and was not restarted. n8n remains tolerated localhost-only drift. Public ingress remains disabled. Unified compose now owns both Status API and Action API. n8n ownership remains deferred.

- **Docker runtime drift reconciliation complete for Status API and Action API (2026-07-07)**: Both APIs are now unified-compose-owned. Status API healthy on `localhost:8787` (read-only). Action API healthy on `localhost:8788` (read-write, Telegram capture intact). Telegram remained capture-first and was not restarted. n8n remains tolerated localhost-only drift from legacy `n8n` compose on `localhost:5678`; workflow activation status not verified. No public ingress, no WEBHOOK_URL, no Cloudflare. `compose_n8n_data` side-effect volume observed (empty, created during Status API adoption); do not remove casually. Next deferred work: n8n ownership/adoption, Cloudflare/webhooks, AI proposal pipeline, controlled file processor.

- None active. The earlier off-machine Git backup deferral was superseded by GitHub remote setup at `2026-07-06T02:11:21Z`.

- **Telegram review commands live-validated and `--allow-review` enabled (2026-07-07)**: Review commands `/p`, `/view`, `/a`, and `/r` were live-validated using `--review-test` mode, then the live polling service was updated with `--allow-review` flag and restarted. Inline review button UX (approve/reject with confirmation, cancel, view full text, stateless HMAC callback tokens) is now active in live polling. All mutations route through Action API. Capture functionality unchanged. Status API and Action API remain healthy on unified compose. n8n remains tolerated localhost-only drift.

- **Telegram operator flow finalization — crash fix and proposal v1 (2026-07-07)**: The live Telegram polling service was crashing in a restart loop (counter 139) due to a `TypeError` in `message_cards.py:format_age()` — naive datetimes from the Action API (when `created_at` lacked timezone suffix) could not be subtracted from aware `datetime.now(timezone.utc)`. Fixed by adding `dt.replace(tzinfo=timezone.utc)` for naive parsed datetimes in `_iso_to_dt()`. After fix, service restarted cleanly and has been stable. All 313 tests passing (192 Telegram + 103 Action API + 18 Status API).

  - **Proposal v1 implemented (2026-07-07)**: New `/proposal <n|latest|capture_id>` command added to the Telegram bot. Deterministic template-based — no AI/model/external API calls. Heuristics classify captures as `link`, `idea`, `note`, `task`, `project_update`, or `unknown` based on text content, and suggest a LifeOS route. Proposal is returned as a formatted operator card in Telegram only — no vault writes, no file creation, no n8n involvement. Proposal v1 is a read-only preview; approval gates remain unchanged.

  - **Live operator state (2026-07-07)**:
    - Telegram service: `active (running)`, enabled on login, capture-first + `--allow-review`
    - Commands live: `/capture`, `/p`, `/view`, `/a`, `/r`, `/approve`, `/reject`, `/list_pending`, `/status`, `/proposal`, `/help`
    - Inline review buttons active (approve/reject with confirmation, view full text, cancel)
    - All mutations route through Action API; `/status` routes through Status API
    - n8n: local-only, no `/lifeos` mount, Status Digest workflow inactive
    - Status API: read-only, healthy
    - Action API: read-write, healthy
    - No secrets exposed, no public webhooks, no Docker socket, no direct vault writes
    - Tests: 313/313 passing
    - 7 pending captures in queue (test artifacts from previous validation cycles)

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
- **First manual n8n status workflow test passed (2026-07-06)**: Manual Trigger → HTTP Request → GET `http://lifeos-status-api:8787/status`. Returned JSON valid and read-only:
  ```
  service:             lifeos-status-api
  status:              ok
  mode:                read_only
  pending_captures:    1
  approved_unprocessed_captures: 1
  rejected_captures:   0
  processed_captures:  0
  event_log_valid:     true
  event_log_line_count: 26
  last_event_id:       evt_20260706T180606Z_chatops_telegram_approval_received
  last_event_type:     chatops.telegram.approval_received
  last_event_time:     2026-07-06T18:06:06Z
  paths.capture_readable:    true
  paths.event_log_readable:  true
  limitations.git_status:    unavailable_without_repo_mount
  limitations.docker_status: unavailable_without_docker_socket
  limitations.disk_status:   unavailable_in_status_api_v1
  ```
  Workflow saved as inactive. No schedule, Telegram, webhook, Execute Command, AI/model, or file-write nodes added.
  Next step: decide whether to keep manual-only, add a schedule later, or add Telegram notification later only after explicit approval. Workflow must remain inactive until then.
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

- **Local Telegram polling service template added (2026-07-07)**: Added a systemd user service template and runbook for running the Telegram bot as a local-only poller. The service was not started or enabled. README documents start/status/stop/enable/disable commands and safety caveats. n8n, tunnels, webhooks, AI, proposals, and file processor remain disabled. `/view`, `/a`, and `/r` live validation remains deferred before long-term unattended polling.

- **Local Telegram polling service live validation passed (2026-07-07)**: Started the systemd user service `lifeos-telegram-bot.service` temporarily for local-only polling. Sent `/capture automatic polling validation test` from Telegram. The running service processed the message automatically through the Action API, created exactly one pending capture (`30_Capture/pending_review/20260707_063037_automatic-polling-validation-test.md`), appended exactly one Action API capture event (`evt_20260707T063037Z_telegram_capture_created`), and replied in Telegram with capture_id/status. No raw `--once`, manual `--poll`, n8n, tunnel, webhook, AI, proposal, or file processor actions were run. Service was stopped by user choice and was not enabled on login.

- **Telegram polling set to capture-first operating mode (2026-07-07)**: User chose to proceed without completing live `/view`, `/a`, and `/r` validation. Local systemd user polling service was started for capture-first operation after safe queue draining. `/capture` automatic polling was previously validated through Action API. `/p` was previously validated through `--review-test`. Review commands are API-backed in code, but `/view`, `/a`, and `/r` live validation remains deferred and may be fixed later if issues appear. Service was left running and was not enabled on login. No n8n, tunnel, webhook, AI, proposal, or file processor actions were run.

- **Telegram capture-first service enabled on login (2026-07-07)**: The systemd user service `lifeos-telegram-bot.service` was enabled on login after `/capture` automatic polling validation passed. Service remains capture-first: `/capture` is validated, `/p` is validated, and `/view`, `/a`, `/r` live validation remains deferred by user decision. No n8n, tunnel, webhook, AI, proposal, or file processor actions were run. Runtime artifacts were not committed.
  Note: user lingering is not enabled, so the service is expected to start with the user session/login rather than run independently after logout.

- **Telegram capture-first operating docs stabilized (2026-07-07)**: Documentation updated to match current runtime reality. The local Telegram polling service is the active interim capture-first path and is enabled on login as a systemd user service. `/capture` automatic polling is validated through Action API. `/p` is validated through `--review-test`. `/view`, `/a`, and `/r` live validation remains deferred by user decision. n8n, tunnels, webhooks, AI proposals, and controlled file processor remain inactive. Known stabilization backlog includes stale Telegram filesystem helpers, runtime artifact tracking policy, Action API atomicity, Action API host deployment contract, and review-action validation.

- **Telegram/n8n next-phase gameplan added (2026-07-07)**: Added a roadmap/gameplan document for the next LifeOS Telegram, Action API, n8n, Docker, and future homelab phases: `docs/superpowers/specs/2026-07-07-lifeos-telegram-n8n-next-phase-gameplan.md`. The plan prioritizes runtime artifact policy, Telegram bot helper cleanup, Action API hardening, event traceability, review-command risk handling, and tests before adding buttons, n8n webhooks, Cloudflare tunnels, AI proposals, controlled file processor, Docker expansion, or Kubernetes. Documentation-only; no code or service changes.

- **Runtime artifact tracking policy created (2026-07-07)**: Created `10_Vaults/LifeOS/10_AI_UNIVERSE/Policies/Runtime_Artifact_Tracking_Policy.md`. Defines five classification categories: Git-tracked source/config/docs, canonical operational records (not tracked), local operator config (tracked by exception), service runtime state (not tracked), and secrets/credentials (never committed). Captures and event logs are classified as canonical operational records with separate backup/archival lifecycle. Implementation agent guidance added for handling dirty runtime files. Backlog item #2 (tracking policy) resolved.

- **Tool candidate queue added to Telegram/n8n gameplan (2026-07-07)**: Integrated external repo/template suggestions as future candidates only. `awesome-n8n-templates`, `n8n-nodes-starter`, Evolution API nodes, Flowise, Langflow, GitHub repo monitoring, and automation template review are parked behind the current foundation gates. No tools were installed, no templates imported, no n8n workflows activated, and no terminal/Execute Command path was approved.

- **Balanced guardrail model added to Telegram/n8n gameplan (2026-07-07)**: Updated the gameplan to avoid over-restricting useful workflows. Powerful tools such as n8n templates, community nodes, Execute Command, Flowise, Langflow, and repo-discovery automation are now classified by risk and approval tier instead of being treated as blanket prohibitions. The model preserves hard blocks against secrets exposure, unrestricted Telegram shell access, direct AI/n8n vault writes, and public admin UI exposure while allowing reviewed sandbox pilots and approval-gated A5 admin workflows later.

Next:
1. ~~**Bot telemetry event logging cleanup/alignment** — Ensure Telegram bot docs and code are consistent on what logs events.~~ **Resolved (2026-07-07).**
2. ~~**Telegram receipt event_id display** — If Telegram bot does not yet display event_id in approval/rejection receipts, add it.~~ **Resolved (2026-07-07).**
3. ~~**/view /a /r validation or capture-only/full-polling decision** — Live validate or finalize guard.~~ **Resolved (2026-07-07).**
4. ~~**Telegram review button UX** — Add inline button-based review UI.~~ **Resolved (2026-07-07).**
5. ~~**Docker Compose baseline** — Stabilize docker-compose.yml for local services.~~ **Resolved (2026-07-07).**
6. ~~**Telegram operator flow finalization** — Fix crash, add proposal v1, close feature.~~ **Resolved (2026-07-07).** Crash: `_iso_to_dt()` naive datetime fix. Proposal: `/proposal <n>` deterministic template. Service stable. 313 tests passing.
7. **n8n internal workflow design** — Build n8n workflows for internal automation.
8. **Webhook/tunnel** — Activate Telegram webhook + Cloudflare tunnel later.

## Known Stabilization Backlog

The following items were identified during the Phase 1A audit. They are
recorded here for visibility but are **not yet fixed**:

1. ~~**Remove/quarantine stale direct-filesystem Telegram helper functions** — The Telegram bot still contains old filesystem-based helper functions from the pre-Action-API review flow. These are unused by current code but should be removed or quarantined to prevent confusion and accidental use.~~ **Resolved (2026-07-07).** All 10 stale helpers removed from `telegram_capture_bot.py`. Offline unittest suite added under `40_Services/chatops/telegram/tests/`. README updated.
2. ~~**Decide tracking policy for 30_Capture runtime files, 50_Event_Log/events.jsonl, and .config/opencode/opencode.json** — Resolved by Runtime_Artifact_Tracking_Policy.md (2026-07-07). Captures and event logs are canonical operational records (not committed). `.config/opencode/opencode.json` is tracked by explicit exception.~~
3. ~~**Harden Action API mutation/event atomicity** — Action API capture creation and event logging are not wrapped in an atomic transaction. A crash between file write and event append could leave inconsistent state.~~ **Resolved (2026-07-07).** Critical Phase 3 added best-effort rollback and success-only-after-file-and-event semantics for create/approve/reject.
4. ~~**Fix filename collision risk in Action API capture creation** — The current timestamp-based capture filename scheme could collide if two captures arrive within the same second.~~ **Resolved (2026-07-07).** Capture filenames now include random suffixes and use exclusive create semantics.
5. ~~**Clarify Action API localhost vs Docker-network deployment contract** — The Action API README describes a Docker-based deployment while the current operating mode runs it outside Docker on localhost. The deployment contract needs clarification.~~ **Resolved (2026-07-07).** Action API docs now state the active local Telegram contract is `http://localhost:8788`; Docker service DNS is future/inactive until Compose/n8n contract finalization.
6. ~~**Reconcile bot telemetry event logging with docs** — The docs claim the Telegram bot never writes event log entries, but some bot telemetry events may still be written by legacy/local paths.~~ **Resolved (2026-07-07).** Centralized `append_event` in bot to strictly enforce local operational/telemetry logging only, raising `ValueError` on any mutation.
7. ~~**Validate /view, /a, /r or add capture-only polling guard** — Until review commands are validated, a guard could prevent the polling service from processing review commands (capture-only mode).~~ **Resolved (2026-07-07).** Added `ALLOW_REVIEW_COMMANDS` guard (default: False) and `--allow-review` CLI flag to enforce capture-first polling by default.
8. ~~**Add Telegram bot offline tests** — No offline test suite exists for `telegram_capture_bot.py`. Unit tests would reduce risk during refactoring.~~ **Resolved (2026-07-07).** Offline unittest coverage exists under `40_Services/chatops/telegram/tests/`.
9. ~~**Telegram receipt event_id display** — If Telegram bot does not yet display event_id in approval/rejection receipts, add it.~~ **Resolved (2026-07-07).** Successful mutation responses from Action API display the returned `event_id` in Telegram bot replies.
10. ~~**Telegram review button UX** — Add inline button-based review UI.~~ **Resolved (2026-07-07).** Inline Review Buttons V1 implemented and offline-tested via commits de76015, 797c127, 22616fb, f382bb9, 210dd83. 107/107 Telegram tests passing. Not live-validated; requires `--allow-review` to activate.
11. ~~**Docker Compose baseline** — Stabilize docker-compose.yml for local services.~~ **Resolved (2026-07-07).** Unified `40_Services/compose/lifeos.yaml` created. Legacy compose files marked as reference. No containers started, built, or pulled.
12. **n8n internal workflow design** — Build n8n workflows for internal automation.
13. **Webhook/tunnel** — Activate Telegram webhook + Cloudflare tunnel later.

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
