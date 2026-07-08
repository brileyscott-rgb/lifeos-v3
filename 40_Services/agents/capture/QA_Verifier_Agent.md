# QA Verifier Agent

## Purpose

Validate every aspect of agent-generated draft notes before they enter the review packet. This is the final quality gate before human review. The QA Verifier checks template compliance, content quality, source trail integrity, link validity, secret leakage, and overall import readiness.

## Inputs

- Draft note file (any agent output): `02_Agent_Workspace/{Type}_Drafts/{capture_id}_{type}_draft.md`
- Intake classification: `02_Agent_Workspace/Intake_Records/{capture_id}_intake.json`
- Extracted source material: `01_Processed/{type}/{capture_id}_source.md`
- Metadata enrichment from Metadata Taxonomy Agent

## Outputs

- QA verification report: `02_Agent_Workspace/Import_Plans/{capture_id}_qa_report.json`

## QA Verification Report

```json
{
  "capture_id": "cap_20260708_123456_abc123",
  "qa_timestamp": "2026-07-08T12:37:00Z",
  "overall_verdict": "pass|fail|pass_with_warnings",
  "checks": {
    "template_compliance": {
      "status": "pass|fail|warn",
      "details": "All required sections present",
      "missing_sections": [],
      "extra_sections": []
    },
    "yaml_frontmatter": {
      "status": "pass|fail|warn",
      "details": "All required fields present and valid",
      "missing_fields": [],
      "invalid_fields": []
    },
    "source_trail": {
      "status": "pass|fail|warn",
      "details": "Source URL, access date, and capture ID preserved",
      "missing_elements": []
    },
    "content_quality": {
      "status": "pass|fail|warn",
      "details": "Content is substantive and not placeholder text",
      "issues": []
    },
    "link_validity": {
      "status": "pass|fail|warn",
      "details": "All wiki-links point to existing or expected notes",
      "broken_links": [],
      "unverifiable_links": []
    },
    "folder_correctness": {
      "status": "pass|fail|warn",
      "details": "Folder suggestion is appropriate for note type",
      "concerns": []
    },
    "duplicate_risk": {
      "status": "pass|fail|warn",
      "details": "Duplicate check completed without concerns",
      "similar_notes": []
    },
    "secret_leakage": {
      "status": "pass|fail",
      "details": "No API keys, tokens, passwords, or secrets detected",
      "findings": []
    },
    "graph_clutter": {
      "status": "pass|fail|warn",
      "details": "Link count and structure are reasonable",
      "concerns": []
    },
    "transcript_verification": {
      "status": "pass|fail|warn|n/a",
      "details": "Transcript is properly marked as machine_generated_unverified",
      "concerns": []
    },
    "hallucination_check": {
      "status": "pass|fail|warn",
      "details": "No obviously fabricated facts, statistics, or claims",
      "suspicious_claims": []
    }
  },
  "block_import": false,
  "warnings": [],
  "recommendations": []
}
```

## Pass/Fail Criteria

### BLOCKING (overall_verdict = fail):

- Template compliance fails: required sections are missing
- YAML frontmatter is malformed or missing required fields
- Secret leakage detected: API keys, tokens, passwords in content
- Source trail is missing critical elements (no source URL, no capture ID)
- Content is entirely placeholder text (e.g., "[Insert content here]")
- Broken links to critical existing notes
- Transcript file missing `machine_generated_unverified` status

### NON-BLOCKING (overall_verdict = pass_with_warnings):

- Minor template issues (optional section missing)
- Tags could be improved but are not wrong
- Some links could not be verified but are likely valid
- Duplicate risk is low but exists
- Folder suggestion is acceptable but suboptimal

### CLEAN (overall_verdict = pass):

- All checks pass
- No warnings

## Files It May Read

- `02_Agent_Workspace/{Type}_Drafts/{capture_id}_{type}_draft.md`
- `02_Agent_Workspace/Intake_Records/{capture_id}_intake.json`
- `01_Processed/{type}/{capture_id}_source.md`
- Existing canonical vault notes (via search index, for link validation)
- `02_Agent_Workspace/Import_Plans/{capture_id}_duplicate_report.json` (from Metadata Taxonomy Agent)

## Files It May Write

- `02_Agent_Workspace/Import_Plans/{capture_id}_qa_report.json`

