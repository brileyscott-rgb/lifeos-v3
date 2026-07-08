"""
Tests for the deterministic Capture Classifier (V0).

All tests use isolated temp directories and pure function calls.
No real vault access, no Action API, no AI/LLM calls.
"""

import unittest
import sys
import os

# Ensure the orchestrator is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.classifier import classify_capture, is_importable, VALID_CLASSIFICATIONS


class TestClassifyCapture(unittest.TestCase):
    """Test the deterministic classification rules."""

    def test_empty_text(self):
        """Empty or None text should return unknown with low confidence."""
        result = classify_capture("")
        self.assertEqual(result["classification"], "unknown")
        self.assertEqual(result["confidence"], "low")

        result = classify_capture(None)
        self.assertEqual(result["classification"], "unknown")
        self.assertEqual(result["confidence"], "low")

    def test_rule1_url_detection(self):
        """Rule 1: Text starting with http:// or https:// -> source_capture."""
        result = classify_capture("https://example.com/article")
        self.assertEqual(result["classification"], "source_capture")
        self.assertEqual(result["confidence"], "medium")

        result = classify_capture("http://localhost:8080/api")
        self.assertEqual(result["classification"], "source_capture")
        self.assertEqual(result["confidence"], "medium")

    def test_rule2_github_repo(self):
        """Rule 2: GitHub repo pattern -> tool_repo_candidate."""
        result = classify_capture("Check out https://github.com/user/repo for the code")
        self.assertEqual(result["classification"], "tool_repo_candidate")
        self.assertEqual(result["confidence"], "high")

        # github.com in the middle of text still matches
        result = classify_capture("I found a great tool: github.com/org/project is awesome")
        self.assertEqual(result["classification"], "tool_repo_candidate")

    def test_rule3_idea(self):
        """Rule 3: Text starting with 'idea:' or mentioning 'idea'."""
        result = classify_capture("idea: build a monitoring dashboard for lifeos")
        self.assertEqual(result["classification"], "idea")
        self.assertEqual(result["confidence"], "medium")

        result = classify_capture("I have an idea about improving the capture pipeline")
        self.assertEqual(result["classification"], "idea")

    def test_rule4_task(self):
        """Rule 4: Text starting with 'task:' or 'todo:'."""
        result = classify_capture("task: write unit tests for classifier")
        self.assertEqual(result["classification"], "task")
        self.assertEqual(result["confidence"], "high")

        result = classify_capture("todo: refactor the capture pipeline")
        self.assertEqual(result["classification"], "task")
        self.assertEqual(result["confidence"], "high")

    def test_rule5_project_update(self):
        """Rule 5: Text containing project/progress/milestone/deliverable."""
        result = classify_capture("The project is on track for milestone completion")
        self.assertEqual(result["classification"], "project_update")
        self.assertEqual(result["confidence"], "medium")

        result = classify_capture("Made progress on the deliverable")
        self.assertEqual(result["classification"], "project_update")

        result = classify_capture("Sprint completed and all tasks are done")
        self.assertEqual(result["classification"], "project_update")

    def test_rule6_definitional_knowledge(self):
        """Rule 6: Text with definitional patterns -> knowledge."""
        result = classify_capture("Docker is a containerization platform that simplifies deployment")
        self.assertEqual(result["classification"], "knowledge")
        self.assertEqual(result["confidence"], "medium")

        result = classify_capture("In machine learning, gradient descent refers to an optimization algorithm")
        self.assertEqual(result["classification"], "knowledge")

        result = classify_capture("Recursion is defined as a function that calls itself")
        self.assertEqual(result["classification"], "knowledge")

    def test_rule7_technical_terms_knowledge(self):
        """Rule 7: Text with technical terms -> knowledge."""
        result = classify_capture("Kubernetes handles container orchestration at scale")
        self.assertEqual(result["classification"], "knowledge")
        self.assertEqual(result["confidence"], "medium")

        result = classify_capture("PostgreSQL supports ACID transactions and complex queries")
        self.assertEqual(result["classification"], "knowledge")

        result = classify_capture("Prometheus and Grafana provide monitoring and observability")
        self.assertEqual(result["classification"], "knowledge")

    def test_rule8_reference(self):
        """Rule 8: Text starting with 'ref:' or 'reference:'."""
        # Use text without technical terms so rule 7 doesn't fire first
        result = classify_capture("ref: a good video about networking concepts")
        self.assertEqual(result["classification"], "reference")
        self.assertEqual(result["confidence"], "medium")

        result = classify_capture("reference: paper on organizational strategies")
        self.assertEqual(result["classification"], "reference")

    def test_rule9_short_unknown(self):
        """Rule 9: Short text (< 140 chars) without other matches -> unknown."""
        result = classify_capture("cool stuff")
        self.assertEqual(result["classification"], "unknown")
        self.assertEqual(result["confidence"], "low")

        result = classify_capture("hmm interesting")
        self.assertEqual(result["classification"], "unknown")

    def test_rule10_default_knowledge(self):
        """Rule 10: Default fallback -> knowledge with low confidence."""
        # Text must avoid: technical terms, "is a"/"are"/"defined as" patterns,
        # project/progress/milestone keywords, URLs, idea:/task:/ref: prefixes,
        # github.com, and must be >140 chars to pass rule 9.
        long_text = (
            "Wow this really seems like something quite interesting but honestly "
            "I cannot quite figure out exactly where to place it yet perhaps later "
            "after some thought things will become clearer and then maybe I will "
            "have a better sense of direction regarding how to organize everything "
            "into the correct categories going forward from here on out eventually "
            "once enough additional context has been gathered over time hopefully "
            "the situation will resolve itself through further consideration yeah"
        ) * 2
        result = classify_capture(long_text)
        self.assertEqual(result["classification"], "knowledge")
        self.assertEqual(result["confidence"], "low")

    def test_priority_ordering(self):
        """URL should take priority over technical terms."""
        result = classify_capture("https://docs.docker.com/engine/ is about docker and containers")
        # Rule 1 (URL) should fire before Rule 7 (technical terms)
        self.assertEqual(result["classification"], "source_capture")

    def test_very_long_text(self):
        """Very long text should still classify successfully."""
        long_text = "Docker is a platform for developing, shipping, and running applications. " * 100
        result = classify_capture(long_text)
        # Should match definitional pattern (rule 6)
        self.assertEqual(result["classification"], "knowledge")

    def test_source_passed_through(self):
        """Source parameter should be accepted without error."""
        result = classify_capture("Docker is a tool", source="telegram")
        self.assertEqual(result["classification"], "knowledge")

    def test_all_valid_classifications_available(self):
        """All classification values should be in the valid list."""
        for classification in VALID_CLASSIFICATIONS:
            self.assertIn(classification, [
                "knowledge", "idea", "project_update", "task",
                "reference", "source_capture", "tool_repo_candidate", "unknown",
            ])


class TestIsImportable(unittest.TestCase):
    """Test the is_importable function."""

    def test_knowledge_is_importable(self):
        """Only 'knowledge' should be importable in V0."""
        self.assertTrue(is_importable("knowledge"))

    def test_other_classifications_not_importable(self):
        """All other classifications should not be importable in V0."""
        self.assertFalse(is_importable("idea"))
        self.assertFalse(is_importable("task"))
        self.assertFalse(is_importable("project_update"))
        self.assertFalse(is_importable("reference"))
        self.assertFalse(is_importable("source_capture"))
        self.assertFalse(is_importable("tool_repo_candidate"))
        self.assertFalse(is_importable("unknown"))
        self.assertFalse(is_importable(""))
        self.assertFalse(is_importable("nonexistent"))


if __name__ == "__main__":
    unittest.main()
