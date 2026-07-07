# LifeOS Telegram + n8n Next-Phase Gameplan

## 1. Executive Recommendation

Stay in **capture-first local polling mode**.

Do not advance n8n, Telegram webhooks, Cloudflare tunnels, AI proposals, controlled file processing, Docker expansion, homelab expansion, or Kubernetes yet.

The next LifeOS V3 work should harden the current local Telegram -> Action API -> pending review -> event log path before adding new ingress, UI, automation, or infrastructure. The first five priorities are:

1. Runtime artifact policy.
2. Telegram helper cleanup.
3. Action API hardening.
4. `event_id` response contract.
5. Telegram offline tests plus capture-only/review-risk guard.

## 2. Current Operating State

Current active path:

```text
Telegram /capture
-> local systemd user polling service
-> telegram_capture_bot.py --poll --interval 3
-> Action API
-> 30_Capture/pending_review
-> 50_Event_Log/events.jsonl
```

Current operating mode:

- Capture-first local polling.
- `lifeos-telegram-bot.service` active/running.
- Service enabled on login.
- `linger=no`, so the service is tied to user session/login behavior.
- n8n Telegram workflows inactive.
- Cloudflare tunnels inactive.
- Telegram webhooks inactive.
- AI proposal processing inactive.
- Controlled file processor inactive.
- Kubernetes/homelab expansion inactive.

## 3. Validated Capabilities

Validated:

- `/capture` through `--capture-test`.
- Automatic `/capture` through the systemd polling service.
- `/p` through `--review-test`.

Validated boundaries:

- `/capture` routes through the Action API.
- Captures land in `30_Capture/pending_review`.
- Capture events append to `50_Event_Log/events.jsonl`.
- n8n, webhooks, tunnels, AI proposals, and controlled file processor are not part of the active path.

## 4. Deferred / Unvalidated Capabilities

Deferred:

- `/view` live validation.
- `/a` live validation.
- `/r` live validation.
- Button UX live validation.

Inactive/future:

- n8n Telegram workflows.
- Cloudflare tunnels.
- Telegram webhooks.
- AI proposal processing.
- Controlled file processor.
- Kubernetes/homelab expansion.

Non-operational status banner:

- `/view`, `/a`, and `/r` are not live-validated.
- Telegram Review Button UX V1 is implemented/offline-tested but not live-validated and not active in the live capture-first service.
- n8n Telegram workflows are not active.
- Telegram webhooks are not registered.
- Cloudflare tunnels are not active.
- AI proposal processing is not active.
- Controlled file processor is not active.

## 5. Non-Negotiable Safety Boundaries

- Do not inspect or print secrets, tokens, or `.env` contents.
- Do not run raw `--once` for Telegram validation.
- Do not run manual foreground `--poll` for this documentation task.
- Do not run live Telegram tests for this gameplan update.
- Do not stop, start, restart, enable, or disable services as part of this gameplan update.
- Do not start n8n.
- Do not start tunnels.
- Do not register Telegram webhooks.
- Do not invoke AI proposals or controlled file processing.
- Do not modify Python code or Action API code during this gameplan update.
- Do not move, delete, archive, or commit captures.
- Do not commit runtime artifacts under `30_Capture/`.
- Do not commit `50_Event_Log/events.jsonl`.
- Do not commit `.config/opencode/opencode.json`.

## 6. Hard Gates Before More Features

These gates must pass before adding buttons, n8n webhooks, Cloudflare tunnels, AI proposal processing, controlled file processing, Docker expansion, homelab expansion, or Kubernetes:

| Gate | Required outcome |
|---|---|
| Runtime artifact policy | Explicit policy for `30_Capture` runtime files, `50_Event_Log/events.jsonl`, local service state, bot runtime files, logs, backup/sync behavior, and what must remain untracked. |
| Telegram helper cleanup | No stale direct-filesystem Telegram helper path can bypass the Action API or confuse future implementers. |
| Action API hardening | The API has explicit action boundaries, auth/local exposure rules, input schemas, idempotency/replay posture, rate-limit posture, failure semantics, deployment contract, and review-command risk posture. |
| Atomicity and collision safety | Capture/review mutation does not silently produce orphan files, orphan events, or filename collisions. |
| `event_id` response contract | Every accepted mutation returns and records a durable correlation ID. |
| Review-command risk handling | Either live review mutations are validated or polling is guarded to capture-only behavior until validation. |
| Offline Telegram tests | Telegram behavior is testable without Telegram network, n8n, Cloudflare, or live services. |

