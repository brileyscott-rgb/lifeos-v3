#!/usr/bin/env python3
"""LifeOS Custom MCP Server V0 — minimal MCP-compatible stdio JSON-RPC server.

Transport: stdio (read from stdin, write to stdout, stderr for debug only).
Protocol: JSON-RPC 2.0.
Python stdlib only.

Methods:
  - initialize
  - tools/list
  - tools/call

Read-only tools:
  - lifeos.status
  - lifeos.capture_summary
  - lifeos.capture_metadata
  - lifeos.template_catalog
  - lifeos.current_working_state_summary

Usage:
  python3 lifeos_mcp_server.py             # run server loop
  python3 lifeos_mcp_server.py --self-test # basic connectivity checks (no server loop)
"""

import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import Counter

# ── Constants ──────────────────────────────────────────────────────────────────

ALLOWED_TOOLS = {
    "lifeos.status",
    "lifeos.capture_summary",
    "lifeos.capture_metadata",
    "lifeos.template_catalog",
    "lifeos.current_working_state_summary",
}

FORBIDDEN_PATHS = {
    "/home/lifeos/.env",
    "/home/lifeos/40_Services/capture_api/.env",
    "/home/lifeos/.ssh",
    "/home/lifeos/.config",
    "/var/run/docker.sock",
}

FORBIDDEN_PARAM_PATTERNS = [
    re.compile(r"\.\.[\\/]"),   # ../ or ..\
    re.compile(r"~"),
    re.compile(r"\$"),
    re.compile(r"`"),
    re.compile(r"\|"),
    re.compile(r";"),
    re.compile(r"&"),
    re.compile(r"\n"),
    re.compile(r"\r"),
]

# Paths
CAPTURE_QUEUE_PATH = "/home/lifeos/LifeOS_Capture_Buffer/00_Raw/captures.jsonl"
CURRENT_WORKING_STATE_PATH = "/home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Current_Working_State.md"
TEMPLATES_DIR = "/home/lifeos/10_Vaults/LifeOS/08_TEMPLATES"

STATUS_API_URL = "http://127.0.0.1:8787/status"
ACTION_API_CAPTURES_URL = "http://127.0.0.1:8788/captures"
ACTION_API_LATEST_URL = "http://127.0.0.1:8788/captures/pending/latest"

MAX_PARAM_SIZE = 16 * 1024  # 16 KB

VERSION = "0.1.0"
PROTOCOL_VERSION = "2024-11-05"

# ── Template Catalog Static Data ───────────────────────────────────────────────

TEMPLATE_CATALOG = [
    {
        "name": "Knowledge_Note.md",
        "path": "08_TEMPLATES/Knowledge_Note.md",
        "description": "Template for creating knowledge notes — reference material, how-tos, and concept explanations.",
        "category": "notes",
    },
    {
        "name": "Project.md",
        "path": "08_TEMPLATES/Project.md",
        "description": "Template for creating projects — active initiatives with goals, tasks, and status tracking.",
        "category": "projects",
    },
    {
        "name": "Capture.md",
        "path": "08_TEMPLATES/Capture.md",
        "description": "Template for capture entries — raw intake from Telegram, desktop, web, or manual sources.",
        "category": "intake",
    },
    {
        "name": "Area.md",
        "path": "08_TEMPLATES/Area.md",
        "description": "Template for areas of responsibility — ongoing domains without a defined end date.",
        "category": "areas",
    },
    {
        "name": "Decision.md",
        "path": "08_TEMPLATES/Decision.md",
        "description": "Template for recording architectural and policy decisions with context and rationale.",
        "category": "decisions",
    },
    {
        "name": "AI_Context.md",
        "path": "08_TEMPLATES/AI_Context.md",
        "description": "Template for AI context files — project scope, allowed paths, and agent instructions.",
        "category": "ai",
    },
    {
        "name": "Approval_Request.md",
        "path": "08_TEMPLATES/Approval_Request.md",
        "description": "Template for approval requests — gated actions requiring human or agent approval.",
        "category": "governance",
    },
    {
        "name": "Daily.md",
        "path": "08_TEMPLATES/Daily.md",
        "description": "Template for daily notes — journal entries, standup notes, and day planning.",
        "category": "journal",
    },
]

