# Capture Processor Roadmap

Status: architecture/scaffold
Created: 2026-07-08
Purpose: catalog all planned Dockerized processors for the Agentic Capture Pipeline with purpose, inputs/outputs, risk assessment, storage impact, and V1/V2/V3 recommendations.

## Processor Catalog

### metadata_processor

- **Purpose:** Extract and normalize metadata from any capture (title, author, date, language, domain, content type, word count, reading time). Runs on all captures regardless of type.
- **Inputs:** Raw capture record from `00_Raw/captures.jsonl`
- **Outputs:** `01_Processed/media_metadata/{capture_id}_meta.json`
- **Docker/Dependencies:** Python stdlib + `python-magic` for MIME detection, `langdetect` for language detection, `readability-lxml` for article metadata
- **Risk Level:** Low — read-only analysis, no network calls
- **Storage Impact:** Negligible (JSON metadata only, ~1 KB per capture)
- **V1 Recommendation:** Implement — foundational for all downstream processors
- **V2:** Add entity extraction (people, organizations, technologies)
- **V3:** Add semantic topic modeling
- **Tests Needed:** Type detection accuracy, language detection across common languages, metadata extraction from HTML/PDF/media files, edge cases (empty input, binary files, very long text)

### article_processor

- **Purpose:** Extract clean article text from URLs. Remove ads, navigation, sidebars, comments, and boilerplate. Preserve headings, paragraphs, lists, and code blocks.
- **Inputs:** URL from capture, metadata from `metadata_processor`
- **Outputs:** `01_Processed/articles/{capture_id}_source.md`
- **Docker/Dependencies:** Python + `readability-lxml`, `requests`, `beautifulsoup4`, `html2text`. Network egress required (HTTP/HTTPS to source URL).
- **Risk Level:** Medium — network egress, content from untrusted URLs
- **Storage Impact:** Small (Markdown text, ~10-50 KB per article)
- **V1 Recommendation:** Implement — core functionality for URL captures
- **V2:** Paywall detection, multi-page article support, image extraction to media archive
- **V3:** JavaScript-rendered page support (headless browser)
- **Tests Needed:** Article extraction quality on diverse sources (blogs, news, docs, Wikipedia), paywall detection, 404/timeout handling, encoding handling, malicious URL handling

### web_clipper_processor

- **Purpose:** Capture web page snapshots as clean Markdown with preserved structure. For pages where article_processor cannot extract clean text (SPAs, dashboards, interactive content).
- **Inputs:** URL from capture, clipping parameters
- **Outputs:** `01_Processed/articles/{capture_id}_clipped.md` with optional screenshot
- **Docker/Dependencies:** Node.js + Puppeteer/Playwright (headless Chromium). Network egress. Larger image size.
- **Risk Level:** Medium-High — headless browser, JavaScript execution, larger attack surface
- **Storage Impact:** Medium (Markdown + optional screenshot, ~100 KB - 2 MB per capture)
- **V1 Recommendation:** Defer — article_processor handles most cases. Implement when SPA capture becomes needed.
- **V2:** Implement with strict sandboxing (read_only rootfs where possible, network egress allowlist)
- **V3:** Selective clipping (user highlights section of page)
- **Tests Needed:** SPA rendering, authentication-gated pages, infinite scroll pages, memory/CPU limits, sandbox escape prevention

### media_downloader

- **Purpose:** Download media files (images, audio, video) from URLs or attached files. Store in LifeOS Media Archive with capture-ID-prefixed filenames. Enforce size limits.
- **Inputs:** Media URL or attached file reference, metadata
- **Outputs:** `LifeOS_Media_Archive/{type}/YYYY/MM/{capture_id}_{slug}.{ext}`
- **Docker/Dependencies:** Python + `requests`, `yt-dlp` (for YouTube and other platforms). Network egress. Write access to media archive only.
- **Risk Level:** Medium — network egress, large file downloads, potential for malicious media files
- **Storage Impact:** High (video files can be 100 MB - 2 GB each)
- **V1 Recommendation:** Implement with size limits (default 500 MB per file). Add `yt-dlp` for video platform support.
- **V2:** Parallel downloads, resumable downloads, format selection (audio-only for podcasts)
- **V3:** Automatic quality selection based on storage pressure
- **Tests Needed:** YouTube download, direct URL download, size limit enforcement, timeout handling, retry logic, media archive path correctness

### video_processor

