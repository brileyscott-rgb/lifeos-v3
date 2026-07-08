# LifeOS Agentic Capture Pipeline V1

Status: architecture/scaffold
Created: 2026-07-08
Purpose: define the safe end-to-end architecture for turning captures from Telegram, HTTP Shortcuts, bookmarklets, web pages, videos, files, and future MCP/n8n inputs into high-quality LifeOS-ready draft notes inside a headless buffer vault, with specialized AI agents preparing review packets for human approval before canonical LifeOS import.

## Overall Pipeline

```
Telegram / HTTP Shortcuts / Bookmarklet / Desktop / Future MCP / n8n
        │
        ▼
  Tailscale-only Capture API
        │
        ▼
  Queue (append-only)
        │
        ▼
  Dockerized Processors (type-specific)
        │
        ▼
  Headless Capture Buffer Vault
        │
        ▼
  Specialized AI Agents (10 agents)
        │
        ▼
  Review Packet (human-approval format)
        │
        ▼
  Human Approval (manual, explicit)
        │
        ▼
  Canonical LifeOS Import (automated but gated)
```

No step in this pipeline writes directly to the canonical LifeOS vault. Every import requires an explicit human approval step.

## Pipeline Stages

### Stage 1: Capture Intake

**Input channels (all Tailscale-only, no public webhooks):**

| Channel | Transport | Auth | Current State |
|---|---|---|---|
| Telegram bot | Polling (systemd) | Sender allowlist | Live, capture-first |
| HTTP Shortcuts | Capture API POST | HMAC token | Roadmap |
| Bookmarklet | Capture API POST | HMAC token | Roadmap |
| Desktop scripts | Capture API POST | HMAC token | Roadmap |
| n8n workflows | Capture API POST | Internal network token | Roadmap |
| Future MCP tools | Capture API POST | Scoped MCP token | Roadmap |

**Intake behavior:**
- Normalize raw input (text, URL, file reference, media reference)
- Detect source type
- Assign unique capture ID
- Write to append-only raw capture queue
- Return receipt to sender
- No processing, no vault writes, no AI invocation inside the request handler

### Stage 2: Queue

- Append-only, durable, idempotency-aware
- Ordered by arrival timestamp
- Supports: pending, processing, processed, failed, skipped states
- Processors pull from queue; no push-based fanout from intake
- Queue failures log to event log; captures retained for retry

### Stage 3: Dockerized Processors

Type-specific processors run in isolated Docker containers:
- `metadata_processor` — extract and normalize metadata
- `article_processor` — extract clean article text from URLs
- `web_clipper_processor` — capture web page snapshots
- `media_downloader` — download images, audio, video
- `video_processor` — extract key frames, timestamps
- `whisper_transcript_processor` — transcribe audio/video
- `pdf_processor` — extract text, metadata, structure
- `github_repo_processor` — clone, summarize, extract structure
- `duplicate_detector` — detect near-duplicate captures
- `markdown_formatter` — produce LifeOS-standard Markdown
- `review_packet_builder` — assemble review packets
- `import_exporter` — execute approved imports into canonical vault

All processors:
- Operate on buffer vault only (never mount canonical vault)
- Run with `read_only` rootfs where possible
- `cap_drop: ALL`, `no-new-privileges`, non-root user
- No Docker socket, no shell MCP, no network egress unless required and documented
- Log to `07_Logs/` in buffer vault

### Stage 4: Headless Capture Buffer Vault

Located at `/home/lifeos/LifeOS_Capture_Buffer/`.

Purpose:
- Isolate raw captures, processed drafts, agent workspace, review packets, and import plans from the canonical LifeOS vault
- Prevent accidental writes, AI drift, and unreviewed imports
- Provide a clean workspace for AI agents without exposing the full vault

Structure defined in `Headless_Capture_Buffer_Vault_Policy.md`.

### Stage 5: Specialized AI Agents