Phase gate: **No external ingress until the Action API boundary is hardened.** n8n, Telegram webhooks, and Cloudflare tunnels must remain inactive until local Action API behavior has explicit auth/local exposure rules, stable response contracts, idempotency/replay handling, traceable `event_id`s, and tested failure semantics.

## 7. Recommended Execution Order

1. Phase 1 - Runtime Artifact Policy.
2. Phase 2 - Telegram Helper Cleanup.
3. Phase 3 - Action API Contract Hardening.
4. Phase 4 - Action API Atomicity + Filename Collision Safety.
5. Phase 5 - `event_id` Response Contract.
6. Phase 6 - Capture-Only vs Full Polling Decision.
7. Phase 7 - Telegram Offline Tests.
8. Phase 8 - `/view` `/a` `/r` Validation.
9. Phase 9 - Button-Based Review UX.
10. Phase 10 - Docker Compose Structure.
11. Phase 11 - n8n Future Webhook Path.
12. Phase 12 - Cloudflare Tunnel Later.
13. Phase 13 - Read-Only GitHub Repo / Tool Discovery.
14. Phase 14 - Docker / Homelab / Kubernetes Later.

## 8. GPT-Owned Planning / Review Tasks

- Own architecture sequencing and phase gates.
- Write and review runtime artifact policy.
- Define Action API boundary, success responses, error responses, and deployment assumptions.
- Define `event_id` semantics and traceability requirements.
- Decide capture-only versus full polling posture before review commands are validated.
- Define review UX acceptance criteria for `/view`, `/a`, `/r`, and buttons.
- Define Docker Compose service boundaries and volume policy before implementation.
- Define n8n and Cloudflare as future adapters that cannot bypass Action API invariants.
- Keep AI/proposals/file processor outside the active path until capture/review traceability is reliable.
- Act as scope-control reviewer when implementation pressure tries to skip foundation gates.

## 9. DeepSeek-Owned Implementation Tasks

- Inventory stale Telegram helpers and identify direct-filesystem remnants.
- Implement Telegram helper cleanup after GPT confirms the boundary decision.
- Implement Action API hardening once the contract is explicit.
- Implement atomic write/collision-safety changes and associated tests.
- Implement `event_id` response contract and reconciliation tests.
- Implement capture-only guard or review-command validation changes after the decision is made.
- Implement Telegram offline tests with mocked updates and mocked Action API responses.
- Implement `/view`, `/a`, and `/r` validation work only after tests and guardrails exist.
- Implement button UX only after command review workflow is stable.
- Implement Docker Compose, n8n, and Cloudflare changes only after the required gates pass.

## 10. Phase Details

### Phase 1 - Runtime Artifact Policy

- **Goal:** Decide what is canonical, runtime-only, disposable, backed up, synced, tracked, ignored, or manually reviewed.
- **Why now / why later:** This comes first because every later phase touches files, logs, service state, or generated artifacts. Without policy, later Docker/n8n/AI work will blur source-of-truth boundaries.
- **Files likely touched:** `10_Vaults/LifeOS/10_AI_UNIVERSE/Policies/`, `10_Vaults/LifeOS/10_AI_UNIVERSE/Current_Working_State.md`, `.gitignore`, Telegram and Action API docs.
- **Owner:** GPT.
- **Risk level:** High.
- **Validation method:** Policy review confirms explicit handling for `30_Capture/*`, `50_Event_Log/events.jsonl`, Telegram runtime offset/cache files, service logs, n8n data, Action API artifacts, backups, and local OpenCode runtime state.
- **Stop condition:** Stop if the policy would track runtime captures or `events.jsonl` without explicit approval, or if it requires secret/token inspection.
- **Explicit forbidden actions:** Do not inspect `.env`; do not print secrets; do not move/delete/archive captures; do not stage runtime artifacts; do not change services.