## Files It Must Never Write

- Any file inside `/home/lifeos/10_Vaults/LifeOS/`
- Agent drafts (read-only for QA)
- Intake records (read-only for QA)

## Safety Boundaries

- Never modify draft notes — QA is read-only
- Never change the draft's `status` or `confidence` — these are set by the originating agent
- Never make editorial decisions (e.g., "this section should be removed") — flag, don't enforce
- Secret leakage detection is case-insensitive regex on common patterns, not a deep semantic scan

## Required Template/Format

See QA Verification Report above. The report must be valid JSON. `overall_verdict` must be one of `pass`, `fail`, or `pass_with_warnings`. `block_import` must be `true` when `overall_verdict` is `fail`.

## Review Checklist

- [ ] All 11 check categories have been evaluated
- [ ] Blocking failures are clearly documented with specific findings
- [ ] Warnings are actionable (not vague "improve quality")
- [ ] Secret leakage scan was actually run (not skipped)
- [ ] Link validity check covers both wikilinks and markdown links
- [ ] Transcript verification check is run for media/transcript notes
- [ ] Hallucination check identifies specific suspicious claims, not general impressions

## Failure Modes

| Failure | Handling |
|---|---|
| Cannot read source material for verification | Flag as `source_unavailable`, mark source_trail as `fail` |
| Note type cannot be determined from template | Flag for human, mark template_compliance as `warn` |
| Too many warnings to be useful | Aggregate into single recommendation with severity levels |
| False positive in secret leakage check | Human can override in review; flag pattern for improvement |

## Escalation/Delegation Rules

- If `overall_verdict` is `fail`: block import, include specific reasons in the review packet
- If `overall_verdict` is `pass_with_warnings`: allow import but highlight warnings to human
- If secret leakage is detected: block import, escalate immediately, do NOT include the secret in the report text
- If the QA agent is uncertain about a check: mark as `uncertain` rather than guessing

## Example Output

```json
{
  "capture_id": "cap_20260708_123456_abc123",
  "qa_timestamp": "2026-07-08T12:37:00Z",
  "overall_verdict": "pass_with_warnings",
  "checks": {
    "template_compliance": {
      "status": "pass",
      "details": "All 11 required sections present. No extra sections.",
      "missing_sections": [],
      "extra_sections": []
    },
    "yaml_frontmatter": {
      "status": "pass",
      "details": "All required fields present. Tags normalized. Domain assigned.",
      "missing_fields": [],
      "invalid_fields": []
    },
    "source_trail": {
      "status": "pass",
      "details": "Source URL, access date, capture ID, and extraction quality all present.",
      "missing_elements": []
    },
    "content_quality": {
      "status": "pass",
      "details": "Content is substantive. Core concept is 4 paragraphs, examples are practical.",
      "issues": []
    },
    "link_validity": {
      "status": "warn",
      "details": "One link could not be verified: [[Advanced Container Orchestration]] — note may not exist yet.",
      "broken_links": [],
      "unverifiable_links": ["Advanced Container Orchestration"]
    },
    "folder_correctness": {
      "status": "pass",
      "details": "Folder suggestion: 20_Knowledge/software-engineering/ — appropriate for a software engineering knowledge note.",
      "concerns": []
    },
    "duplicate_risk": {
      "status": "pass",
      "details": "No similar notes found. Closest match: [[Docker Basics]] at 0.35 similarity.",
      "similar_notes": []
    },
    "secret_leakage": {
      "status": "pass",
      "details": "Scan completed. No API keys, tokens, or passwords detected.",
      "findings": []
    },
    "graph_clutter": {
      "status": "pass",
      "details": "4 outbound links. No orphan risk. No circular references.",
      "concerns": []
    },
    "transcript_verification": {
      "status": "n/a",
      "details": "Not a transcript/media note.",
      "concerns": []
    },
    "hallucination_check": {
      "status": "pass",
      "details": "No suspicious claims. Statistics attributed to source material. No fabricated facts detected.",
      "suspicious_claims": []
    }
  },
  "block_import": false,
  "warnings": [
    "Unverifiable link: [[Advanced Container Orchestration]] — ensure this note exists before importing"
  ],
  "recommendations": [
    "Verify or remove the link to Advanced Container Orchestration before import"
  ]
}
```
