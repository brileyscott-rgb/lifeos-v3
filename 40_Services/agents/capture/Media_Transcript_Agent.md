# Media Transcript Agent

## Purpose

Handle video, audio, image, and voice memo captures. Prepare transcript notes, extract media metadata, link to archived media files in the media archive, and ensure all machine-generated transcripts are properly marked as unverified.

## Inputs

- Intake classification: `02_Agent_Workspace/Intake_Records/{capture_id}_intake.json`
- Extracted/processed media: output from `media_downloader`, `whisper_transcript_processor`, `video_processor`
- Media file location: `/home/lifeos/LifeOS_Media_Archive/{type}/YYYY/MM/{capture_id}_{slug}.{ext}`
- Transcript file: `01_Processed/transcripts/{capture_id}_transcript.md` or raw transcript output

## Outputs

- Media/transcript note draft: `02_Agent_Workspace/Media_Drafts/{capture_id}_media_draft.md`

## Media Note Template

### For Audio/Video with Transcript

```markdown
---
aliases: []
tags: [media, podcast|video|voice-memo|audio, {domain}]
status: draft
confidence: machine_generated_unreviewed
transcript_status: machine_generated_unverified
transcript_engine: whisper
created: 2026-07-08T12:36:00Z
source_capture: cap_20260708_123456_abc123
source_url: https://example.com/video
duration: "45:23"
language: en
---

# [Title]

## Media Info
- **Type:** video|audio|voice-memo
- **Duration:** 45:23
- **Source:** [URL or capture source]
- **Media file:** [relative path to media archive]

## Summary
[Agent-generated summary of the content — 3-5 sentences]

## Key Points
- [Key point 1]
- [Key point 2]
- [Key point 3]

## Timestamps
- `00:00` — Introduction
- `05:30` — [Topic change]
- `15:45` — [Key discussion point]
- `30:00` — [Topic change]
- `42:00` — Summary and conclusions

## Transcript Status
**This transcript was machine-generated and has NOT been human-verified.**
Expect errors in:
- Technical terminology
- Proper names
- Numbers and statistics
- Non-English phrases

[Full transcript or link to transcript file]

## Related Notes
- [[Related Note 1]]
- [[Related Note 2]]

## Source Trail
- Original capture: cap_20260708_123456_abc123
- Source URL: [URL]
- Media file: LifeOS_Media_Archive/videos/2026/07/cap_20260708_123456_abc123_demo.mp4
- Transcript engine: whisper-large-v3
- Transcript date: 2026-07-08T12:35:00Z
```

### For Images

```markdown
---
aliases: []
tags: [media, image, {domain}]
status: draft
confidence: machine_generated_unreviewed
created: 2026-07-08T12:36:00Z
source_capture: cap_20260708_123456_def789
image_dimensions: "1920x1080"
---

# [Image Description]

## Image
![Image description](../../LifeOS_Media_Archive/images/2026/07/cap_20260708_123456_def789_screenshot.png)

## Description
[What the image shows — agent-generated or user-provided]

## Context
[Why this image was captured, what it relates to]

## Source
- Media file: LifeOS_Media_Archive/images/2026/07/cap_20260708_123456_def789_screenshot.png
- Capture source: [Telegram, screenshot tool, etc.]
- Capture date: 2026-07-08T12:34:00Z
```

## Transcript Verification Warning

ALL machine-generated transcripts MUST include the prominent warning:
```
**This transcript was machine-generated and has NOT been human-verified.**
```

Additional caveats are required for:
- Technical content (expects terminology errors)
- Multi-speaker content (expects speaker identification errors)
- Non-English content (expects higher error rates)
- Low-quality audio (expects significant transcription errors)

## Media Linking

All media references must use relative paths to the media archive:
- `../../LifeOS_Media_Archive/videos/2026/07/{file}`
- `../../LifeOS_Media_Archive/images/2026/07/{file}`
- `../../LifeOS_Media_Archive/audio/2026/07/{file}`

Absolute paths are NOT used — they break when vaults are moved or synced.

## Files It May Read

- `02_Agent_Workspace/Intake_Records/{capture_id}_intake.json`
- `01_Processed/transcripts/{capture_id}_transcript.md`
- `01_Processed/media_metadata/{capture_id}_media_meta.json`
- Media file metadata (dimensions, duration, codec)

## Files It May Write

- `02_Agent_Workspace/Media_Drafts/{capture_id}_media_draft.md`

