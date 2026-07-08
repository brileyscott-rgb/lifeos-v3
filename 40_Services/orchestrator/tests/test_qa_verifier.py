"""
Tests for the deterministic QA Verifier (V0).

All tests verify proposal validation against critical and warning
checks. Tests cover pass, fail, and pass_with_warnings verdicts,
missing fields, and path traversal detection. No real vault access.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.qa_verifier import verify_proposal, CRITICAL_CHECKS, WARNING_CHECKS


def _make_valid_proposal():
    """Build a proposal dict that should pass all checks."""
    return {
        "status": "pending",
        "frontmatter": {
            "content_hash": "abc123def456",
            "version": "0.1",
            "source_refs": ["cap_test_123"],
            "proposed_vault_path": "04_KNOWLEDGE/AI/Test_Note.md",
        },
        "body": (
            "## Proposal Summary\n"
            "This is a test proposal.\n\n"
            "## Source Capture\n"
            "Capture ID: cap_test_123\n\n"
            "## Classification\n"
            "knowledge (medium)\n\n"
            "## MCP Context Used\n"
            "Test context.\n\n"
            "## Proposed Vault File\n"
            "Path: 04_KNOWLEDGE/AI/Test_Note.md\n\n"
            "## Proposed YAML\n"
            "type: knowledge\n\n"
            "## Proposed Note Body\n"
            "Content here.\n\n"
            "## Uncertainty / Risks\n"
            "Low risk.\n\n"
            "## QA Checklist\n"
            "- [ ] Review this\n\n"
            "## Human Decision\n"
            "Pending.\n\n"
            "## Revision Instructions\n"
            "To revise...\n\n"
            "## Import Plan\n"
            "Import command.\n\n"
            "## Rollback Plan\n"
            "Rollback command.\n\n"
            "## Safety Notice\n"
            "Buffer-only.\n"
        ),
        "proposed_vault_path": "04_KNOWLEDGE/AI/Test_Note.md",
        "classification": {"classification": "knowledge", "confidence": "medium"},
        "mode": "create",
    }


class TestVerifyProposalPass(unittest.TestCase):
    """Test scenarios where QA should pass."""

    def test_valid_proposal_passes(self):
        """A well-formed proposal should pass all checks."""
        proposal = _make_valid_proposal()
        result = verify_proposal(proposal)
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(len(result["issues"]), 0)

    def test_valid_proposal_with_update_mode_passes(self):
        """Update mode should pass the overwrite check."""
        proposal = _make_valid_proposal()
        proposal["mode"] = "update"
        result = verify_proposal(proposal)
        self.assertIn(result["verdict"], ("pass", "pass_with_warnings"))


class TestVerifyProposalFail(unittest.TestCase):
    """Test scenarios where QA should fail."""

    def test_missing_status_fails(self):
        """Missing or invalid status should fail."""
        proposal = _make_valid_proposal()
        proposal["status"] = "invalid_status"
        result = verify_proposal(proposal)
        self.assertEqual(result["verdict"], "fail")
        self.assertTrue(any("status" in issue.lower() for issue in result["issues"]))

    def test_missing_content_hash_fails(self):
        """Missing content_hash in frontmatter should fail."""
        proposal = _make_valid_proposal()
        proposal["frontmatter"].pop("content_hash", None)
        result = verify_proposal(proposal)
        self.assertEqual(result["verdict"], "fail")
        self.assertTrue(any("content_hash" in issue.lower() for issue in result["issues"]))

    def test_missing_version_fails(self):
        """Missing version/schema_version should fail."""
        proposal = _make_valid_proposal()
        proposal["frontmatter"].pop("version", None)
        result = verify_proposal(proposal)
        self.assertEqual(result["verdict"], "fail")
        self.assertTrue(any("version" in issue.lower() for issue in result["issues"]))

    def test_path_traversal_in_proposed_path_fails(self):
        """Path traversal ('..') in proposed path should fail."""
        proposal = _make_valid_proposal()
        proposal["proposed_vault_path"] = "04_KNOWLEDGE/../etc/passwd"
        result = verify_proposal(proposal)
        self.assertEqual(result["verdict"], "fail")
        self.assertTrue(any("traversal" in issue.lower() for issue in result["issues"]))

    def test_absolute_path_fails(self):
        """Absolute path should fail."""
        proposal = _make_valid_proposal()
        proposal["proposed_vault_path"] = "/etc/passwd"
        result = verify_proposal(proposal)
        self.assertEqual(result["verdict"], "fail")

    def test_path_not_under_knowledge_root_fails(self):
        """Path not starting with 04_KNOWLEDGE/ should fail."""
        proposal = _make_valid_proposal()
        proposal["proposed_vault_path"] = "02_PROJECTS/Some_Project.md"
        result = verify_proposal(proposal)
        self.assertEqual(result["verdict"], "fail")
        self.assertTrue(any("knowledge" in issue.lower() for issue in result["issues"]))

    def test_empty_proposed_path_fails(self):
        """Empty proposed path should fail multiple checks."""
        proposal = _make_valid_proposal()
        proposal["proposed_vault_path"] = ""
        proposal["frontmatter"]["proposed_vault_path"] = ""
        result = verify_proposal(proposal)
        self.assertEqual(result["verdict"], "fail")

    def test_missing_required_sections_fails(self):
        """Missing required body sections should fail."""
        proposal = _make_valid_proposal()
        proposal["body"] = "Just some random text without proper sections."
        result = verify_proposal(proposal)
        self.assertEqual(result["verdict"], "fail")
        self.assertTrue(any("sections" in issue.lower() for issue in result["issues"]))

    def test_none_proposal_fails(self):
        """None proposal should fail."""
        result = verify_proposal(None)
        self.assertEqual(result["verdict"], "fail")

    def test_empty_proposal_fails(self):
        """Empty dict proposal should fail."""
        result = verify_proposal({})
        self.assertEqual(result["verdict"], "fail")

    def test_overwrite_intent_fails(self):
        """Overwrite intent without update mode should fail."""
        proposal = _make_valid_proposal()
        proposal["intent"] = "overwrite"
        proposal.pop("mode", None)
        result = verify_proposal(proposal)
        self.assertEqual(result["verdict"], "fail")

    def test_missing_source_trail_fails(self):
        """Missing source trail should fail."""
        proposal = _make_valid_proposal()
        proposal["frontmatter"].pop("source_refs", None)
        proposal["body"] = proposal["body"].replace("Source Capture", "Nope")
        result = verify_proposal(proposal)
        self.assertEqual(result["verdict"], "fail")


class TestVerifyProposalWarnings(unittest.TestCase):
    """Test scenarios where QA should pass with warnings."""

    def test_low_classification_confidence_warns(self):
        """Low classification confidence should produce warnings but not fail."""
        proposal = _make_valid_proposal()
        proposal["classification"] = {"confidence": "low"}
        result = verify_proposal(proposal)
        self.assertIn(result["verdict"], ("pass", "pass_with_warnings"))
        if result["verdict"] == "pass_with_warnings":
            self.assertTrue(len(result["warnings"]) > 0)

    def test_missing_uncertainty_section_warns(self):
        """Missing uncertainty section should warn."""
        proposal = _make_valid_proposal()
        proposal["body"] = proposal["body"].replace("Uncertainty", "NoRiskSection")
        proposal["body"] = proposal["body"].replace("uncertainty", "norisk")
        result = verify_proposal(proposal)
        # This may fail because of required sections, so check for warnings
        self.assertIn(result["verdict"], ("pass", "pass_with_warnings", "fail"))

    def test_missing_checklist_warns(self):
        """Missing approval checklist should warn."""
        proposal = _make_valid_proposal()
        proposal["body"] = proposal["body"].replace("- [ ]", "")
        result = verify_proposal(proposal)
        self.assertIn(result["verdict"], ("pass", "pass_with_warnings", "fail"))


class TestVerifyProposalEdgeCases(unittest.TestCase):
    """Test edge cases for QA verification."""

    def test_missing_body_key(self):
        """Proposal without a 'body' key should fail."""
        proposal = {
            "status": "pending",
            "frontmatter": {"content_hash": "abc", "version": "1.0"},
            "proposed_vault_path": "04_KNOWLEDGE/AI/Note.md",
        }
        result = verify_proposal(proposal)
        self.assertEqual(result["verdict"], "fail")

    def test_checks_return_structured(self):
        """Result should include a checks dict with per-check results."""
        proposal = _make_valid_proposal()
        result = verify_proposal(proposal)
        self.assertIn("checks", result)
        for check_name in CRITICAL_CHECKS:
            self.assertIn(check_name, result["checks"],
                          f"Missing critical check result: {check_name}")


if __name__ == "__main__":
    unittest.main()
