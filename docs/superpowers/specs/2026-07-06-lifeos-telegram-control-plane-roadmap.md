# LifeOS Telegram Control Plane — Long-Term Roadmap

## Executive Summary

LifeOS Telegram Control Plane lets the user capture anything from Telegram, review and approve it, have AI process approved captures into proposed LifeOS files/updates, retrieve LifeOS content back through Telegram, and run recurring drift scans for stale docs/folders/organization issues — all through controlled APIs, approval gates, and event logs. The architecture separates capture, review, AI extraction, file creation, retrieval, drift auditing, and private dashboard into independently buildable modules with explicit security boundaries. n8n orchestrates the flow between Telegram and the LifeOS APIs but never directly writes vault files, executes shell commands, or accesses secrets.

---

## Current State

### Already Implemented

| Component | Status | Details |
|---|---|---|
| **LifeOS Status API** | Implemented, hardened | Read-only Python HTTP server on port 8787. Endpoints: `GET /health`, `GET /status`. Reads `30_Capture/` and `50_Event_Log/` via read-only mounts. `cap_drop: ALL`, `no-new-privileges`, non-root user. No Docker socket, no vault access, no secrets access. Unit tests pass. |
| **LifeOS Action API** | Implemented, hardened | Read-write Python HTTP server on port 8788. Endpoints for capture create, pending list, approve, reject. Mounts `30_Capture/` and `50_Event_Log/` as read-write. Hardened container with `cap_drop: ALL`, non-root user (uid 1001). No shell execution, no Docker socket, no vault access. Latest test count: 91/91. |
| **Manual n8n Status API Test** | Passed | Manual Trigger → HTTP Request → `GET http://lifeos-status-api:8787/status`. Returned valid JSON with `status: ok`, `mode: read_only`. Workflow saved as inactive. No schedule, Telegram, webhook, or AI nodes added. |
| **Telegram Capture Processing Vision** | Locked in design doc | `docs/superpowers/specs/2026-07-06-lifeos-telegram-automation-operator-design.md` defines capture modes, review flow, AI pipeline design, processor boundary, and UX. Vision locked; no implementation beyond Action API. |
| **Cloudflare Tunnel Scaffold** | Created, guardrails added | `40_Services/n8n/cloudflared/` with `config.example.yml`, `docker-compose.cloudflared.example.yml`, README runbook. Guardrails prevent leaks, credentials exposure, and public n8n UI. Catch-all 404 rule documented. No tunnel active. |

### Not Yet Implemented

| Component | Status |
|---|---|
| Active Cloudflare Tunnel | Not started — requires user domain/Cloudflare readiness |
| Telegram Webhook Registration | Not started — requires active tunnel |
| n8n Telegram Workflow | Not created or activated — requires tunnel + webhook |
| Capture Mode (`/capture` with no text → multi-message) | Not implemented |
| AI Extraction Pipeline | Not implemented — requires stable capture + review flow |
| Controlled File Processor | Not implemented — requires AI proposal format + review flow |
| Retrieval Operator (read-only Telegram content retrieval) | Not implemented |
| Drift Auditor (recurring stale docs/organization scans) | Not implemented |
| Private Ops Dashboard (Tailscale/local only) | Not implemented |

---

## Module Breakdown

### 1. Capture Operator

**Purpose**: Receive capture requests from Telegram and create pending capture files in `30_Capture/pending_review/`. Never write directly to the vault.

**Inputs**: Telegram messages — `/capture <text>`, future capture mode (multi-message with `/cancel` and timeout), future photos, voice memos, documents.

**Outputs**: Capture files with standardized frontmatter in `30_Capture/pending_review/`. Event log entries. Telegram receipt replies.

**Dependencies**: Action API (`POST /captures`, `GET /captures/pending`). n8n Telegram Webhook + HTTP Request nodes.

**Security Boundary**: Action API has bounded write access to `30_Capture/` and `50_Event_Log/` only. No vault access. No shell execution. n8n orchestrates but does not write files directly.

**Implementation Status**: Action API supports create/list. n8n Telegram workflow not built. Capture mode not implemented. Photo/voice/document capture deferred.

**Future Commands/Interfaces**:
- `/capture <text>` — immediate capture (requires n8n workflow)
- `/capture` (no text) — enter capture mode (multi-message with timeout)
- `/cancel` — exit capture mode without creating capture

---

### 2. Review Operator

**Purpose**: Let the user review pending captures, view their contents, approve or reject them through Telegram.