# ── Tool Input Schemas ─────────────────────────────────────────────────────────

TOOL_SCHEMAS = {
    "lifeos.status": {
        "type": "object",
        "properties": {},
        "required": [],
    },
    "lifeos.capture_summary": {
        "type": "object",
        "properties": {},
        "required": [],
    },
    "lifeos.capture_metadata": {
        "type": "object",
        "properties": {
            "capture_ref": {
                "type": "string",
                "description": "Capture ID or reference string (max 128 chars)",
                "maxLength": 128,
            }
        },
        "required": ["capture_ref"],
    },
    "lifeos.template_catalog": {
        "type": "object",
        "properties": {},
        "required": [],
    },
    "lifeos.current_working_state_summary": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

# ── JSON-RPC Error Codes ──────────────────────────────────────────────────────

JSONRPC_ERRORS = {
    "PARSE_ERROR": (-32700, "Parse error"),
    "INVALID_REQUEST": (-32600, "Invalid Request"),
    "METHOD_NOT_FOUND": (-32601, "Method not found"),
    "INVALID_PARAMS": (-32602, "Invalid params"),
    "INTERNAL_ERROR": (-32603, "Internal error"),
    "TOOL_NOT_FOUND": (-32001, "Tool not found"),
    "TOOL_EXECUTION_ERROR": (-32002, "Tool execution error"),
}

# ── Safety Validation ──────────────────────────────────────────────────────────

def _is_safe_param_value(value):
    """Check a single param value for forbidden patterns and size limits."""
    if isinstance(value, str):
        # Check size limit
        if len(value.encode("utf-8")) > MAX_PARAM_SIZE:
            return False
        # Check forbidden patterns
        for pattern in FORBIDDEN_PARAM_PATTERNS:
            if pattern.search(value):
                return False
        # Check for null bytes and control characters (except common whitespace)
        if "\x00" in value:
            return False
        for ch in value:
            if ord(ch) < 0x20 and ch not in ("\t", "\n", "\r"):
                return False
    elif isinstance(value, (int, float, bool, type(None))):
        # Primitives are safe
        pass
    elif isinstance(value, (list, dict)):
        # Check serialized size
        try:
            serialized = json.dumps(value)
            if len(serialized.encode("utf-8")) > MAX_PARAM_SIZE:
                return False
        except (TypeError, ValueError):
            return False
    return True


def _validate_params(params, schema):
    """Validate params against tool schema. Returns (True, None) or (False, error_message)."""
    if not isinstance(params, dict):
        return False, "params must be a JSON object"

    required = schema.get("required", [])
    properties = schema.get("properties", {})

    # Check all required params are present
    for key in required:
        if key not in params:
            return False, "missing required parameter: {}".format(key)

    # Check no unknown params
    for key in params:
        if key not in properties:
            return False, "unknown parameter: {}".format(key)

    # Check each param value is safe
    for key, value in params.items():
        if not _is_safe_param_value(value):
            return False, "invalid parameter value for: {}".format(key)

        # Check string length constraints
        prop_schema = properties.get(key, {})
        if isinstance(value, str) and "maxLength" in prop_schema:
            if len(value) > prop_schema["maxLength"]:
                return False, "parameter '{}' exceeds max length of {}".format(
                    key, prop_schema["maxLength"]
                )

    return True, None


# ── CaptureSummary (inlined from lifeos_capture_summary.py) ────────────────────


class CaptureSummary:
    """Metadata-only summary of the capture JSONL queue."""

    def __init__(self):
        self.queue_exists = False
        self.queue_count = 0
        self.newest_capture_id = ""
        self.newest_received_at = ""
        self.sources_breakdown = {}
        self.types_breakdown = {}
        self.processed_markdown_count = 0
        self.malformed_count = 0


def _get_capture_summary(queue_path):
    """Read the capture JSONL queue and return a CaptureSummary with metadata only.
    NEVER reads full capture content into the result dict."""
    s = CaptureSummary()
    if not os.path.isfile(queue_path):
        return s
    s.queue_exists = True
    sources = Counter()
    types_ = Counter()
    newest_ts = ""
    try:
        with open(queue_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    s.malformed_count += 1
                    continue
                s.queue_count += 1
                src = rec.get("source", "unknown")
                sources[src] += 1
                ct = rec.get("capture_type", "unknown")
                types_[ct] += 1
                ts = rec.get("received_at", "")
                cid = rec.get("capture_id", "")
                if not newest_ts or ts > newest_ts:
                    newest_ts = ts
                    s.newest_received_at = ts
                    s.newest_capture_id = cid
    except (IOError, OSError) as e:
        print("[lifeos_mcp_server] Warning: could not read capture queue: {}".format(e), file=sys.stderr)
    s.sources_breakdown = dict(sources)
    s.types_breakdown = dict(types_)
    return s


def _capture_summary_to_dict(s):
    """Convert CaptureSummary to dict — metadata only, no capture bodies."""
    return {
        "queue_exists": s.queue_exists,
        "queue_count": s.queue_count,
        "newest_capture_id": s.newest_capture_id,
        "newest_received_at": s.newest_received_at,
        "sources_breakdown": s.sources_breakdown,
        "types_breakdown": s.types_breakdown,
        "processed_markdown_count": s.processed_markdown_count,
        "malformed_count": s.malformed_count,
    }


# ── Tool Implementations ───────────────────────────────────────────────────────


def _tool_lifeos_status():
    """Call the Status API and return structured JSON status.
    Falls back gracefully if the API is unavailable."""
    try:
        req = urllib.request.Request(STATUS_API_URL, method="GET")
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)
            return {"api_available": True, "status": data}
    except urllib.error.URLError as e:
        return {
            "api_available": False,
            "error": "Status API unavailable: {}".format(str(e)),
            "status": {"service": "unknown", "status": "unreachable"},
        }
    except (json.JSONDecodeError, ValueError) as e:
        return {
            "api_available": False,
            "error": "Status API returned invalid JSON: {}".format(str(e)),
            "status": {"service": "unknown", "status": "parse_error"},
        }
    except Exception as e:
        return {
            "api_available": False,
            "error": "Status API error: {}".format(str(e)),
            "status": {"service": "unknown", "status": "error"},
        }


def _tool_lifeos_capture_summary():
    """Return capture queue metadata summary. NEVER prints full capture bodies."""
    s = _get_capture_summary(CAPTURE_QUEUE_PATH)
    return _capture_summary_to_dict(s)


def _tool_lifeos_capture_metadata(capture_ref):
    """Look up a capture's metadata via the Action API.
    Returns: capture_id, title/preview, source_type, created_at, status, content_length.
    NEVER reads full capture content. NEVER mutates capture state."""
    # Try specific capture lookup first
    url = "{}/{}".format(ACTION_API_CAPTURES_URL, urllib.request.quote(capture_ref, safe=""))
    try:
        req = urllib.request.Request(url, method="GET")
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)
            return _format_capture_metadata(data)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            # Try latest endpoint
            return _tool_lifeos_capture_metadata_latest()
        return {
            "error": "Action API returned HTTP {}: {}".format(e.code, str(e)),
            "capture_id": capture_ref,
            "found": False,
        }
    except Exception as e:
        return {
            "error": "Action API error: {}".format(str(e)),
            "capture_id": capture_ref,
            "found": False,
        }


