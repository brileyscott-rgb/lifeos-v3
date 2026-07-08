#!/usr/bin/env python3
"""LifeOS MCP Client — Python stdlib client for lifeos_mcp_server.py.

Spawns the MCP server as a stdio subprocess, sends JSON-RPC 2.0
requests, and reads responses. Guarantees process cleanup on exit.
Use as a context manager.

Key safety properties:
- No arbitrary command from caller
- No caller-provided executable path (except test fixture)
- No persistent daemon
- No ports
- Timeout on every call
- Process cleanup guaranteed
"""

import json
import os
import select
import subprocess
import time  # noqa: F401 — import present per spec, used if needed

MCP_SERVER_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lifeos_mcp_server.py")


class MCPClient:
    """Spawns lifeos_mcp_server.py as stdio subprocess.

    Sends JSON-RPC requests and reads JSON-RPC responses.
    Has timeout. Cleans up process on exit.

    Use as context manager:
        with MCPClient() as client:
            result = client.status()
    """

    def __init__(self, server_script=None, timeout=30):
        self.server_script = server_script or MCP_SERVER_SCRIPT
        self.timeout = timeout
        self.process = None
        self._request_id = 0
        self._initialized = False

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self):
        if not os.path.isfile(self.server_script):
            raise FileNotFoundError(f"MCP server script not found: {self.server_script}")

        self.process = subprocess.Popen(
            ["python3", self.server_script],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        # Send initialize
        self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "lifeos-orchestrator", "version": "0.1.0"},
        })
        resp = self._read_response()
        self._initialized = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.process is None:
            return False

        # Close stdin to signal the server to stop reading
        try:
            self.process.stdin.close()
        except Exception:
            pass

        # Wait for graceful exit
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # Escalate: terminate
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                # Final escalation: kill
                try:
                    self.process.kill()
                    self.process.wait()
                except Exception:
                    pass
        except Exception:
            pass

        # Close stdout and stderr to prevent ResourceWarning
        try:
            self.process.stdout.close()
        except Exception:
            pass
        try:
            self.process.stderr.close()
        except Exception:
            pass

        return False  # Do not suppress exceptions

    # ------------------------------------------------------------------
    # Core JSON-RPC transport
    # ------------------------------------------------------------------

    def _send_request(self, method, params):
        """Send a JSON-RPC request to the server. Returns the request id."""
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }
        payload = json.dumps(request)
        try:
            self.process.stdin.write(payload + "\n")
            self.process.stdin.flush()
        except BrokenPipeError:
            raise RuntimeError("MCP server process has terminated unexpectedly")
        return self._request_id

    def _read_response(self):
        """Read a single JSON-RPC response line from the server.

        Blocks up to self.timeout seconds. Raises TimeoutError if no
        response arrives in time.
        """
        if self.process is None:
            raise RuntimeError("MCPClient not connected — use as context manager")

        ready, _, _ = select.select([self.process.stdout], [], [], self.timeout)
        if not ready:
            raise TimeoutError(f"MCP call timed out after {self.timeout}s")

        line = self.process.stdout.readline()
        if not line:
            raise RuntimeError("MCP server closed stdout unexpectedly")

        try:
            return json.loads(line.strip())
        except json.JSONDecodeError:
            raise RuntimeError(f"MCP server returned invalid JSON: {line[:200]}")

    # ------------------------------------------------------------------
    # Public API — tool calls
    # ------------------------------------------------------------------

    def call_tool(self, tool_name, arguments=None):
        """Call a named MCP tool with optional arguments.

        Returns the tool result content (the inner result from the
        MCP protocol envelope).

        Raises RuntimeError if the server returns an error.
        """
        if arguments is None:
            arguments = {}
        self._send_request("tools/call", {"name": tool_name, "arguments": arguments})
        resp = self._read_response()
        if "error" in resp:
            err_info = resp["error"]
            msg = err_info.get("message", str(err_info))
            raise RuntimeError(f"MCP tool error: {msg}")
        return resp.get("result", {})

    # ------------------------------------------------------------------
    # Typed convenience methods
    # ------------------------------------------------------------------

    def status(self):
        """Get current LifeOS system status."""
        return self.call_tool("lifeos.status")

    def capture_summary(self):
        """Get summary of captures in the buffer."""
        return self.call_tool("lifeos.capture_summary")

    def capture_metadata(self, capture_ref):
        """Get metadata for a specific capture."""
        return self.call_tool("lifeos.capture_metadata", {"capture_ref": capture_ref})

    def template_catalog(self):
        """List available templates in the vault."""
        return self.call_tool("lifeos.template_catalog")

    def current_working_state_summary(self):
        """Get summary of current working state."""
        return self.call_tool("lifeos.current_working_state_summary")