**Inputs**: Telegram commands — `/pending`, `/view <number>`, `/approve <number>`, `/reject <number>`, `/view latest`, `/approve latest`, `/reject latest`.

**Outputs**: Capture state transitions (pending → approved, pending → rejected). File moves between `pending_review/`, `approved/`, `rejected/`. Event log entries. Telegram confirmation replies.

**Dependencies**: Action API (`GET /captures/pending`, `GET /captures/pending/<index>`, `POST /captures/<id>/approve`, `POST /captures/<id>/reject`). n8n Telegram Webhook + HTTP Request + Telegram Send Message nodes.

**Security Boundary**: Same as Capture Operator — bounded to capture lifecycle. No vault access. Only moves files within `30_Capture/`.

**Implementation Status**: Action API supports all review endpoints. n8n workflow not built.

**Future Commands/Interfaces**:
- `/pending` — list pending captures with numbered index
- `/view <number>` — show full content of a pending capture
- `/approve <number>` — approve (moves to `approved/`)
- `/reject <number>` — reject (moves to `rejected/`)
- `/review` mode — step through pending captures one by one with inline approve/reject/skip buttons
- Inline keyboard buttons on capture messages

---

### 3. AI Processing Pipeline

**Purpose**: Read approved captures, extract structured information (summary, classification, links, action items, source metadata), and produce a proposal for LifeOS file creation — without directly writing anything.

**Inputs**: Approved capture files from `30_Capture/approved/`.

**Outputs**: Structured proposal documents stored in `30_Capture/processing/proposals/`. Event log entries.

**Dependencies**: AI model integration (OpenAI API, Claude API, or local model). Proposal queue storage. Future `/proposals` review command.

**Security Boundary**: AI reads only approved captures. AI produces proposals only — no direct file-write, git, shell, or vault access. Proposals require user approval before any file changes are applied.

**Implementation Status**: Not implemented. Will be built after Phase C (capture + review) is stable.

**Future Proposals Model**:
```json
{
  "proposal_id": "prop_20260706_article_link",
  "capture_id": "capture_20260706_article_link",
  "title": "Rust Async Patterns Article",
  "summary": "Reference link to an article about Rust async patterns.",
  "capture_type": "link",
  "source_url": "https://example.com/rust-async-patterns",
  "action_items": ["Review the article for applicable patterns"],
  "suggested_destination": "10_Vaults/LifeOS/04_KNOWLEDGE/Rust/",
  "proposed_files": [
    {
      "path": "10_Vaults/LifeOS/04_KNOWLEDGE/Rust/async-patterns-reference.md",
      "content": "# Rust Async Patterns Reference\n\n...",
      "action": "create"
    }
  ]
}
```

---

### 4. Controlled File Processor

**Purpose**: Read approved proposals from the processing queue and apply validated file changes to LifeOS vault/directory structure. Never create or modify files outside allowlisted paths.

**Inputs**: Approved proposal documents from `30_Capture/processing/proposals/`.

**Outputs**: Created/updated LifeOS vault files. Event log entries.

**Dependencies**: Proposal queue. Template library. Path allowlist. Validation schemas.

**Security Boundary**: Processor uses validated templates with frontmatter schemas. Each file path is checked against an allowlist of writable directories. Only user-approved proposals are applied. Processor logs before/after state for recovery. No secrets, credentials, or Docker socket access. n8n must not directly write vault files — the processor is the only vault-writing component, and only after user approval.

**Implementation Status**: Not implemented. Requires AI proposal format, review flow, and explicit design/security review.

---

### 5. Retrieval Operator

**Purpose**: Let the user retrieve or summarize LifeOS content through Telegram. Read-only initially; later may support approved update proposals.

**Inputs**: Telegram commands — `/search <query>`, `/get <path>`, future summarized views.

**Outputs**: Telegram messages with content, summaries, or file listings. Event log entries.

**Dependencies**: Read-only access to LifeOS vault and knowledge base. Search/index capability (future Qdrant or grep-based).

**Security Boundary**: Read-only only. No secrets, credentials, or runtime database files retrievable. Retrieval scope is bounded to specific allowed directories (e.g., `10_Vaults/LifeOS/`). Private runtime files (`40_Services/`, `50_Event_Log/`, `30_Capture/` with credentials, `.env`) excluded from search results.

**Implementation Status**: Not implemented. Will be designed after capture/review is stable.