def _tool_lifeos_capture_metadata_latest():
    """Fallback: get metadata for the latest pending capture."""
    try:
        req = urllib.request.Request(ACTION_API_LATEST_URL, method="GET")
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8")
            data = json.loads(body)
            return _format_capture_metadata(data)
    except urllib.error.HTTPError as e:
        return {"error": "Latest capture endpoint returned HTTP {}".format(e.code), "found": False}
    except Exception as e:
        return {"error": "Latest capture endpoint error: {}".format(str(e)), "found": False}


def _format_capture_metadata(data):
    """Extract metadata-only fields from an Action API capture response.
    NEVER includes full capture content."""
    if not isinstance(data, dict):
        return {"found": False, "error": "Unexpected response format"}

    metadata = {"found": True}

    # Map known fields — metadata only, never content
    for key in ("capture_id", "title", "source_type", "source", "created_at",
                "status", "capture_type", "url", "received_at", "schema_version"):
        if key in data and data[key] is not None:
            metadata[key] = data[key]

    # Provide preview from title or first content line (truncated)
    if "title" in data and data["title"]:
        metadata["preview"] = data["title"][:200]
    elif "content" in data and data["content"]:
        first_line = data["content"].split("\n")[0]
        metadata["preview"] = first_line[:200]
    else:
        metadata["preview"] = ""

    # Content length (but never the content itself)
    if "content" in data:
        if isinstance(data["content"], str):
            metadata["content_length"] = len(data["content"])
        else:
            metadata["content_length"] = len(str(data.get("content", "")))

    return metadata


