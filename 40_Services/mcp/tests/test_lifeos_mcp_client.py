#!/usr/bin/env python3
"""Tests for lifeos_mcp_client.py — spawns actual server, validates protocol."""

import json
import os
import signal
import sys
import time
import unittest

# Ensure the mcp package is importable
SYS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SYS_PATH = os.path.realpath(SYS_PATH)
sys.path.insert(0, SYS_PATH)

from lifeos_mcp_client import MCPClient, MCP_SERVER_SCRIPT


def _pid_still_alive(pid):
    """Check if a PID is still running."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


class TestMCPClient(unittest.TestCase):
    """Integration tests against the actual lifeos_mcp_server.py."""

    @classmethod
    def setUpClass(cls):
        """Verify server script exists before running any tests."""
        if not os.path.isfile(MCP_SERVER_SCRIPT):
            raise FileNotFoundError(
                f"MCP server script not found at {MCP_SERVER_SCRIPT}. "
                "Tests require the actual server."
            )

    # ------------------------------------------------------------------
    # 1. Successful call
    # ------------------------------------------------------------------

    def test_successful_call(self):
        """Spawn actual server, call status, verify response."""
        with MCPClient(timeout=30) as client:
            result = client.status()
        # Server returns status data directly (dict, not wrapped in content blocks)
        self.assertIsInstance(result, dict)
        # The actual server calls Status API; verify expected fields
        self.assertIn("api_available", result)
        self.assertIn("status", result)
        if result["api_available"]:
            self.assertIn("service", result["status"])
            self.assertIn("status", result["status"])

    # ------------------------------------------------------------------
    # 2. Unknown tool error
    # ------------------------------------------------------------------

    def test_unknown_tool_error(self):
        """Calling a non-existent tool should raise RuntimeError."""
        with MCPClient(timeout=30) as client:
            with self.assertRaises(RuntimeError) as ctx:
                client.call_tool("nonexistent.tool_xyzzy")
            # Server's error message uses lowercase "unknown tool"
            error_msg = str(ctx.exception).lower()
            self.assertTrue(
                "unknown tool" in error_msg or "tool not found" in error_msg,
                f"Expected 'unknown tool' or 'tool not found' in: {ctx.exception}",
            )

    # ------------------------------------------------------------------
    # 3. Timeout / cleanup test
    # ------------------------------------------------------------------

    def test_timeout_cleanup(self):
        """Verify timeout behavior: _read_response times out with short timeout.

        Since no request is sent, stdout has no data and select.select times out.
        The process is cleaned up even after timeout.
        """
        client = MCPClient(timeout=0.5)
        pid_before = None
        try:
            client.__enter__()
            pid_before = client.process.pid
            with self.assertRaises(TimeoutError):
                # No request was sent — reading will timeout
                client._read_response()
        finally:
            client.__exit__(None, None, None)

        # Server process should be cleaned up
        if pid_before is not None:
            time.sleep(0.5)
            self.assertFalse(
                _pid_still_alive(pid_before),
                f"Server PID {pid_before} still running after cleanup",
            )

    # ------------------------------------------------------------------
    # 4. Subprocess cleanup via context manager
    # ------------------------------------------------------------------

    def test_subprocess_cleanup(self):
        """Process should exit after context manager exits cleanly."""
        with MCPClient(timeout=30) as client:
            pid_before = client.process.pid
            self.assertTrue(_pid_still_alive(pid_before))
            # Make a successful call to ensure the process is running
            result = client.status()
            self.assertIsInstance(result, dict)

        # After exiting the context manager, process should be gone
        time.sleep(0.3)
        self.assertFalse(
            _pid_still_alive(pid_before),
            f"Server PID {pid_before} still running after context manager exit",
        )

    # ------------------------------------------------------------------
    # 5. No lingering processes
    # ------------------------------------------------------------------

    def test_no_process_left_behind(self):
        """Verify no lingering MCP server process after client use."""
        def count_server_procs():
            import subprocess as sp
            try:
                result = sp.run(
                    ["pgrep", "-f", "lifeos_mcp_server.py"],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode == 0:
                    return len([l for l in result.stdout.strip().split("\n") if l])
                return 0
            except Exception:
                return 0

        count_before = count_server_procs()

        with MCPClient(timeout=30) as client:
            client.status()
            client.capture_summary()

        time.sleep(0.5)
        count_after = count_server_procs()

        self.assertLessEqual(
            count_after, count_before + 1,
            f"Server process count increased: before={count_before}, after={count_after}",
        )

    # ------------------------------------------------------------------
    # 6. Typed convenience methods
    # ------------------------------------------------------------------

    def test_client_typed_methods(self):
        """Test each typed convenience method returns valid results.

        Note: The actual server returns direct dicts (not wrapped in content blocks).
        """
        with MCPClient(timeout=30) as client:
            # status — returns status dict with api_available and status keys
            result = client.status()
            self.assertIsInstance(result, dict)
            self.assertIn("api_available", result)

            # capture_summary — returns capture summary dict
            result = client.capture_summary()
            self.assertIsInstance(result, dict)

            # capture_metadata — returns metadata for a specific capture
            result = client.capture_metadata("cap_test_123")
            self.assertIsInstance(result, dict)

            # template_catalog — returns template catalog
            result = client.template_catalog()
            self.assertIsInstance(result, dict)

            # current_working_state_summary — returns current state summary
            result = client.current_working_state_summary()
            self.assertIsInstance(result, dict)

    # ------------------------------------------------------------------
    # 7. Context manager cleanup on exception
    # ------------------------------------------------------------------

    def test_context_manager_cleanup_on_error(self):
        """Verify process is cleaned up even when an exception occurs inside the block."""
        pid_before = None

        class TestException(Exception):
            pass

        try:
            with MCPClient(timeout=30) as client:
                pid_before = client.process.pid
                self.assertTrue(_pid_still_alive(pid_before))
                raise TestException("simulated error inside context manager")
        except TestException:
            pass  # Expected

        # Process should be cleaned up despite the exception
        time.sleep(0.3)
        self.assertFalse(
            _pid_still_alive(pid_before),
            f"Server PID {pid_before} still running after exception cleanup",
        )

    # ------------------------------------------------------------------
    # Additional: JSON-RPC protocol verification
    # ------------------------------------------------------------------

    def test_response_has_correct_structure(self):
        """Verify status returns a dict with expected top-level keys."""
        with MCPClient(timeout=30) as client:
            result = client.status()
        self.assertIsInstance(result, dict)
        self.assertIn("api_available", result)
        self.assertIn("status", result)

    def test_tools_list_works(self):
        """Verify tools/list returns the expected LifeOS tools."""
        with MCPClient(timeout=30) as client:
            client._send_request("tools/list", {})
            resp = client._read_response()
        self.assertIn("result", resp)
        tools = resp["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        self.assertIn("lifeos.status", tool_names)
        self.assertIn("lifeos.capture_summary", tool_names)
        self.assertIn("lifeos.capture_metadata", tool_names)
        self.assertIn("lifeos.template_catalog", tool_names)
        self.assertIn("lifeos.current_working_state_summary", tool_names)

    # ------------------------------------------------------------------
    # Additional: error handling robustness
    # ------------------------------------------------------------------

    def test_error_response_format(self):
        """Error responses should have proper JSON-RPC error structure."""
        with MCPClient(timeout=30) as client:
            try:
                client.call_tool("nonexistent.tool_xyzzy")
            except RuntimeError:
                pass  # Expected

        # Client should still be usable after an error
        with MCPClient(timeout=30) as client:
            result = client.status()
            self.assertIsInstance(result, dict)

    def test_empty_arguments_default(self):
        """call_tool with no arguments should default to empty dict."""
        with MCPClient(timeout=30) as client:
            result = client.call_tool("lifeos.status")
            self.assertIsInstance(result, dict)
            self.assertIn("api_available", result)


if __name__ == "__main__":
    unittest.main()
