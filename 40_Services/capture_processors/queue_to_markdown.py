#!/usr/bin/env python3
import argparse
import json
import os
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
    yaml_special = set(":#{}[]&*!|>%@`,'\"")
    needs_quotes = (any(c in s for c in yaml_special) or
                    s.startswith("- ") or s.startswith("? ") or
                    s.lower() in ("null", "true", "false", "yes", "no", "on", "off") or
                    s.strip() == "")
    if needs_quotes:
        escaped = s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")
        return f'"{escaped}"'
    return s


def _slugify(text, max_len=40):
    s = str(text).lower()
    slug = "".join(c if c.isalnum() or c in "-_" else "-" for c in s)
    slug = slug.strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug[:max_len] if slug else "capture"


def _make_frontmatter(rec):
    lines = ["---"]
    lines.append(f"type: capture_review_draft")
    lines.append(f"capture_id: {_safe_yaml_value(rec.get('capture_id', ''))}")
    lines.append(f"source: {_safe_yaml_value(rec.get('source', 'unknown'))}")
    lines.append(f"capture_type: {_safe_yaml_value(rec.get('capture_type', 'unknown'))}")
    lines.append(f"status: buffer_review")
    lines.append(f"created: {_safe_yaml_value(rec.get('received_at', ''))}")
    lines.append(f"schema_version: {SCHEMA_VERSION}")
    if rec.get("priority"):
        lines.append(f"priority: {_safe_yaml_value(rec['priority'])}")
    tags = rec.get("tags", [])
    if tags:
        tag_str = "[" + ", ".join(_safe_yaml_value(t) for t in tags) + "]"
        lines.append(f"tags: {tag_str}")
    if rec.get("title"):
        lines.append(f"title: {_safe_yaml_value(rec['title'])}")
    lines.append("---")
    return "\n".join(lines) + "\n"


def _make_body(rec):
    parts = []
    parts.append("# Capture Review Draft\n")
    parts.append("> **Buffer note:** This is a buffer draft only. It has not been imported into the canonical LifeOS vault.\n")
    parts.append("## Capture Summary\n")
    capture_type = rec.get("capture_type", "unknown")
    source = rec.get("source", "unknown")
    parts.append(f"- **Type:** {capture_type}")
    parts.append(f"- **Source:** {source}")
    parts.append(f"- **Capture ID:** {rec.get('capture_id', 'unknown')}")
    parts.append(f"- **Received:** {rec.get('received_at', 'unknown')}")
    parts.append("")

    content = (rec.get("content") or "").strip()
    url = (rec.get("url") or "").strip()
    title = (rec.get("title") or "").strip()

    if title:
        parts.append("## Title\n")
        parts.append(f"{title}\n")

    if content:
        parts.append("## Original Content\n")
        parts.append(f"{content}\n")

    if url:
        parts.append("## Source URL\n")
        parts.append(f"- {url}\n")

    metadata = rec.get("metadata", {})
    if metadata and isinstance(metadata, dict) and len(metadata) > 0:
        parts.append("## Metadata\n")
        for k, v in metadata.items():
            if isinstance(v, (list, dict)):
                v = json.dumps(v)
            parts.append(f"- **{_safe_yaml_value(k)}:** {_safe_yaml_value(v)}")
        parts.append("")

    parts.append("## Suggested Next Review\n")
    parts.append("- Review the content above for accuracy and relevance.")
    parts.append("- Determine whether this capture should be imported into the canonical LifeOS vault.")
    if url:
        parts.append("- Consider whether the source URL content needs to be fetched and reviewed separately.")
    parts.append("- Approve, reject, or request modifications via the review flow.")
    parts.append("")

    parts.append("## Safety Notes\n")
    parts.append("- This file is in the buffer vault, not the canonical LifeOS vault.")
    parts.append("- No AI processing, URL scraping, or automatic import has been performed.")
    parts.append("- No canonical vault files have been created or modified.")
    parts.append("")

    return "\n".join(parts) + "\n"


def _output_filename(rec):
    cap_id = rec.get("capture_id", "unknown")
    content = (rec.get("content") or rec.get("title") or "capture").strip()
    slug = _slugify(content)
    return f"{cap_id}_{slug}.md"


def _read_queue(queue_path):
    if not os.path.isfile(queue_path):
        return
    with open(queue_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as e:
                print(f"WARNING: skipping malformed JSONL line: {str(e)[:100]}", file=sys.stderr)


def process_queue(queue_path, output_dir, dry_run=False, limit=None, capture_id=None):
    if _is_forbidden_output(output_dir):
        raise ValueError(f"Refusing output to forbidden path: {output_dir}")
    count = 0
    for rec in _read_queue(queue_path):
        if capture_id and rec.get("capture_id") != capture_id:
            continue
        out_file = os.path.join(output_dir, _output_filename(rec))
        if os.path.exists(out_file):
            continue
        count += 1
        if dry_run:
            yield f"[dry-run] {out_file}"
            continue
        os.makedirs(output_dir, exist_ok=True)
        with open(out_file, "w") as f:
            f.write(_make_frontmatter(rec))
            f.write("\n")
            f.write(_make_body(rec))
        yield out_file
        if limit and count >= limit:
            break


def main():
    parser = argparse.ArgumentParser(description="Convert capture JSONL queue to review-draft Markdown files")
    parser.add_argument("--queue-path",
                        default=os.path.expanduser("/home/lifeos/LifeOS_Capture_Buffer/00_Raw/captures.jsonl"),
                        help="Path to captures JSONL queue")
    parser.add_argument("--output-dir",
                        default=os.path.expanduser("/home/lifeos/LifeOS_Capture_Buffer/01_Processed/manual_markdown"),
                        help="Output directory for Markdown files")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--limit", type=int, default=None, help="Max captures to process")
    parser.add_argument("--capture-id", default=None, help="Process only a specific capture ID")
    args = parser.parse_args()

    for result in process_queue(
        args.queue_path,
        args.output_dir,
        dry_run=args.dry_run,
        limit=args.limit,
        capture_id=args.capture_id,
    ):
        print(result)


if __name__ == "__main__":
    main()