**Future Commands/Interfaces**:
- `/search <query>` — search vault content (text or semantic)
- `/get <path>` — retrieve a specific file
- `/summary <topic>` — AI-summarized view of content
- `/recent` — list recently created/modified notes

---

### 6. Drift Auditor

**Purpose**: Recurring or manual scans that detect stale docs, organizational drift, stale folders, outdated phase wording, broken roadmap references, unresolved organization problems, privacy risks, and outdated checklists. Produces reports and proposed fixes that require approval before application.

**Inputs**: LifeOS vault, event log, project files, roadmap documents, workspace directories.

**Outputs**: Drift reports with categorized findings. Proposed fix actions. Event log entries.

**Dependencies**: Read-only filesystem access. Event log parsing. Vault structure knowledge.

**Scan Categories**:
- **Stale docs** — files not modified in >90 days
- **Stale folders** — project folders with no recent activity
- **Organizational drift** — files in wrong directories, naming convention violations
- **Phase wording** — roadmap references to outdated phases
- **Broken roadmap references** — cross-links to non-existent sections
- **Privacy risks** — credentials, personal data in vault files
- **Checklist mismatch** — outdated checklists, incomplete items
- **Unresolved captures** — captures stuck in pending/rejected without resolution

**Security Boundary**: Read-only scanning. Produces reports/proposals only. No automatic fixes. Every proposed fix requires explicit user approval before application. Reports are stored for user review.

**Implementation Status**: Not implemented. Will be designed and built after core capture/review flow.

**Future Commands/Interfaces**:
- `/drift` — manual drift scan trigger
- `/drift status` — last scan timestamp, finding count
- `/proposals` — list pending audit proposals
- Recurring schedule (weekly/monthly) with summary report

---

### 7. Private Ops Dashboard

**Purpose**: Local/Tailscale-only visibility layer showing n8n, Status API, Action API, Cloudflare Tunnel, capture queue, event log, git state, disk state, and drift status. Not publicly exposed.

**Inputs**: Data from Status API, Action API, git state, disk usage, Drift Auditor reports.

**Outputs**: Web-based dashboard accessible over local network or Tailscale only.

**Dependencies**: Status API. Action API. Drift Auditor reports. Git state queries.

**Security Boundary**: Local network only (127.0.0.1 or Tailscale IP). No public exposure. No Docker socket. No secrets display. No credentials in dashboard. Read-only display — no actions from dashboard UI (actions must go through Telegram or authorized APIs).

**Implementation Status**: Not implemented. Will be designed and built after multiple API modules are stable.

---

## Phased Build Plan

### Phase B3 — Controlled Cloudflare Tunnel Activation

| Dimension | Detail |
|---|---|
| **Goal** | Activate the Cloudflare Tunnel with real configuration so that a public HTTPS endpoint exists for n8n webhooks. |
| **Deliverable** | Active cloudflared container with real config.yml, tunnel established to Cloudflare edge, catch-all 404 rule. |
| **Success Criteria** | `cloudflared tunnel list` shows tunnel connected. `https://telegram.<domain>/webhook/test` returns n8n response. `https://telegram.<domain>/` returns 404. Status API not public. Action API not public. |
| **Stop Condition** | User has not provided Cloudflare domain, zone, or tunnel token. Guardrails prevent config.yml with placeholder values from working. |

### Phase C1 — Generic n8n Webhook Reachability Test

| Dimension | Detail |
|---|---|
| **Goal** | Verify the tunnel + n8n webhook path works end-to-end before any Telegram integration. |
| **Deliverable** | Temporary n8n webhook workflow at `/webhook/test` that returns a 200 response. |
| **Success Criteria** | `curl https://telegram.<domain>/webhook/test` returns 200. Response payload valid. |
| **Stop Condition** | Phase B3 not complete. |

### Phase C2 — Minimal Telegram Receive Workflow

| Dimension | Detail |
|---|---|
| **Goal** | Create the n8n Telegram webhook workflow that receives Telegram updates, authenticates the sender, and routes to command handlers. |
| **Deliverable** | n8n workflow: Webhook → Code (extract sender/message) → IF (allowlist check) → Switch (route by command). Telegram webhook registered via `setWebhook`. Workflow saved as activated. |
| **Success Criteria** | Telegram message reaches n8n. Unauthorized user rejected. Authorized user proceeds to routing. |
| **Stop Condition** | Phase C1 not complete. Telegram token not configured in n8n credential store. |

### Phase C3 — /start, /help, /status