### Phase 2 - Telegram Helper Cleanup

- **Goal:** Remove or quarantine stale direct-filesystem Telegram helper paths so the bot cannot bypass the Action API.
- **Why now / why later:** This must happen before adding tests, buttons, n8n, or webhooks because stale helpers create confusing alternative write paths.
- **Files likely touched:** `40_Services/chatops/telegram/telegram_capture_bot.py`, Telegram README, Telegram offline tests once created.
- **Owner:** DeepSeek implements; GPT reviews the architecture boundary.
- **Risk level:** Medium-high.
- **Validation method:** Static review and offline tests prove the Telegram bot does not directly list, read, move, or mutate `30_Capture/` or append review lifecycle events to `50_Event_Log/events.jsonl`.
- **Stop condition:** Stop if any live Telegram testing, service restart, capture movement, or `.env` inspection appears necessary.
- **Explicit forbidden actions:** Do not run raw `--once`; do not run manual `--poll`; do not run live Telegram tests; do not move captures; do not alter Action API behavior in this phase.

### Phase 3 - Action API Contract Hardening

- **Goal:** Define and harden the Action API as the single mutation boundary for capture/review lifecycle operations.
- **Why now / why later:** The Action API must be stable before review UX, n8n, webhooks, Cloudflare, AI proposals, or Docker expansion depend on it.
- **Files likely touched:** `40_Services/action_api/README.md`, `40_Services/action_api/notes/security_boundaries.md`, Action API implementation, Action API tests, Telegram README.
- **Owner:** GPT defines contract; DeepSeek implements.
- **Risk level:** High.
- **Validation method:** Contract tests cover accepted requests, rejected requests, malformed payloads, unsupported actions, missing dependencies, safe error shape, auth/local exposure behavior, idempotency/replay behavior, and rate-limit posture.
- **Stop condition:** Stop if API behavior differs between test modes and polling service, or if external ingress is proposed before local contract stability.
- **Explicit forbidden actions:** Do not start n8n; do not register webhooks; do not start tunnels; do not expose Action API publicly; do not add AI/proposal/file-processor behavior.

### Phase 4 - Action API Atomicity + Filename Collision Safety

- **Goal:** Prevent orphan files, orphan events, partial writes, and timestamp filename collisions.
- **Why now / why later:** Event traceability must be reliable before adding review mutations, buttons, webhooks, or AI proposals.
- **Files likely touched:** Action API persistence code, Action API tests, Action API README/security notes.
- **Owner:** DeepSeek implements; GPT reviews failure semantics.
- **Risk level:** High.
- **Validation method:** Tests cover burst captures in the same second, duplicate/retry behavior, path traversal rejection, event/file reconciliation, and partial-write failure behavior.
- **Stop condition:** Stop if the API can return success without a durable pending artifact and matching event, or if recovery/reconciliation is undefined.
- **Explicit forbidden actions:** Do not move/delete/archive existing captures; do not mutate runtime event log during tests unless tests use isolated fixtures; do not commit generated runtime artifacts.

### Phase 5 - `event_id` Response Contract

- **Goal:** Ensure every accepted Action API mutation returns a durable `event_id` and any relevant capture/review identifier.
- **Why now / why later:** n8n, buttons, AI proposals, and future external ingress all need correlation handles; retrofitting traceability later is error-prone.
- **Files likely touched:** Action API response code, Telegram API client handling, Action API README, Telegram README, tests.
- **Owner:** GPT defines schema; DeepSeek implements.
- **Risk level:** High.
- **Validation method:** Success responses include `status`, `event_id`, relevant capture/review ID, and capture-only/review status where applicable. Tests verify returned `event_id` appears in `events.jsonl` and the pending/review artifact references the same trace.
- **Stop condition:** Stop if callers cannot correlate Telegram command, Action API request, pending artifact, and event log entry.
- **Explicit forbidden actions:** Do not invent AI proposal IDs; do not change existing runtime captures; do not expose secrets or tokens in responses/logs.

