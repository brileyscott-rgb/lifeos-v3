# Capture Review Packet Format

Status: architecture/scaffold
Created: 2026-07-08
Purpose: define the standard review packet format presented to the human operator for approval before any canonical LifeOS vault import.

## Overview

A review packet is the final artifact produced by the Agentic Capture Pipeline before human approval. It bundles all processing results into a single, inspectable document that the operator can review, approve, reject, or request changes to.

## Required Sections

Every review packet must include:

| Section | Required | Purpose |
|---|---|---|
| Capture Summary | Yes | Capture ID, source, type, status, processing timeline |
| Proposed Changes | Yes | Exact files to create, update, or not touch |
| Agent Outputs | Yes | Draft content from all contributing agents |
| Summary of Changes | Yes | Human-readable summary of what this import does |
| Source Trail | Yes | Traceability from capture to import |
| Risks | Yes | Known risks, caveats, and concerns |
| QA Result | Yes | Verifier verdict and details |
| Human Approval Checklist | Yes | Explicit checklist for the operator |
| Import Command/Procedure | Yes | How to execute the import |
| Rollback Procedure | Yes | How to reverse the import if needed |

## Full Template

```markdown
# Review Packet: [Capture Title]

## Capture Summary
- **Capture ID:** cap_YYYYMMDD_HHMMSS_rand_slug
- **Source:** [Telegram | HTTP Shortcuts | Bookmarklet | Desktop | n8n | MCP]
- **Source Type:** [text | url_article | url_video | url_audio | image | pdf | github_repo | voice_memo | etc.]
- **Original Content Preview:** [first 200 chars or description]
- **Processing Status:** ready_for_review
- **Agent Route:** [knowledge_note | project | idea | reference | media_transcript]
- **Captured:** 2026-07-08T12:34:00Z
- **Processed:** 2026-07-08T12:36:00Z
- **Ready for Review:** 2026-07-08T12:37:00Z

## Proposed Changes

### Files to Create

| File | Destination Path | Type | Size |
|---|---|---|---|
| [filename] | `[canonical_vault_path]` | [note_type] | ~[size] |

### Files to Update

| File | Path | Change Description |
|---|---|---|
| [filename] | `[canonical_vault_path]` | [what changed and why] |

### Files Explicitly Not Touched
- All other files in the canonical vault
- [Any specific files that could have been affected but are explicitly preserved]

## Agent Outputs

### [Agent Name] Output

[Full or summarized content of the draft note/file produced by this agent]

---

[Repeat for each contributing agent]

## Summary of Changes

[2-5 sentences describing what this import does:
- What new content is added to the vault
- What existing content is updated
- Why this matters or what gap it fills
- How it relates to existing vault content]

## Source Trail

- **Original Capture:** cap_YYYYMMDD_HHMMSS_rand_slug
- **Capture Channel:** [source]
- **Source URL:** [URL if applicable]
- **Source Author:** [if known]
- **Source Date:** [if known]
- **Access Date:** [when the source was retrieved]
- **Extraction Quality:** [full | partial | failed]
- **Extraction Engine:** [processor name and version]
- **Agent Processing Chain:** Intake → Source Extraction → [agent] → Metadata → QA → Import Planner

## Risks

| Risk | Severity | Description | Mitigation |
|---|---|---|---|
| [risk name] | low/medium/high | [description] | [how it's addressed] |

## QA Result

- **Verdict:** [pass | pass_with_warnings | fail]
- **Blocking Issues:** [count or "None"]
- **Warnings:** [count or "None"]
- **QA Report:** [summary of key findings]
- **Full QA Report:** [reference to qa_report.json]

## Human Approval Checklist

- [ ] Content is accurate and reflects the source material
- [ ] Folder/vault placement is correct
- [ ] Links are valid or intentionally forward-looking
- [ ] No secrets, API keys, passwords, or personal information exposed
- [ ] Template follows LifeOS standards for the note type
- [ ] Tags, aliases, and domain are appropriate
- [ ] Note adds value beyond the original source (synthesis, not copy)
- [ ] No duplicate content with existing vault notes
- [ ] For transcripts: machine_generated_unverified status is preserved
- [ ] Rollback procedure is understood and testable

## Approval Decision

- **Decision:** [ ] Approve — [ ] Reject — [ ] Request Changes
- **Approved By:** [operator]
- **Approved At:** [timestamp]
- **Notes:** [any additional context]

## Import Command

```bash
# Execute the import:
lifeos-import approve cap_YYYYMMDD_HHMMSS_rand_slug