- **Purpose:** Extract key frames and timestamps from video files. Detect scene changes, generate thumbnail strips, identify chapters or topic segments.
- **Inputs:** Video file in media archive, media metadata
- **Outputs:** Key frame images in `LifeOS_Media_Archive/images/YYYY/MM/`, timestamp manifest in `01_Processed/media_metadata/{capture_id}_video_manifest.json`
- **Docker/Dependencies:** Python + `opencv-python-headless`, `ffmpeg`. No network egress required.
- **Risk Level:** Low-Medium — video processing is CPU-intensive, large output files possible
- **Storage Impact:** Medium (key frames: ~10-50 images × 200 KB = 2-10 MB per video)
- **V1 Recommendation:** Defer — implement after media_downloader and whisper_transcript are stable
- **V2:** Implement with CPU limits, key frame count limits
- **V3:** Scene-level topic detection using visual AI
- **Tests Needed:** Key frame extraction accuracy, scene detection on diverse content, CPU/memory limits, large video handling, corrupted video handling

### whisper_transcript_processor

- **Purpose:** Transcribe audio and video files using Whisper. Support multiple languages and models. Always mark output as machine_generated_unverified.
- **Inputs:** Audio/video file in media archive, language preference
- **Outputs:** `01_Processed/transcripts/{capture_id}_transcript.md` with timestamps, `01_Processed/transcripts/{capture_id}_transcript.json` with structured segments
- **Docker/Dependencies:** Python + `openai-whisper` or `faster-whisper`. GPU recommended but CPU fallback. No network egress if model is pre-downloaded.
- **Risk Level:** Low — local processing only, no network, no write outside designated directories
- **Storage Impact:** Small (transcript text ~10-100 KB). Model storage: ~3 GB for Whisper large-v3.
- **V1 Recommendation:** Implement — core functionality for audio/video capture
- **V2:** Speaker diarization, language auto-detection, confidence scores per segment
- **V3:** Real-time streaming transcription
- **Tests Needed:** Transcription accuracy on clean audio, accuracy on noisy audio, multi-speaker handling, language detection, memory usage, GPU vs CPU performance, long audio handling (>1 hour)

### pdf_processor

- **Purpose:** Extract text, metadata, table of contents, and structure from PDF files. Handle scanned PDFs (OCR fallback). Preserve heading hierarchy where possible.
- **Inputs:** PDF file in media archive or attached to capture
- **Outputs:** `01_Processed/pdf_extracts/{capture_id}_source.md`
- **Docker/Dependencies:** Python + `PyMuPDF` (fitz) or `pdfplumber`, `pytesseract` + `tesseract-ocr` for scanned PDFs. No network egress.
- **Risk Level:** Low — local file processing only
- **Storage Impact:** Small (extracted text ~5-500 KB)
- **V1 Recommendation:** Implement — common capture format
- **V2:** Table extraction to Markdown/CSV, form field extraction, image extraction
- **V3:** Structural analysis (identify chapters, sections, references)
- **Tests Needed:** Text PDF extraction, scanned PDF OCR, multi-column layout, table extraction, encrypted PDF handling, corrupted PDF handling

### github_repo_processor

- **Purpose:** Clone and summarize GitHub repositories. Extract README, directory structure, key files, language stats, and dependency information. Does not execute code.
- **Inputs:** GitHub URL (repo, issue, PR, gist)
- **Outputs:** `01_Processed/repo_summaries/{capture_id}_source.md`
- **Docker/Dependencies:** Python + `git` CLI, `PyGithub` (optional, for API-based metadata). Network egress (git clone). Clone to temp directory only, not persisted.
- **Risk Level:** Medium — clones untrusted code, network egress, disk usage for large repos
- **Storage Impact:** Temporary (clone is discarded after processing). Small output (~5-50 KB Markdown).
- **V1 Recommendation:** Implement — valuable for developer knowledge capture
- **V2:** Issue/PR summarization, release notes extraction, dependency graph
- **V3:** Code quality metrics, security vulnerability scanning (read-only)
- **Tests Needed:** Public repo clone, private repo handling (should gracefully fail or require token), large repo handling (Linux kernel?), malicious repo detection (no code execution), shallow clone behavior

### duplicate_detector

