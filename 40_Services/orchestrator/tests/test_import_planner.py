"""
Tests for the deterministic Import Planner (V0).

All tests verify path planning behavior, category selection, filename
sanitization, path traversal prevention, and fallback to Reference.
No real vault access — all path operations are logical only.
"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.import_planner import plan_import_path, KNOWLEDGE_CATEGORIES


class TestPlanImportPath(unittest.TestCase):
    """Test the deterministic import path planning."""

    def test_returns_vault_relative_path(self):
        """The returned path must be vault-relative, not absolute."""
        path = plan_import_path("My Note", "docker containers are cool")
        self.assertFalse(path.startswith("/"))
        self.assertFalse(path.startswith(".."))
        self.assertFalse("\\" in path)

    def test_path_starts_with_knowledge_root(self):
        """All paths must be under 04_KNOWLEDGE/."""
        path = plan_import_path("Some Title", "random text")
        self.assertTrue(path.startswith("04_KNOWLEDGE/"))

    def test_path_ends_with_md_extension(self):
        """All paths must end with .md."""
        path = plan_import_path("Note Title", "content")
        self.assertTrue(path.endswith(".md"))

    def test_docker_maps_to_systems(self):
        """Docker-related text should map to Systems category."""
        path = plan_import_path("Docker Basics", "Docker is a container runtime")
        self.assertIn("/Systems/", path)

    def test_kubernetes_maps_to_systems(self):
        """Kubernetes text should map to Systems category."""
        path = plan_import_path("K8s Intro", "Kubernetes orchestrates containers")
        self.assertIn("/Systems/", path)

    def test_api_maps_to_software(self):
        """API-related text should map to Software category."""
        # Use only Software-specific keywords, avoid Systems keywords like "service"
        path = plan_import_path("REST API Design", "APIs with programming languages and frameworks")
        self.assertIn("/Software/", path)

    def test_ai_ml_maps_to_ai(self):
        """AI/ML text should map to AI category."""
        path = plan_import_path("Machine Learning Intro", "Machine learning is a subset of AI")
        self.assertIn("/AI/", path)

    def test_network_maps_to_networking(self):
        """Network-related text should map to Networking."""
        path = plan_import_path("TCP Protocol", "TCP is a connection-oriented protocol")
        self.assertIn("/Networking/", path)

    def test_hardware_maps_to_hardware(self):
        """Hardware text should map to Hardware."""
        path = plan_import_path("ESP32 Setup", "ESP32 is a microcontroller")
        self.assertIn("/Hardware/", path)

    def test_lifeos_maps_to_lifeos(self):
        """LifeOS-related text should map to LifeOS."""
        path = plan_import_path("Capture Pipeline", "The LifeOS capture pipeline processes")
        self.assertIn("/LifeOS/", path)

    def test_no_match_falls_back_to_reference(self):
        """Text with no keyword matches should fall back to Reference."""
        path = plan_import_path("Random Thought", "completely unrelated text here nothing matches")
        self.assertIn("/Reference/", path)

    def test_filename_sanitized(self):
        """Special characters in title should be sanitized."""
        path = plan_import_path("Docker: What <is> it?", "docker containers")
        self.assertNotIn(":", path)
        self.assertNotIn("<", path)
        self.assertNotIn(">", path)
        self.assertNotIn("?", path)

    def test_empty_title(self):
        """Empty title should produce a safe default."""
        path = plan_import_path("", "some content")
        self.assertTrue(path.endswith(".md"))
        self.assertTrue(len(path) > 0)

    def test_no_path_traversal(self):
        """Path traversal attempts in title should not affect the output path."""
        path = plan_import_path("../../../etc/passwd", "docker")
        self.assertFalse(".." in path.split("/"))
        self.assertTrue(path.startswith("04_KNOWLEDGE/"))

    def test_category_scoring_prefers_specificity(self):
        """More keyword matches should score higher and win."""
        # Text heavy on Systems keywords vs Software keywords
        path = plan_import_path(
            "Docker System",
            "docker containers run on linux systems using kernel features",
        )
        # "docker", "linux", "kernel", "system", "container" = Systems > Software
        self.assertIn("/Systems/", path)

    def test_python_maps_to_software(self):
        """Python-related text should map to Software."""
        path = plan_import_path("Python Guide", "Python is a programming language")
        self.assertIn("/Software/", path)

    def test_long_title_truncated_in_filename(self):
        """Very long titles should be truncated to safe length."""
        long_title = "A" * 300
        path = plan_import_path(long_title, "docker")
        filename = path.split("/")[-1]
        # Should not exceed 200 chars for name + .md
        self.assertTrue(len(filename) <= 204)  # 200 + ".md"

    def test_lifeos_mcp_reference(self):
        """MCP and orchestrator keywords should map to LifeOS."""
        path = plan_import_path("MCP Integration", "MCP servers and orchestrators in LifeOS")
        self.assertIn("/LifeOS/", path)


class TestKnowledgeCategories(unittest.TestCase):
    """Test the KNOWLEDGE_CATEGORIES structure."""

    def test_categories_have_keywords(self):
        """All non-Reference categories should have keywords."""
        for category, keywords in KNOWLEDGE_CATEGORIES.items():
            if category != "Reference":
                self.assertTrue(len(keywords) > 0,
                                f"Category '{category}' has no keywords")

    def test_reference_has_no_keywords(self):
        """Reference category should be empty — it's the fallback."""
        self.assertEqual(KNOWLEDGE_CATEGORIES["Reference"], [])

    def test_keywords_are_lowercase(self):
        """All keywords should be lowercase for case-insensitive matching."""
        for category, keywords in KNOWLEDGE_CATEGORIES.items():
            for kw in keywords:
                self.assertEqual(kw, kw.lower(),
                                 f"Keyword '{kw}' in '{category}' is not lowercase")


if __name__ == "__main__":
    unittest.main()