### Phase 6 - Capture-Only vs Full Polling Decision

- **Goal:** Decide whether the active polling service should accept only capture/status-style commands until `/view`, `/a`, and `/r` are validated.
- **Why now / why later:** The service is active/running and enabled on login; review commands are higher-risk than capture and remain partially unvalidated.
- **Files likely touched:** Telegram README, Current Working State, Telegram bot command guard code if capture-only is chosen, tests.
- **Owner:** GPT decides; DeepSeek implements guard or validation support.
- **Risk level:** High.
- **Validation method:** Command matrix proves each command is allowed, blocked, or safe-failed under the selected mode.
- **Stop condition:** Stop if live polling can approve/reject without validated behavior, or if the plan implies `/view`, `/a`, or `/r` are already validated.
- **Explicit forbidden actions:** Do not run live `/view`, `/a`, or `/r` tests in this decision phase; do not stop/start/restart/enable/disable the service without explicit approval.

### Phase 7 - Telegram Offline Tests

- **Goal:** Make Telegram bot behavior reproducible without Telegram network, live services, n8n, Cloudflare, or secrets.
- **Why now / why later:** Offline tests should exist before refactoring stale helpers, changing guards, validating review commands, or adding buttons.
- **Files likely touched:** Telegram test files, Telegram bot fixtures, Telegram README.
- **Owner:** DeepSeek.
- **Risk level:** Medium.
- **Validation method:** Tests cover `/capture`, `/p`, invalid commands, unauthorized sender, malformed payloads, Action API unavailable, duplicate update behavior, and no direct filesystem bypass.
- **Stop condition:** Stop if tests require a real Telegram token, `.env`, live Telegram network, or live runtime artifacts.
- **Explicit forbidden actions:** Do not inspect `.env`; do not call Telegram API; do not run live bot modes; do not mutate `30_Capture/` or `50_Event_Log/events.jsonl`.

### Phase 8 - `/view` `/a` `/r` Validation

- **Goal:** Validate the deferred review commands through the Action API with controlled, observable behavior.
- **Why now / why later:** This happens only after the API contract, traceability, review-risk decision, and offline tests exist.
- **Files likely touched:** Telegram README, validation notes, Telegram tests, Action API tests if defects are found.
- **Owner:** DeepSeek validates; GPT reviews acceptance criteria.
- **Risk level:** High.
- **Validation method:** Controlled validation proves `/view` is read-only, `/a` approves only the selected pending item, `/r` rejects only the selected pending item, stale/duplicate commands fail safely, and events are traceable.
- **Stop condition:** Stop if any command acts on the wrong item, hides failure, mutates without traceability, or requires raw `--once`.
- **Explicit forbidden actions:** Do not use raw `--once`; do not validate against important real captures; do not trigger AI, n8n, webhooks, tunnels, proposals, file processor, or vault writes.

### Phase 9 - Button-Based Review UX

- **Goal:** Add Telegram button review UX as a convenience layer over the same Action API-backed review workflow.
- **Why now / why later:** Buttons are deferred until command semantics are stable because buttons make actions easier to trigger.
- **Files likely touched:** Telegram bot callback handling, Telegram tests, Telegram README, future n8n notes if webhook buttons are later routed there.
- **Owner:** DeepSeek implements; GPT reviews UX and safety.
- **Risk level:** Medium-high.
- **Validation method:** Button callbacks call the same validated Action API paths as commands; duplicate/stale callback IDs fail safely; no second review path is introduced.
- **Stop condition:** Stop if buttons bypass command validation, skip explicit item identity, or hide irreversible action details.
- **Explicit forbidden actions:** Do not introduce n8n callback routing yet; do not register webhooks; do not expose public ingress; do not approve/reject without explicit item identity.

### Phase 10 - Docker Compose Structure

