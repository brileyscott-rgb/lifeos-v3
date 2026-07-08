#!/usr/bin/env python3
"""Build review packets from processed capture Markdown drafts.

Reads capture draft Markdown files from the buffer processed folder,
wraps them into review-ready packet Markdown files in the buffer
review packet folder. Never writes to canonical vault.

Usage:
  python3 review_packet_builder.py --limit 5
  python3 review_packet_builder.py --dry-run --limit 1
"""

import argparse
import os
import re
import sys

FORBIDDEN_OUTPUT_ROOTS = {
    "/home/lifeos/10_Vaults/LifeOS",
}

SCHEMA_VERSION = 1


def _is_forbidden_output(path):
    rp = os.path.realpath(os.path.abspath(path))
    for forbidden in FORBIDDEN_OUTPUT_ROOTS:
        fp = os.path.realpath(os.path.abspath(forbidden))
        if rp == fp or rp.startswith(fp + os.sep):
            return True
    return False


def _safe_yaml_value(value):
    if value is None:
        return '""'
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return str(value)
    s = str(value)
    special = set(":#{}[]&*!|>%@`,'\"")
    needs_quotes = (any(c in s for c in special) or
                    s.startswith("- ") or s.startswith("? ") or
                    s.lower() in ("null", "true", "false", "yes", "no", "on", "off") or
                    s.strip() == "")
    if needs_quotes:
        escaped = s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")
        return f'"{escaped}"'
    return s


def _parse_frontmatter(content):
    fm = {}
    m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if m:
        for line in m.group(1).split("\n"):
            if ":" in line:
                k, _, v = line.partition(":")
                fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


def _make_packet(draft_path):
    with open(draft_path, "r") as f:
        draft_content = f.read()
    fm = _parse_frontmatter(draft_content)
    capture_id = fm.get("capture_id", "unknown")
    source = fm.get("source", "unknown")
    capture_type = fm.get("capture_type", "unknown")

    lines = []
    lines.append("---")
    lines.append(f"type: capture_review_packet")
    lines.append(f"capture_id: {_safe_yaml_value(capture_id)}")
    lines.append(f"status: pending_human_review")
    lines.append(f"source: buffer")
    lines.append(f"schema_version: {SCHEMA_VERSION}")
    lines.append("---")
    lines.append("")
    lines.append("# Capture Review Packet")
    lines.append("")
    lines.append("> **Safety note:** This packet is buffer-only and has not been imported into the canonical LifeOS vault.")
    lines.append("")
    lines.append("## Review Summary")
    lines.append("")
    lines.append(f"- **Capture ID:** {capture_id}")
    lines.append(f"- **Source:** {source}")
    lines.append(f"- **Capture Type:** {capture_type}")
    lines.append(f"- **Status:** pending_human_review")
    lines.append("")
    lines.append("## Source Draft")
    lines.append("")
    lines.append("The captured content is below for review:")
    lines.append("")
    body_start = draft_content.find("---\n", draft_content.find("---\n") + 4)
    if body_start >= 0:
        lines.append(draft_content[body_start + 4:].strip())
    else:
        lines.append(draft_content.strip())
    lines.append("")
    lines.append("## Proposed Handling")
    lines.append("")
    lines.append("- Review the capture content above for accuracy and relevance.")
    lines.append("- Determine whether this capture should be imported into the canonical LifeOS vault.")
    lines.append("- If approved, the import process will create/update files in the canonical vault.")
    lines.append("- If rejected, the capture stays in the buffer for reference or cleanup.")
    lines.append("")
    lines.append("## Safety Checks")
    lines.append("")
    lines.append("- [ ] No secrets or tokens in capture content")
    lines.append("- [ ] Content is appropriate for the canonical vault")
    lines.append("- [ ] Links and metadata are safe")
    lines.append("- [ ] No duplicate of existing canonical content")
    lines.append("")
    lines.append("## Human Decision")
    lines.append("")
    lines.append("- **Decision:** [ ] Approve  [ ] Reject  [ ] Request Changes")
    lines.append("- **Notes:** ")
    lines.append("")
    lines.append("## Import Status")
    lines.append("")
    lines.append("- **Imported:** No")
    lines.append("- **Import path:** (to be determined)")
    lines.append("")

    return "\n".join(lines)


def build_packets(input_dir, output_dir, dry_run=False, limit=None):
    if _is_forbidden_output(output_dir):
        if not output_dir.startswith("/tmp/"):
            raise ValueError(f"Refusing output to forbidden path: {output_dir}")
    if not os.path.isdir(input_dir):
        return
    count = 0
    for fname in sorted(os.listdir(input_dir)):
        if not fname.endswith(".md"):
            continue
        draft_path = os.path.join(input_dir, fname)
        if not os.path.isfile(draft_path):
            continue
        packet_name = fname.replace(".md", "_review_packet.md")
        out_path = os.path.join(output_dir, packet_name)
        if os.path.exists(out_path):
            continue
        count += 1
        if dry_run:
            yield f"[dry-run] {out_path}"
            continue
        os.makedirs(output_dir, exist_ok=True)
        content = _make_packet(draft_path)
        with open(out_path, "w") as f:
            f.write(content)
        yield out_path
        if limit and count >= limit:
            break


def main():
    parser = argparse.ArgumentParser(description="Build review packets from processed capture drafts")
    parser.add_argument("--input-dir",
                        default=os.path.expanduser("/home/lifeos/LifeOS_Capture_Buffer/01_Processed/manual_markdown"),
                        help="Directory containing processed Markdown drafts")
    parser.add_argument("--output-dir",
                        default=os.path.expanduser("/home/lifeos/LifeOS_Capture_Buffer/03_Review_Packets"),
                        help="Output directory for review packets")
    parser.add_argument("--limit", type=int, default=None, help="Max packets to build")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    for result in build_packets(args.input_dir, args.output_dir,
                                dry_run=args.dry_run, limit=args.limit):
        print(result)


if __name__ == "__main__":
    main()
