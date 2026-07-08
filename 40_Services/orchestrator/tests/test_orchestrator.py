"""
Tests for the Capture Review Orchestrator (V0).

Tests cover capture resolution, proposal flow, dry-run mode, approval
flow, and rejection flow. External dependencies (Action API, filesystem)
are mocked. No real vault writes, no real API calls.
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Ensure the orchestrator is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import capture_review_orchestrator as orch


class TestResolveCapture(unittest.TestCase):
    """Test the resolve_capture function with mocked Action API."""

    def setUp(self):
        self.sample_capture = {
            "success": True,
            "capture": {
                "capture_id": "cap_test_abc123",
                "file_name": "test.md",
                "content": "Docker is a container platform.",
                "frontmatter": {
                    "capture_id": "cap_test_abc123",
                    "source": "telegram",
                    "created_at": "2026-07-08T12:00:00Z",
                    "status": "pending_review",
                },
            },
        }

    @patch.object(orch, '_action_api_get')
    def test_resolve_latest(self, mock_get):
        """'latest' should resolve the most recent pending capture."""
        mock_get.return_value = self.sample_capture
        result = orch.resolve_capture("latest")
        self.assertEqual(result["capture_id"], "cap_test_abc123")
        mock_get.assert_called_with("/captures/pending/latest")

    @patch.object(orch, '_action_api_get')
    def test_resolve_by_index(self, mock_get):
        """Numeric index should resolve by 1-based position."""
        mock_get.return_value = self.sample_capture
        result = orch.resolve_capture("1")
        self.assertEqual(result["capture_id"], "cap_test_abc123")
        mock_get.assert_called_with("/captures/pending/1")

    @patch.object(orch, '_action_api_get')
    def test_resolve_by_capture_id(self, mock_get):
        """Capture ID should resolve by exact match."""
        mock_get.return_value = self.sample_capture
        result = orch.resolve_capture("cap_test_abc123")
        self.assertEqual(result["capture_id"], "cap_test_abc123")
        mock_get.assert_called_with("/captures/cap_test_abc123")

    @patch.object(orch, '_action_api_get')
    def test_resolve_not_found_raises(self, mock_get):
        """API error should raise ValueError."""
        mock_get.return_value = {"success": False, "error": "capture_not_found"}
        with self.assertRaises(ValueError) as ctx:
            orch.resolve_capture("nonexistent")
        self.assertIn("Failed to resolve", str(ctx.exception))

    @patch.object(orch, '_action_api_get')
    def test_resolve_empty_latest_raises(self, mock_get):
        """Empty pending list should raise ValueError."""
        mock_get.return_value = {
            "success": True,
            "pending": [],
            "count": 0,
        }
        # When API returns [] and latest path returns no capture
        with self.assertRaises(ValueError):
            orch.resolve_capture("latest")


class TestProposeKnowledge(unittest.TestCase):
    """Test the propose_knowledge flow."""

    def setUp(self):
        self.sample_capture = {
            "success": True,
            "capture": {
                "capture_id": "cap_test_abc123",
                "file_name": "test.md",
                "content": "Docker is a platform for containerization. It uses Linux kernel features for process isolation.",
                "frontmatter": {
                    "capture_id": "cap_test_abc123",
                    "source": "telegram",
                    "created_at": "2026-07-08T12:00:00Z",
                    "status": "pending_review",
                },
            },
        }

    @patch.object(orch, 'resolve_capture')
    def test_propose_knowledge_successful(self, mock_resolve):
        """Full knowledge proposal flow should succeed."""
        mock_resolve.return_value = self.sample_capture["capture"]

        with tempfile.TemporaryDirectory() as tmpdir:
            # Override PROPOSAL_DIR to use temp dir
            original_proposal_dir = orch.PROPOSAL_DIR
            orch.PROPOSAL_DIR = tmpdir

            try:
                result = orch.propose_knowledge("latest", dry_run=False)
                self.assertTrue(result["success"])
                self.assertIn("proposal_id", result)
                self.assertIn("file_path", result)
                self.assertEqual(result["classification"], "knowledge")
                # Verify the file was actually written
                self.assertTrue(os.path.exists(result["file_path"]))
            finally:
                orch.PROPOSAL_DIR = original_proposal_dir

    @patch.object(orch, 'resolve_capture')
    def test_propose_knowledge_dry_run(self, mock_resolve):
        """Dry run should not write to disk."""
        mock_resolve.return_value = self.sample_capture["capture"]

        with tempfile.TemporaryDirectory() as tmpdir:
            original_proposal_dir = orch.PROPOSAL_DIR
            orch.PROPOSAL_DIR = tmpdir

            try:
                result = orch.propose_knowledge("latest", dry_run=True)
                self.assertTrue(result["success"])
                self.assertTrue(result["dry_run"])
                self.assertIn("proposal", result)
                # Verify no files were written
                files = os.listdir(tmpdir)
                self.assertEqual(len(files), 0)
            finally:
                orch.PROPOSAL_DIR = original_proposal_dir

    @patch.object(orch, 'resolve_capture')
    def test_propose_non_knowledge_fails(self, mock_resolve):
        """Non-knowledge classification should fail in V0."""
        capture = dict(self.sample_capture["capture"])
        capture["content"] = "https://example.com/article"
        mock_resolve.return_value = capture

        result = orch.propose_knowledge("latest")
        self.assertFalse(result["success"])
        self.assertIn("V0 only supports knowledge", result["error"])

    @patch.object(orch, 'resolve_capture')
    def test_propose_resolve_failure(self, mock_resolve):
        """Capture resolution failure should return error."""
        mock_resolve.side_effect = ValueError("capture_not_found")
        result = orch.propose_knowledge("nonexistent")
        self.assertFalse(result["success"])
        self.assertIn("capture_not_found", result["error"])

    @patch.object(orch, 'resolve_capture')
    def test_propose_empty_text(self, mock_resolve):
        """Empty capture text should return error."""
        capture = dict(self.sample_capture["capture"])
        capture["content"] = ""
        mock_resolve.return_value = capture

        result = orch.propose_knowledge("latest")
        self.assertFalse(result["success"])

    @patch.object(orch, 'resolve_capture')
    def test_propose_force_new(self, mock_resolve):
        """Force new should create a fresh proposal regardless."""
        mock_resolve.return_value = self.sample_capture["capture"]

        with tempfile.TemporaryDirectory() as tmpdir:
            original_proposal_dir = orch.PROPOSAL_DIR
            orch.PROPOSAL_DIR = tmpdir

            try:
                # First proposal
                result1 = orch.propose_knowledge("latest", force_new=True)
                self.assertTrue(result1["success"])
                # Second proposal should succeed with force_new
                result2 = orch.propose_knowledge("latest", force_new=True)
                self.assertTrue(result2["success"])
            finally:
                orch.PROPOSAL_DIR = original_proposal_dir


class TestProposalIO(unittest.TestCase):
    """Test proposal file I/O operations."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.original_proposal_dir = orch.PROPOSAL_DIR
        orch.PROPOSAL_DIR = self.tmpdir

        self.sample_proposal = {
            "proposal_id": "prop_test_123",
            "frontmatter": {
                "type": "review_packet",
                "schema_version": "0.1",
                "status": "pending",
                "capture_id": "cap_test_abc",
                "content_hash": "abc123",
                "version": "0.1",
                "source_refs": ["cap_test_abc"],
                "proposed_vault_path": "03_KNOWLEDGE/AI/Test.md",
                "classification": "knowledge",
                "created_at": "2026-07-08T12:00:00Z",
            },
            "body": (
                "## Proposal Summary\nTest proposal.\n\n"
                "## Source Capture\ncap_test_abc\n\n"
                "## Classification\nknowledge\n\n"
                "## MCP Context Used\nTest context.\n\n"
                "## Proposed Vault File\nTest.md\n\n"
                "## Proposed YAML\n```yaml\ntype: knowledge\n```\n\n"
                "## Proposed Note Body\nContent.\n\n"
                "## Uncertainty / Risks\nNone.\n\n"
                "## QA Checklist\n- [ ] Review\n\n"
                "## Human Decision\nPending.\n\n"
                "## Revision Instructions\nRevise.\n\n"
                "## Import Plan\nImport.\n\n"
                "## Rollback Plan\nRollback.\n\n"
                "## Safety Notice\nBuffer-only.\n"
            ),
            "status": "pending",
            "classification": {"classification": "knowledge", "confidence": "medium"},
        }

    def tearDown(self):
        orch.PROPOSAL_DIR = self.original_proposal_dir
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_save_and_load_proposal(self):
        """Saving and loading a proposal should be symmetric."""
        file_path = orch.save_proposal("prop_test_123", self.sample_proposal)
        self.assertTrue(os.path.exists(file_path))

        loaded = orch.load_proposal("prop_test_123")
        self.assertEqual(loaded["proposal_id"], "prop_test_123")
        self.assertEqual(loaded["frontmatter"]["status"], "pending")
        self.assertIn("Test proposal", loaded["body"])

    def test_load_nonexistent_proposal(self):
        """Loading a nonexistent proposal should raise FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            orch.load_proposal("prop_nonexistent")

    def test_update_proposal_status(self):
        """Updating a proposal status should persist."""
        orch.save_proposal("prop_test_123", self.sample_proposal)

        updated = orch.update_proposal_status("prop_test_123", "approved")
        self.assertEqual(updated["status"], "approved")
        self.assertEqual(updated["frontmatter"]["status"], "approved")

        # Reload and verify
        reloaded = orch.load_proposal("prop_test_123")
        self.assertEqual(reloaded["frontmatter"]["status"], "approved")

    def test_update_with_extra_fields(self):
        """Extra fields should be added to frontmatter on update."""
        orch.save_proposal("prop_test_123", self.sample_proposal)

        updated = orch.update_proposal_status(
            "prop_test_123",
            "rejected",
            extra_fields={"rejection_reason": "Not useful", "priority": "low"},
        )
        self.assertEqual(updated["frontmatter"]["status"], "rejected")
        self.assertEqual(updated["frontmatter"]["rejection_reason"], "Not useful")
        self.assertEqual(updated["frontmatter"]["priority"], "low")


class TestProposalApproval(unittest.TestCase):
    """Test the approve-import flow."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.original_proposal_dir = orch.PROPOSAL_DIR
        orch.PROPOSAL_DIR = self.tmpdir

        self.sample_proposal = {
            "proposal_id": "prop_approve_test",
            "frontmatter": {
                "type": "review_packet",
                "schema_version": "0.1",
                "status": "pending",
                "capture_id": "cap_test_abc",
                "content_hash": "abc123",
                "version": "0.1",
                "source_refs": ["cap_test_abc"],
                "proposed_vault_path": "03_KNOWLEDGE/AI/Test_Note.md",
                "classification": "knowledge",
                "created_at": "2026-07-08T12:00:00Z",
            },
            "body": (
                "## Proposal Summary\nTest proposal.\n\n"
                "## Source Capture\ncap_test\n\n"
                "## Classification\nknowledge\n\n"
                "## MCP Context Used\nTest.\n\n"
                "## Proposed Vault File\nTest.md\n\n"
                "## Proposed YAML\ntype: knowledge\n\n"
                "## Proposed Note Body\nContent.\n\n"
                "## Uncertainty / Risks\nLow.\n\n"
                "## QA Checklist\n- [ ] Review\n\n"
                "## Human Decision\nPending.\n\n"
                "## Revision Instructions\nRevise.\n\n"
                "## Import Plan\nImport.\n\n"
                "## Rollback Plan\nRollback.\n\n"
                "## Safety Notice\nBuffer-only.\n"
            ),
            "status": "pending",
            "proposed_vault_path": "03_KNOWLEDGE/AI/Test_Note.md",
            "classification": {"classification": "knowledge", "confidence": "medium"},
        }

    def tearDown(self):
        orch.PROPOSAL_DIR = self.original_proposal_dir
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_approve_import_successful(self):
        """Approving a valid proposal should succeed."""
        orch.save_proposal("prop_approve_test", self.sample_proposal)

        from agents.qa_verifier import verify_proposal
        proposal = orch.load_proposal("prop_approve_test")

        # Build a proposal dict that qa_verifier expects
        qa_proposal = {
            "status": proposal["frontmatter"].get("status", "pending"),
            "frontmatter": proposal["frontmatter"],
            "body": proposal["body"],
            "proposed_vault_path": proposal["frontmatter"].get("proposed_vault_path", ""),
            "classification": {"confidence": "medium"},
        }

        qa_result = verify_proposal(qa_proposal)
        self.assertIn(qa_result["verdict"], ("pass", "pass_with_warnings"))

        # Update to approved
        updated = orch.update_proposal_status("prop_approve_test", "approved")
        self.assertEqual(updated["frontmatter"]["status"], "approved")

    def test_reject_proposal(self):
        """Rejecting a proposal should update its status."""
        orch.save_proposal("prop_approve_test", self.sample_proposal)

        updated = orch.update_proposal_status(
            "prop_approve_test",
            "rejected",
            extra_fields={"rejection_reason": "Content not useful"},
        )
        self.assertEqual(updated["status"], "rejected")
        self.assertEqual(updated["frontmatter"]["rejection_reason"], "Content not useful")

    def test_revise_proposal(self):
        """Marking a proposal for revision should update its status."""
        orch.save_proposal("prop_approve_test", self.sample_proposal)

        updated = orch.update_proposal_status(
            "prop_approve_test",
            "revised",
            extra_fields={"revision_instruction": "Change the title to be more specific"},
        )
        self.assertEqual(updated["status"], "revised")
        self.assertIn("revision_instruction", updated["frontmatter"])


