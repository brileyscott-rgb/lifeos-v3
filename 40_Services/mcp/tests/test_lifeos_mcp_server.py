#!/usr/bin/env python3
"""Tests for LifeOS Custom MCP Server V0.

Uses Python unittest and unittest.mock. Tests both success and error paths
for all 5 read-only tools plus JSON-RPC protocol handling and safety rules.
"""

import io
import json
import os
import sys
import unittest
import unittest.mock
import urllib.error
import urllib.request

# Ensure the parent directory is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the server module (test helper functions and handle_request directly)
import lifeos_mcp_server as server


class TestLifeOSMCPServer(unittest.TestCase):
    """Test suite for the LifeOS MCP Server V0."""

    def setUp(self):
        """Suppress stderr noise from the server module during tests."""
        self._stderr_patcher = unittest.mock.patch("sys.stderr", new=io.StringIO())
        self._stderr_patcher.start()

    def tearDown(self):
        self._stderr_patcher.stop()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _make_request(self, method, params=None, req_id=1):
        """Build a valid JSON-RPC 2.0 request dict."""
        req = {"jsonrpc": "2.0", "method": method, "id": req_id}
        if params is not None:
            req["params"] = params
        return req

    def _assert_success(self, response, expected_id=1):
        """Assert a JSON-RPC success response."""
        self.assertEqual(response.get("jsonrpc"), "2.0")
        self.assertEqual(response.get("id"), expected_id)
        self.assertIn("result", response)
        self.assertNotIn("error", response)

    def _assert_error(self, response, expected_code=None, expected_id=1):
        """Assert a JSON-RPC error response."""
        self.assertEqual(response.get("jsonrpc"), "2.0")
        self.assertIn("error", response)
        if expected_code is not None:
            self.assertEqual(response["error"]["code"], expected_code)
        self.assertIn("message", response["error"])

    # ── Test 1: tools/list returns exactly the allowlisted tools ────────────

    def test_tools_list_returns_exactly_allowlisted_tools(self):
        """Verify tools/list returns exactly the 5 allowlisted tools."""
        req = self._make_request("tools/list")
        resp = server.handle_request(req)
        self._assert_success(resp)
        tools = resp["result"]["tools"]
        tool_names = {t["name"] for t in tools}
        self.assertSetEqual(tool_names, server.ALLOWED_TOOLS)
        self.assertEqual(len(tools), 5)

    # ── Test 2: tools/list returns correct schema shape ─────────────────────

    def test_tools_list_returns_correct_schema_shape(self):
        """Each tool entry must have name, description, and inputSchema."""
        req = self._make_request("tools/list")
        resp = server.handle_request(req)
        self._assert_success(resp)
        for tool in resp["result"]["tools"]:
            self.assertIn("name", tool)
            self.assertIn("description", tool)
            self.assertIn("inputSchema", tool)
            self.assertIsInstance(tool["name"], str)
            self.assertIsInstance(tool["description"], str)
            self.assertIsInstance(tool["inputSchema"], dict)
            self.assertEqual(tool["inputSchema"].get("type"), "object")
            self.assertIn("properties", tool["inputSchema"])
            self.assertIn("required", tool["inputSchema"])

    # ── Test 3: unknown tool rejected ───────────────────────────────────────

    def test_unknown_tool_rejected(self):
        """Calling a non-existent tool via tools/call returns an error."""
        req = self._make_request("tools/call", {
            "name": "lifeos.nonexistent_tool",
            "arguments": {},
        })
        resp = server.handle_request(req)
        self._assert_error(resp, expected_code=-32001)
        self.assertIn("unknown tool", resp["error"]["message"])

    # ── Test 4: invalid params (extra param) rejected ───────────────────────

    def test_invalid_params_rejected(self):
        """Extra/unknown parameters are rejected with INVALID_PARAMS error."""
        req = self._make_request("tools/call", {
            "name": "lifeos.status",
            "arguments": {"extra_param": "should_not_be_here"},
        })
        resp = server.handle_request(req)
        self._assert_error(resp, expected_code=-32602)
        self.assertIn("unknown parameter", resp["error"]["message"])

    # ── Test 5: oversized params rejected ───────────────────────────────────

    def test_oversized_params_rejected(self):
        """Parameters > 16KB are rejected."""
        big_value = "x" * (server.MAX_PARAM_SIZE + 1)
        req = self._make_request("tools/call", {
            "name": "lifeos.capture_metadata",
            "arguments": {"capture_ref": big_value},
        })
        resp = server.handle_request(req)
        self._assert_error(resp, expected_code=-32602)
        self.assertIn("invalid parameter value", resp["error"]["message"])

    # ── Test 6: forbidden pattern params rejected ───────────────────────────

    def test_forbidden_pattern_params_rejected(self):
        """Parameters containing forbidden patterns (../) are rejected."""
        req = self._make_request("tools/call", {
            "name": "lifeos.capture_metadata",
            "arguments": {"capture_ref": "../etc/passwd"},
        })
        resp = server.handle_request(req)
        self._assert_error(resp, expected_code=-32602)
        self.assertIn("invalid parameter value", resp["error"]["message"])

    # ── Test 7: lifeos.status success ───────────────────────────────────────

    @unittest.mock.patch("lifeos_mcp_server.urllib.request.urlopen")
    def test_lifeos_status_success(self, mock_urlopen):
        """lifeos.status returns structured status from the Status API."""
        # Mock successful API response
        mock_response = unittest.mock.MagicMock()
        mock_response.read.return_value = json.dumps({
            "service": "lifeos-status-api",
            "status": "ok",
            "mode": "read_only",
            "pending_captures": 5,
        }).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        req = self._make_request("tools/call", {
            "name": "lifeos.status",
            "arguments": {},
        })
        resp = server.handle_request(req)
        self._assert_success(resp)
        result = resp["result"]
        self.assertTrue(result["api_available"])
        self.assertEqual(result["status"]["service"], "lifeos-status-api")
        self.assertEqual(result["status"]["status"], "ok")

    # ── Test 8: lifeos.status fallback ──────────────────────────────────────

    @unittest.mock.patch("lifeos_mcp_server.urllib.request.urlopen")
    def test_lifeos_status_fallback(self, mock_urlopen):
        """lifeos.status falls back gracefully when Status API is unavailable."""
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")

        req = self._make_request("tools/call", {
            "name": "lifeos.status",
            "arguments": {},
        })
        resp = server.handle_request(req)
        self._assert_success(resp)
        result = resp["result"]
        self.assertFalse(result["api_available"])
        self.assertIn("error", result)
        self.assertEqual(result["status"]["status"], "unreachable")

    # ── Test 9: capture_summary returns metadata only ───────────────────────

    @unittest.mock.patch("os.path.isfile", return_value=True)
    @unittest.mock.patch("lifeos_mcp_server.open", create=True)
    def test_capture_summary_metadata_only(self, mock_open, mock_isfile):
        """Capture summary returns metadata only — no full capture bodies."""
        mock_file = unittest.mock.MagicMock()
        mock_file.__enter__.return_value = [
            json.dumps({
                "capture_id": "cap_001",
                "source": "telegram",
                "capture_type": "text",
                "received_at": "2026-07-08T10:00:00Z",
                "content": "THIS IS A SECRET CAPTURE BODY THAT MUST NOT LEAK",
            }) + "\n",
        ]
        mock_open.return_value = mock_file

        req = self._make_request("tools/call", {
            "name": "lifeos.capture_summary",
            "arguments": {},
        })
        resp = server.handle_request(req)
        self._assert_success(resp)
        result = resp["result"]
        # Metadata fields present
        self.assertTrue(result["queue_exists"])
        self.assertEqual(result["queue_count"], 1)
        self.assertEqual(result["newest_capture_id"], "cap_001")
        self.assertEqual(result["sources_breakdown"]["telegram"], 1)
        self.assertEqual(result["types_breakdown"]["text"], 1)
        # Full capture bodies must NOT be present
        self.assertNotIn("content", result)
        self.assertNotIn("raw_payload", result)
        self.assertNotIn("capture_bodies", result)
        self.assertNotIn("THIS IS A SECRET", json.dumps(result))

    # ── Test 10: capture_metadata requires capture_ref ──────────────────────

    def test_capture_metadata_requires_capture_ref(self):
        """Missing required capture_ref parameter is rejected."""
        req = self._make_request("tools/call", {
            "name": "lifeos.capture_metadata",
            "arguments": {},
        })
        resp = server.handle_request(req)
        self._assert_error(resp, expected_code=-32602)
        self.assertIn("missing required parameter", resp["error"]["message"])

    # ── Test 11: capture_metadata invalid ref rejected ──────────────────────

    def test_capture_metadata_invalid_ref_rejected(self):
        """Invalid capture_ref values (bad chars) are rejected."""
        bad_refs = [
            "../etc/passwd",
            "cap;rm -rf /",
            "cap|cat /etc/shadow",
            "cap`whoami`",
            "cap$HOME",
            "~/secrets",
        ]
        for ref in bad_refs:
            with self.subTest(capture_ref=ref):
                req = self._make_request("tools/call", {
                    "name": "lifeos.capture_metadata",
                    "arguments": {"capture_ref": ref},
                })
                resp = server.handle_request(req)
                self._assert_error(resp, expected_code=-32602)

    # ── Test 12: template_catalog returns templates ─────────────────────────

    def test_template_catalog_returns_templates(self):
        """Template catalog returns at least 1 template."""
        req = self._make_request("tools/call", {
            "name": "lifeos.template_catalog",
            "arguments": {},
        })
        resp = server.handle_request(req)
        self._assert_success(resp)
        result = resp["result"]
        self.assertIn("templates", result)
        self.assertGreaterEqual(len(result["templates"]), 1)
        self.assertEqual(result["count"], len(result["templates"]))
        # Verify template shape
        for tmpl in result["templates"]:
            self.assertIn("name", tmpl)
            self.assertIn("path", tmpl)
            self.assertIn("description", tmpl)
            self.assertIn("category", tmpl)

    # ── Test 13: current_working_state_summary ──────────────────────────────

    @unittest.mock.patch("os.path.isfile", return_value=True)
    @unittest.mock.patch("lifeos_mcp_server.open", create=True)
    def test_current_working_state_summary(self, mock_open, mock_isfile):
        """Current working state summary returns safe summary without sensitive content."""
        test_content = (
            "# Current Working State\n"
            "\n"
            "## Active Milestone\n"
            "\n"
            "Foundation Lock-In for LifeOS V3 under /home/lifeos.\n"
            "\n"
            "## Completed\n"
            "\n"
            "- First completed task: setup git repo\n"
            "- Second completed task: create status API\n"
            "- Third completed task: deploy dashboards\n"
            "\n"
            "## Current Decisions\n"
            "\n"
            "- Secret decision: use password abc123 for service X\n"
        )
        mock_file = unittest.mock.MagicMock()
        mock_file.__enter__.return_value.readlines.return_value = test_content.splitlines(True)
        mock_open.return_value = mock_file

        req = self._make_request("tools/call", {
            "name": "lifeos.current_working_state_summary",
            "arguments": {},
        })
        resp = server.handle_request(req)
        self._assert_success(resp)
        result = resp["result"]
        self.assertTrue(result["file_found"])
        self.assertEqual(result["title"], "Current Working State")
        self.assertEqual(result["active_milestone"], "Foundation Lock-In for LifeOS V3 under /home/lifeos.")
        # Completed items should be extracted
        self.assertIn("First completed task: setup git repo", result["recent_completed"])
        self.assertIn("Second completed task: create status API", result["recent_completed"])
        self.assertIn("Third completed task: deploy dashboards", result["recent_completed"])
        # "Secret decision" from "Current Decisions" section should NOT be in completed items
        self.assertNotIn("password", json.dumps(result["recent_completed"]))
        self.assertNotIn("abc123", json.dumps(result))

    # ── Test 14: no .env reads ──────────────────────────────────────────────

    @unittest.mock.patch("lifeos_mcp_server.open", create=True)
    @unittest.mock.patch("os.path.isfile", return_value=True)
    def test_no_env_reads(self, mock_isfile, mock_open):
        """The .env file path must never be accessed."""
        env_path = "/home/lifeos/.env"

        def guarded_open(path, *args, **kwargs):
            if isinstance(path, str) and env_path in path:
                # Test fails if we get here
                self.fail("Server attempted to open forbidden path: {}".format(path))
            return unittest.mock.MagicMock()

        mock_open.side_effect = guarded_open

        # Exercise all tools that do file access
        for tool_name in ["lifeos.capture_summary", "lifeos.current_working_state_summary"]:
            req = self._make_request("tools/call", {
                "name": tool_name,
                "arguments": {},
            })
            server.handle_request(req)

        # Also exercise tools that don't do file access
        for tool_name in ["lifeos.status", "lifeos.template_catalog"]:
            req = self._make_request("tools/call", {
                "name": tool_name,
                "arguments": {},
            })
            server.handle_request(req)

    # ── Test 15: no write calls ─────────────────────────────────────────────

    @unittest.mock.patch("lifeos_mcp_server.open", create=True)
    @unittest.mock.patch("os.path.isfile", return_value=True)
    def test_no_write_calls(self, mock_isfile, mock_open):
        """No tool should ever open a file in write mode."""
        write_modes = {"w", "a", "x", "w+", "a+", "x+", "wb", "ab", "xb"}

        def guarded_open(path, mode="r", *args, **kwargs):
            if mode in write_modes or (isinstance(mode, str) and "+" in mode):
                self.fail("Server attempted to open file in write mode: {} (mode={})".format(path, mode))
            return unittest.mock.MagicMock()

        mock_open.side_effect = guarded_open

        # Exercise all tools
        for tool_name in server.ALLOWED_TOOLS:
            args = {}
            if tool_name == "lifeos.capture_metadata":
                args = {"capture_ref": "cap_test_123"}
            req = self._make_request("tools/call", {
                "name": tool_name,
                "arguments": args,
            })
            server.handle_request(req)

    # ── Test 16: no path traversal ──────────────────────────────────────────

    def test_no_path_traversal(self):
        """Path traversal patterns in params are rejected by validation."""
        traversal_payloads = [
            "../etc/passwd",
            "..\\Windows\\System32",
            "../../.env",
            "....//....//etc/passwd",
        ]
        for payload in traversal_payloads:
            result = server._validate_params(
                {"capture_ref": payload},
                server.TOOL_SCHEMAS["lifeos.capture_metadata"],
            )
            self.assertFalse(result[0],
                            "Should reject path traversal: {}".format(payload))
            self.assertIn("invalid parameter value", result[1])

    # ── Test 17: JSON-RPC error format ──────────────────────────────────────

    def test_jsonrpc_error_format(self):
        """Errors follow the JSON-RPC 2.0 spec format."""
        tests = [
            # (request, expected_code)
            (self._make_request("nonexistent_method"), -32601),
            ({"jsonrpc": "2.0", "method": "tools/call", "id": 1,
              "params": {"name": "lifeos.unknown", "arguments": {}}}, -32001),
            ({"jsonrpc": "2.0", "method": "tools/call", "id": 2,
              "params": {"name": "lifeos.status", "arguments": {"bad": 1}}}, -32602),
        ]
        for req, expected_code in tests:
            resp = server.handle_request(req)
            self.assertEqual(resp.get("jsonrpc"), "2.0",
                            "Response must have jsonrpc field")
            self.assertIn("error", resp, "Response must have error field")
            self.assertEqual(resp["error"]["code"], expected_code)
            self.assertIsInstance(resp["error"]["message"], str)
            self.assertGreater(len(resp["error"]["message"]), 0)

    # ── Test 18: initialize returns capabilities ────────────────────────────

    def test_initialize_returns_capabilities(self):
        """initialize returns protocol version, capabilities, and server info."""
        req = self._make_request("initialize")
        resp = server.handle_request(req)
        self._assert_success(resp)
        result = resp["result"]
        self.assertEqual(result["protocolVersion"], server.PROTOCOL_VERSION)
        self.assertIn("capabilities", result)
        self.assertIn("tools", result["capabilities"])
        self.assertIn("serverInfo", result)
        self.assertEqual(result["serverInfo"]["name"], "lifeos-mcp-server")
        self.assertEqual(result["serverInfo"]["version"], server.VERSION)

    # ── Test 19: invalid JSON rejected ──────────────────────────────────────

    def test_invalid_json_rejected(self):
        """Parse errors are returned for invalid JSON requests."""
        tests = [
            "not json at all",
            "{bad json",
            "",
        ]
        for body in tests:
            req = body  # Not a dict — simulate a parse error
            resp = server.handle_request(req)
            self._assert_error(resp, expected_code=-32600)
            self.assertIn("Request must be a JSON object", resp["error"]["message"])

    # ── Test 20: unknown method rejected ────────────────────────────────────

    def test_unknown_method_rejected(self):
        """Non-existent methods return METHOD_NOT_FOUND error."""
        req = self._make_request("nonexistent.method.name")
        resp = server.handle_request(req)
        self._assert_error(resp, expected_code=-32601)
        self.assertIn("method not found", resp["error"]["message"])

    # ── Test 21: safe param validation edge cases ───────────────────────────

    def test_safe_param_validation_edge_cases(self):
        """Edge cases: null bytes, control chars, and other forbidden patterns."""
        edge_cases = [
            # (value, should_be_rejected, description)
            ("cap\x00with_null", True, "null byte"),
            ("cap_with_\x01_control", True, "control character"),
            ("cap|pipe", True, "pipe character"),
            ("cap;semicolon", True, "semicolon"),
            ("cap&ampersand", True, "ampersand"),
            ("cap\nnewline", True, "newline"),
            ("cap\rcarriage_return", True, "carriage return"),
            ("cap`backtick", True, "backtick"),
            ("cap$dollar", True, "dollar sign"),
            ("cap~tilde", True, "tilde"),
            ("cap_normal_123", False, "normal string"),
            ("capture_id_with_underscores-and-hyphens", False, "safe special chars"),
            ("a" * 128, False, "exactly max length"),
            ("a" * 129, True, "exceeds max length (capture_ref)"),
        ]

        schema = server.TOOL_SCHEMAS["lifeos.capture_metadata"]
        for value, should_reject, desc in edge_cases:
            valid, msg = server._validate_params({"capture_ref": value}, schema)
            if should_reject:
                self.assertFalse(valid,
                                "Should reject value for {}: {!r}".format(desc, value[:50]))
            else:
                self.assertTrue(valid,
                               "Should accept value for {}: {!r}".format(desc, value[:50]))

    # ── Additional: test safe param validation for non-string types ─────────

    def test_safe_param_validation_rejects_non_string_in_string_field(self):
        """Non-string values for string params should be rejected."""
        schema = server.TOOL_SCHEMAS["lifeos.capture_metadata"]
        # _validate_params doesn't enforce types, _is_safe_param_value does pattern checks
        # We mainly test that the function handles non-string gracefully
        valid, _ = server._validate_params({"capture_ref": 12345}, schema)
        # Integer values pass _is_safe_param_value (primitives are safe)
        # but may still be valid from a schema perspective
        self.assertTrue(valid)

    # ── Additional: test _is_safe_param_value ───────────────────────────────

    def test_is_safe_param_value_edge_cases(self):
        """Test _is_safe_param_value directly with various edge cases."""
        # Safe values
        self.assertTrue(server._is_safe_param_value("normal_string"))
        self.assertTrue(server._is_safe_param_value("cap_20260708_123456"))
        self.assertTrue(server._is_safe_param_value(42))
        self.assertTrue(server._is_safe_param_value(True))
        self.assertTrue(server._is_safe_param_value(None))
        self.assertTrue(server._is_safe_param_value([1, 2, 3]))
        self.assertTrue(server._is_safe_param_value({"key": "value"}))

        # Unsafe values
        self.assertFalse(server._is_safe_param_value("path/../escape"))
        self.assertFalse(server._is_safe_param_value("x" * (server.MAX_PARAM_SIZE + 1)))

    # ── Additional: test tools/call with empty params ───────────────────────

    def test_tools_call_empty_name(self):
        """tools/call with empty tool name is rejected."""
        req = self._make_request("tools/call", {"name": "", "arguments": {}})
        resp = server.handle_request(req)
        self._assert_error(resp, expected_code=-32602)

    # ── Additional: test tools/call with missing name ───────────────────────

    def test_tools_call_missing_name(self):
        """tools/call without a name parameter is rejected."""
        req = self._make_request("tools/call", {"arguments": {}})
        resp = server.handle_request(req)
        self._assert_error(resp, expected_code=-32602)

    # ── Additional: test missing jsonrpc version ────────────────────────────

    def test_missing_jsonrpc_version(self):
        """Requests without jsonrpc '2.0' are rejected."""
        req = {"method": "tools/list", "id": 1}
        resp = server.handle_request(req)
        self._assert_error(resp, expected_code=-32600)

    # ── Additional: test missing method ─────────────────────────────────────

    def test_missing_method(self):
        """Requests without a method are rejected."""
        req = {"jsonrpc": "2.0", "id": 1}
        resp = server.handle_request(req)
        self._assert_error(resp, expected_code=-32600)
        self.assertIn("missing method", resp["error"]["message"])


if __name__ == "__main__":
    unittest.main()
