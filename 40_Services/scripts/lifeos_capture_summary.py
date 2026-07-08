#!/usr/bin/env python3
"""Read the capture JSONL queue and report metadata summary only.

Usage:
  python3 lifeos_capture_summary.py --text
  python3 lifeos_capture_summary.py --json
  python3 lifeos_capture_summary.py --text --queue-path /path/to/captures.jsonl

Reports:
  - queue_exists, queue_count
  - newest_capture_id, newest_received_at
  - sources breakdown, capture_type breakdown
  - processed_markdown_count
  - malformed_jsonl_count (lines that fail to parse)

This script does NOT:
  - Print full capture content
  - Read .env or secrets
  - Write to canonical vault
"""

import argparse
import json
import os
import sys
from collections import Counter


class CaptureSummary:

    def __init__(self):
        self.queue_exists = False
        self.queue_count = 0
        self.newest_capture_id = ""
        self.newest_received_at = ""
        self.sources_breakdown = {}
        self.types_breakdown = {}
        self.processed_markdown_count = 0
        self.malformed_count = 0


def get_summary(queue_path, processed_dir=None):
    s = CaptureSummary()
    if not os.path.isfile(queue_path):
        return s
    s.queue_exists = True
    sources = Counter()
    types_ = Counter()
    newest_ts = ""
    with open(queue_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                s.malformed_count += 1
                continue
            s.queue_count += 1
            src = rec.get("source", "unknown")
            sources[src] += 1
            ct = rec.get("capture_type", "unknown")
            types_[ct] += 1
            ts = rec.get("received_at", "")
            cid = rec.get("capture_id", "")
            if not newest_ts or ts > newest_ts:
                newest_ts = ts
                s.newest_received_at = ts
                s.newest_capture_id = cid
    s.sources_breakdown = dict(sources)
    s.types_breakdown = dict(types_)
    if processed_dir and os.path.isdir(processed_dir):
        s.processed_markdown_count = len([
            f for f in os.listdir(processed_dir)
            if f.endswith(".md") and os.path.isfile(os.path.join(processed_dir, f))
        ])
    return s


def to_dict(s):
    return {
        "queue_exists": s.queue_exists,
        "queue_count": s.queue_count,
        "newest_capture_id": s.newest_capture_id,
        "newest_received_at": s.newest_received_at,
        "sources_breakdown": s.sources_breakdown,
        "types_breakdown": s.types_breakdown,
        "processed_markdown_count": s.processed_markdown_count,
        "malformed_count": s.malformed_count,
    }


def format_text(s):
    lines = []
    lines.append("=== LifeOS Capture Queue Summary ===")
    lines.append(f"Queue exists: {s.queue_exists}")
    lines.append(f"Queue count: {s.queue_count}")
    if s.newest_capture_id:
        lines.append(f"Newest capture: {s.newest_capture_id}")
        lines.append(f"Newest received: {s.newest_received_at}")
    if s.sources_breakdown:
        lines.append("Sources:")
        for src, count in sorted(s.sources_breakdown.items()):
            lines.append(f"  {src}: {count}")
    if s.types_breakdown:
        lines.append("Capture types:")
        for ct, count in sorted(s.types_breakdown.items()):
            lines.append(f"  {ct}: {count}")
    lines.append(f"Processed markdown files: {s.processed_markdown_count}")
    if s.malformed_count:
        lines.append(f"Malformed JSONL lines: {s.malformed_count}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Capture queue metadata summary")
    parser.add_argument("--text", action="store_true", help="Human-readable text output")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--queue-path",
                        default=os.path.expanduser("/home/lifeos/LifeOS_Capture_Buffer/00_Raw/captures.jsonl"),
                        help="Path to captures JSONL queue")
    parser.add_argument("--processed-dir",
                        default=os.path.expanduser("/home/lifeos/LifeOS_Capture_Buffer/01_Processed/manual_markdown"),
                        help="Path to processed markdown directory")
    args = parser.parse_args()
    if not args.text and not args.json:
        args.text = True

    s = get_summary(args.queue_path, args.processed_dir)
    if args.json:
        print(json.dumps(to_dict(s), indent=2))
    else:
        print(format_text(s))
    return 0


if __name__ == "__main__":
    sys.exit(main())