class TestBuildProposalPacket(unittest.TestCase):
    """Test the build_proposal_packet function."""

    def test_build_proposal_produces_required_fields(self):
        """Building a proposal should produce all required fields."""
        capture_text = "Docker is a container platform."
        capture_data = {
            "capture_id": "cap_test_123",
            "file_name": "test.md",
            "content": capture_text,
            "frontmatter": {"source": "telegram"},
        }
        classification = {
            "classification": "knowledge",
            "confidence": "medium",
            "reasons": ["Contains technical terms"],
        }
        curated = {
            "title": "Docker Container Platform",
            "yaml_frontmatter": {
                "type": "knowledge",
                "status": "draft",
                "domain": "knowledge",
                "created": "2026-07-08T12:00:00Z",
                "source_refs": ["cap_test_123"],
                "tags": ["knowledge"],
                "approval_required": True,
            },
            "body_sections": {
                "summary": "Docker is a container platform.",
                "definition_context": "Definition here.",
                "key_details": "Key details.",
                "why_it_matters": "It matters.",
                "how_it_connects": "It connects.",
                "source_trail": "Source info.",
                "related_concepts": "Docker, Containers",
                "review_notes": "V0 deterministic.",
            },
        }
        import_path = "03_KNOWLEDGE/Systems/Docker_Container_Platform.md"

        proposal = orch.build_proposal_packet(
            capture_text, capture_data, classification, curated, import_path,
        )

        self.assertIn("proposal_id", proposal)
        self.assertIn("frontmatter", proposal)
        self.assertIn("body", proposal)
        self.assertIn("status", proposal)
        self.assertEqual(proposal["status"], "pending")
        self.assertTrue(proposal["proposal_id"].startswith("prop_"))

    def test_build_proposal_body_has_required_sections(self):
        """The proposal body must include all required sections."""
        capture_text = "Test capture"
        capture_data = {"capture_id": "cap_test", "frontmatter": {"source": "test"}}
        classification = {"classification": "knowledge", "confidence": "medium", "reasons": []}
        curated = {
            "title": "Test",
            "yaml_frontmatter": {"type": "knowledge", "status": "draft", "source_refs": ["cap_test"], "tags": [], "approval_required": True, "domain": "knowledge", "created": "now"},
            "body_sections": {k: k for k in ["summary", "definition_context", "key_details", "why_it_matters", "how_it_connects", "source_trail", "related_concepts", "review_notes"]},
        }
        import_path = "03_KNOWLEDGE/Reference/Test.md"

        proposal = orch.build_proposal_packet(
            capture_text, capture_data, classification, curated, import_path,
        )

        body = proposal["body"]
        self.assertIn("Proposal Summary", body)
        self.assertIn("Source Capture", body)
        self.assertIn("Classification", body)
        self.assertIn("Proposed Vault File", body)
        self.assertIn("Safety Notice", body)
        self.assertIn("buffer-only", body.lower())