# Or via API:
curl -X POST http://localhost:8788/imports/{capture_id}/approve
```

## Rollback Procedure

```bash
# Reverse the import:
lifeos-import rollback cap_YYYYMMDD_HHMMSS_rand_slug

# This will:
# 1. Delete files created during this import from canonical vault
# 2. Revert any file updates to pre-import state
# 3. Log the rollback to the event log
# 4. Preserve all buffer vault artifacts for re-import if needed
```

## Appendix: Full Import Manifest

```json
[import manifest JSON for machine consumption]
```
```

## Example 1: Knowledge Note Import

```markdown
# Review Packet: Container Security Best Practices

## Capture Summary
- **Capture ID:** cap_20260708_123456_abc123
- **Source:** Telegram
- **Source Type:** url_article
- **Original Content Preview:** Check out this article about container security: https://example.com/container-security-best-practices
- **Processing Status:** ready_for_review
- **Agent Route:** knowledge_note
- **Captured:** 2026-07-08T12:34:00Z
- **Processed:** 2026-07-08T12:36:00Z
- **Ready for Review:** 2026-07-08T12:37:00Z

## Proposed Changes

### Files to Create

| File | Destination Path | Type | Size |
|---|---|---|---|
| Container Security Best Practices.md | `20_Knowledge/software-engineering/` | knowledge_note | ~3.2 KB |

### Files to Update
None

### Files Explicitly Not Touched
- All other files in the canonical vault

## Agent Outputs

### Knowledge Note Agent Output
[A standard LifeOS Knowledge note with: Definition, Why It Matters, Core Concept, How It Works, Examples, LifeOS Relationships, Safety/Caveats, Common Problems, Related Concepts, Source Trail]

## Summary of Changes
A new Knowledge note on Container Security Best Practices will be created in the software-engineering domain. The note synthesizes a single source article into the LifeOS Knowledge standard, including practical examples and LifeOS-specific relationship links. This addresses a gap in the vault's container security coverage.

## Source Trail
- **Original Capture:** cap_20260708_123456_abc123
- **Capture Channel:** Telegram
- **Source URL:** https://example.com/container-security-best-practices
- **Source Author:** Jane Author
- **Source Date:** 2026-06-15
- **Access Date:** 2026-07-08T12:35:00Z
- **Extraction Quality:** full
- **Extraction Engine:** article_processor_v1
- **Agent Processing Chain:** Intake → Source Extraction → Knowledge Note → Metadata → QA → Import Planner

## Risks

| Risk | Severity | Description | Mitigation |
|---|---|---|---|
| Unverifiable link | Low | [[Advanced Container Orchestration]] may not exist yet | Link is forward-looking; will resolve when note is created |

## QA Result
- **Verdict:** pass_with_warnings
- **Blocking Issues:** None
- **Warnings:** 1 (unverifiable link)
- **QA Report:** All template sections present. Source trail complete. No secrets detected. One link could not be verified.

## Human Approval Checklist
- [ ] Content accurately reflects the source article
- [ ] Folder placement (`20_Knowledge/software-engineering/`) is correct
- [ ] Link to [[Advanced Container Orchestration]] is intentional
- [ ] No secrets or personal information in the note
- [ ] Template follows the LifeOS Knowledge note standard
- [ ] Note adds value beyond the original source (synthesis, not just copy)

## Import Command
```bash
lifeos-import approve cap_20260708_123456_abc123
```

## Rollback Procedure
```bash
lifeos-import rollback cap_20260708_123456_abc123
# Deletes: 10_Vaults/LifeOS/20_Knowledge/software-engineering/Container Security Best Practices.md
# All buffer vault artifacts preserved.
```
```

## Example 2: Project Scaffold Import

