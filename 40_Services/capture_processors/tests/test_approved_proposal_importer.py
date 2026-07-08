#!/usr/bin/env python3
"""Tests for approved_proposal_importer.py — temp fixtures only, NEVER real vault."""

import hashlib
import json
import os
import re
import sys
import tempfile
import unittest

# Ensure the capture_processors package is importable
SYS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SYS_PATH = os.path.realpath(SYS_PATH)
sys.path.insert(0, SYS_PATH)

import approved_proposal_importer as importer


# ---------------------------------------------------------------------------
# Test helper
# ---------------------------------------------------------------------------

def make_test_proposal(temp_dir, status="approved_for_import",
                       proposed_path="AI/Test_Note.md",
                       note_type="knowledge", content_hash=None,
                       proposal_id="prop_test_001",
                       extra_frontmatter=None,
                       body_override=None):
    """Create a test proposal Markdown file in temp_dir.

    The content_hash is computed over the body (everything after the
    closing --- of frontmatter), matching what validate_proposal()
    actually checks. Use content_hash=None for auto-computation.

    Returns the path to the created proposal file.
    """
    body = body_override or "## Proposed Note Body\n\nThis is test content.\n"

    # The body after closing --- includes the heading and a trailing newline
    # (the f-string template adds a newline before the closing """)
    full_body = f"# Proposal\n\n{body}\n"
    h = content_hash or hashlib.sha256(full_body.encode()).hexdigest()

    extra_lines = ""
    if extra_frontmatter:
        for k, v in extra_frontmatter.items():
            extra_lines += f"{k}: {v}\n"

    packet = f"""---
type: capture_to_vault_proposal
schema_version: 1
proposal_id: {proposal_id}
proposal_version: 1
status: {status}
capture_id: cap_test_123
capture_ref: test_ref
created_at: 2026-07-08T12:00:00Z
classification: knowledge
approval_required: true
import_status: not_imported
proposed_note_type: {note_type}
proposed_vault_path: {proposed_path}
content_hash: {h}
{extra_lines}---
# Proposal

{body}
"""
    os.makedirs(temp_dir, exist_ok=True)
    path = os.path.join(temp_dir, f"{proposal_id}.md")
    with open(path, "w") as f:
        f.write(packet)
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestApprovedProposalImporter(unittest.TestCase):

    def setUp(self):
        """Create isolated temp directories for vault and proposals."""
        self.tmp_root = tempfile.mkdtemp(prefix="lifeos_importer_test_")
        self.vault_root = os.path.join(self.tmp_root, "vault")
        self.proposal_dir = os.path.join(self.tmp_root, "proposals")
        os.makedirs(self.vault_root, exist_ok=True)
        os.makedirs(self.proposal_dir, exist_ok=True)

    def tearDown(self):
        """Clean up temp directories."""
        import shutil
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def _create_and_import(self, **kwargs):
        """Helper: create a test proposal and call import_proposal.

        Keyword args for make_test_proposal go through directly.
        dry_run is passed to import_proposal, not make_test_proposal.
        """
        dry_run = kwargs.pop("dry_run", False)
        make_test_proposal(self.proposal_dir, **kwargs)
        return importer.import_proposal(
            "prop_test_001",
            vault_root=self.vault_root,
            proposal_dir=self.proposal_dir,
            dry_run=dry_run,
        )

    # ------------------------------------------------------------------
    # 1. dry_run writes nothing
    # ------------------------------------------------------------------

    def test_dry_run_writes_nothing(self):
        """Dry-run should validate but not create any files."""
        result = self._create_and_import(dry_run=True)
        self.assertTrue(result["success"])
        self.assertTrue(result["dry_run"])
        # No file should be created in vault
        dest = os.path.join(self.vault_root, "AI/Test_Note.md")
        self.assertFalse(os.path.exists(dest),
                         "Dry-run should not create destination file")
        # Proposal file should NOT be modified (status still not_imported)
        proposal_path = os.path.join(self.proposal_dir, "prop_test_001.md")
        with open(proposal_path, "r") as f:
            content = f.read()
        fm = importer.parse_proposal_frontmatter(content)
        self.assertEqual(fm.get("import_status"), "not_imported")

    # ------------------------------------------------------------------
    # 2. Approved proposal imports successfully
    # ------------------------------------------------------------------

    def test_approved_proposal_imports(self):
        """An approved proposal should import to the temp vault."""
        result = self._create_and_import()
        self.assertTrue(result["success"])
        self.assertFalse(result.get("dry_run", False))
        self.assertEqual(result["destination"], "AI/Test_Note.md")

        # Verify file was created
        dest = os.path.join(self.vault_root, "AI/Test_Note.md")
        self.assertTrue(os.path.exists(dest),
                        f"Expected file at {dest}")

        # Verify content
        with open(dest, "r") as f:
            content = f.read()
        self.assertIn("This is test content.", content)
        self.assertIn("---", content)  # Has frontmatter

        # Verify proposal was updated
        proposal_path = os.path.join(self.proposal_dir, "prop_test_001.md")
        with open(proposal_path, "r") as f:
            updated = f.read()
        fm = importer.parse_proposal_frontmatter(updated)
        self.assertEqual(fm.get("status"), "imported")
        self.assertEqual(fm.get("import_status"), "imported")
        self.assertIn("imported_at", fm)
        self.assertIn("imported_path", fm)

    # ------------------------------------------------------------------
    # 3. Pending proposal refused
    # ------------------------------------------------------------------

    def test_pending_proposal_refused(self):
        """A non-approved proposal should be rejected."""
        make_test_proposal(self.proposal_dir, status="pending_human_review")
        with self.assertRaises(ValueError) as ctx:
            importer.import_proposal(
                "prop_test_001",
                vault_root=self.vault_root,
                proposal_dir=self.proposal_dir,
            )
        self.assertIn("not approved", str(ctx.exception))

    # ------------------------------------------------------------------
    # 4. Stale hash refused
    # ------------------------------------------------------------------

    def test_stale_hash_refused(self):
        """A mismatched content hash should be rejected."""
        # Create proposal with a hash that doesn't match the body
        make_test_proposal(
            self.proposal_dir,
            content_hash="abc123def4567890abc123def4567890abc123def4567890abc123def4567890",
        )
        with self.assertRaises(ValueError) as ctx:
            importer.import_proposal(
                "prop_test_001",
                vault_root=self.vault_root,
                proposal_dir=self.proposal_dir,
            )
        self.assertIn("hash mismatch", str(ctx.exception).lower())

    # ------------------------------------------------------------------
    # 5. Path traversal refused
    # ------------------------------------------------------------------

    def test_path_traversal_refused(self):
        """A proposal with ../ in path should be rejected."""
        make_test_proposal(self.proposal_dir, proposed_path="../escape/note.md")
        with self.assertRaises(ValueError) as ctx:
            importer.import_proposal(
                "prop_test_001",
                vault_root=self.vault_root,
                proposal_dir=self.proposal_dir,
            )
        self.assertIn("traversal", str(ctx.exception).lower())

    def test_double_dot_path_traversal_refused(self):
        """A proposal with deep .. traversal should be rejected."""
        make_test_proposal(
            self.proposal_dir,
            proposed_path="AI/../../etc/passwd.md",
        )
        with self.assertRaises(ValueError) as ctx:
            importer.import_proposal(
                "prop_test_001",
                vault_root=self.vault_root,
                proposal_dir=self.proposal_dir,
            )
        self.assertIn("traversal", str(ctx.exception).lower())

    # ------------------------------------------------------------------
    # 6. Overwrite refused
    # ------------------------------------------------------------------

    def test_overwrite_refused(self):
        """Importing to an existing path should raise FileExistsError."""
        # First import
        make_test_proposal(self.proposal_dir, proposal_id="prop_first")
        importer.import_proposal(
            "prop_first",
            vault_root=self.vault_root,
            proposal_dir=self.proposal_dir,
        )

        # Create a second proposal targeting the same path
        make_test_proposal(self.proposal_dir, proposal_id="prop_second")

        # Second import to same path should fail
        with self.assertRaises(FileExistsError) as ctx:
            importer.import_proposal(
                "prop_second",
                vault_root=self.vault_root,
                proposal_dir=self.proposal_dir,
            )
        self.assertIn("already exists", str(ctx.exception))

    # ------------------------------------------------------------------
    # 7. Non-knowledge proposal refused
    # ------------------------------------------------------------------

    def test_non_knowledge_refused(self):
        """A non-knowledge proposal should be rejected."""
        make_test_proposal(self.proposal_dir, note_type="project")
        with self.assertRaises(ValueError) as ctx:
            importer.import_proposal(
                "prop_test_001",
                vault_root=self.vault_root,
                proposal_dir=self.proposal_dir,
            )
        self.assertIn("Not a knowledge note", str(ctx.exception))

    # ------------------------------------------------------------------
    # 8. Successful import updates proposal status
    # ------------------------------------------------------------------

    def test_successful_import_updates_proposal_status(self):
        """After import, the proposal's frontmatter should show imported."""
        self._create_and_import()  # This does the import

        proposal_path = os.path.join(self.proposal_dir, "prop_test_001.md")
        with open(proposal_path, "r") as f:
            content = f.read()

        fm = importer.parse_proposal_frontmatter(content)
        self.assertEqual(fm.get("status"), "imported")
        self.assertEqual(fm.get("import_status"), "imported")
        self.assertIn("imported_at", fm)
        self.assertIn("imported_path", fm)
        self.assertEqual(fm.get("imported_path"), "AI/Test_Note.md")

    # ------------------------------------------------------------------
    # 9. Canonical write blocked (escape vault root)
    # ------------------------------------------------------------------

    def test_canonical_write_blocked(self):
        """Writing outside the vault root should be blocked."""
        # Set up a proposal that would resolve outside vault_root
        make_test_proposal(
            self.proposal_dir,
            proposed_path="../outside_vault/note.md",
        )
        with self.assertRaises(ValueError) as ctx:
            importer.import_proposal(
                "prop_test_001",
                vault_root=self.vault_root,
                proposal_dir=self.proposal_dir,
            )
        self.assertIn("traversal", str(ctx.exception).lower())

    # ------------------------------------------------------------------
    # 10. No arbitrary (absolute) vault paths
    # ------------------------------------------------------------------

    def test_no_arbitrary_vault_paths(self):
        """Absolute path in proposed_vault_path should be rejected."""
        make_test_proposal(
            self.proposal_dir,
            proposed_path="/etc/evil_note.md",
        )
        with self.assertRaises(ValueError) as ctx:
            importer.import_proposal(
                "prop_test_001",
                vault_root=self.vault_root,
                proposal_dir=self.proposal_dir,
            )
        self.assertIn("Absolute path", str(ctx.exception))

    # ------------------------------------------------------------------
    # Additional boundary tests
    # ------------------------------------------------------------------

    def test_already_imported_refused(self):
        """A proposal with import_status=imported should be rejected."""
        make_test_proposal(
            self.proposal_dir,
            status="approved_for_import",
            extra_frontmatter={"import_status": "imported"},
        )
        # Remove the default import_status line that conflicts
        proposal_path = os.path.join(self.proposal_dir, "prop_test_001.md")
        with open(proposal_path, "r") as f:
            content = f.read()
        content = content.replace("import_status: not_imported\n", "")
        with open(proposal_path, "w") as f:
            f.write(content)

        with self.assertRaises(ValueError) as ctx:
            importer.import_proposal(
                "prop_test_001",
                vault_root=self.vault_root,
                proposal_dir=self.proposal_dir,
            )
        self.assertIn("Already imported", str(ctx.exception))

    def test_wrong_schema_version_refused(self):
        """Schema version != 1 should be rejected."""
        make_test_proposal(self.proposal_dir)
        proposal_path = os.path.join(self.proposal_dir, "prop_test_001.md")
        with open(proposal_path, "r") as f:
            content = f.read()
        content = content.replace("schema_version: 1", "schema_version: 2")
        with open(proposal_path, "w") as f:
            f.write(content)

        with self.assertRaises(ValueError) as ctx:
            importer.import_proposal(
                "prop_test_001",
                vault_root=self.vault_root,
                proposal_dir=self.proposal_dir,
            )
        self.assertIn("Wrong schema version", str(ctx.exception))

    def test_wrong_proposal_type_refused(self):
        """Wrong type should be rejected."""
        make_test_proposal(self.proposal_dir)
        proposal_path = os.path.join(self.proposal_dir, "prop_test_001.md")
        with open(proposal_path, "r") as f:
            content = f.read()
        content = content.replace(
            "type: capture_to_vault_proposal",
            "type: something_else",
        )
        with open(proposal_path, "w") as f:
            f.write(content)

        with self.assertRaises(ValueError) as ctx:
            importer.import_proposal(
                "prop_test_001",
                vault_root=self.vault_root,
                proposal_dir=self.proposal_dir,
            )
        self.assertIn("Wrong proposal type", str(ctx.exception))

    def test_approval_not_required_refused(self):
        """If approval_required != 'true', should be rejected."""
        make_test_proposal(self.proposal_dir)
        proposal_path = os.path.join(self.proposal_dir, "prop_test_001.md")
        with open(proposal_path, "r") as f:
            content = f.read()
        content = content.replace(
            "approval_required: true",
            "approval_required: false",
        )
        with open(proposal_path, "w") as f:
            f.write(content)

        with self.assertRaises(ValueError) as ctx:
            importer.import_proposal(
                "prop_test_001",
                vault_root=self.vault_root,
                proposal_dir=self.proposal_dir,
            )
        self.assertIn("Approval not marked required", str(ctx.exception))

    def test_stale_proposal_refused(self):
        """Proposal older than 24h should be rejected."""
        make_test_proposal(self.proposal_dir)
        proposal_path = os.path.join(self.proposal_dir, "prop_test_001.md")
        with open(proposal_path, "r") as f:
            content = f.read()
        # Set created_at to 48 hours ago
        content = content.replace(
            "created_at: 2026-07-08T12:00:00Z",
            "created_at: 2026-07-06T12:00:00Z",
        )
        with open(proposal_path, "w") as f:
            f.write(content)

        with self.assertRaises(ValueError) as ctx:
            importer.import_proposal(
                "prop_test_001",
                vault_root=self.vault_root,
                proposal_dir=self.proposal_dir,
            )
        self.assertIn("too old", str(ctx.exception).lower())

    def test_empty_proposed_path_refused(self):
        """Missing proposed_vault_path should be rejected."""
        make_test_proposal(self.proposal_dir)
        proposal_path = os.path.join(self.proposal_dir, "prop_test_001.md")
        with open(proposal_path, "r") as f:
            content = f.read()
        # Remove the proposed_vault_path line
        content = re.sub(r'proposed_vault_path:.*\n', '', content)
        with open(proposal_path, "w") as f:
            f.write(content)

        with self.assertRaises(ValueError) as ctx:
            importer.import_proposal(
                "prop_test_001",
                vault_root=self.vault_root,
                proposal_dir=self.proposal_dir,
            )
        self.assertIn("No proposed vault path", str(ctx.exception))

    def test_file_not_found(self):
        """Non-existent proposal should raise FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            importer.import_proposal(
                "nonexistent_proposal_xyz",
                vault_root=self.vault_root,
                proposal_dir=self.proposal_dir,
            )

    def test_nested_directories_created(self):
        """Import should create intermediate directories."""
        make_test_proposal(
            self.proposal_dir,
            proposed_path="AI/Sub/Deep/Nested_Note.md",
        )
        result = importer.import_proposal(
            "prop_test_001",
            vault_root=self.vault_root,
            proposal_dir=self.proposal_dir,
        )
        self.assertTrue(result["success"])
        dest = os.path.join(self.vault_root, "AI/Sub/Deep/Nested_Note.md")
        self.assertTrue(os.path.exists(dest))

    def test_proposed_yaml_section_preserved(self):
        """If proposal has ## Proposed YAML block, use it in output."""
        custom_body = (
            "## Proposed YAML\n"
            "```yaml\n"
            "type: knowledge\n"
            "status: draft\n"
            "tags: [test, ai]\n"
            "author: lifeos\n"
            "```\n\n"
            "## Proposed Note Body\n\n"
            "This is curated content.\n"
        )
        make_test_proposal(
            self.proposal_dir,
            proposed_path="AI/Yaml_Note.md",
            proposal_id="prop_test_yaml",
            body_override=custom_body,
        )

        result = importer.import_proposal(
            "prop_test_yaml",
            vault_root=self.vault_root,
            proposal_dir=self.proposal_dir,
        )
        self.assertTrue(result["success"])

        dest = os.path.join(self.vault_root, "AI/Yaml_Note.md")
        with open(dest, "r") as f:
            note_content = f.read()
        self.assertIn("tags: [test, ai]", note_content)
        self.assertIn("author: lifeos", note_content)
        self.assertIn("This is curated content.", note_content)

if __name__ == "__main__":
    unittest.main()