Ten specialized agents operate on the buffer vault only:
1. Intake Agent — normalize and classify raw captures
2. Source Extraction Agent — extract clean source material
3. Knowledge Note Agent — draft Knowledge notes
4. Project Note Agent — draft project scaffold files
5. Idea Agent — convert captures into future idea notes
6. Reference Agent — preserve source material without over-processing
7. Media Transcript Agent — handle video/audio/image capturers
8. Metadata Taxonomy Agent — clean YAML, tags, domains, links
9. QA Verifier Agent — validate quality, source trail, compliance
10. Import Planner Agent — produce review packets for human approval

All defined in `40_Services/agents/capture/`.

### Stage 6: Review Packet

A review packet bundles:
- Capture ID, source, source type, processing status
- Agent outputs (proposed notes, files, metadata)
- Proposed canonical destination path
- Files to create, update, or explicitly not touch
- Source trail, risks, QA result
- Human approval checklist
- Import command/procedure placeholder
- Rollback procedure

Format defined in `Capture_Review_Packet_Format.md`.

### Stage 7: Human Approval

Required for every import into the canonical LifeOS vault.
- Review packet presented in Telegram (or dashboard)
- Operator reviews: content quality, placement correctness, link integrity, secret leakage, template compliance
- Approve: import proceeds via Import Planner → import_exporter
- Reject: capture moved to `05_Rejected/` in buffer vault with reason
- Modify: agent reworks based on feedback, re-submits

### Stage 8: Canonical LifeOS Import

Only after explicit human approval:
- Import Planner generates the exact import manifest
- import_exporter processor executes the import
- Files are created/updated in the canonical vault per manifest
- Source trail and import events logged to event log
- Buffer vault copies retained per retention policy

## Why the Buffer Vault Exists

The canonical LifeOS vault is the trusted knowledge graph. Everything in it should be reviewed, intentional, and high-quality.

The buffer vault provides:
1. **Containment** — AI agents, processors, and draft workflows operate on a copy/scratch space, not the production vault
2. **Safety** — accidental writes, bad AI output, and incomplete drafts never reach the canonical vault
3. **Reviewability** — every proposed change to the canonical vault is packaged as a review packet with full context
4. **Rollback** — rejected or failed captures are contained and can be inspected or re-processed without vault impact
5. **Performance** — buffer vault can be mounted read-write into Docker containers without exposing canonical vault data

## Why Canonical LifeOS Is Protected

The canonical LifeOS vault contains:
- Years of curated knowledge, decisions, and project context
- Active project files, AI contexts, and implementation plans
- Identity patterns, policies, and personal reference material
- Symlinks and Obsidian-specific graph relationships

Direct AI writes to this vault risk:
- Content drift (AI-generated notes diverging from user intent)
- Graph pollution (bad links, wrong tags, incorrect folder placement)
- Secret exposure (AI processing may inadvertently surface or embed secrets)
- Template violation (AI-generated notes not matching LifeOS standards)
- Irreversible damage (no review checkpoint before vault mutation)

## Why AI Agents May Draft But Not Directly Import

Agents are powerful but imperfect. They may:
- Misclassify a capture type
- Place content in the wrong folder
- Generate hallucinated facts or links
- Miss duplicate content
- Apply wrong templates
- Include incorrect metadata

The approval gate ensures human judgment remains the final authority on what enters the canonical knowledge graph. Agents prepare; humans decide.

## How Telegram Becomes One Input Source

The current Telegram bot is the first capture channel, but it must not become a privileged writer.

- Telegram captures flow through the same Capture API as all other sources
- No special Telegram-only processing or bypass of review gates
- Telegram review UI is convenient but not the only approval path
- Future channels (HTTP Shortcuts, bookmarklet, desktop, n8n, MCP) use the identical pipeline

## How HTTP Shortcuts and Bookmarklets Fit

**HTTP Shortcuts (mobile):**
- Android/iOS Shortcuts app sends POST to Capture API
- Payload: text, URL, or structured data
- Auth: HMAC-signed request with pre-shared key
- Response: capture ID receipt

**Bookmarklet (desktop browser):**
- JavaScript bookmarklet extracts current page title + URL
- Sends POST to Capture API
- Auth: HMAC-signed request with pre-shared key
- Response: capture ID receipt shown in browser alert