def _tool_lifeos_template_catalog():
    """Return the approved template catalog with metadata.
    Uses static data with optional file size reads from allowlisted paths."""
    result = []
    for tmpl in TEMPLATE_CATALOG:
        entry = dict(tmpl)  # shallow copy
        full_path = os.path.join(TEMPLATES_DIR, tmpl["name"])
        if os.path.isfile(full_path):
            try:
                entry["file_size_bytes"] = os.path.getsize(full_path)
                entry["exists"] = True
            except OSError:
                entry["exists"] = False
        else:
            entry["exists"] = False
        result.append(entry)
    return {"templates": result, "count": len(result)}


def _tool_lifeos_current_working_state_summary():
    """Return a short safe summary from Current_Working_State.md.
    Only reads the first line (title) and list of recent completed items.
    No full vault scan, no sensitive content."""
    result = {
        "file_found": False,
        "title": "",
        "recent_completed": [],
        "active_milestone": "",
    }
    if not os.path.isfile(CURRENT_WORKING_STATE_PATH):
        return result

    result["file_found"] = True

    try:
        with open(CURRENT_WORKING_STATE_PATH, "r") as f:
            lines = f.readlines()
    except (IOError, OSError):
        return result

    # Extract title (first line starting with #)
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            result["title"] = stripped[2:].strip()
            break

    # Extract active milestone
    in_milestone = False
    for line in lines:
        stripped = line.strip()
        if stripped == "## Active Milestone":
            in_milestone = True
            continue
        if in_milestone:
            if stripped.startswith("## "):
                break
            if stripped and not stripped.startswith("#"):
                result["active_milestone"] = stripped
                break

    # Extract recent completed items (from "## Completed" or "Completed:" section)
    in_completed = False
    completed_items = []
    for line in lines:
        stripped = line.strip()
        if re.match(r"^#{1,3}\s+(Completed)", stripped) or stripped == "Completed:":
            in_completed = True
            continue
        if in_completed:
            # Stop at next section header
            if stripped.startswith("## ") or stripped.startswith("# "):
                break
            # Collect bullet/list items
            if stripped.startswith("- ") or stripped.startswith("* "):
                item_text = stripped[2:].strip()
                # Truncate long items for safety
                if len(item_text) > 280:
                    item_text = item_text[:277] + "..."
                completed_items.append(item_text)

    # Return up to 20 most recent completed items
    result["recent_completed"] = completed_items[:20]
    result["completed_count"] = len(completed_items)

    return result