| Dimension | Detail |
|---|---|
| **Goal** | Implement the three informational commands in the n8n Telegram workflow. |
| **Deliverable** | `/start` → welcome message. `/help` → command list. `/status` → HTTP Request to Status API → formatted reply. |
| **Success Criteria** | Each command returns correct Telegram reply. `/status` shows live capture queue + event log state from Status API. |
| **Stop Condition** | Phase C2 not complete. Status API unreachable. |

### Phase C4 — /capture <text>

| Dimension | Detail |
|---|---|
| **Goal** | Implement immediate text capture through Telegram. |
| **Deliverable** | `/capture <text>` → HTTP Request to Action API `POST /captures` → Telegram reply with receipt (capture_id, event_id, type, status, next actions). |
| **Success Criteria** | Capture file created in `30_Capture/pending_review/`. Event appended to `events.jsonl`. Receipt returned to Telegram. `/capture` with no text returns error (capture mode deferred to Phase C7). |
| **Stop Condition** | Phase C3 not complete. Action API unreachable. |

### Phase C5 — /pending, /view, /approve, /reject

| Dimension | Detail |
|---|---|
| **Goal** | Implement the review lifecycle commands. |
| **Deliverable** | `/pending` → list with numbered index. `/view <num>` → full capture content. `/approve <num>` → approve via Action API → confirmation. `/reject <num>` → reject via Action API → confirmation. `/approve latest` and `/reject latest` resolve to most recent pending. |
| **Success Criteria** | Full review cycle works: capture → pending list → view → approve → file moves to approved. Rejected moves to rejected. Remove from pending. Events logged. Correct replies. |
| **Stop Condition** | Phase C4 not complete. |

### Phase C6 — /menu and Button UI

| Dimension | Detail |
|---|---|
| **Goal** | Add mobile-friendly inline keyboard menu and optional BotFather command menu registration. |
| **Deliverable** | `/menu` → inline keyboard with buttons for Capture, Pending, Approve, Reject, Status, Help. Inline approve/reject buttons on pending list items where feasible. BotFather `/setcommands` registration documented. |
| **Success Criteria** | `/menu` shows working buttons. Button taps execute correct commands. |
| **Stop Condition** | Phase C5 not complete. |

### Phase C7 — /capture Mode with /cancel and Timeout

| Dimension | Detail |
|---|---|
| **Goal** | Implement multi-message capture mode for convenient mobile capture without prefixing each message. |
| **Deliverable** | `/capture` (no text) → enter capture mode. Bot replies with instructions. Next message becomes capture. `/cancel` exits without capture. Timeout (10 min idle) exits with notification. |
| **Success Criteria** | Capture mode works. Multiple sequential captures work. `/cancel` works. Timeout works. Events logged. No duplicate or orphan captures. |
| **Stop Condition** | Phase C5 not complete. Capture mode creates hangs or orphan states. |

### Phase E1 — AI Extraction Proposal Format

| Dimension | Detail |
|---|---|
| **Goal** | Design and document the AI extraction proposal format and processing queue structure. |
| **Deliverable** | Documented proposal schema. Processing queue location (`30_Capture/processing/proposals/`). Proposal review/rejection format. Event types defined. |
| **Success Criteria** | Schema reviewed, approved, and committed. No implementation code. |
| **Stop Condition** | Capture and review flow (Phase C) not stable. |

### Phase E2 — AI Extraction Workflow

| Dimension | Detail |
|---|---|
| **Goal** | Build the AI extraction workflow that reads approved captures and produces proposals. |
| **Deliverable** | n8n workflow or script that sends approved captures to AI model, extracts structured information, produces proposal document in processing queue. Events logged for extraction start, completion, and errors. |
| **Success Criteria** | Approved capture → AI reads → structured proposal produced. Proposal stored in `30_Capture/processing/proposals/`. No direct file writes to vault. No shell execution. |
| **Stop Condition** | Phase E1 not complete. AI model integration not security-reviewed. |

### Phase F1 — Controlled File Processor Design

| Dimension | Detail |
|---|---|
| **Goal** | Design the controlled file processor that applies approved proposals to create/update LifeOS files. |
| **Deliverable** | Design document: processor API, path allowlist, template system, validation rules, event logging, rollback mechanism. Approval gate design (how user approves/rejects proposals). |
| **Success Criteria** | Design reviewed, approved, committed. No implementation code. |
| **Stop Condition** | AI extraction (Phase E) not producing valid proposals. |

### Phase F2 — Controlled File Processor Implementation