Both use the Tailscale-only Capture API. No public endpoints.

## How Web Articles, Videos, Images, Audio, PDFs, and GitHub Repos Are Handled

| Content Type | Processor Chain | Output |
|---|---|---|
| URL (article) | metadata → article_processor → duplicate_detector → markdown_formatter | Knowledge/Reference note draft with source link |
| URL (web page) | web_clipper_processor → markdown_formatter | Clipped Markdown + metadata |
| Video URL | media_downloader → video_processor → whisper_transcript → markdown_formatter | Transcript note + key frames + source link |
| Image | media_downloader → metadata | Reference note with image link (image in media archive) |
| Audio file | whisper_transcript → markdown_formatter | Transcript note + source link |
| PDF | pdf_processor → markdown_formatter | Extracted text + metadata + source link |
| GitHub repo | github_repo_processor → markdown_formatter | Summary + structure + key files reference |
| Voice memo | whisper_transcript → metadata | Transcript note |

All media files (images, audio, video, PDFs) are stored in `/home/lifeos/LifeOS_Media_Archive/`, not in the buffer vault or canonical vault. Markdown notes link to media via relative or local paths.

## How n8n May Call the Capture API

n8n workflows may:
- POST captures to the Capture API on the internal Docker network
- Receive capture ID receipts
- Read capture status from Status API
- Trigger processor chains via queue or API

n8n workflows must NOT:
- Write directly to the buffer vault or canonical vault
- Execute shell commands to manipulate captures
- Bypass the approval gate for canonical imports
- Read or write secrets, env files, or Docker socket

n8n is a workflow orchestrator, not a privileged root actor.

## How MCP Tools May Support Extraction/Search

MCP tools may:
- Search the buffer vault for existing captures (read-only)
- Query vector stores for similarity/duplicate detection (read-only)
- Provide structured metadata extraction (read-only)
- Report processor status (read-only)

MCP tools must NOT:
- Write to any vault or buffer location
- Execute shell commands
- Access Docker socket
- Read or expose secrets
- Make outbound network calls except to approved services

All MCP tools are allowlisted. Deny-by-default policy applies.

## Risk Model

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| AI agent writes bad content to canonical vault | Medium | High | Buffer vault + approval gate; agents never mount canonical vault |
| Capture API exposed publicly | Low | Critical | Tailscale-only listener, no port forwarding, no public webhooks |
| Processor container escapes | Low | Critical | `read_only` rootfs, `cap_drop: ALL`, non-root, no Docker socket |
| Secret leakage through capture content | Medium | High | QA Verifier checks for secrets; review packet includes secret scan |
| Media files fill disk | High | Medium | Media archive policy, size limits, storage monitoring |
| Duplicate capture flooding | Medium | Medium | Duplicate detector, rate limiting, idempotency keys |
| Review packet approval fatigue | Medium | Medium | Batch review, auto-approve low-risk captures (future), clear UX |
| Transcript hallucination by Whisper | High | Low | All transcripts marked `machine_generated_unverified`; human review required |
| Processor queue backlog | Medium | Medium | Queue monitoring, retry with backoff, dead letter queue |

## Rollback Model

1. **Capture rollback:** Delete or move failed capture from buffer vault. Queue marks as failed. Event logged.
2. **Processor rollback:** Re-process capture with different parameters or processor version. Processor outputs are idempotent by capture ID.
3. **Agent rollback:** Delete agent outputs in buffer vault. Re-run agent with corrected parameters. Agent outputs are idempotent by capture ID.
4. **Import rollback:** If import was approved but is wrong, the import manifest serves as a change log. Revert by deleting or moving the imported files from canonical vault. Buffer vault copy retained for re-import after correction.
5. **Full pipeline rollback:** Stop processors. Drain queue. Inspect buffer vault. No canonical vault writes occur without approval, so full pipeline rollback is always safe.

No rollback deletes event log entries — events are append-only. Rollback events are logged as new events with references to the rolled-back capture.
