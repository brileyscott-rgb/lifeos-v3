# Capture Processors

Dockerized processors for the LifeOS Agentic Capture Pipeline.

**Status:** architecture/scaffold — not yet implemented.

## Purpose

Type-specific processors that transform raw captures into structured, agent-ready content inside the Headless Capture Buffer Vault.

## Planned Processors

| Processor | Purpose | V1 Priority |
|---|---|---|
| metadata_processor | Extract and normalize metadata | High |
| article_processor | Extract clean article text from URLs | High |
| web_clipper_processor | Browser-based page capture | Deferred |
| media_downloader | Download media files to archive | Medium |
| video_processor | Extract key frames, timestamps | Deferred |
| whisper_transcript_processor | Transcribe audio/video | Medium |
| pdf_processor | Extract text from PDFs | High |
| github_repo_processor | Clone and summarize repos | Medium |
| duplicate_detector | Detect near-duplicate captures | High |
| markdown_formatter | Format to LifeOS Markdown standards | High |
| review_packet_builder | Assemble review packets | High |
| import_exporter | Execute approved imports | Deferred |

## Key Safety Rules

- No canonical vault mounts (buffer vault + media archive only)
- `read_only: true` rootfs where possible
- `cap_drop: ALL`, non-root user
- No Docker socket access
- No shell MCP exposure
- Log to buffer vault `07_Logs/`

## Roadmap

See `40_Services/docs/Capture_Processor_Roadmap.md` for full specification.