| Dimension | Detail |
|---|---|
| **Goal** | Build the controlled file processor as a hardened API (Processor API) that creates/updates vault files from approved proposals. |
| **Deliverable** | Processor API container with path allowlist, template-based file creation, frontmatter validation, event logging, rollback support. User review/approval workflow for proposals. |
| **Success Criteria** | Approved proposal → processor creates valid vault file. Path outside allowlist rejected. Missing template rejected. Event logged. n8n does not bypass processor. |
| **Stop Condition** | Phase F1 not complete. Security review not passed. |

### Phase G1 — Read-Only Retrieval/Search Design

| Dimension | Detail |
|---|---|
| **Goal** | Design the read-only content retrieval/search system for Telegram-based LifeOS queries. |
| **Deliverable** | Design document: command set, search scope, privacy boundaries, excluded paths, response format, rate limits. |
| **Success Criteria** | Design reviewed, approved, committed. No implementation code. |
| **Stop Condition** | Core capture/review flow (Phase C) not stable. |

### Phase G2 — Telegram Retrieval Commands

| Dimension | Detail |
|---|---|
| **Goal** | Implement read-only retrieval/search commands for Telegram. |
| **Deliverable** | `/search <query>` → grep or semantic search results. `/get <path>` → file content with size limits. Scope bounded to `10_Vaults/LifeOS/` and explicit allowlist. Secrets and runtime paths excluded. |
| **Success Criteria** | Search returns valid results. Secrets not retrievable. Large files truncated. Events logged. |
| **Stop Condition** | Phase G1 not complete. Security review not passed. |

### Phase H1 — Drift Auditor Design

| Dimension | Detail |
|---|---|
| **Goal** | Design the Drift Auditor system for stale docs, organizational drift, and privacy risk scanning. |
| **Deliverable** | Design document: scan categories, report format, scan frequency, proposal/approval workflow, excluded paths. |
| **Success Criteria** | Design reviewed, approved, committed. No implementation code. |
| **Stop Condition** | Core LifeOS vault and file structure not stable enough for meaningful scanning. |

### Phase H2 — Recurring Drift Scan/Report

| Dimension | Detail |
|---|---|
| **Goal** | Build and deploy the recurring Drift Auditor as a scheduled task or n8n workflow. |
| **Deliverable** | Drift Auditor script/workflow that scans vault, event log, project files, and workspace directories. Produces categorized report with proposed fixes. Sends summary via Telegram or stores for review. |
| **Success Criteria** | Scan produces valid report. Stale docs detected. Organizational drift detected. Privacy risks flagged. Proposed fixes do not auto-apply — require approval. Recurring schedule works. |
| **Stop Condition** | Phase H1 not complete. Approval workflow for fixes not defined. |

### Phase I1 — Private Dashboard Design

| Dimension | Detail |
|---|---|
| **Goal** | Design the private operations dashboard accessible over Tailscale/local network only. |
| **Deliverable** | Design document: dashboard layout, data sources (Status API, Action API, Drift Auditor, git state, disk state), read-only constraint, Tailscale-only access requirement. |
| **Success Criteria** | Design reviewed, approved, committed. No implementation code. |
| **Stop Condition** | Multiple API modules not yet stable. |

### Phase I2 — Dashboard Implementation

| Dimension | Detail |
|---|---|
| **Goal** | Build and deploy the private operations dashboard. |
| **Deliverable** | Web-based dashboard serving at local IP/Tailscale IP only. Shows n8n status, capture queue, event log state, git dirty state, disk usage, Cloudflare Tunnel status, Drift Auditor state. Read-only display. No actions from UI. |
| **Success Criteria** | Dashboard reachable over Tailscale. Not reachable publicly. All data sources connected. Read-only. No credentials or secrets displayed. |
| **Stop Condition** | Phase I1 not complete. Security review not passed. |

---

## Safety Model

