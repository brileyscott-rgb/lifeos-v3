import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SRC = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.realpath(SRC))
import lifeos_repo_radar


class TestLoadRegistry(unittest.TestCase):

    def setUp(self):
        self.valid_registry = {
            "meta": {"version": "1.0.0"},
            "candidates": [
                {
                    "name": "test-server",
                    "url": "https://example.com",
                    "category": "mcp-server",
                    "risk_tier": "A0",
                    "install_status": "not-installed",
                    "activation_status": "inactive",
                    "recommendation": "sandbox",
                    "why_interesting": "Test candidate.",
                    "proposed_use": "Testing only.",
                    "secrets_required": False,
                    "docker_socket_required": False,
                    "filesystem_access": False,
                    "network_exposure": "none",
                    "browser_automation": False,
                    "shell_execution": False,
                    "tests_available": True,
                    "recent_maintenance": True,
                    "clear_license": True,
                    "read_only_mode": "inherently read-only",
                    "sandboxable": True,
                    "clean_removal": True,
                    "reality_check_notes": "Safe test candidate.",
                },
                {
                    "name": "high-risk-repo",
                    "url": "https://example.com/risky",
                    "category": "mcp-server",
                    "risk_tier": "A5-critical",
                    "install_status": "not-installed",
                    "activation_status": "inactive",
                    "recommendation": "reject",
                    "why_interesting": "Dangerous testing candidate.",
                    "proposed_use": "None.",
                    "secrets_required": True,
                    "docker_socket_required": True,
                    "filesystem_access": True,
                    "network_exposure": "outbound",
                    "browser_automation": True,
                    "shell_execution": True,
                    "tests_available": False,
                    "recent_maintenance": False,
                    "clear_license": False,
                    "read_only_mode": False,
                    "sandboxable": False,
                    "clean_removal": False,
                    "reality_check_notes": "Rejected candidate.",
                },
                {
                    "name": "discovery-index-repo",
                    "url": "https://example.com/discovery",
                    "category": "discovery-index",
                    "risk_tier": "A0",
                    "install_status": "not-installed",
                    "activation_status": "inactive",
                    "recommendation": "discovery_reference",
                    "why_interesting": "Reference list.",
                    "proposed_use": "Awareness only.",
                    "secrets_required": False,
                    "docker_socket_required": False,
                    "filesystem_access": False,
                    "network_exposure": "none",
                    "browser_automation": False,
                    "shell_execution": False,
                    "tests_available": False,
                    "recent_maintenance": True,
                    "clear_license": True,
                    "read_only_mode": "inherently read-only",
                    "sandboxable": False,
                    "clean_removal": True,
                    "reality_check_notes": "Discovery index only.",
                },
            ],
            "catalog_groups": {
                "approved_for_sandbox": ["test-server"],
                "rejected_for_now": ["high-risk-repo"],
            },
        }

    def test_loads_valid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(self.valid_registry, f)
            tmp_path = f.name
        try:
            registry = lifeos_repo_radar.load_registry(tmp_path)
            self.assertEqual(registry["meta"]["version"], "1.0.0")
            self.assertEqual(len(registry["candidates"]), 3)
        finally:
            os.unlink(tmp_path)

    def test_raises_on_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            lifeos_repo_radar.load_registry("/nonexistent/path.json")

    def test_raises_on_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json {{{")
            tmp_path = f.name
        try:
            with self.assertRaises(json.JSONDecodeError):
                lifeos_repo_radar.load_registry(tmp_path)
        finally:
            os.unlink(tmp_path)


class TestFilterCandidates(unittest.TestCase):

    def setUp(self):
        self.candidates = [
            {
                "name": "alpha",
                "category": "mcp-server",
                "risk_tier": "A0",
                "recommendation": "sandbox",
            },
            {
                "name": "beta",
                "category": "mcp-server",
                "risk_tier": "A3",
                "recommendation": "defer",
            },
            {
                "name": "gamma",
                "category": "proxy",
                "risk_tier": "A2",
                "recommendation": "sandbox",
            },
            {
                "name": "delta",
                "category": "discovery-index",
                "risk_tier": "A0",
                "recommendation": "discovery_reference",
            },
            {
                "name": "epsilon",
                "category": "mcp-server",
                "risk_tier": "A5-critical",
                "recommendation": "reject",
            },
        ]

    def test_no_filters_returns_all(self):
        result = lifeos_repo_radar.filter_candidates(self.candidates)
        self.assertEqual(len(result), 5)

    def test_filter_by_risk_tier_exact(self):
        result = lifeos_repo_radar.filter_candidates(self.candidates, risk_tier="A0")
        self.assertEqual(len(result), 2)
        names = {c["name"] for c in result}
        self.assertEqual(names, {"alpha", "delta"})

    def test_filter_by_risk_tier_substring(self):
        result = lifeos_repo_radar.filter_candidates(
            self.candidates, risk_tier="A5"
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "epsilon")

    def test_filter_by_risk_tier_case_insensitive(self):
        result = lifeos_repo_radar.filter_candidates(
            self.candidates, risk_tier="a0"
        )
        self.assertEqual(len(result), 2)

    def test_filter_by_recommendation(self):
        result = lifeos_repo_radar.filter_candidates(
            self.candidates, recommendation="sandbox"
        )
        self.assertEqual(len(result), 2)
        names = {c["name"] for c in result}
        self.assertEqual(names, {"alpha", "gamma"})

    def test_filter_by_recommendation_case_insensitive(self):
        result = lifeos_repo_radar.filter_candidates(
            self.candidates, recommendation="SANDBOX"
        )
        self.assertEqual(len(result), 2)

    def test_filter_by_category(self):
        result = lifeos_repo_radar.filter_candidates(
            self.candidates, category="mcp-server"
        )
        self.assertEqual(len(result), 3)

    def test_filter_combined(self):
        result = lifeos_repo_radar.filter_candidates(
            self.candidates,
            risk_tier="A0",
            recommendation="sandbox",
            category="mcp-server",
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["name"], "alpha")

    def test_filter_no_match_returns_empty(self):
        result = lifeos_repo_radar.filter_candidates(
            self.candidates, risk_tier="A4"
        )
        self.assertEqual(len(result), 0)


class TestTextOutput(unittest.TestCase):

    def setUp(self):
        self.candidate = {
            "name": "test-server",
            "url": "https://example.com",
            "category": "mcp-server",
            "risk_tier": "A0",
            "install_status": "not-installed",
            "activation_status": "inactive",
            "recommendation": "sandbox",
            "secrets_required": False,
            "docker_socket_required": False,
            "filesystem_access": False,
            "network_exposure": "none",
            "browser_automation": False,
            "shell_execution": False,
            "tests_available": True,
            "recent_maintenance": True,
            "clear_license": True,
            "read_only_mode": "inherently read-only",
            "sandboxable": True,
            "clean_removal": True,
            "why_interesting": "Test candidate.",
            "proposed_use": "Testing only.",
            "reality_check_notes": "Safe test.",
        }

    def test_format_text_summary_has_header(self):
        result = lifeos_repo_radar.format_text_summary([self.candidate])
        self.assertIn("Name", result)
        self.assertIn("Category", result)
        self.assertIn("Risk", result)
        self.assertIn("Rec", result)

    def test_format_text_summary_has_candidate_name(self):
        result = lifeos_repo_radar.format_text_summary([self.candidate])
        self.assertIn("test-server", result)

    def test_format_text_summary_shows_total(self):
        result = lifeos_repo_radar.format_text_summary([self.candidate])
        self.assertIn("Total: 1", result)

    def test_format_text_summary_empty_list(self):
        result = lifeos_repo_radar.format_text_summary([])
        self.assertIn("Total: 0", result)

    def test_format_text_detail_has_all_fields(self):
        result = lifeos_repo_radar.format_text_detail(self.candidate)
        self.assertIn("Name:", result)
        self.assertIn("URL:", result)
        self.assertIn("Category:", result)
        self.assertIn("Risk Tier:", result)
        self.assertIn("Recommendation:", result)
        self.assertIn("Secrets Required:", result)
        self.assertIn("Docker Socket:", result)
        self.assertIn("Filesystem Access:", result)
        self.assertIn("Network Exposure:", result)
        self.assertIn("Browser Automation:", result)
        self.assertIn("Shell Execution:", result)
        self.assertIn("Tests Available:", result)
        self.assertIn("Recent Maintenance:", result)
        self.assertIn("Clear License:", result)
        self.assertIn("Read-Only Mode:", result)
        self.assertIn("Sandboxable:", result)
        self.assertIn("Clean Removal:", result)
        self.assertIn("Why Interesting:", result)
        self.assertIn("Proposed Use:", result)
        self.assertIn("Reality Check:", result)

    def test_format_text_detail_contains_candidate_name(self):
        result = lifeos_repo_radar.format_text_detail(self.candidate)
        self.assertIn("test-server", result)


class TestDefaultRegistryExists(unittest.TestCase):

    def test_default_registry_path_is_absolute(self):
        path = lifeos_repo_radar.DEFAULT_REGISTRY
        self.assertTrue(path.is_absolute())

    def test_default_registry_filename(self):
        path = lifeos_repo_radar.DEFAULT_REGISTRY
        self.assertEqual(path.name, "lifeos_repo_radar_registry.json")

    def test_default_registry_parent_dir(self):
        path = lifeos_repo_radar.DEFAULT_REGISTRY.parent
        self.assertEqual(path.name, "scripts")


class TestScriptIsReadOnly(unittest.TestCase):
    """Verify the radar script never reads secrets, env, or tokens."""

    def test_no_env_access_in_source(self):
        src_path = os.path.join(
            os.path.dirname(__file__), "..", "lifeos_repo_radar.py"
        )
        with open(src_path, "r") as f:
            source = f.read()
        self.assertNotIn("environ", source)
        self.assertNotIn("os.getenv", source)
        self.assertNotIn("os.environ", source)
        self.assertNotIn("dotenv", source)
        self.assertNotIn(".env", source)

    def test_no_network_imports_in_source(self):
        src_path = os.path.join(
            os.path.dirname(__file__), "..", "lifeos_repo_radar.py"
        )
        with open(src_path, "r") as f:
            source = f.read()
        self.assertNotIn("import requests", source)
        self.assertNotIn("from requests", source)
        self.assertNotIn("import urllib", source)
        self.assertNotIn("from urllib", source)
        self.assertNotIn("import socket", source)
        self.assertNotIn("from socket", source)
        self.assertNotIn("import http.client", source)
        self.assertNotIn("from http.client", source)

    def test_no_subprocess_in_source(self):
        src_path = os.path.join(
            os.path.dirname(__file__), "..", "lifeos_repo_radar.py"
        )
        with open(src_path, "r") as f:
            source = f.read()
        self.assertNotIn("subprocess", source)
        self.assertNotIn("os.system", source)

    def test_stdlib_only_imports(self):
        src_path = os.path.join(
            os.path.dirname(__file__), "..", "lifeos_repo_radar.py"
        )
        with open(src_path, "r") as f:
            source = f.read()
        allowed = {"argparse", "json", "sys", "pathlib", "Path", "os"}
        for line in source.split("\n"):
            line = line.strip()
            if line.startswith("import ") or line.startswith("from "):
                if line.startswith("from "):
                    module = line.split("from ")[1].split(" import")[0].strip()
                else:
                    module = line.split("import ")[1].split(" as")[0].strip()
                self.assertIn(
                    module,
                    allowed,
                    f"Unexpected import '{module}' in radar script",
                )


if __name__ == "__main__":
    unittest.main()
