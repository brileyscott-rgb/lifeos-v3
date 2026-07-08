"""
Tests for the deterministic Knowledge Curator (V0).

All tests verify that the curation produces the expected output
structure with required fields. The curator uses only deterministic
pattern matching — no AI/LLM calls are mocked because none are made.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.knowledge_curator import curate_knowledge


class TestCurateKnowledge(unittest.TestCase):
    """Test the deterministic knowledge curation function."""

    def setUp(self):
        self.capture_metadata = {
            "capture_id": "cap_test_abc123",
            "source": "telegram",
            "created_at": "2026-07-08T12:34:00Z",
        }

    def test_curation_produces_required_fields(self):
        """The returned dict must have title, yaml_frontmatter, body_sections."""
        result = curate_knowledge(
            "Kubernetes is a container orchestration platform.",
            self.capture_metadata,
        )
        self.assertIn("title", result)
        self.assertIn("yaml_frontmatter", result)
        self.assertIn("body_sections", result)

    def test_body_sections_has_required_keys(self):
        """Body sections must include all required content areas."""
        result = curate_knowledge(
            "Docker is a platform for building and running containers. It uses namespaces and cgroups for isolation.",
            self.capture_metadata,
        )
        sections = result["body_sections"]
        self.assertIn("summary", sections)
        self.assertIn("definition_context", sections)
        self.assertIn("key_details", sections)
        self.assertIn("why_it_matters", sections)
        self.assertIn("how_it_connects", sections)
        self.assertIn("source_trail", sections)
        self.assertIn("related_concepts", sections)
        self.assertIn("review_notes", sections)

    def test_yaml_frontmatter_has_required_fields(self):
        """YAML frontmatter must include standard metadata fields."""
        result = curate_knowledge(
            "Python is a high-level programming language.",
            self.capture_metadata,
        )
        fm = result["yaml_frontmatter"]
        self.assertEqual(fm["type"], "knowledge")
        self.assertEqual(fm["status"], "draft")
        self.assertEqual(fm["domain"], "knowledge")
        self.assertIn("created", fm)
        self.assertIn("source_refs", fm)
        self.assertIn("tags", fm)
        self.assertTrue(fm["approval_required"])

    def test_title_from_first_line(self):
        """Title should be derived from the first line of capture text."""
        result = curate_knowledge(
            "Docker Container Architecture\n\nDocker uses a client-server architecture.",
            self.capture_metadata,
        )
        self.assertTrue(len(result["title"]) > 0)
        self.assertIn("Docker", result["title"])

    def test_summary_first_200_chars(self):
        """Summary should be the first 200 characters of capture text."""
        short_text = "A brief note about something."
        result = curate_knowledge(short_text, self.capture_metadata)
        self.assertIn("A brief note", result["body_sections"]["summary"])

    def test_with_mcp_context(self):
        """With MCP context, how_it_connects should reference the state."""
        result = curate_knowledge(
            "Linux is an operating system kernel.",
            self.capture_metadata,
            working_state_summary="Pending captures: 5. Event log lines: 100.",
        )
        self.assertIn("Pending captures", result["body_sections"]["how_it_connects"])

    def test_without_mcp_context(self):
        """Without MCP context, how_it_connects should have a generic message."""
        result = curate_knowledge(
            "Linux is an operating system kernel.",
            self.capture_metadata,
        )
        self.assertIn("No working state summary", result["body_sections"]["how_it_connects"])

    def test_empty_text(self):
        """Empty text should produce safe defaults, not crash."""
        result = curate_knowledge("", self.capture_metadata)
        self.assertIn("title", result)
        self.assertIn("yaml_frontmatter", result)
        self.assertIn("body_sections", result)

    def test_none_text(self):
        """None text should produce safe defaults, not crash."""
        result = curate_knowledge(None, self.capture_metadata)
        self.assertIn("title", result)

    def test_no_metadata(self):
        """Missing metadata should still produce valid output."""
        result = curate_knowledge("Some knowledge text.", {})
        self.assertIn("title", result)
        fm = result["yaml_frontmatter"]
        self.assertIn("source_refs", fm)
        # source_refs should default to ["unknown"]
        self.assertEqual(fm["source_refs"], ["unknown"])

    def test_definition_extraction(self):
        """Text with 'is a' should produce definition context."""
        result = curate_knowledge(
            "API is a set of defined rules that enables different applications to communicate with each other.",
            self.capture_metadata,
        )
        context = result["body_sections"]["definition_context"]
        self.assertNotEqual(context, "No definitional sentences identified in the capture text.")

    def test_technical_term_extraction(self):
        """Text with technical terms should produce key details."""
        result = curate_knowledge(
            "Docker containers provide isolated environments for applications using Linux namespaces.",
            self.capture_metadata,
        )
        details = result["body_sections"]["key_details"]
        self.assertNotEqual(details, "No specific technical details extracted.")

    def test_related_concepts_extraction(self):
        """Text with capitalized phrases should produce related concepts."""
        result = curate_knowledge(
            "Docker Container Runtime uses Linux Kernel features for isolation.",
            self.capture_metadata,
        )
        concepts = result["body_sections"]["related_concepts"]
        self.assertTrue(len(concepts) > 0)

    def test_review_notes_mentions_v0(self):
        """Review notes should indicate V0 deterministic nature."""
        result = curate_knowledge("Some text", self.capture_metadata)
        review = result["body_sections"]["review_notes"]
        self.assertIn("V0", review)
        self.assertIn("No AI/LLM", review)

    def test_source_trail_includes_metadata(self):
        """Source trail should include capture metadata when available."""
        result = curate_knowledge(
            "Test capture",
            {"capture_id": "cap_test_123", "source": "desktop", "created_at": "2026-07-08T12:00:00Z"},
        )
        trail = result["body_sections"]["source_trail"]
        self.assertIn("cap_test_123", trail)
        self.assertIn("desktop", trail)

    def test_very_long_text(self):
        """Very long text should be handled without error."""
        long_text = "Docker is a container platform. " * 500
        result = curate_knowledge(long_text, self.capture_metadata)
        self.assertIn("title", result)
        # Summary should be truncated
        self.assertTrue(len(result["body_sections"]["summary"]) >= 200)


if __name__ == "__main__":
    unittest.main()