- **Goal:** Package stable local components in Docker Compose without changing domain behavior.
- **Why now / why later:** Compose should come after local behavior is stable; it should not be used to mask unresolved API or runtime policy issues.
- **Files likely touched:** Docker Compose files, service README files, Action API deployment docs, runtime policy docs.
- **Owner:** GPT designs; DeepSeek implements.
- **Risk level:** Medium.
- **Validation method:** Compose config review, health checks, volume policy review, no secrets in config, and equivalence check against the current local polling path.
- **Stop condition:** Stop if Compose changes behavior, obscures artifact ownership, introduces secret risk, or starts inactive services prematurely.
- **Explicit forbidden actions:** Do not start n8n as part of Telegram activation; do not expose ports publicly; do not include real secrets; do not enable tunnels/webhooks.

### Phase 11 - n8n Future Webhook Path

- **Goal:** Design n8n Telegram webhook handling as a future ingress adapter into the Action API.
- **Why now / why later:** This is later because n8n must not become a second source of truth or compete with active polling before boundaries are stable.
- **Files likely touched:** n8n workflow docs, n8n security notes, activation checklist, webhook adapter docs, Action API ingress docs.
- **Owner:** GPT plans; DeepSeek validates workflows and tests.
- **Risk level:** High.
- **Validation method:** Local-only webhook mock, signed request validation, replay/idempotency tests, workflow JSON review for secrets and prohibited writes.
- **Stop condition:** Stop if n8n can bypass Action API invariants, directly mutate vault/captures/events, or compete with the Telegram polling update queue.
- **Explicit forbidden actions:** Do not activate n8n Telegram workflows; do not register Telegram webhooks; do not start tunnels; do not add AI model nodes; do not write vault files.

### Phase 12 - Cloudflare Tunnel Later

- **Goal:** Add public ingress only after local webhook behavior is safe and access controls are proven.
- **Why now / why later:** Cloudflare is deferred because public ingress increases blast radius and should expose only stable, minimal webhook paths.
- **Files likely touched:** Cloudflare runbooks/config examples, n8n security notes, activation checklist, incident rollback docs.
- **Owner:** GPT gatekeeps; DeepSeek prepares preflight checklist.
- **Risk level:** High.
- **Validation method:** Tunnel route audit, catch-all 404 verification, access policy review, Telegram `secret_token` plan, external request simulation, emergency disable procedure.
- **Stop condition:** Stop if n8n UI, Status API, Action API, or non-webhook paths become publicly reachable.
- **Explicit forbidden actions:** Do not start Cloudflare tunnel; do not register webhook; do not commit tunnel credentials/tokens; do not expose raw internal services.

### Phase 13 - Read-Only GitHub Repo / Tool Discovery

- **Goal:** Discover popular GitHub repositories/tools that could kickstart later LifeOS features without integrating them yet.
- **Why now / why later:** Discovery can be useful later, but it must remain read-only and must not distract from foundation hardening.
- **Files likely touched:** Future discovery notes or parking-lot docs only.
- **Owner:** GPT curates scope; DeepSeek researches candidates.
- **Risk level:** Low if read-only, medium if allowed to become integration work.
- **Validation method:** Catalog includes purpose, license, maturity, security concerns, integration boundary, and explicit no-activation status.
- **Stop condition:** Stop if discovery turns into installation, workflow activation, code import, runtime execution, or writes to LifeOS state.
- **Explicit forbidden actions:** Do not install tools; do not vendor repositories; do not start services; do not grant credentials; do not write captures/events/vault files.

### Phase 14 - Docker / Homelab / Kubernetes Later

- **Goal:** Treat homelab and Kubernetes as deployment evolution, not architecture foundation.
- **Why now / why later:** Kubernetes is inappropriate until Docker Compose is stable, service boundaries are proven, and operational pain justifies orchestration.
- **Files likely touched:** Future deployment docs, homelab runbooks, backup/restore docs, Compose docs, Kubernetes manifests only much later.
- **Owner:** GPT decides readiness; DeepSeek supports operational checklist.
- **Risk level:** High.
- **Validation method:** Compose stability record, backup/restore test, host reboot behavior, monitoring/alerting checklist, clear reason Kubernetes is needed.
- **Stop condition:** Stop if infrastructure work is being used to compensate for unclear Action API, artifact, review, or event-traceability boundaries.
- **Explicit forbidden actions:** Do not create Kubernetes manifests yet; do not migrate active services to homelab; do not expose public ingress; do not start new infrastructure services without explicit approval.