# ── Tool Registry ──────────────────────────────────────────────────────────────

TOOL_HANDLERS = {
    "lifeos.status": _tool_lifeos_status,
    "lifeos.capture_summary": _tool_lifeos_capture_summary,
    "lifeos.capture_metadata": _tool_lifeos_capture_metadata,
    "lifeos.template_catalog": _tool_lifeos_template_catalog,
    "lifeos.current_working_state_summary": _tool_lifeos_current_working_state_summary,
}


# ── JSON-RPC Response Helpers ──────────────────────────────────────────────────

def _make_response(id_, result):
    """Build a JSON-RPC 2.0 success response."""
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def _make_error(id_, code, message):
    """Build a JSON-RPC 2.0 error response."""
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


# ── Request Handling ───────────────────────────────────────────────────────────

def _handle_initialize(id_, params):
    """Handle the initialize method."""
    result = {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities": {"tools": {}},
        "serverInfo": {
            "name": "lifeos-mcp-server",
            "version": VERSION,
        },
    }
    return _make_response(id_, result)


def _handle_tools_list(id_, params):
    """Handle the tools/list method."""
    tools = []
    for name, schema in TOOL_SCHEMAS.items():
        descriptions = {
            "lifeos.status": "Get LifeOS service status from the Status API.",
            "lifeos.capture_summary": "Get capture queue metadata summary. NEVER returns full capture bodies.",
            "lifeos.capture_metadata": "Get metadata for a specific capture by ID. Requires capture_ref parameter.",
            "lifeos.template_catalog": "List approved LifeOS vault templates with metadata.",
            "lifeos.current_working_state_summary": "Get a short safe summary from the Current Working State file.",
        }
        tools.append({
            "name": name,
            "description": descriptions.get(name, "LifeOS tool: {}".format(name)),
            "inputSchema": schema,
        })
    return _make_response(id_, {"tools": tools})


def _handle_tools_call(id_, params):
    """Handle the tools/call method."""
    if not isinstance(params, dict):
        return _make_error(id_, JSONRPC_ERRORS["INVALID_PARAMS"][0],
                          "params must be a JSON object")

    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})

    if not tool_name:
        return _make_error(id_, JSONRPC_ERRORS["INVALID_PARAMS"][0],
                          "missing required parameter: name")

    if tool_name not in ALLOWED_TOOLS:
        code, _msg = JSONRPC_ERRORS["TOOL_NOT_FOUND"]
        return _make_error(id_, code, "unknown tool: {}".format(tool_name))

    if tool_name not in TOOL_HANDLERS:
        code, _msg = JSONRPC_ERRORS["TOOL_NOT_FOUND"]
        return _make_error(id_, code, "tool not implemented: {}".format(tool_name))

    # Validate arguments against schema
    schema = TOOL_SCHEMAS.get(tool_name, {})
    valid, err_msg = _validate_params(arguments, schema)
    if not valid:
        code, _msg = JSONRPC_ERRORS["INVALID_PARAMS"]
        return _make_error(id_, code, err_msg)

    # Execute the tool
    try:
        handler = TOOL_HANDLERS[tool_name]
        # Call handler with arguments if it has required params, else no args
        if tool_name == "lifeos.capture_metadata":
            result = handler(arguments["capture_ref"])
        else:
            result = handler()

        return _make_response(id_, result)
    except Exception as e:
        code, _msg = JSONRPC_ERRORS["TOOL_EXECUTION_ERROR"]
        return _make_error(id_, code, "tool execution failed: {}".format(str(e)))


METHOD_HANDLERS = {
    "initialize": _handle_initialize,
    "tools/list": _handle_tools_list,
    "tools/call": _handle_tools_call,
}


