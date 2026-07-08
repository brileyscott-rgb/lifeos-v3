#!/usr/bin/env python3
import argparse
import os
import sys

BUFFER_STRUCTURE = [
    "00_Raw",
    "00_Raw/attachments",
    "01_Processed",
    "01_Processed/articles",
    "01_Processed/transcripts",
    "01_Processed/pdf_extracts",
    "01_Processed/repo_summaries",
    "01_Processed/media_metadata",
    "01_Processed/manual_markdown",
    "02_Agent_Workspace",
    "02_Agent_Workspace/Knowledge_Drafts",
    "02_Agent_Workspace/Project_Drafts",
    "02_Agent_Workspace/Idea_Drafts",
    "02_Agent_Workspace/Reference_Drafts",
    "02_Agent_Workspace/Media_Drafts",
    "02_Agent_Workspace/Import_Plans",
    "03_Review_Packets",
    "04_Approved_For_Import",
    "05_Rejected",
    "06_Failed",
    "07_Logs",
    "07_Logs/processor_logs",
    "07_Logs/agent_logs",
    "07_Logs/import_logs",
]

MEDIA_STRUCTURE = [
    "Images",
    "Audio",
    "Video",
    "Documents",
    "Transcripts",
]

FORBIDDEN_ROOTS = {
    "/",
    "/home",
    "/home/lifeos/10_Vaults/LifeOS",
}

BUFFER_README = """# LifeOS Capture Buffer

WARNING: This is the LifeOS capture buffer vault, NOT the canonical
LifeOS vault. All content here is in-progress, unapproved, or rejected.
Nothing in this directory structure is imported into the canonical
LifeOS vault (/home/lifeos/10_Vaults/LifeOS/).

DO NOT sync this directory with Obsidian Sync, Syncthing, or any
real-time sync tool. This is a local-only processing workspace.

## Directory Purpose

- 00_Raw/ — Incoming capture queue and raw attachments
- 01_Processed/ — Processor outputs (pre-review)
- 02_Agent_Workspace/ — Agent draft notes (not yet reviewed)
- 03_Review_Packets/ — Assembled review packets for approval
- 04_Approved_For_Import/ — Approved captures awaiting import
- 05_Rejected/ — Rejected captures
- 06_Failed/ — Captures that failed processing
- 07_Logs/ — Per-processor and per-agent logs

## Safety

- Buffer vault is OUTSIDE canonical LifeOS vault
- Never mount buffer vault inside canonical vault
- Never configure sync tools to watch this directory
- No secrets, env files, or credentials should be stored here
"""

MEDIA_README = """# LifeOS Media Archive

WARNING: This is the LifeOS media archive. Media files are NOT stored
in Git, NOT stored in the buffer vault, and NOT stored in the canonical
LifeOS vault.

## Directory Purpose

- Images/ — Captured images
- Audio/ — Audio recordings
- Video/ — Video files
- Documents/ — PDF, Office documents, etc.
- Transcripts/ — Machine-generated and human-verified transcripts

## Safety

- Media archive is OUTSIDE canonical LifeOS vault
- NOT synced by Obsidian Sync, Syncthing, or Git
- Media files are NOT stored in Git (this path is gitignored)
- Files organized by type for human browsability
- Every file prefixed with capture ID for source traceability
"""


def _is_forbidden(root):
    rp = os.path.realpath(os.path.abspath(root))
    for forbidden in FORBIDDEN_ROOTS:
        fp = os.path.realpath(os.path.abspath(forbidden))
        if rp == fp:
            return True
    if rp.startswith(os.path.realpath("/etc")) or rp.startswith(os.path.realpath("/sys")):
        return True
    return False


def _is_test_path(root):
    return root.startswith("/tmp/")


def init_buffer(root, dry_run=False):
    if not _is_test_path(root) and _is_forbidden(root):
        raise ValueError(f"Refusing to create buffer vault at forbidden root: {root}")
    for subdir in BUFFER_STRUCTURE:
        path = os.path.join(root, subdir)
        if dry_run:
            print(f"[dry-run] Would create: {path}")
        else:
            os.makedirs(path, exist_ok=True)
    readme_path = os.path.join(root, "README.md")
    if dry_run:
        print(f"[dry-run] Would create: {readme_path}")
    else:
        with open(readme_path, "w") as f:
            f.write(BUFFER_README)


def init_media(root, dry_run=False):
    if not _is_test_path(root) and _is_forbidden(root):
        raise ValueError(f"Refusing to create media archive at forbidden root: {root}")
    for subdir in MEDIA_STRUCTURE:
        path = os.path.join(root, subdir)
        if dry_run:
            print(f"[dry-run] Would create: {path}")
        else:
            os.makedirs(path, exist_ok=True)
    readme_path = os.path.join(root, "README.md")
    if dry_run:
        print(f"[dry-run] Would create: {readme_path}")
    else:
        with open(readme_path, "w") as f:
            f.write(MEDIA_README)


def main():
    parser = argparse.ArgumentParser(description="Initialize LifeOS capture buffer vault and media archive")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, do not create")
    parser.add_argument("--buffer-root", default=os.path.expanduser("/home/lifeos/LifeOS_Capture_Buffer"),
                        help="Buffer vault root path")
    parser.add_argument("--media-root", default=os.path.expanduser("/home/lifeos/LifeOS_Media_Archive"),
                        help="Media archive root path")
    parser.add_argument("--buffer-only", action="store_true", help="Only create buffer vault")
    parser.add_argument("--media-only", action="store_true", help="Only create media archive")
    args = parser.parse_args()

    if not args.media_only:
        init_buffer(args.buffer_root, dry_run=args.dry_run)
        if not args.dry_run:
            print(f"Buffer vault initialized: {args.buffer_root}")
    if not args.buffer_only:
        init_media(args.media_root, dry_run=args.dry_run)
        if not args.dry_run:
            print(f"Media archive initialized: {args.media_root}")


if __name__ == "__main__":
    main()
