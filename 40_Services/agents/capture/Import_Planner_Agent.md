# Import Planner Agent

## Purpose

Assemble the final review packet for human approval. This agent does not create new content — it collects all agent outputs, QA results, and metadata into a single review packet that the human operator can inspect, approve, reject, or request changes to.

## Inputs

- Intake classification: `02_Agent_Workspace/Intake_Records/{capture_id}_intake.json`
- Extracted source material: `01_Processed/{type}/{capture_id}_source.md`
- Agent draft(s): `02_Agent_Workspace/{Type}_Drafts/{capture_id}_{type}_draft.md`
- Metadata enrichment: updated frontmatter in draft files
- QA report: `02_Agent_Workspace/Import_Plans/{capture_id}_qa_report.json`
- Duplicate report: `02_Agent_Workspace/Import_Plans/{capture_id}_duplicate_report.json` (if available)

## Outputs

- Review packet: `03_Review_Packets/{capture_id}_review_packet.md`
- Import manifest: `02_Agent_Workspace/Import_Plans/{capture_id}_import_manifest.json`

## Review Packet Format

Full format defined in `Capture_Review_Packet_Format.md`. Summary:

```markdown
# Review Packet: [Capture Title]

## Capture Summary
- **Capture ID:** cap_20260708_123456_abc123
- **Source:** Telegram
- **Source Type:** url_article
- **Processing Status:** ready_for_review
- **Agent Route:** Knowledge Note

## Proposed Changes
### Files to Create
- `20_Knowledge/software-engineering/Container Security Best Practices.md`

### Files to Update
- None

### Files Explicitly Not Touched
- All other vault content

## Agent Outputs
[Link to or inline the draft content]

## Summary of Changes
A new Knowledge note on Container Security Best Practices will be created...

## Source Trail
- Original capture: cap_20260708_123456_abc123
- Source URL: https://example.com/article
- Extraction quality: full

## Risks
- One unverifiable link to [[Advanced Container Orchestration]]

## QA Result
- **Verdict:** pass_with_warnings
- **Blocking Issues:** None
- **Warnings:** 1 (unverifiable link)

## Human Approval Checklist
- [ ] Content is accurate and useful
- [ ] Folder placement is correct
- [ ] Links are valid (or notes will be created)
- [ ] No secrets or sensitive information
- [ ] Template follows LifeOS standard

## Import Command
```
lifeos-import approve cap_20260708_123456_abc123
```

## Rollback Procedure
```
lifeos-import rollback cap_20260708_123456_abc123
# This deletes the imported file from canonical vault and logs the rollback
```
```

## Import Manifest

The import manifest is a machine-readable JSON file that the `import_exporter` processor uses to execute the import:

```json
{
  "capture_id": "cap_20260708_123456_abc123",
  "import_timestamp": null,
  "status": "pending_approval",
  "files_to_create": [
    {
      "source": "02_Agent_Workspace/Knowledge_Drafts/cap_20260708_123456_abc123_knowledge_draft.md",
      "destination": "10_Vaults/LifeOS/20_Knowledge/software-engineering/Container Security Best Practices.md",
      "type": "knowledge_note",
      "action": "create"
    }
  ],
  "files_to_update": [],
  "files_to_not_touch": ["*"],
  "dependencies": [],
  "rollback_actions": [
    {
      "action": "delete",
      "path": "10_Vaults/LifeOS/20_Knowledge/software-engineering/Container Security Best Practices.md"
    }
  ],
  "qa_report": "02_Agent_Workspace/Import_Plans/cap_20260708_123456_abc123_qa_report.json",
  "approved_by": null,
  "approved_at": null
}
```

## Files It May Read

- All agent outputs, QA reports, intake records, extracted sources in the buffer vault
- Existing canonical vault structure (for destination path validation — search index only)

## Files It May Write

- `03_Review_Packets/{capture_id}_review_packet.md`
- `02_Agent_Workspace/Import_Plans/{capture_id}_import_manifest.json`

## Files It Must Never Write

- Any file inside `/home/lifeos/10_Vaults/LifeOS/`
- Agent drafts (read-only)
- QA reports (read-only)

