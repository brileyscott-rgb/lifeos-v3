# Intake Agent

## Purpose

Receive a raw capture and produce a normalized classification record. This is the first agent in the pipeline — it does NOT process content, only identifies what it is and what needs to happen next.

## Inputs

- Raw capture text from `00_Raw/captures.jsonl`
- Capture ID from the queue
- Any attached raw files in `00_Raw/attachments/{capture_id}/`

## Outputs

- Intake classification record written to `02_Agent_Workspace/Intake_Records/{capture_id}_intake.json`

```json
{
  "capture_id": "cap_20260708_123456_abc123",
  "intake_timestamp": "2026-07-08T12:34:56Z",
  "source_channel": "telegram",
  "raw_text_preview": "first 200 chars of raw text",
  "detected_type": "url_article",
  "detected_subtype": null,
  "confidence": 0.95,
  "detected_language": "en",
  "attached_files": [],
  "required_processors": ["metadata_processor", "article_processor", "duplicate_detector"],
  "suggested_agent_route": "knowledge_note",
  "content_flags": [],
  "duplicate_check_similarity_threshold": 0.85,
  "notes": "YouTube video link detected, will need whisper transcript after download"
}
```

## Type Detection

The Intake Agent classifies captures into one of these types:

| Detected Type | Indicators |
|---|---|
| `text` | Plain text, no URL, no file attachment |
| `url_article` | URL pointing to blog, news, documentation, Wikipedia |
| `url_video` | URL from YouTube, Vimeo, etc. |
| `url_audio` | URL from podcast, audio hosting |
| `url_github` | GitHub repo, issue, PR, gist URL |
| `url_webpage` | Generic URL not matching other categories |
| `image` | Attached image file |
| `audio_file` | Attached audio file |
| `video_file` | Attached video file |
| `pdf` | Attached PDF file |
| `document` | Attached document (docx, odt, txt, etc.) |
| `voice_memo` | Short audio from Telegram voice message |
| `idea` | Short text with idea-like patterns |
| `task` | Text with task/todo patterns |
| `note` | Longer text with note/journal patterns |
| `unknown` | Cannot determine type |

## Tools/Processors It May Call

- None directly — Intake Agent is a classifier, not an executor
- May read metadata from `metadata_processor` output if the processor ran first

## Files It May Read

- `00_Raw/captures.jsonl` — the raw capture record
- `00_Raw/attachments/{capture_id}/` — any attached files
- `07_Logs/processor_logs/metadata_processor/` — if processor pre-ran

## Files It May Write

- `02_Agent_Workspace/Intake_Records/{capture_id}_intake.json` — the classification record
- Nothing else

## Files It Must Never Write

- Any file inside `/home/lifeos/10_Vaults/LifeOS/`
- `00_Raw/captures.jsonl` (append-only, never modify)
- Any approved/rejected folder
- Any canonical vault path

## Safety Boundaries

- Read-only except for its own output file
- No network access
- No shell execution
- No file deletion
- No secret handling

## Required Template/Format

See Outputs section above. The `detected_type` must be one of the enumerated types. The `required_processors` list must reference actual processor names from the processor roadmap.

## Review Checklist

- [ ] Type detection confidence meets minimum threshold (0.7)
- [ ] Required processors are appropriate for the detected type
- [ ] Suggested agent route is reasonable
- [ ] No confidential or secret content in raw_text_preview
- [ ] Attached files list is complete and accurate
- [ ] Content flags are appropriate (nsfw, paywall, non_english, etc.)

## Failure Modes

| Failure | Handling |
|---|---|
| Cannot determine type | Set type to `unknown`, route to Reference Agent for manual review |
| Multiple types detected | Select highest-confidence primary type, list alternatives in notes |
| Raw text is empty | Flag as `invalid`, move to `06_Failed/` |
| Attachments missing or corrupted | Log warning, continue with text-only classification |
| Language detection fails | Default to `en`, flag for human review |

## Escalation/Delegation Rules

- If confidence < 0.7 for detected type: escalate to human operator before routing
- If capture contains potential secrets (API keys, tokens): flag immediately, do NOT include in preview, escalate
- If attached file type is unknown: route to Reference Agent with instruction to inspect

## Example Output

```json
{
  "capture_id": "cap_20260708_123456_abc123",
  "intake_timestamp": "2026-07-08T12:34:56Z",
  "source_channel": "telegram",
  "raw_text_preview": "Check out this article about container security: https://example.com/container-security-best-practices",
  "detected_type": "url_article",
  "detected_subtype": null,
  "confidence": 0.95,
  "detected_language": "en",
  "attached_files": [],
  "required_processors": ["metadata_processor", "article_processor", "duplicate_detector"],
  "suggested_agent_route": "knowledge_note",
  "content_flags": [],
  "duplicate_check_similarity_threshold": 0.85,
  "notes": "Standard article URL from tech blog — likely Knowledge note candidate"
}
```
