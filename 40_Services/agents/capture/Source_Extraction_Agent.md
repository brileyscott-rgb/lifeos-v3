# Source Extraction Agent

## Purpose

Extract clean, structured source material from raw captures. Handle URL fetching, article text extraction, PDF parsing, GitHub repo cloning, media downloading, and attachment processing. Produce clean intermediate files that downstream agents can work with.

## Inputs

- Intake classification record: `02_Agent_Workspace/Intake_Records/{capture_id}_intake.json`
- Raw capture data from `00_Raw/captures.jsonl`
- Raw attachment files in `00_Raw/attachments/{capture_id}/`

## Outputs

- Extracted source material: `01_Processed/{type}/{capture_id}_source.md`

The extracted source file contains:
```markdown
---
capture_id: cap_20260708_123456_abc123
source_url: https://example.com/article
source_type: article
extraction_engine: article_processor_v1
extraction_timestamp: 2026-07-08T12:35:00Z
source_title: Container Security Best Practices
source_author: Jane Author
source_date: 2026-06-15
source_domain: example.com
extraction_quality: full
---

# Container Security Best Practices

[Extracted clean text content]

---
Source extracted by Source Extraction Agent.
Original URL: https://example.com/article
Access date: 2026-07-08T12:35:00Z
```

## Extraction Delegation

The agent delegates actual extraction to the appropriate processor:

| Source Type | Processor | Output Location |
|---|---|---|
| URL (article) | `article_processor` | `01_Processed/articles/` |
| URL (webpage) | `web_clipper_processor` | `01_Processed/articles/` |
| PDF | `pdf_processor` | `01_Processed/pdf_extracts/` |
| GitHub repo | `github_repo_processor` | `01_Processed/repo_summaries/` |
| Audio/Video | `media_downloader` + `whisper_transcript_processor` | `01_Processed/transcripts/` |
| Image | `metadata_processor` | `01_Processed/media_metadata/` |

The agent invokes the processor, waits for completion, and formats the output into the standard source file.

## Source Trail Preservation

Every extracted source file must include:
- Original source URL (if applicable)
- Capture ID
- Extraction engine and version
- Timestamp of extraction
- Access date
- Original title, author, date (if available)
- Any content warnings or extraction caveats

The source trail is critical for:
- Referencing the original material later
- Detecting link rot
- Distinguishing human-written from machine-extracted content
- Attribution and copyright compliance

## Files It May Read

- `00_Raw/captures.jsonl`
- `00_Raw/attachments/{capture_id}/`
- `02_Agent_Workspace/Intake_Records/{capture_id}_intake.json`
- Processor output logs in `07_Logs/processor_logs/`

## Files It May Write

- `01_Processed/{type}/{capture_id}_source.md`
- `01_Processed/media_metadata/{capture_id}_media_meta.json` (for media files)

## Files It Must Never Write

- Any file inside `/home/lifeos/10_Vaults/LifeOS/`
- `00_Raw/captures.jsonl` (append-only)
- Any agent workspace file belonging to other agents

## Safety Boundaries

- Does not decide final canonical placement
- Does not evaluate content quality (that is QA Verifier's job)
- Does not modify raw capture data
- Processors handle network access; this agent only delegates and formats

## Required Template/Format

See Outputs section. The extracted source file must always start with YAML frontmatter containing the capture_id, source_url, and extraction metadata.

## Review Checklist

- [ ] Source URL is preserved and accessible
- [ ] Extraction quality is assessed (full, partial, failed)
- [ ] Paywalls or access restrictions noted
- [ ] Content language matches detected language
- [ ] Source material is clean (no ads, navigation, boilerplate)
- [ ] Special characters and encoding handled correctly
- [ ] Images and embedded media noted but not embedded in text

## Failure Modes

| Failure | Handling |
|---|---|
| URL unreachable (404, timeout) | Log failure, mark extraction_quality as `failed`, write available metadata only, move to `06_Failed/` |
| Paywall detected | Mark extraction_quality as `partial`, include paywall warning in source file |
| PDF corrupted or encrypted | Log failure, move to `06_Failed/`, note encryption status |
| GitHub repo too large | Clone shallow (--depth 1), extract README + structure, note limitation |
| Video too long for Whisper | Process in chunks, note chunking in transcript, mark quality as `partial` |
| Media download timeout | Retry once with longer timeout, then fail |

## Escalation/Delegation Rules

- If source is behind a login wall: escalate to human (not possible to extract automatically)
- If source requires JavaScript rendering (SPA): flag for web_clipper_processor (headless browser)
- If media file exceeds size limit (configurable, default 500 MB): escalate for human decision
- If extraction produces no usable text: escalate, move to `06_Failed/`

## Example Output

```markdown
---
capture_id: cap_20260708_123456_abc123
source_url: https://example.com/container-security-best-practices
source_type: article
extraction_engine: article_processor_v1
extraction_timestamp: 2026-07-08T12:35:00Z
source_title: Container Security Best Practices for 2026
source_author: Jane Author
source_date: 2026-06-15
source_domain: example.com
extraction_quality: full
content_warnings: []
---

# Container Security Best Practices for 2026

Container security has evolved significantly...

[Full extracted article text]

---
Source extracted by Source Extraction Agent.
Original URL: https://example.com/container-security-best-practices
Access date: 2026-07-08T12:35:00Z
```
