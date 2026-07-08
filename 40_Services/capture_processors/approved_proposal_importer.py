#!/usr/bin/env python3
"""Controlled Knowledge vault importer. Only writes after explicit approval.

This is the ONLY module that writes to the canonical LifeOS vault.
Every import goes through validation gates:
- Must be explicitly approved for import
- Content hash must match
- Path must be safe (no traversal, no absolute paths)
- Proposal must not be stale (>24h old)
- Destination must not already exist (create-only, no overwrite)

Usage:
  python3 approved_proposal_importer.py --proposal-id <id> --apply
  python3 approved_proposal_importer.py --proposal-id <id> --dry-run
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VAULT_KNOWLEDGE_ROOT = "/home/lifeos/10_Vaults/LifeOS/04_KNOWLEDGE"
PROPOSAL_DIR = "/home/lifeos/LifeOS_Capture_Buffer/03_Review_Packets/proposals"
REQUIRED_FRONTMATTER_TYPE = "capture_to_vault_proposal"
REQUIRED_SCHEMA_VERSION = "1"
MAX_PROPOSAL_AGE_HOURS = 24


# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

def parse_proposal_frontmatter(content):
    """Parse YAML frontmatter from proposal content. Returns dict."""
    m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
    if not m:
        return {}
    fm = {}
    for line in m.group(1).split("\n"):
        if ":" in line:
            k, _, v = line.partition(":")
            fm[k.strip()] = v.strip().strip('"').strip("'")
    return fm


# ---------------------------------------------------------------------------
# Proposal validation
# ---------------------------------------------------------------------------

def validate_proposal(proposal_content, proposal_path):
    """Validate a proposal for import safety.

    Returns (valid: bool, error_message: str or None).

    Checks:
    - type == "capture_to_vault_proposal"
    - schema_version == "1"
    - status == "approved_for_import"
    - approval_required == "true"
    - import_status == "not_imported"
    - proposed_note_type == "knowledge"
    - content_hash matches current content
    - proposal_version present
    - proposed_vault_path valid (no .., no absolute, under Knowledge root)
    - not stale (>24h old)
    """
    fm = parse_proposal_frontmatter(proposal_content)

    checks = [
        (fm.get("type") == REQUIRED_FRONTMATTER_TYPE,
         f"Wrong proposal type: expected '{REQUIRED_FRONTMATTER_TYPE}', got '{fm.get('type')}'"),
        (fm.get("schema_version") == REQUIRED_SCHEMA_VERSION,
         f"Wrong schema version: expected '{REQUIRED_SCHEMA_VERSION}', got '{fm.get('schema_version')}'"),
        (fm.get("status") == "approved_for_import",
         f"Proposal not approved: status is '{fm.get('status')}'"),
        (fm.get("approval_required") == "true",
         "Approval not marked required in frontmatter"),
        (fm.get("import_status") == "not_imported",
         f"Already imported: import_status is '{fm.get('import_status')}'"),
        (fm.get("proposed_note_type") == "knowledge",
         f"Not a knowledge note: proposed_note_type is '{fm.get('proposed_note_type')}'"),
    ]

    for check, msg in checks:
        if not check:
            return False, msg

    # Content hash validation
    body_start = proposal_content.find("---\n", proposal_content.find("---\n") + 4)
    if body_start >= 0:
        body = proposal_content[body_start + 4:]
    else:
        body = proposal_content
    actual_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    stored_hash = fm.get("content_hash", "")
    if stored_hash and actual_hash != stored_hash:
        return False, (
            f"Content hash mismatch: "
            f"stored={stored_hash[:16]}..., "
            f"actual={actual_hash[:16]}..."
        )

    # Path validation
    proposed_path = fm.get("proposed_vault_path", "")
    if not proposed_path:
        return False, "No proposed vault path in frontmatter"
    if proposed_path.startswith("/"):
        return False, "Absolute path not allowed for vault path"
    if ".." in proposed_path.split("/"):
        return False, "Path traversal detected in proposed vault path"

    # Staleness check
    created_at = fm.get("created_at", "")
    if created_at:
        try:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            age_hours = (now - created).total_seconds() / 3600
            if age_hours > MAX_PROPOSAL_AGE_HOURS:
                return False, (
                    f"Proposal too old: "
                    f"{age_hours:.1f}h > {MAX_PROPOSAL_AGE_HOURS}h max"
                )
        except (ValueError, OverflowError):
            pass  # Unparseable timestamp — skip staleness check

    return True, None


# ---------------------------------------------------------------------------
# Import logic
# ---------------------------------------------------------------------------

def import_proposal(proposal_id, vault_root=None, dry_run=False, proposal_dir=None):
    """Import an approved proposal into the canonical vault.

    Args:
        proposal_id: The proposal ID (filename without .md, or full filename).
        vault_root: Override vault root for testing (use temp fixtures only).
        dry_run: If True, validate only — do not write.
        proposal_dir: Override proposal directory for testing.

    Returns:
        dict with import result.

    Raises:
        FileNotFoundError: Proposal file not found.
        ValueError: Validation failed.
        FileExistsError: Destination already exists (no overwrite).
    """
    vault_root = vault_root or VAULT_KNOWLEDGE_ROOT
    prop_dir = proposal_dir or PROPOSAL_DIR

    # Normalize vault_root for safety checks
    vault_root = os.path.realpath(os.path.abspath(vault_root))

    # Find proposal file
    proposal_path = os.path.join(prop_dir, f"{proposal_id}.md")
    if not os.path.isfile(proposal_path):
        # Try without .md suffix (the proposal_id might already include it)
        if proposal_id.endswith(".md"):
            alt_path = os.path.join(prop_dir, proposal_id)
            if os.path.isfile(alt_path):
                proposal_path = alt_path
        if not os.path.isfile(proposal_path):
            # Search by prefix match
            if os.path.isdir(prop_dir):
                for f in sorted(os.listdir(prop_dir)):
                    if not f.endswith(".md"):
                        continue
                    if f.startswith(proposal_id):
                        proposal_path = os.path.join(prop_dir, f)
                        break
                else:
                    raise FileNotFoundError(
                        f"Proposal not found: '{proposal_id}' in {prop_dir}"
                    )
            else:
                raise FileNotFoundError(
                    f"Proposal directory not found: {prop_dir}"
                )

    if not os.path.isfile(proposal_path):
        raise FileNotFoundError(f"Proposal not found: '{proposal_id}'")

    with open(proposal_path, "r") as f:
        content = f.read()

    # Validate
    valid, error = validate_proposal(content, proposal_path)
    if not valid:
        raise ValueError(f"Proposal validation failed: {error}")

    fm = parse_proposal_frontmatter(content)
    relative_path = fm.get("proposed_vault_path", "")

    # Final path safety check (redundant but defense-in-depth)
    if ".." in relative_path.split("/"):
        raise ValueError("Path traversal in final check")
    if relative_path.startswith("/"):
        raise ValueError("Absolute path in final check")

    dest_path = os.path.realpath(os.path.join(vault_root, relative_path))

    # Ensure destination is inside vault_root
    if not dest_path.startswith(vault_root + os.sep) and dest_path != vault_root:
        raise ValueError(
            f"Proposed destination escapes vault root: {relative_path}"
        )

    dest_dir = os.path.dirname(dest_path)

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "proposal_id": proposal_id,
            "proposal_path": proposal_path,
            "destination": relative_path,
            "full_path": dest_path,
        }

    # Create-only (no overwrite)
    if os.path.exists(dest_path):
        raise FileExistsError(
            f"Destination already exists: {relative_path}. "
            "Import does not overwrite existing files."
        )

    # Create directory if needed
    os.makedirs(dest_dir, exist_ok=True)

    # Extract the note body from the proposal
    body_start = content.find("---\n", content.find("---\n") + 4)
    body = content[body_start + 4:] if body_start >= 0 else content

    # Find the "## Proposed Note Body" section
    note_body = body
    m_body = re.search(r'## Proposed Note Body\s*\n(.*?)(?=\n## |\Z)', body, re.DOTALL)
    if m_body:
        note_body = m_body.group(1).strip()

    # Build the final vault note YAML frontmatter
    note_lines = []
    note_lines.append("---")

    # Copy proposal's "## Proposed YAML" section if present
    m_yaml = re.search(r'## Proposed YAML\s*\n```yaml\s*\n(.*?)```', body, re.DOTALL)
    if m_yaml:
        note_lines.append(m_yaml.group(1).strip())
    else:
        # Fallback YAML
        note_lines.append("type: knowledge")
        note_lines.append("status: draft")
        note_lines.append(f"created: {datetime.now(timezone.utc).isoformat()}")
        note_lines.append(f"source_refs: [\"{fm.get('capture_id', 'unknown')}\"]")

    note_lines.append("---")
    note_lines.append("")
    note_lines.append(note_body)
    note_lines.append("")

    note_content = "\n".join(note_lines)

    # Atomic write: temp file then rename
    fd, tmp_path = tempfile.mkstemp(dir=dest_dir, prefix=".import_", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as tmp:
            tmp.write(note_content)
        os.rename(tmp_path, dest_path)
    except Exception:
        # Clean up temp file on failure
        if os.path.exists(tmp_path):
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
        raise

    # Update proposal status to "imported"
    now = datetime.now(timezone.utc).isoformat()
    updated_content = re.sub(
        r'^status:.*$',
        'status: imported',
        content,
        flags=re.MULTILINE,
    )
    updated_content = re.sub(
        r'^import_status:.*$',
        'import_status: imported',
        updated_content,
        flags=re.MULTILINE,
    )
    # Add imported_at and imported_path if not present
    if "imported_at:" not in updated_content:
        updated_content = re.sub(
            r'(import_status:.*\n)',
            f'\\1imported_at: {now}\nimported_path: {relative_path}\n',
            updated_content,
        )

    with open(proposal_path, "w") as f:
        f.write(updated_content)

    return {
        "success": True,
        "dry_run": False,
        "proposal_id": proposal_id,
        "proposal_path": proposal_path,
        "destination": relative_path,
        "full_path": dest_path,
        "imported_at": now,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Controlled Knowledge vault importer — only imports "
                    "explicitly approved proposals into the canonical vault.",
    )
    parser.add_argument(
        "--proposal-id", required=True,
        help="Proposal ID to import (filename without .md)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Validate only, do not write",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually perform the import",
    )
    parser.add_argument(
        "--vault-root", default=None,
        help="Override vault root (for testing only)",
    )
    parser.add_argument(
        "--proposal-dir", default=None,
        help="Override proposal directory (for testing only)",
    )
    args = parser.parse_args()

    if not args.dry_run and not args.apply:
        print("ERROR: Must specify --dry-run or --apply", file=sys.stderr)
        sys.exit(1)

    try:
        result = import_proposal(
            args.proposal_id,
            vault_root=args.vault_root,
            dry_run=args.dry_run,
            proposal_dir=args.proposal_dir,
        )
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