```markdown
# Review Packet: Home Automation Dashboard

## Capture Summary
- **Capture ID:** cap_20260708_140000_def456
- **Source:** Telegram
- **Source Type:** text
- **Original Content Preview:** I want to build a dashboard for my home automation system. ESP32 sensors, MQTT broker, and a simple web UI. Maybe integrate with Home Assistant later.
- **Processing Status:** ready_for_review
- **Agent Route:** project
- **Captured:** 2026-07-08T14:00:00Z
- **Processed:** 2026-07-08T14:05:00Z
- **Ready for Review:** 2026-07-08T14:07:00Z

## Proposed Changes

### Files to Create

| File | Destination Path | Type |
|---|---|---|
| Home Automation Dashboard.md | `30_Projects/Incubating/home-automation-dashboard/` | project_main |
| AI_Context.md | `30_Projects/Incubating/home-automation-dashboard/` | project_ai_context |
| Architecture.md | `30_Projects/Incubating/home-automation-dashboard/` | project_architecture |
| Implementation_Plan.md | `30_Projects/Incubating/home-automation-dashboard/` | project_implementation |
| Testing_Checklist.md | `30_Projects/Incubating/home-automation-dashboard/` | project_testing |
| Risks.md | `30_Projects/Incubating/home-automation-dashboard/` | project_risks |
| Next_Actions.md | `30_Projects/Incubating/home-automation-dashboard/` | project_actions |
| BOM.md | `30_Projects/Incubating/home-automation-dashboard/` | project_bom |
| Wiring.md | `30_Projects/Incubating/home-automation-dashboard/` | project_wiring |
| References.md | `30_Projects/Incubating/home-automation-dashboard/` | project_references |

### Files to Update
None

### Files Explicitly Not Touched
- All other files in the canonical vault

## Agent Outputs

### Project Note Agent Output
[10 files: main_note with goal/motivation/scope, AI_Context with project background, Architecture with ESP32 + MQTT + web UI design, Implementation_Plan phased approach, Testing_Checklist, Risks, Next_Actions, BOM with ESP32 and sensor list, Wiring with pinout diagram description, References with MQTT and ESP32 docs]

**Critical:** No fake build results. No fabricated test pass/fail. No claimed hardware validation. All files are draft templates for the operator to populate.

## Summary of Changes
A new hardware/software project "Home Automation Dashboard" will be scaffolded in the Incubating folder. The project uses ESP32 sensors communicating over MQTT with a web UI dashboard. Ten scaffold files provide the complete LifeOS project template. No code is written, no hardware is claimed to exist.

## Source Trail
- **Original Capture:** cap_20260708_140000_def456
- **Capture Channel:** Telegram
- **Source URL:** N/A (personal idea)
- **Extraction Quality:** N/A
- **Agent Processing Chain:** Intake → Project Note → Metadata → QA → Import Planner

## Risks

| Risk | Severity | Description | Mitigation |
|---|---|---|---|
| Project scope unclear | Medium | Original capture is vague on specifics | Scaffold is minimal; operator fills details |
| MQTT broker choice | Low | No specific broker selected | Operator decides Mosquitto vs EMQX vs cloud |
| Hardware unvalidated | Low | BOM is suggested, not validated | Operator verifies component compatibility |

## QA Result
- **Verdict:** pass
- **Blocking Issues:** None
- **Warnings:** None
- **QA Report:** All required files present. No fabricated claims. Templates are complete. Hardware files present (BOM, Wiring) — appropriate for project type.

## Human Approval Checklist
- [ ] Project scope and goal are acceptable
- [ ] Folder placement (`30_Projects/Incubating/`) is appropriate
- [ ] BOM components are reasonable (operator to validate)
- [ ] No fabricated build results or test claims
- [ ] Templates follow LifeOS project standards
- [ ] No duplicate with existing projects

## Import Command
```bash
lifeos-import approve cap_20260708_140000_def456
```

## Rollback Procedure
```bash
lifeos-import rollback cap_20260708_140000_def456
# Deletes the entire home-automation-dashboard/ folder from canonical vault
```
```

## Example 3: Idea Note Import