def handle_request(request):
    """Handle a single JSON-RPC 2.0 request and return a response dict."""
    if not isinstance(request, dict):
        return _make_error(None, JSONRPC_ERRORS["INVALID_REQUEST"][0], "Request must be a JSON object")

    jsonrpc = request.get("jsonrpc", "")
    if jsonrpc != "2.0":
        return _make_error(request.get("id"), JSONRPC_ERRORS["INVALID_REQUEST"][0],
                          "jsonrpc must be '2.0'")

    method = request.get("method", "")
    req_id = request.get("id")
    params = request.get("params", {})

    if not method:
        return _make_error(req_id, JSONRPC_ERRORS["INVALID_REQUEST"][0], "missing method")

    if method not in METHOD_HANDLERS:
        code, _msg = JSONRPC_ERRORS["METHOD_NOT_FOUND"]
        return _make_error(req_id, code, "method not found: {}".format(method))

    try:
        handler = METHOD_HANDLERS[method]
        return handler(req_id, params)
    except Exception as e:
        code, _msg = JSONRPC_ERRORS["INTERNAL_ERROR"]
        return _make_error(req_id, code, "internal error: {}".format(str(e)))


# ── Self-Test ──────────────────────────────────────────────────────────────────

def _self_test():
    """Run basic connectivity checks without starting the server loop."""
    print("[self-test] LifeOS MCP Server V0 — connectivity checks", file=sys.stderr)
    results = []

    # Test 1: Status API
    print("[self-test] Checking Status API at {} ...".format(STATUS_API_URL), file=sys.stderr)
    status_result = _tool_lifeos_status()
    results.append(("Status API", status_result.get("api_available", False)))

    # Test 2: Capture queue
    print("[self-test] Checking capture queue at {} ...".format(CAPTURE_QUEUE_PATH), file=sys.stderr)
    summary = _get_capture_summary(CAPTURE_QUEUE_PATH)
    results.append(("Capture Queue", summary.queue_exists))

    # Test 3: Templates directory
    print("[self-test] Checking templates at {} ...".format(TEMPLATES_DIR), file=sys.stderr)
    results.append(("Templates Dir", os.path.isdir(TEMPLATES_DIR)))

    # Test 4: Current working state
    print("[self-test] Checking current working state at {} ...".format(CURRENT_WORKING_STATE_PATH), file=sys.stderr)
    results.append(("Current Working State", os.path.isfile(CURRENT_WORKING_STATE_PATH)))

    # Test 5: Action API
    print("[self-test] Checking Action API at {} ...".format(ACTION_API_LATEST_URL), file=sys.stderr)
    try:
        req = urllib.request.Request(ACTION_API_LATEST_URL, method="GET")
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=5) as resp:
            results.append(("Action API", True))
    except Exception:
        results.append(("Action API", False))

    # Summary
    print("\n[self-test] Results:", file=sys.stderr)
    all_pass = True
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        if not passed:
            all_pass = False
        print("  {}: {}".format(name, status), file=sys.stderr)

    return 0 if all_pass else 1


# ── Main ───────────────────────────────────────────────────────────────────────

def _run_server():
    """Run the MCP server main loop: read JSON-RPC from stdin, write to stdout."""
    print("[lifeos_mcp_server] Starting LifeOS MCP Server v{}".format(VERSION), file=sys.stderr)
    print("[lifeos_mcp_server] Protocol: JSON-RPC 2.0, Transport: stdio", file=sys.stderr)
    print("[lifeos_mcp_server] {} tools registered".format(len(ALLOWED_TOOLS)), file=sys.stderr)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as e:
            err_response = _make_error(None, JSONRPC_ERRORS["PARSE_ERROR"][0],
                                       "Parse error: {}".format(str(e)))
            sys.stdout.write(json.dumps(err_response) + "\n")
            sys.stdout.flush()
            continue

        response = handle_request(request)
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


def main():
    if "--self-test" in sys.argv:
        sys.exit(_self_test())
    else:
        _run_server()


if __name__ == "__main__":
    main()