## 11. Features To Defer

- `/view`, `/a`, and `/r` live validation until foundation gates are ready.
- Button UX until review commands are validated.
- Docker Compose expansion until runtime policy and Action API boundaries are stable.
- n8n Telegram webhook path until local polling, Action API, artifact policy, tests, and review-risk handling are complete.
- Cloudflare tunnel until local webhook behavior and access controls are proven.
- AI proposal processing until capture/review traceability is reliable.
- Controlled file processor until exact proposal/version approval and review workflow are stable.
- Homelab expansion until Compose is stable.
- Kubernetes until Compose is boring, stable, and Kubernetes solves a real operational need.

## 12. Features To Avoid For Now

- Public webhooks are not approved for unattended or unrestricted production use; narrow webhook endpoints may be piloted later after auth, replay, and rollback review.
- Active Cloudflare tunnels are not approved for current Telegram/n8n work; narrow tunnel routing may be piloted later after endpoint and access review.
- n8n Telegram workflow activation is deferred until local boundaries, review-command handling, and Action API hardening are stable.
- AI model nodes in Telegram-triggered flows are deferred until proposal-only behavior, review gates, and traceability are defined.
- Proposal generation or approval flows are deferred until exact proposal packets and version-locked approval are implemented.
- Controlled file processor execution is deferred until A4 approval gates, rollback, and audit logging are implemented.
- Direct Telegram filesystem writes remain blocked; Telegram must route mutations through approved APIs.
- Button callbacks that bypass Action API remain blocked; button UX must use the same reviewed API path as commands.
- Raw `--once` validation remains blocked for live Telegram validation because it can process stale queued commands.
- Manual foreground `--poll` validation is not needed for current planning and should only occur under an explicit validation plan.
- Runtime artifact commits remain blocked unless a future runtime artifact policy explicitly approves a narrow tracked subset.
- Kubernetes manifests or cluster deployment remain deferred until Docker Compose is stable and a concrete operational need exists.

## 13. Future Feature Parking Lot

- n8n Telegram webhook adapter.
- Cloudflare domain-based tunnel with narrow webhook exposure.
- Telegram button review UX.
- Multi-message capture mode.
- Photo, voice memo, and document capture.
- AI proposal generation with exact proposal packets and version locking.
- Controlled file processor after explicit approval gates.
- Popular GitHub repo/tool discovery for future acceleration, limited to read-only cataloging until approved.
- Docker Compose service packaging.
- Homelab deployment runbooks.
- Kubernetes only after Compose stability and real need are proven.
- Tool and template discovery queue for reviewed future candidates only.

## 14. Balanced Guardrail Model

1. Safety should preserve usefulness, not block the workflow.
2. Powerful tools are classified, not banned.
3. Unrestricted direct mutation is blocked.
4. Reviewed sandbox experimentation is allowed.
5. Production activation requires explicit approval.
6. Shell/terminal execution is A5/high-risk, but not forbidden forever.
7. External tools must start read-only, sandboxed, or inactive.
8. Any tool that can write files, run commands, expose webhooks, or change services needs an approval gate and rollback plan.

Permission tiers:

| Tier | Scope | Rule |
|---|---|---|
| A0 | Read-only status/search/list | Allowed when authenticated. |
| A1 | Capture intake | Allowed through Action API. |
| A2 | Review lifecycle | Allowed after validation and through Action API. |
| A3 | AI draft/proposal | Allowed only as proposal generation, no direct writes. |
| A4 | Approved file write | Allowed only through controlled file processor. |
| A5 | Shell/Docker/service/admin operations | Allowed only with explicit approval, allowlisted commands, logging, and rollback. |

Hard prohibitions remain narrow and intentional:

- Committing secrets.
- Publicly exposing admin UIs.
- Unrestricted shell access from Telegram.
- Direct AI vault writes.
- Direct n8n vault writes.
- Unapproved file processor writes.

## 15. Tool Candidate / Template Discovery Queue

These candidates are classified for controlled future use. None are active in the current capture-first path.