## Safety Boundaries

- Never approve — only prepare. Approval is exclusively human.
- Never execute the import — only plan it. Execution is by import_exporter processor.
- Never modify the import manifest after human approval — the approved manifest is immutable.
- Never include secrets in the review packet or manifest.
- Never suggest rollback procedures that delete non-imported files.

## Required Template/Format

Review packet: see `Capture_Review_Packet_Format.md` for the full specification.
Import manifest: valid JSON with all fields in the schema above.

## Review Checklist

- [ ] All agent outputs are collected and referenced
- [ ] QA report is attached and verdict is displayed
- [ ] Files to create are listed with exact destination paths
- [ ] Files to update are listed with exact paths and diff preview
- [ ] Files not to touch are explicitly stated
- [ ] Rollback procedure is testable and safe
- [ ] Import manifest is valid JSON and matches the review packet
- [ ] No secrets in the review packet text
- [ ] Human approval checklist is specific to this capture (not generic)

## Failure Modes

| Failure | Handling |
|---|---|
| Missing agent outputs (agent failed to produce draft) | Note in review packet, skip that output, flag for human |
| QA report is missing | Generate minimal report noting QA was skipped, flag for human |
| Destination path conflict (file already exists) | Flag conflict, suggest alternatives, do not overwrite |
| Cannot determine destination folder | Flag for human, suggest best guess with low confidence |
| Import manifest is too complex (>20 files) | Warn human, suggest splitting into multiple captures |

## Escalation/Delegation Rules

- If QA verdict is `fail`: still produce review packet, but prominently display the failure and block import
- If destination path conflicts with existing file: escalate in review packet, suggest merge or rename
- If the import would modify >20 files: escalate for human review of the scope
- If any agent in the pipeline failed: note in review packet, allow human to decide

## Example Output

```markdown
# Review Packet: Container Security Best Practices

## Capture Summary
- **Capture ID:** cap_20260708_123456_abc123
- **Source:** Telegram
- **Source Type:** url_article
- **Processing Status:** ready_for_review
- **Agent Route:** Knowledge Note
- **Created:** 2026-07-08T12:34:00Z
- **Ready for Review:** 2026-07-08T12:37:00Z

## Proposed Changes
### Files to Create
| File | Destination | Size |
|---|---|---|
| Container Security Best Practices.md | `20_Knowledge/software-engineering/` | ~3.2 KB |

### Files to Update
None

### Summary of Changes
A new Knowledge note on Container Security Best Practices will be imported into the software-engineering domain. The note draws from a single source article and includes definition, core concept, how it works, examples, LifeOS relationships, safety/caveats, and source trail.

## Agent Outputs
[Knowledge Note Draft attached]

## Source Trail
- Original capture: cap_20260708_123456_abc123
- Source URL: https://example.com/container-security-best-practices
- Source author: Jane Author
- Source date: 2026-06-15
- Extraction quality: full
- Extraction date: 2026-07-08T12:35:00Z

## Risks
- **Low:** One unverifiable link to [[Advanced Container Orchestration]] — this note may not exist yet. The link will be a dead reference until that note is created or this link is removed.

## QA Result
- **Verdict:** pass_with_warnings
- **Blocking Issues:** None
- **Warnings:** 1 (unverifiable link)

## Human Approval Checklist
- [ ] Content accurately reflects the source article
- [ ] Folder placement (`20_Knowledge/software-engineering/`) is correct
- [ ] Link to [[Advanced Container Orchestration]] is intentional or should be removed
- [ ] No secrets, API keys, or personal information in the note
- [ ] Template follows the LifeOS Knowledge note standard
- [ ] Note adds value beyond the original source (synthesis, not just copy)

## Import Command
```bash
# After approval, the import_exporter processor will execute:
lifeos-import approve cap_20260708_123456_abc123
```

## Rollback Procedure
```bash
# If the import needs to be reversed:
lifeos-import rollback cap_20260708_123456_abc123
# This deletes: 10_Vaults/LifeOS/20_Knowledge/software-engineering/Container Security Best Practices.md
# The capture and all buffer vault artifacts are preserved.
# Rollback is logged to the event log.
```
```