| Rule | Enforcement |
|---|---|
| No arbitrary shell from Telegram | No Execute Command nodes in any n8n workflow. No `shell=True` in Python APIs. |
| No direct n8n vault writes | n8n routes through APIs only. Action API bounded to `30_Capture/`. Processor API (future) controlled by allowlist and approval gate. |
| No public n8n UI | n8n bound to `127.0.0.1:5678`. Cloudflare Tunnel catch-all returns 404 for non-webhook paths. |
| No Docker socket | No container mounts `/var/run/docker.sock`. |
| No secrets retrieval | Retrieval Operator (future) excludes secrets paths, credentials, runtime databases. |
| No AI applying file changes without approval | AI pipeline produces proposals only. Processor applies only approved proposals. |
| Status API read-only | Container `read_only: true`, `cap_drop: ALL`, no write mounts. |
| Action API bounded to capture lifecycle | Writable mounts limited to `30_Capture/` and `50_Event_Log/`. No vault access. Specific file operations only (create, list, move within capture structure). |
| Future Processor API approval-gated | Only user-approved proposals applied. Path allowlist. Template validation. |
| Retrieval starts read-only | First retrieval iteration is read-only. Update proposals deferred to later phase. |
| Drift Auditor produces proposals/reports first | No automatic fixes. Every proposed fix requires explicit user approval. |

---

## Permission Tiers

| Tier | Level | Scope | Examples |
|---|---|---|---|
| **A0** | Read/Status | Status API access only. | `/status`, dashboard read-only views, drift report reading. |
| **A1** | Capture Intake | Create pending captures. No review, no modification. | `/capture`, capture mode. |
| **A2** | Review/Approve/Reject | Capture lifecycle management. Transition captures between pending/approved/rejected states. | `/pending`, `/view`, `/approve`, `/reject`. |
| **A3** | AI Extraction/Proposal | Read approved captures, produce proposals. No direct file writes. | AI reading approved captures, generating proposal documents. |
| **A4** | Approved File Creation/Update | Create/update LifeOS vault files from approved proposals. Uses templates, allowlist, validation. | Controlled Processor applying approved proposals to create/update vault files. |
| **A5** | High-Risk Operations | Destructive or system-level operations. Requires explicit manual review. | Delete, move, archive, git operations, service restart. |

**A5 Early Limitation**: A5 operations must not be triggerable directly from Telegram in early phases. They require explicit manual review through approved channels (terminal, approved scripts) and a separate confirmation step outside the Telegram automation flow.

---

## Recommended New Features

All features below are **future, not implemented**.

| Feature | Description | Phase |
|---|---|---|
| `/menu` | Inline keyboard menu for mobile-friendly navigation | C6 |
| `/selftest` | Self-test that checks Action API, Status API, capture directory, event log. Returns pass/fail per check. | C3+ |
| `/review` mode | Step through pending captures one by one with inline approve/reject/skip buttons | C5+ |
| `/search` | Search vault content from Telegram (text or semantic) | G2 |
| `/get` | Retrieve a specific file's content from allowed directories | G2 |
| `/drift` | Manual drift scan trigger with status and report access | H2 |
| `/proposals` | List pending AI proposals and audit proposals | E2+ |
| `/privacy` check | Trigger a targeted privacy risk scan (subset of drift auditor) | H2 |
| Attachment quarantine | Quarantine incoming attachments (photos, files, voice) in a temporary area before review | C7+ |
| Event redaction | Selective event redaction for privacy-sensitive events | Future, beyond current scope |
| Proposal preview cards | Rich-formatted proposal display in Telegram with accept/reject/edit buttons | E2 |
| Private Tailscale dashboard | Local-only operations dashboard | I1/I2 |
| Service registry | Track all running LifeOS services, their ports, health, and access methods | I2 |
| Recurring drift report | Weekly/monthly drift summary sent to Telegram | H2 |

---

## Key Architecture Principle (Restated)

**Keep capture, extraction, file creation, retrieval, auditing, and dashboarding separated into safe modules:**

- **Capture Operator**: Telegram → n8n → Action API → `30_Capture/pending_review/`
- **Review Operator**: Telegram → n8n → Action API → approve/reject → `30_Capture/approved/` or `30_Capture/rejected/`
- **AI Processing Pipeline**: Approved capture → AI model → structured proposal → `30_Capture/processing/proposals/`
- **Controlled File Processor**: Approved proposal → template/validation → allowlisted LifeOS vault path
- **Retrieval Operator**: Telegram command → read-only bounded search → content summary/reply
- **Drift Auditor**: Scheduled/manual scan → report with proposed fixes → approval before application
- **Private Ops Dashboard**: Local/Tailscale-only → read-only display of system state

Do not collapse these into one unsafe workflow. Each module has its own security boundary, approval gate, and event logging.

---

**Document Version**: 1.0  
**Date**: 2026-07-06  
**Status**: Roadmap locked  
**Supersedes**: No prior roadmap document. Complements `2026-07-06-lifeos-telegram-automation-operator-design.md` (operator architecture design).