```markdown
# Review Packet: Daily Habitat Score Tracker

## Capture Summary
- **Capture ID:** cap_20260708_150000_ghi789
- **Source:** Telegram
- **Source Type:** text
- **Original Content Preview:** what if i had a daily habitat score that tracked how aligned my day was? nothing heavy, just a simple check-in
- **Processing Status:** ready_for_review
- **Agent Route:** idea
- **Captured:** 2026-07-08T15:00:00Z
- **Processed:** 2026-07-08T15:02:00Z
- **Ready for Review:** 2026-07-08T15:04:00Z

## Proposed Changes

### Files to Create

| File | Destination Path | Type |
|---|---|---|
| Daily Habitat Score Tracker.md | `40_Ideas/lifeos/` | idea_note |

### Files to Update
None

### Files Explicitly Not Touched
- All other files in the vault

## Agent Outputs

### Idea Agent Output
[Lightweight idea note: The Spark, Why It Might Matter, What It Would Look Like, What's Needed, Related Ideas/Projects, Obstacles/Concerns, measurable Promotion Criteria]

**Critical:** This is an idea, not a project. No implementation plan, BOM, architecture, or next actions. Promotion criteria are concrete and measurable.

## Summary of Changes
A new idea note will be created in the LifeOS ideas folder. The note captures the concept of a daily habitat score tracker — a lightweight self-observation tool. Promotion criteria define when this idea is ready to become a project.

## Source Trail
- **Original Capture:** cap_20260708_150000_ghi789
- **Capture Channel:** Telegram
- **Source URL:** N/A (personal idea)
- **Agent Processing Chain:** Intake → Idea → Metadata → QA → Import Planner

## Risks

| Risk | Severity | Description | Mitigation |
|---|---|---|---|
| Overlap with existing habit trackers | Low | Idea may duplicate existing tools | Promotion criteria include scope definition |

## QA Result
- **Verdict:** pass
- **Blocking Issues:** None
- **Warnings:** None
- **QA Report:** Idea is appropriately lightweight. Promotion criteria are measurable (not vague). No overbuilding detected.

## Human Approval Checklist
- [ ] Idea is worth preserving in the vault
- [ ] Promotion criteria are reasonable and measurable
- [ ] Not better suited as a Reference or Project note
- [ ] No overbuilding (it's an idea, not a disguised project)

## Import Command
```bash
lifeos-import approve cap_20260708_150000_ghi789
```

## Rollback Procedure
```bash
lifeos-import rollback cap_20260708_150000_ghi789
# Deletes: 10_Vaults/LifeOS/40_Ideas/lifeos/Daily Habitat Score Tracker.md
```
```

## Example 4: Reference Note Import

```markdown
# Review Packet: Docker Networking Deep Dive (Reference)

## Capture Summary
- **Capture ID:** cap_20260708_160000_jkl012
- **Source:** HTTP Shortcuts
- **Source Type:** url_video
- **Original Content Preview:** https://youtube.com/watch?v=docker-networking-deep-dive
- **Processing Status:** ready_for_review
- **Agent Route:** reference
- **Captured:** 2026-07-08T16:00:00Z
- **Processed:** 2026-07-08T16:10:00Z
- **Ready for Review:** 2026-07-08T16:15:00Z

## Proposed Changes

### Files to Create

| File | Destination Path | Type |
|---|---|---|
| Docker Networking Deep Dive.md | `50_References/software-engineering/` | reference_note |

### Files to Update
None

### Files Explicitly Not Touched
- All other files in the vault

## Agent Outputs

### Reference Agent Output
[A reference note with: Source Summary, Key Claims/Takeaways, Why I Saved This, Related Topics, Route Suggestions, Source trail]

## Summary of Changes
A reference note for a Docker networking video will be created. It preserves source metadata, key takeaways, and personal context for why this was saved. It's a reference — not a Knowledge note — because it primarily bookmarks and summarizes external content rather than synthesizing it into a standalone concept explanation.

## Source Trail
- **Original Capture:** cap_20260708_160000_jkl012
- **Capture Channel:** HTTP Shortcuts
- **Source URL:** https://youtube.com/watch?v=docker-networking-deep-dive
- **Extraction Quality:** partial (video transcript used)
- **Extraction Engine:** whisper_transcript_processor
- **Agent Processing Chain:** Intake → Source Extraction → Media Transcript → Reference → Metadata → QA → Import Planner

## Risks

| Risk | Severity | Description | Mitigation |
|---|---|---|---|
| Transcript accuracy | Medium | Key claims drawn from unverified transcript | Note marked as reference (not factual knowledge); source link preserved for verification |

## QA Result
- **Verdict:** pass
- **Blocking Issues:** None
- **Warnings:** None
- **QA Report:** Reference format correct. Source trail complete. Content is appropriately lightweight for a reference note.

## Human Approval Checklist
- [ ] Reference is worth keeping in the vault
- [ ] Key claims appear accurate based on the source
- [ ] "Why I Saved This" provides useful context
- [ ] Route suggestions are reasonable

## Import Command
```bash
lifeos-import approve cap_20260708_160000_jkl012
```

## Rollback Procedure
```bash
lifeos-import rollback cap_20260708_160000_jkl012
# Deletes: 10_Vaults/LifeOS/50_References/software-engineering/Docker Networking Deep Dive.md
```
```