- **Purpose:** Detect near-duplicate captures using content similarity, URL matching, and semantic comparison. Prevent duplicate notes from being imported into the canonical vault.
- **Inputs:** Processed source material from any processor, existing canonical vault content (via search index or vector store)
- **Outputs:** `02_Agent_Workspace/Import_Plans/{capture_id}_duplicate_report.json`
- **Docker/Dependencies:** Python + `scikit-learn` (TF-IDF/cosine similarity), optional ChromaDB for vector similarity
- **Risk Level:** Low — read-only comparison, no network egress
- **Storage Impact:** Negligible (JSON report)
- **V1 Recommendation:** Implement — prevents vault clutter
- **V2:** Semantic duplicate detection via embeddings, cross-capture cluster detection
- **V3:** Automatic merge suggestion for near-duplicates
- **Tests Needed:** Exact duplicate detection, near-duplicate detection (paraphrased), cross-language duplicate, URL-based duplicate, false positive rate, performance on large vault

### markdown_formatter

- **Purpose:** Format agent outputs into LifeOS-standard Markdown. Ensure consistent frontmatter, heading hierarchy, link syntax, code block formatting, and file naming conventions.
- **Inputs:** Any agent draft or processed content
- **Outputs:** Formatted Markdown in the appropriate agent workspace directory (in-place or as new file)
- **Docker/Dependencies:** Python stdlib + `python-frontmatter`. No network egress.
- **Risk Level:** Low — text formatting only
- **Storage Impact:** Negligible (formatting changes only)
- **V1 Recommendation:** Implement — ensures consistent vault quality
- **V2:** Template validation against LifeOS note type schemas
- **V3:** Auto-fix common formatting issues without human review
- **Tests Needed:** Frontmatter validation, heading hierarchy check, wiki-link formatting, code block language tags, special character escaping, file naming convention enforcement

### review_packet_builder

- **Purpose:** Assemble all agent outputs, QA reports, and metadata into a single review packet Markdown file for human approval.
- **Inputs:** All agent outputs, QA report, duplicate report, import manifest
- **Outputs:** `03_Review_Packets/{capture_id}_review_packet.md`
- **Docker/Dependencies:** Python stdlib. No network egress.
- **Risk Level:** Low — read-only assembly
- **Storage Impact:** Small (~5-50 KB per review packet)
- **V1 Recommendation:** Implement — core approval gate mechanism
- **V2:** Batch review packet generation, diff-style file change previews
- **V3:** Interactive review UI (Telegram buttons, dashboard)
- **Tests Needed:** Review packet completeness, all required sections present, import manifest validity, rollback procedure correctness

### import_exporter

- **Purpose:** Execute approved imports into the canonical LifeOS vault. Read the approved import manifest, copy files to correct destinations, log the import event, and verify the import completed correctly.
- **Inputs:** Approved import manifest from `02_Agent_Workspace/Import_Plans/{capture_id}_import_manifest.json`
- **Outputs:** Imported files in the canonical vault, import event in event log, import receipt in `07_Logs/import_logs/{capture_id}_import_receipt.json`
- **Docker/Dependencies:** Python stdlib. Write access to canonical vault paths (explicit, not full mount). Read access to buffer vault.
- **Risk Level:** Medium — writes to canonical vault. Must be tightly controlled.
- **Storage Impact:** Small (copies files; source remains in buffer vault)
- **V1 Recommendation:** Implement only after approval gate is fully tested and human-in-the-loop verified
- **V2:** Atomic imports (all-or-nothing), pre-import validation, post-import verification
- **V3:** Scheduled batch imports, import analytics
- **Tests Needed:** Import execution accuracy, rollback correctness, conflict handling (file already exists), permission handling, atomicity (no partial imports), event log verification, dry-run mode

## Implementation Priority

### V1 (Foundation)
1. metadata_processor
2. article_processor
3. pdf_processor
4. markdown_formatter
5. duplicate_detector
6. review_packet_builder

### V2 (Media)
7. media_downloader
8. whisper_transcript_processor
9. video_processor
10. github_repo_processor

### V3 (Advanced)
11. web_clipper_processor
12. import_exporter

## Processor Safety Standards

All processors must:
- Run as non-root user
- Use `read_only: true` rootfs where possible
- `cap_drop: ALL`
- `no-new-privileges: true`
- Mount only required directories (buffer vault, media archive)
- NEVER mount canonical vault paths (exception: import_exporter with explicit file-level bind mounts)
- NEVER mount Docker socket
- Log to `07_Logs/processor_logs/{processor_name}/`
- Respect `MAX_REQUEST_BYTES` and file size limits
- Time out gracefully (no infinite processing)