class TestYamlSerialization(unittest.TestCase):
    """Test the stdlib YAML serialization helpers."""

    def test_yaml_dump_simple(self):
        """Simple dict should serialize to valid YAML-like frontmatter."""
        data = {"type": "knowledge", "status": "draft", "count": 42}
        result = orch._yaml_dump(data)
        self.assertTrue(result.startswith("---"))
        self.assertTrue(result.endswith("---"))
        self.assertIn("type: knowledge", result)
        self.assertIn("status: draft", result)

    def test_yaml_dump_with_list(self):
        """Dict with list values should serialize correctly."""
        data = {"tags": ["knowledge", "docker"], "count": 3}
        result = orch._yaml_dump(data)
        self.assertIn("tags:", result)
        self.assertIn("knowledge", result)
        self.assertIn("docker", result)

    def test_yaml_dump_with_boolean(self):
        """Booleans should serialize as true/false."""
        data = {"approval_required": True, "optional": False}
        result = orch._yaml_dump(data)
        self.assertIn("true", result)
        self.assertIn("false", result)


class TestGatherMCPContext(unittest.TestCase):
    """Test the MCP context gathering function."""

    def test_returns_expected_keys(self):
        """MCP context should return capture_metadata, template_catalog, working_state_summary."""
        capture_data = {
            "capture_id": "cap_test",
            "frontmatter": {"source": "telegram", "created_at": "now"},
        }
        context = orch._gather_mcp_context(capture_data)
        self.assertIn("capture_metadata", context)
        self.assertIn("template_catalog", context)
        self.assertIn("working_state_summary", context)

    def test_mcp_unavailable_graceful(self):
        """When MCP is unavailable, should still return valid context."""
        capture_data = {"capture_id": "cap_test"}
        context = orch._gather_mcp_context(capture_data)
        self.assertIn("capture_metadata", context)
        # working_state_summary may be None if Status API unavailable
        self.assertIn("template_catalog", context)


if __name__ == "__main__":
    unittest.main()