## Example 5: Media/Transcript Import

```markdown
# Review Packet: Docker Networking Deep Dive (Transcript)

## Capture Summary
- **Capture ID:** cap_20260708_160000_jkl012
- **Source:** HTTP Shortcuts
- **Source Type:** url_video
- **Original Content Preview:** https://youtube.com/watch?v=docker-networking-deep-dive
- **Processing Status:** ready_for_review
- **Agent Route:** media_transcript
- **Captured:** 2026-07-08T16:00:00Z
- **Processed:** 2026-07-08T16:10:00Z
- **Ready for Review:** 2026-07-08T16:15:00Z

## Proposed Changes

### Files to Create

| File | Destination Path | Type |
|---|---|---|
| Docker Networking Deep Dive (Transcript).md | `50_References/Media/` | media_transcript |

### Files to Update
None

### Files Explicitly Not Touched
- All other files in the vault
- Media file: LifeOS_Media_Archive/videos/2026/07/cap_20260708_160000_jkl012_docker-networking.mp4 (stays in media archive)

## Agent Outputs

### Media Transcript Agent Output
[Media note with: Media Info (type, duration, source), Summary, Key Points, Timestamps, Transcript Status (MACHINE_GENERATED_UNVERIFIED with prominent warning), Related Notes, Source Trail]

## Summary of Changes
A transcript note for a 32-minute Docker networking video will be imported into the Media references folder. The media file itself remains in the LifeOS Media Archive and is NOT imported into the vault. The transcript is machine-generated and prominently marked as unverified.

## Source Trail
- **Original Capture:** cap_20260708_160000_jkl012
- **Capture Channel:** HTTP Shortcuts
- **Source URL:** https://youtube.com/watch?v=docker-networking-deep-dive
- **Media File:** LifeOS_Media_Archive/videos/2026/07/cap_20260708_160000_jkl012_docker-networking.mp4
- **Transcript Engine:** whisper-large-v3
- **Transcript Status:** machine_generated_unverified
- **Agent Processing Chain:** Intake → Source Extraction → Media Transcript → Metadata → QA → Import Planner

## Risks

| Risk | Severity | Description | Mitigation |
|---|---|---|---|
| Transcript accuracy | Medium | Whisper may have errors in technical terms, commands, IP addresses | Prominent unverified warning; source video preserved for verification |
| Media file size | Low | Video is 180 MB in media archive | Media archive policy applies; vault only gets the transcript |

## QA Result
- **Verdict:** pass
- **Blocking Issues:** None
- **Warnings:** None
- **QA Report:** Transcript status properly marked as machine_generated_unverified. Warning is prominent. Media links use relative paths. Timestamps appear to match 32-minute duration.

## Human Approval Checklist
- [ ] Transcript warning is visible and appropriate
- [ ] Key points appear accurate based on the source topic
- [ ] Timestamps are reasonable for the content
- [ ] Media file link is correct
- [ ] This transcript adds value to the vault

## Import Command
```bash
lifeos-import approve cap_20260708_160000_jkl012
```

## Rollback Procedure
```bash
lifeos-import rollback cap_20260708_160000_jkl012
# Deletes: 10_Vaults/LifeOS/50_References/Media/Docker Networking Deep Dive (Transcript).md
# Media file in LifeOS_Media_Archive is NOT deleted (managed separately)
```
```