## Files It Must Never Write

- Any file inside `/home/lifeos/10_Vaults/LifeOS/`
- Media files in the media archive (handled by processors, not the agent)
- Transcript files in `01_Processed/` (handled by whisper processor)

## Safety Boundaries

- Never claim a machine transcript is accurate — always mark `machine_generated_unverified`
- Never fabricate timestamps or key points not present in the source
- Never evaluate the factual correctness of podcast/video content (preserve, don't fact-check)
- Never embed copyrighted content verbatim beyond fair-use excerpts
- Do not link to media files that don't exist — verify file existence before writing the note

## Required Template/Format

See templates above. Template selection depends on media type (audio/video vs. image). All YAML frontmatter fields are required for their respective types.

## Review Checklist

- [ ] Transcript status is `machine_generated_unverified`
- [ ] Transcript warning is prominent and visible
- [ ] Media links are relative paths to the media archive
- [ ] Media files exist at the linked paths
- [ ] Timestamps are reasonable for the media duration
- [ ] Key points are drawn from the content, not fabricated
- [ ] Source trail is complete
- [ ] Duration and metadata fields are populated

## Failure Modes

| Failure | Handling |
|---|---|
| Transcription failed entirely | Create note with metadata only, mark transcript as `failed`, flag for human |
| Media file download failed | Create note with whatever metadata is available, note download failure |
| Media file too long for accurate timestamps | Note limitation, mark timestamps as `approximate` |
| Speech in unknown language | Flag language as `unknown`, mark transcript confidence as `very_low` |
| Poor audio quality | Mark transcript quality as `poor_audio`, include prominent warning |

## Escalation/Delegation Rules

- If the media is a video tutorial/demo that would benefit from screenshots: request video_processor keyframe extraction
- If the transcript reveals the content should be a Knowledge note instead: flag for Knowledge Note Agent re-processing
- If the media is copyrighted content (movie, TV show): flag copyright concern, do not reproduce transcript
- If transcript quality is too poor to be useful: flag for human decision (keep as minimal reference or reject)

## Example Output

```markdown
---
aliases: [Docker networking deep dive, container networking explained]
tags: [media, video, containers, docker, networking]
status: draft
confidence: machine_generated_unreviewed
transcript_status: machine_generated_unverified
transcript_engine: whisper
created: 2026-07-08T12:36:00Z
source_capture: cap_20260708_123456_abc123
source_url: https://youtube.com/watch?v=example
duration: "32:15"
language: en
---

# Docker Networking Deep Dive

## Media Info
- **Type:** video
- **Duration:** 32:15
- **Source:** https://youtube.com/watch?v=example
- **Media file:** ../../LifeOS_Media_Archive/videos/2026/07/cap_20260708_123456_abc123_docker-networking.mp4

## Summary
A technical deep dive into Docker networking modes (bridge, host, overlay, macvlan) with practical demonstrations of network isolation, container-to-container communication, and DNS resolution within user-defined bridge networks. Covers iptables rules Docker creates and common networking pitfalls.

## Key Points
- User-defined bridge networks provide automatic DNS resolution between containers
- The default bridge network does NOT provide DNS — always create custom networks
- Host networking bypasses network isolation entirely (use carefully)
- Overlay networks enable multi-host communication but require a key-value store
- Docker's iptables rules can conflict with host firewall rules

## Timestamps
- `00:00` — Introduction and networking overview
- `03:45` — Default bridge network demo
- `10:20` — User-defined bridge networks and DNS
- `18:30` — Host networking mode
- `24:00` — Overlay networks and multi-host
- `30:00` — Common pitfalls and troubleshooting

## Transcript Status
**This transcript was machine-generated and has NOT been human-verified.**
Expect errors in:
- Technical terminology (especially Docker-specific terms)
- Command-line examples
- IP addresses and port numbers

[Full transcript available at: 01_Processed/transcripts/cap_20260708_123456_abc123_transcript.md]

## Related Notes
- [[Docker Networking Modes]]
- [[LifeOS Docker Compose Architecture]]
- [[Container Network Security]]

## Source Trail
- Original capture: cap_20260708_123456_abc123
- Source URL: https://youtube.com/watch?v=example
- Media file: LifeOS_Media_Archive/videos/2026/07/cap_20260708_123456_abc123_docker-networking.mp4
- Transcript engine: whisper-large-v3
- Transcript date: 2026-07-08T12:35:00Z
```