- `awesome-n8n-templates`: Allowed as read-only research now. May import selected templates into inactive sandbox workflows after review.
- `n8n community nodes`: Deferred, but not rejected. May install later after backup, dependency/security review, and rollback plan.
- `n8n-nodes-starter`: Allowed later for custom LifeOS n8n nodes that wrap approved APIs instead of bypassing them.
- `Evolution API / n8n-nodes-evolution-api`: Deferred cross-channel messaging candidate. Useful later if Telegram expands to WhatsApp or other chat interfaces.
- `Flowise`: Allowed later as a private AI/RAG experiment surface. Must not directly write vault files.
- `Langflow`: Allowed later as a private AI/RAG/MCP experiment surface. Must not directly write vault files.
- `Execute Command`: Not allowed as an unrestricted Telegram/n8n shortcut. May be allowed later for A5 admin tasks with command allowlists, confirmation, logging, and rollback.
- `GitHub repo watcher`: Allowed later as a read-only discovery and scoring feature for selected repos.
- `GitHub trending digest`: Allowed later as a read-only discovery and scoring feature by topic.
- `Repo evaluation agent`: Allowed later as a read-only discovery and scoring feature for maturity, maintenance, license, install complexity, and LifeOS fit.
- `Automation template review queue`: Allowed later as a reviewed n8n template intake system before any import.

Templates and repos are never imported directly into active automation. They enter a review queue first.

## 16. External Tool Integration Rules

- Execute Command is not approved for unattended or unrestricted Telegram/n8n mutation paths; it may be piloted later for reviewed, allowlisted, logged A5 admin tasks with rollback.
- Telegram/n8n must not be wired directly to terminal or repo directories for unrestricted mutation; any terminal or repo operation requires an A5 approval model.
- Community nodes may be installed later only after backup, dependency/security review, compatibility review, and rollback plan.
- n8n templates may be imported into inactive sandbox workflows after review, but not directly into active automation.
- Flowise and Langflow may run privately for experiments, but cannot directly write vault files or bypass proposal/review gates.
- n8n, Flowise, and Langflow admin UIs must not be publicly exposed; narrow approved webhook endpoints may be exposed later with auth, replay protection, and rollback.
- All future tool integrations must route through approved APIs, proposal packets, or read-only research queues.
- Future n8n templates must be reviewed for secrets, shell execution, filesystem writes, webhook exposure, credential usage, and Action API boundary compliance before import.
- Future repo/tool candidates must be scored for maturity, maintenance, license, install complexity, security posture, and LifeOS fit before implementation is proposed.

## 17. Stop Conditions

Stop the next phase immediately if any of these occur:

- A plan implies n8n, Telegram webhooks, or Cloudflare tunnels are active now.
- A plan says `/view`, `/a`, or `/r` are already live-validated.
- A plan says button UX is already implemented.
- A plan implies any external tool is installed, imported into active automation, or active without approval.
- A plan approves unrestricted or unattended Execute Command for Telegram/n8n mutation paths.
- A plan implies Flowise or Langflow can write files directly.
- Runtime artifacts are staged for commit.
- Code files are modified during a documentation-only phase.
- Secret/token/env inspection is required.
- Service state changes unexpectedly.
- Action API invariants are bypassed by Telegram, n8n, buttons, AI, or file processor paths.
- Review commands can approve/reject without traceable event IDs and validated target identity.
- Any future feature tries to skip runtime policy, helper cleanup, Action API hardening, `event_id`, offline tests, or review-risk handling.

## 18. Final Recommendation

Proceed with **Phase 1 - Runtime Artifact Policy** next.

Keep the current active system in capture-first local polling mode while the foundation is hardened. The safest next implementation sequence is:

1. Runtime artifact policy.
2. Telegram helper cleanup.
3. Action API contract hardening.
4. Action API atomicity and filename collision safety.
5. `event_id` response contract.
6. Capture-only versus full polling decision.
7. Telegram offline tests.

Only after those pass should LifeOS continue to `/view` `/a` `/r` validation, button UX, Docker Compose, n8n webhooks, Cloudflare tunnels, AI proposals, controlled file processing, homelab expansion, or Kubernetes.
