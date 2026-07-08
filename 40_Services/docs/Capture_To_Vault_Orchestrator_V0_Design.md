# Capture-to-Vault Orchestrator V0 — Implementation Design

Status: design spec
Created: 2026-07-08
Purpose: complete implementation design for the Capture-to-Vault Orchestrator V0 — a deterministic MCP-backed, Python-stdlib-only pipeline that transforms raw captures into reviewed, approved Knowledge notes, then imports them into the canonical LifeOS vault.

---

## Table of Contents

1. [MCP JSON-RPC Server Shape](#1-mcp-json-rpc-server-shape)
2. [MCP Tool Schemas](#2-mcp-tool-schemas)
3. [Orchestrator Request/Response Schema](#3-orchestrator-requestresponse-schema)
4. [Capture Resolution Logic](#4-capture-resolution-logic)
5. [Deterministic Classifier](#5-deterministic-classifier)
6. [Knowledge Curator Module](#6-knowledge-curator-module)
7. [Import Planner](#7-import-planner)
8. [QA Verifier](#8-qa-verifier)
9. [Proposal Packet Schema](#9-proposal-packet-schema)
10. [Importer Validation](#10-importer-validation)
11. [Idempotency](#11-idempotency)
12. [Test Plan](#12-test-plan)

---

## 1. MCP JSON-RPC Server Shape

### 1.1 Transport

```
stdio transport:
  - READ:  sys.stdin.buffer (binary, newline-delimited JSON UTF-8)
  - WRITE: sys.stdout.buffer (binary, newline-delimited JSON UTF-8)
  - DEBUG: sys.stderr (text, human-readable, never JSON-RPC)
```

Each message is a single JSON object terminated by `\n`.

### 1.2 JSON-RPC 2.0 Envelope

#### Request format (client → server)

```python
import json, sys

def read_request() -> dict:
    """Blocking read of one JSON-RPC request from stdin."""
    line = sys.stdin.buffer.readline()
    if not line:
        raise EOFError("stdin closed")
    return json.loads(line.decode("utf-8"))
```

```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "lifeos.capture_metadata",
        "arguments": {
            "capture_ref": "cap_20260708_100118_7573e4"
        }
    }
}
```

#### initialize request

```json
{
    "jsonrpc": "2.0",
    "id": 0,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {
            "name": "lifeos-orchestrator",
            "version": "0.1.0"
        }
    }
}
```

#### initialize response

```python
INITIALIZE_RESPONSE = {
    "jsonrpc": "2.0",
    "id": 0,
    "result": {
        "protocolVersion": "2025-03-26",
        "capabilities": {
            "tools": {}
        },
        "serverInfo": {
            "name": "lifeos-capture-mcp",
            "version": "0.1.0"
        }
    }
}
```

#### tools/list request

```json
{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
}
```

#### tools/list response

Returns exactly 5 tools. See §2 for each schema.

```python
TOOLS_LIST_RESPONSE = {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
        "tools": [
            LIFEOS_STATUS_TOOL,
            CAPTURE_SUMMARY_TOOL,
            CAPTURE_METADATA_TOOL,
            TEMPLATE_CATALOG_TOOL,
            CURRENT_WORKING_STATE_TOOL,
        ]
    }
}
```

#### tools/call response (success)

```json
{
    "jsonrpc": "2.0",
    "id": 2,
    "result": {
        "content": [
            {
                "type": "text",
                "text": "{\"capture_id\": \"cap_...\", ...}"
            }
        ],
        "isError": false
    }
}
```

#### tools/call validation flow

```python
ALLOWED_TOOLS = frozenset({
    "lifeos.status",
    "lifeos.capture_summary",
    "lifeos.capture_metadata",
    "lifeos.template_catalog",
    "lifeos.current_working_state_summary",
})

def dispatch_tool_call(request: dict) -> dict:
    params = request.get("params", {})
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    req_id = request.get("id")

    if tool_name not in ALLOWED_TOOLS:
        return error_response(req_id, -32601, f"Tool not found: {tool_name}")

    # Validate arguments with JSON Schema
    schema = TOOL_SCHEMAS[tool_name].get("inputSchema", {"type": "object", "properties": {}, "required": []})
    err = validate_params(arguments, schema)
    if err:
        return error_response(req_id, -32602, f"Invalid params: {err}")

    try:
        result = HANDLERS[tool_name](arguments)
    except Exception as e:
        return error_response(req_id, -32603, f"Internal error: {e}")

    return success_response(req_id, result)
```

### 1.3 Error Format

```python
def error_response(req_id, code: int, message: str, data=None) -> dict:
    resp = {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {
            "code": code,
            "message": message,
        }
    }
    if data is not None:
        resp["error"]["data"] = data
    return resp
```

Standard error codes:

| Code | Meaning | When used |
|------|---------|-----------|
| -32700 | Parse error | Invalid JSON received |
| -32600 | Invalid Request | Not a valid JSON-RPC request |
| -32601 | Method not found | Tool name not in ALLOWED_TOOLS |
| -32602 | Invalid params | Params fail JSON Schema validation |
| -32603 | Internal error | Handler raised exception |

Formatting:

```python
def send_response(resp: dict) -> None:
    """Write one JSON-RPC response to stdout."""
    line = json.dumps(resp, ensure_ascii=False) + "\n"
    sys.stdout.buffer.write(line.encode("utf-8"))
    sys.stdout.buffer.flush()

def debug_log(msg: str) -> None:
    """Write debug info to stderr, never to stdout."""
    print(f"[lifeos-mcp] {msg}", file=sys.stderr, flush=True)
```

### 1.4 Server Main Loop

```python
def main_loop():
    """Read JSON-RPC requests from stdin, dispatch, write responses to stdout."""
    while True:
        try:
            line = sys.stdin.buffer.readline()
            if not line:
                break
            request = json.loads(line.decode("utf-8"))
        except EOFError:
            break
        except json.JSONDecodeError as e:
            send_response(error_response(None, -32700, f"Parse error: {e}"))
            continue

        method = request.get("method", "")
        req_id = request.get("id")

        if method == "initialize":
            resp = dict(INITIALIZE_RESPONSE)
            resp["id"] = req_id
            send_response(resp)
        elif method == "tools/list":
            resp = json.loads(json.dumps(TOOLS_LIST_RESPONSE))
            resp["id"] = req_id
            send_response(resp)
        elif method == "tools/call":
            resp = dispatch_tool_call(request)
            send_response(resp)
        elif method == "notifications/initialized":
            # No response for notifications
            pass
        else:
            send_response(error_response(req_id, -32601, f"Method not found: {method}"))
```

---

## 2. MCP Tool Schemas

### 2.1 Tool General Shape

Each tool is a dict with keys: `name`, `description`, `inputSchema`.

`inputSchema` is a JSON Schema (draft-07) `object` with `properties` and `required`.

Return values are JSON-serializable dicts, wrapped in `{"content": [{"type": "text", "text": "<json-string>"}], "isError": false}`.

### 2.2 `lifeos.status`

No external calls needed — reads filesystem state only.

```python
LIFEOS_STATUS_TOOL = {
    "name": "lifeos.status",
    "description": "Return a read-only summary of the LifeOS system status, including capture queue counts, event log health, git state, disk usage, and running service indicators.",
    "inputSchema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

def handle_lifeos_status(args: dict) -> dict:
    """Return system status summary."""
    return {
        "service": "lifeos-capture-mcp",
        "status": "ok",
        "mode": "read_only",
        "timestamp": _utcnow_iso(),
        "capture_queue": _capture_queue_summary(),
        "event_log": _event_log_summary(),
        "paths": {
            "capture_buffer_exists": os.path.isdir("/home/lifeos/LifeOS_Capture_Buffer"),
            "vault_exists": os.path.isdir("/home/lifeos/10_Vaults/LifeOS"),
            "event_log_exists": os.path.isfile("/home/lifeos/50_Event_Log/events.jsonl"),
        }
    }
```

Return JSON shape:

```python
STATUS_RETURN_SHAPE = {
    "service": "lifeos-capture-mcp",
    "status": "ok",                       # "ok" | "degraded" | "error"
    "mode": "read_only",
    "timestamp": "2026-07-08T12:00:00Z",
    "capture_queue": {
        "exists": True,
        "count": 12,
        "newest_capture_id": "cap_...",
        "newest_received_at": "2026-07-08T...",
        "sources_breakdown": {"telegram_operator": 3, "desktop": 2, "unknown": 7},
        "types_breakdown": {"text": 10, "url": 2},
    },
    "event_log": {
        "exists": True,
        "line_count": 120,
        "last_event_id": "evt_...",
        "last_event_type": "...",
        "last_event_time": "2026-07-08T...",
    },
    "paths": {
        "capture_buffer_exists": True,
        "vault_exists": True,
        "event_log_exists": True,
    }
}
```

### 2.3 `lifeos.capture_summary`

```python
CAPTURE_SUMMARY_TOOL = {
    "name": "lifeos.capture_summary",
    "description": "Return metadata-only summary of the current capture queue: total count, newest capture ID, source and type breakdowns. Does not include capture content.",
    "inputSchema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

def handle_capture_summary(args: dict) -> dict:
    return _capture_queue_summary()
```

Return JSON shape:

```python
CAPTURE_SUMMARY_RETURN = {
    "exists": True,
    "count": 12,
    "newest_capture_id": "cap_20260708_113939_9b9b341a",
    "newest_received_at": "2026-07-08T11:39:39Z",
    "sources_breakdown": {"telegram_operator": 3, "desktop": 2, "unknown": 6, "manual": 1},
    "types_breakdown": {"text": 10, "url": 2},
    "malformed_count": 0,
}
```

### 2.4 `lifeos.capture_metadata`

```python
CAPTURE_METADATA_TOOL = {
    "name": "lifeos.capture_metadata",
    "description": "Return metadata for a specific capture by reference. Does not include capture content text. Accepts capture_ref as a capture_id string.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "capture_ref": {
                "type": "string",
                "description": "Capture reference: a capture_id like 'cap_20260708_100118_7573e4'"
            }
        },
        "required": ["capture_ref"]
    }
}

def handle_capture_metadata(args: dict) -> dict:
    capture_ref = args["capture_ref"]
    # Validate format
    if not _is_valid_capture_id(capture_ref):
        raise ValueError(f"Invalid capture_ref format: {capture_ref}")
    return _lookup_capture_metadata(capture_ref)
```

Return JSON shape:

```python
CAPTURE_METADATA_RETURN = {
    "capture_id": "cap_20260708_100118_7573e4",
    "capture_type": "url",
    "source": "telegram_operator",
    "has_url": True,
    "url": "https://youtube.com/shorts/WgYS3W04aVA...",
    "content_length": 44,
    "content_preview": "https://youtube.com/shorts/WgYS3W04aVA?is=6SPuw-...",
    "received_at": "2026-07-08T10:01:18Z",
    "event_id": "evt_20260708T100118Z_telegram_capture_created",
    "status": "pending_review",       # from pending_review/ file if exists
    "file_exists": True,
    "file_path": "30_Capture/pending_review/20260708_100118_1c9df0_httpsyoutubecomshortswgys3w04avais6spuw-.md",
}
```

### 2.5 `lifeos.template_catalog`

```python
TEMPLATE_CATALOG_TOOL = {
    "name": "lifeos.template_catalog",
    "description": "Return the list of available templates from the LifeOS vault template directory, including name, path, and description.",
    "inputSchema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

def handle_template_catalog(args: dict) -> dict:
    return {
        "templates": _scan_templates(),
        "template_dir": "/home/lifeos/10_Vaults/LifeOS/08_TEMPLATES",
        "timestamp": _utcnow_iso(),
    }
```

Return JSON shape:

```python
TEMPLATE_CATALOG_RETURN = {
    "templates": [
        {"name": "Knowledge_Note.md", "path": "/home/lifeos/10_Vaults/LifeOS/08_TEMPLATES/Knowledge_Note.md", "exists": True, "size_bytes": 0},
        {"name": "Capture.md",        "path": "/home/lifeos/10_Vaults/LifeOS/08_TEMPLATES/Capture.md",        "exists": True, "size_bytes": 0},
        {"name": "Project.md",        "path": "/home/lifeos/10_Vaults/LifeOS/08_TEMPLATES/Project.md",        "exists": True, "size_bytes": 0},
        {"name": "Decision.md",       "path": "/home/lifeos/10_Vaults/LifeOS/08_TEMPLATES/Decision.md",       "exists": True, "size_bytes": 0},
        {"name": "AI_Context.md",     "path": "/home/lifeos/10_Vaults/LifeOS/08_TEMPLATES/AI_Context.md",     "exists": True, "size_bytes": 0},
        {"name": "Area.md",           "path": "/home/lifeos/10_Vaults/LifeOS/08_TEMPLATES/Area.md",           "exists": True, "size_bytes": 0},
        {"name": "Daily.md",          "path": "/home/lifeos/10_Vaults/LifeOS/08_TEMPLATES/Daily.md",          "exists": True, "size_bytes": 0},
        {"name": "Approval_Request.md", "path": "/home/lifeos/10_Vaults/LifeOS/08_TEMPLATES/Approval_Request.md", "exists": True, "size_bytes": 0},
    ],
    "template_dir": "/home/lifeos/10_Vaults/LifeOS/08_TEMPLATES",
    "timestamp": "2026-07-08T12:00:00Z",
}
```

### 2.6 `lifeos.current_working_state_summary`

Reads the first 100 lines (frontmatter + summary) of Current_Working_State.md.

```python
CURRENT_WORKING_STATE_TOOL = {
    "name": "lifeos.current_working_state_summary",
    "description": "Return a structured summary of the current LifeOS working state, including active milestone, completed items, current decisions, and known backlog. Reads from 10_AI_UNIVERSE/Current_Working_State.md.",
    "inputSchema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}

def handle_current_working_state_summary(args: dict) -> dict:
    path = "/home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Current_Working_State.md"
    return {
        "path": path,
        "exists": os.path.isfile(path),
        "content_preview": _read_head(path, lines=100) if os.path.isfile(path) else "",
        "timestamp": _utcnow_iso(),
    }
```

Return JSON shape:

```python
CURRENT_WORKING_STATE_RETURN = {
    "path": "/home/lifeos/10_Vaults/LifeOS/10_AI_UNIVERSE/Current_Working_State.md",
    "exists": True,
    "content_preview": "# Current Working State\n\n## Active Milestone\n\n...",
    "timestamp": "2026-07-08T12:00:00Z",
}
```

### 2.7 Handler Registration

```python
HANDLERS = {
    "lifeos.status":                        handle_lifeos_status,
    "lifeos.capture_summary":               handle_capture_summary,
    "lifeos.capture_metadata":              handle_capture_metadata,
    "lifeos.template_catalog":              handle_template_catalog,
    "lifeos.current_working_state_summary": handle_current_working_state_summary,
}

TOOL_SCHEMAS = {
    "lifeos.status":                        LIFEOS_STATUS_TOOL,
    "lifeos.capture_summary":               CAPTURE_SUMMARY_TOOL,
    "lifeos.capture_metadata":              CAPTURE_METADATA_TOOL,
    "lifeos.template_catalog":              TEMPLATE_CATALOG_TOOL,
    "lifeos.current_working_state_summary": CURRENT_WORKING_STATE_TOOL,
}
```

---

## 3. Orchestrator Request/Response Schema

### 3.1 CLI Entry Point

```
lifeos_orchestrator <subcommand> [options]

Subcommands:
  propose-knowledge       Classify a capture, curate a Knowledge draft, build a proposal packet
  view-proposal           Display a proposal packet
  reject-proposal         Reject a proposal with a reason
  revise-proposal         Trigger proposal revision
  approve-import          Validate and import an approved proposal into the canonical vault
```

### 3.2 `propose-knowledge`

```python
def build_propose_knowledge_parser(subparsers) -> None:
    p = subparsers.add_parser("propose-knowledge",
        help="Classify capture, curate Knowledge note, build proposal packet")
    p.add_argument("--capture", required=True,
                   help="Capture ref: 'latest', 1-based index, or capture_id")
    p.add_argument("--output", choices=["json", "text"], default="text",
                   help="Output format (default: text)")
    p.add_argument("--dry-run", action="store_true",
                   help="Curate and build proposal but do not write proposal packet")
    p.add_argument("--force-new", action="store_true",
                   help="Force new proposal even if existing proposal matches content hash")
    # Paths (with sensible defaults, overridable for testing)
    p.add_argument("--queue-path", default=f"{HOME}/LifeOS_Capture_Buffer/00_Raw/captures.jsonl")
    p.add_argument("--pending-dir", default=f"{HOME}/30_Capture/pending_review")
    p.add_argument("--vault-root", default=f"{HOME}/10_Vaults/LifeOS")
    p.add_argument("--proposals-dir", default=f"{HOME}/LifeOS_Capture_Buffer/03_Review_Packets")
```

#### CLI invocation examples

```bash
# Propose from the newest capture, text output, dry run (no file written)
python3 lifeos_orchestrator.py propose-knowledge --capture latest --output text --dry-run

# Propose from capture index 3, JSON output, write proposal
python3 lifeos_orchestrator.py propose-knowledge --capture 3 --output json

# Propose from specific capture_id, force new proposal ignoring idempotency
python3 lifeos_orchestrator.py propose-knowledge --capture cap_20260708_100118_7573e4 --force-new
```

#### Response JSON shape (--output json)

```python
PROPOSE_KNOWLEDGE_RESPONSE = {
    "proposal_id": "prop_20260708T120000Z_550e84_knowledge_docker_compose_best_practices",
    "capture_ref": "cap_20260708_113939_9b9b341a",
    "classification": {
        "type": "knowledge",
        "subtype": "reference",
        "confidence": "high",
        "rationale": "Technical content about Docker Compose best practices with specific configuration patterns",
        "classification_rules_matched": [
            "contains_technical_terms",
            "educational_content_pattern",
            "reference_documentation_style"
        ]
    },
    "status": "proposed",
    "proposal_path": "/home/lifeos/LifeOS_Capture_Buffer/03_Review_Packets/prop_20260708T120000Z_550e84_knowledge_docker_compose_best_practices.md",
    "dry_run": False,
    "curated_title": "Docker Compose Best Practices",
    "import_destination": "/home/lifeos/10_Vaults/LifeOS/04_KNOWLEDGE/Software/Docker_Compose_Best_Practices.md",
    "content_hash": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "timestamp": "2026-07-08T12:00:00Z",
    "warnings": []
}
```

### 3.3 `view-proposal`

```python
def build_view_proposal_parser(subparsers) -> None:
    p = subparsers.add_parser("view-proposal",
        help="Display a proposal packet")
    p.add_argument("--proposal-id", required=True,
                   help="Proposal ID (prop_...) or path to proposal file")
    p.add_argument("--output", choices=["json", "text"], default="text")
    p.add_argument("--proposals-dir", default=f"{HOME}/LifeOS_Capture_Buffer/03_Review_Packets")
```

#### Response (--output json)

```python
VIEW_PROPOSAL_RESPONSE = {
    "proposal_id": "prop_20260708T120000Z_550e84_knowledge_docker_compose_best_practices",
    "proposal_path": "...",
    "exists": True,
    "frontmatter": { ... },       # parsed YAML frontmatter as dict
    "body": "...",                # full body markdown
    "status": "proposed",
    "import_status": "not_imported",
}
```

### 3.4 `reject-proposal`

```python
def build_reject_proposal_parser(subparsers) -> None:
    p = subparsers.add_parser("reject-proposal",
        help="Reject a proposal with a reason")
    p.add_argument("--proposal-id", required=True)
    p.add_argument("--reason", required=True,
                   help="Reason for rejection (recorded in proposal frontmatter)")
    p.add_argument("--proposals-dir", default=f"{HOME}/LifeOS_Capture_Buffer/03_Review_Packets")
```

#### Behavior
1. Load proposal file
2. Update frontmatter: `status: rejected`, `rejection_reason`, `rejected_at`
3. Rewrite proposal file
4. Move proposal to `05_Rejected/` directory in buffer vault

```python
REJECT_RESPONSE = {
    "proposal_id": "prop_...",
    "status": "rejected",
    "rejection_reason": "Content already covered in existing note",
    "rejected_at": "2026-07-08T12:05:00Z",
    "previous_status": "proposed",
}
```

### 3.5 `revise-proposal`

```python
def build_revise_proposal_parser(subparsers) -> None:
    p = subparsers.add_parser("revise-proposal",
        help="Record a revision instruction on a proposal")
    p.add_argument("--proposal-id", required=True)
    p.add_argument("--instruction", required=True,
                   help="Revision instruction recorded in frontmatter")
    p.add_argument("--proposals-dir", default=f"{HOME}/LifeOS_Capture_Buffer/03_Review_Packets")
```

#### Behavior
1. Load proposal file
2. Update frontmatter: `status: revision_requested`, `revision_instruction`, `revision_requested_at`
3. Rewrite proposal file

```python
REVISE_RESPONSE = {
    "proposal_id": "prop_...",
    "status": "revision_requested",
    "revision_instruction": "Please add more detail about networking configuration",
    "revision_requested_at": "2026-07-08T12:10:00Z",
    "previous_status": "proposed",
}
```

### 3.6 `approve-import`

```python
def build_approve_import_parser(subparsers) -> None:
    p = subparsers.add_parser("approve-import",
        help="Validate and import an approved proposal into the canonical vault")
    p.add_argument("--proposal-id", required=True)
    p.add_argument("--output", choices=["json", "text"], default="text")
    p.add_argument("--vault-root", default=f"{HOME}/10_Vaults/LifeOS")
    p.add_argument("--proposals-dir", default=f"{HOME}/LifeOS_Capture_Buffer/03_Review_Packets")
```

#### Behavior
1. Load proposal
2. Run importer validation (§10) — all checks must pass
3. If validation fails, report errors and abort
4. If validation passes, update frontmatter: `status: approved_for_import`, `approved_at`
5. Execute atomic write of Knowledge note to canonical vault (temp file + rename)
6. Update proposal frontmatter: `import_status: imported`, `imported_at`, `import_destination_path`, `import_event_id`
7. Return success

```python
APPROVE_IMPORT_RESPONSE = {
    "proposal_id": "prop_...",
    "status": "imported",
    "import_destination": "/home/lifeos/10_Vaults/LifeOS/04_KNOWLEDGE/Software/Docker_Compose_Best_Practices.md",
    "imported_at": "2026-07-08T12:15:00Z",
    "import_event_id": "evt_20260708T121500Z_knowledge_imported",
    "content_hash_verified": True,
    "validation_passed": True,
    "warnings": [],
}
```

---

## 4. Capture Resolution Logic

### 4.1 Resolution Function

```python
from typing import Tuple, Optional, List

CaptureRecord = dict
CaptureId = str
QueuePath = str

class CaptureResolutionError(Exception):
    """Raised when a capture reference cannot be resolved."""
    def __init__(self, ref: str, reason: str):
        self.ref = ref
        self.reason = reason
        super().__init__(f"Cannot resolve capture ref '{ref}': {reason}")

def resolve_capture(queue_path: QueuePath, ref: str, pending_dir: Optional[str] = None) -> CaptureRecord:
    """
    Resolve a capture reference to a capture record from the queue.

    Args:
        queue_path: Path to captures.jsonl
        ref:       'latest', 1-based index string like '3', or capture_id like 'cap_...'
        pending_dir: Optional path to pending_review directory for enriched metadata

    Returns:
        Capture record dict with at minimum: capture_id, capture_type, content, ...
        Also enriched with 'resolution_method' and 'queue_index' fields.

    Raises:
        CaptureResolutionError: if ref is invalid or no matching capture found
    """
    records = _load_all_records(queue_path)
    if not records:
        raise CaptureResolutionError(ref, "Queue is empty")

    if ref == "latest":
        return _resolve_latest(records, pending_dir)
    elif ref.isdigit():
        return _resolve_index(records, int(ref), pending_dir)
    else:
        return _resolve_by_id(records, ref, pending_dir)
```

### 4.2 How "latest" resolves

```python
def _resolve_latest(records: List[CaptureRecord], pending_dir: Optional[str]) -> CaptureRecord:
    """Return the newest capture by received_at timestamp."""
    newest = None
    newest_ts = ""
    for i, rec in enumerate(records):
        ts = rec.get("received_at", rec.get("timestamp", ""))
        if not newest_ts or ts > newest_ts:
            newest_ts = ts
            newest = rec
            newest["queue_index"] = i + 1  # 1-based
    if newest is None:
        raise CaptureResolutionError("latest", "No records with timestamps found")
    newest["resolution_method"] = "latest"
    return _enrich_record(newest, pending_dir)
```

### 4.3 How numeric index resolves

```python
def _resolve_index(records: List[CaptureRecord], index: int, pending_dir: Optional[str]) -> CaptureRecord:
    """Resolve by 1-based index from oldest (1 = first record in file)."""
    if index < 1 or index > len(records):
        raise CaptureResolutionError(
            str(index),
            f"Index out of range: 1..{len(records)}"
        )
    rec = records[index - 1]
    rec["queue_index"] = index
    rec["resolution_method"] = "index"
    return _enrich_record(rec, pending_dir)
```

### 4.4 How capture_id resolves

```python
def _resolve_by_id(records: List[CaptureRecord], capture_id: str, pending_dir: Optional[str]) -> CaptureRecord:
    """Resolve by exact capture_id match."""
    # Normalize capture_id: accept both old format "cap_20260706_120503_telegram_note_..."
    # and new format "cap_20260708_093831_647cbd97"
    for i, rec in enumerate(records):
        cid = rec.get("capture_id", "")
        if cid == capture_id:
            rec["queue_index"] = i + 1
            rec["resolution_method"] = "id"
            return _enrich_record(rec, pending_dir)

    # Try partial match (first N chars) as convenience
    for i, rec in enumerate(records):
        cid = rec.get("capture_id", "")
        if cid.startswith(capture_id) and len(capture_id) >= 8:
            rec["queue_index"] = i + 1
            rec["resolution_method"] = "id_partial"
            return _enrich_record(rec, pending_dir)

    raise CaptureResolutionError(capture_id, "No capture found with that ID")

def _is_valid_capture_id(ref: str) -> bool:
    """Validate that a string looks like a capture_id."""
    import re
    # Matches: cap_YYYYMMDD_HHMMSS_HEX or cap_YYYYMMDD_HHMMSS_HEX_slug
    return bool(re.match(r'^cap_\d{8}_\d{6}_[a-f0-9]{4,}', ref))

def _load_all_records(queue_path: str) -> List[CaptureRecord]:
    """Load all valid records from the queue JSONL file."""
    records = []
    if not os.path.isfile(queue_path):
        return records
    with open(queue_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                if "capture_id" in rec:
                    records.append(rec)
            except json.JSONDecodeError:
                continue
    return records

def _enrich_record(rec: CaptureRecord, pending_dir: Optional[str]) -> CaptureRecord:
    """Enrich a queue record with content and file metadata."""
    rec = dict(rec)  # shallow copy so we don't mutate original list

    # Try to load full content from pending_review file
    if pending_dir and os.path.isdir(pending_dir):
        cid = rec.get("capture_id", "")
        # Find the capture file in pending_review/
        for fname in os.listdir(pending_dir):
            if cid in fname and fname.endswith(".md"):
                fpath = os.path.join(pending_dir, fname)
                rec["file_path"] = f"30_Capture/pending_review/{fname}"
                rec["file_exists"] = True
                # Extract content and frontmatter
                content = _read_file(fpath)
                rec["content"] = content
                rec["content_length"] = len(content)
                rec["frontmatter"] = _parse_frontmatter(content)
                break
        else:
            # Capture exists in queue but not (yet) in pending_review
            rec["file_exists"] = False
            rec["content"] = ""
            rec["content_length"] = 0
            rec["frontmatter"] = {}

    return rec
```

### 4.5 Error Messages

```python
# Examples of error messages for invalid resolution:
# CaptureResolutionError("latest", "Queue is empty")
# CaptureResolutionError("0", "Index out of range: 1..15")
# CaptureResolutionError("999", "Index out of range: 1..15")
# CaptureResolutionError("abc", "No capture found with that ID")
# CaptureResolutionError("cap_bad", "Invalid capture_ref format: cap_bad")
```

---

## 5. Deterministic Classifier

### 5.1 Classification Types

```python
from enum import Enum

class CaptureClass(str, Enum):
    KNOWLEDGE = "knowledge"         # V0: only type supported by importer
    IDEA = "idea"
    PROJECT_UPDATE = "project_update"
    TASK = "task"
    REFERENCE = "reference"
    SOURCE_CAPTURE = "source_capture"
    TOOL_REPO_CANDIDATE = "tool_repo_candidate"
    UNKNOWN = "unknown"
```

### 5.2 Classification Rule Engine

```python
import re
from typing import List, Tuple

ClassificationResult = dict  # keys: type, subtype, confidence, rationale, rules_matched

def classify_capture(text: str, capture_type: str = "text", url: Optional[str] = None) -> ClassificationResult:
    """
    Deterministic classification based on text content heuristics.
    No ML, no external AI calls.
    """
    text_lower = text.lower()
    rules_matched = []
    scores = {c: 0 for c in CaptureClass}

    # --- Heuristic rules ---

    # R1: Contains a URL with no/few text -> source_capture
    if capture_type == "url" or (url and len(text.strip()) < 40):
        rules_matched.append("primarily_url")
        scores[CaptureClass.SOURCE_CAPTURE] += 80

    # R2: GitHub/Repo pattern
    if re.search(r'github\.com/[\w.-]+/[\w.-]+', text) or \
       re.search(r'git clone|git@|repository', text_lower):
        rules_matched.append("repo_pattern")
        scores[CaptureClass.TOOL_REPO_CANDIDATE] += 60

    # R3: Task/action patterns
    if re.search(r'\b(todo|task|action item|to do|@todo)\b', text_lower, re.IGNORECASE) or \
       re.search(r'\[ \]|\[x\]|- \[ \]|- \[x\]', text):
        rules_matched.append("task_pattern")
        scores[CaptureClass.TASK] += 50

    # R4: Project update patterns
    if re.search(r'\b(progress|milestone|deliverable|sprint|completed|done|finished|status update)\b', text_lower):
        rules_matched.append("project_update_pattern")
        scores[CaptureClass.PROJECT_UPDATE] += 40

    # R5: Idea patterns
    if re.search(r'\b(what if|imagine|maybe we could|perhaps|concept:|brainstorm)\b', text_lower) or \
       (len(text.split()) < 30 and text.strip().endswith("?")):
        rules_matched.append("idea_pattern")
        scores[CaptureClass.IDEA] += 30

    # R6: Knowledge/educational patterns — strongest signal for V0
    if re.search(r'\b(learn|understand|how to|explain|concept|principle|pattern|architecture|design|best practice|tutorial|guide|reference|documentation|spec|manual|handbook)\b', text_lower):
        rules_matched.append("educational_content")
        scores[CaptureClass.KNOWLEDGE] += 50

    # R7: Technical content
    if re.search(r'\b(api|sdk|framework|library|docker|kubernetes|database|sql|http|json|yaml|python|rust|go|javascript|typescript|linux|kernel|memory|cpu|network|protocol|algorithm|data structure|cache|queue|event|stream)\b', text_lower):
        rules_matched.append("technical_terms")
        scores[CaptureClass.KNOWLEDGE] += 30

    # R8: Structured/documentation style (headings, bullet points, numbered lists)
    heading_count = len(re.findall(r'^#{1,6}\s', text, re.MULTILINE))
    bullet_count = len(re.findall(r'^[\s]*[-*+]\s', text, re.MULTILINE))
    numbered_count = len(re.findall(r'^[\s]*\d+[.)]\s', text, re.MULTILINE))
    structure_score = heading_count * 5 + bullet_count * 2 + numbered_count * 2
    if structure_score >= 10:
        rules_matched.append("structured_content")
        scores[CaptureClass.KNOWLEDGE] += structure_score

    # R9: Short/long text heuristic
    word_count = len(text.split())
    if word_count > 100:
        rules_matched.append("long_form_content")
        scores[CaptureClass.KNOWLEDGE] += 15
        scores[CaptureClass.REFERENCE] += 10
    elif word_count < 10:
        rules_matched.append("short_content")
        scores[CaptureClass.UNKNOWN] += 20

    # R10: Question -> could be knowledge gap or idea
    if "?" in text and word_count > 20:
        rules_matched.append("question_pattern")
        scores[CaptureClass.KNOWLEDGE] += 10

    # Determine winner
    best_type = CaptureClass.UNKNOWN
    best_score = 5  # minimum threshold to beat UNKNOWN default
    for ct in CaptureClass:
        if scores[ct] > best_score:
            best_score = scores[ct]
            best_type = ct

    # Confidence assessment
    if best_score >= 80:
        confidence = "high"
    elif best_score >= 40:
        confidence = "medium"
    else:
        confidence = "low"
        best_type = CaptureClass.UNKNOWN

    # Subtype for knowledge
    subtype = "general"
    if best_type == CaptureClass.KNOWLEDGE:
        if re.search(r'\b(tutorial|guide|how to|step by step)\b', text_lower):
            subtype = "tutorial"
        elif re.search(r'\b(reference|documentation|spec|manual)\b', text_lower):
            subtype = "reference"
        elif re.search(r'\b(pattern|architecture|design|principle)\b', text_lower):
            subtype = "concept"
        elif re.search(r'\b(best practice|optimization|performance)\b', text_lower):
            subtype = "best_practice"

    return {
        "type": best_type.value,
        "subtype": subtype,
        "confidence": confidence,
        "rationale": _build_rationale(rules_matched, scores, best_type),
        "classification_rules_matched": rules_matched,
        "raw_scores": {k.value: v for k, v in scores.items()},
    }

def _build_rationale(rules_matched: List[str], scores: dict, best_type: CaptureClass) -> str:
    """Build a human-readable rationale string."""
    if not rules_matched:
        return "No classification rules matched; defaulting to unknown"
    top_rules = sorted(rules_matched, key=lambda r: _rule_priority(r), reverse=True)[:3]
    return f"Classified as {best_type.value} based on: {', '.join(top_rules)}"

def _rule_priority(rule_name: str) -> int:
    """Priority ordering for rationale building."""
    priorities = {
        "educational_content": 10,
        "technical_terms": 9,
        "structured_content": 8,
        "repo_pattern": 7,
        "project_update_pattern": 6,
        "task_pattern": 5,
        "idea_pattern": 4,
        "long_form_content": 3,
        "short_content": 2,
        "primarily_url": 1,
        "question_pattern": 1,
    }
    return priorities.get(rule_name, 0)
```

### 5.3 V0 Import Restriction

```python
def validate_v0_classification(classification: ClassificationResult) -> Tuple[bool, str]:
    """V0 importer only supports knowledge type."""
    if classification["type"] != CaptureClass.KNOWLEDGE.value:
        return False, (
            f"V0 orchestrator only supports knowledge type. "
            f"Capture classified as '{classification['type']}' (confidence: {classification['confidence']}). "
            f"Other types will be supported in V1+."
        )
    return True, ""
```

---

## 6. Knowledge Curator Module

### 6.1 Module Signature

```python
from typing import Dict, Optional

CuratedKnowledge = dict  # keys: title, frontmatter, body_sections

def curate_knowledge(
    capture_record: CaptureRecord,
    classification: ClassificationResult,
    mcp_context: Dict[str, dict],
    template_version: str = "1.0",
) -> CuratedKnowledge:
    """
    Build a Knowledge note from capture content using deterministic rules.

    Args:
        capture_record: Resolved capture with content, metadata
        classification: Classifier output
        mcp_context: Dict with keys from MCP tools:
            - "template_catalog": template list from template_catalog MCP tool
            - "current_working_state": summary from current_working_state_summary MCP tool
            - "capture_metadata": metadata from capture_metadata MCP tool
            - "capture_summary": queue summary from capture_summary tool
        template_version: Version string for tracking template used

    Returns:
        Dict with title, frontmatter (dict), body_sections (dict of section_name -> content)
    """
    text = capture_record.get("content", capture_record.get("content_preview", ""))
    cid = capture_record["capture_id"]
    source = capture_record.get("source", "unknown")

    # 1. Generate title
    title = _generate_title(text, cid)

    # 2. Build frontmatter
    frontmatter = _build_knowledge_frontmatter(capture_record, classification)

    # 3. Build body sections
    body = _build_knowledge_body(text, capture_record, classification, mcp_context)

    return {
        "title": title,
        "frontmatter": frontmatter,
        "body_sections": body,
    }
```

### 6.2 Title Generation

```python
def _generate_title(text: str, capture_id: str) -> str:
    """
    Generate a title from capture text.

    Strategy:
    1. If text starts with a markdown heading (# Title), use that
    2. If text has a first line that looks like a title (short, no period at end), use that
    3. Fallback: use first 60 chars of text, truncated at word boundary
    4. Last resort: "Capture: {capture_id[:20]}..."
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    if not lines:
        return f"Untitled Capture ({capture_id[:16]})"

    # Strategy 1: Markdown heading
    for line in lines:
        m = re.match(r'^#{1,3}\s+(.+)$', line)
        if m:
            title = m.group(1).strip()
            return _sanitize_title(title)

    # Strategy 2: First substantial line that looks like a title
    for line in lines:
        clean = re.sub(r'^[-*]\s+', '', line)  # strip bullet markers
        clean = clean.strip()
        if 10 <= len(clean) <= 120 and not clean.endswith(('.', ',', ';', ':', '!', '?')):
            return _sanitize_title(clean)

    # Strategy 3: First line, truncated
    first = lines[0][:60].rsplit(" ", 1)[0]
    if len(first) >= 10:
        return _sanitize_title(first)

    # Strategy 4: Fallback
    return f"Capture Note ({capture_id[:20]})"

def _sanitize_title(title: str) -> str:
    """Clean a title string without over-aggressively shortening it."""
    # Remove markdown formatting characters
    title = re.sub(r'[*_~`]', '', title)
    # Remove URL-like fragments
    title = re.sub(r'https?://\S+', '', title)
    # Collapse whitespace
    title = re.sub(r'\s+', ' ', title).strip()
    # Limit length
    if len(title) > 100:
        title = title[:97].rsplit(" ", 1)[0] + "..."
    return title
```

### 6.3 Frontmatter Generation

```python
def _build_knowledge_frontmatter(capture_record: CaptureRecord, classification: ClassificationResult) -> dict:
    """Build YAML frontmatter for a Knowledge note."""
    return {
        "type": "knowledge",
        "subtype": classification.get("subtype", "general"),
        "status": "draft",
        "created": _utcnow_iso_date(),
        "updated": _utcnow_iso_date(),
        "source_type": capture_record.get("capture_type", "unknown"),
        "source": capture_record.get("source", "unknown"),
        "capture_id": capture_record["capture_id"],
        "classification_confidence": classification.get("confidence", "unknown"),
        "template_version": "1.0",
        "schema_version": 1,
        "review_status": "not_reviewed",
        "tags": _infer_tags(classification),
    }

def _infer_tags(classification: ClassificationResult) -> list:
    """Infer tags from classification subtype."""
    tags = ["knowledge"]
    subtype = classification.get("subtype", "general")
    if subtype != "general":
        tags.append(subtype)
    return tags
```

### 6.4 Body Section Generation

```python
def _build_knowledge_body(
    text: str,
    capture_record: CaptureRecord,
    classification: ClassificationResult,
    mcp_context: Dict[str, dict],
) -> Dict[str, str]:
    """
    Build structured body sections for a Knowledge note.
    Returns dict of section_name -> markdown_content.

    Sections:
      1. Summary
      2. Definition / Context
      3. Key Details
      4. Why It Matters
      5. How It Connects to LifeOS
      6. Source Trail
      7. Related Concepts
      8. Review Notes (for human reviewer)
    """
    sections = {}

    # --- 1. Summary ---
    sections["summary"] = _build_summary(text)

    # --- 2. Definition / Context ---
    sections["definition_context"] = _build_definition(text)

    # --- 3. Key Details ---
    sections["key_details"] = _build_key_details(text)

    # --- 4. Why It Matters ---
    sections["why_it_matters"] = _build_why_matters(text, classification, mcp_context)

    # --- 5. How It Connects to LifeOS ---
    sections["lifeos_connection"] = _build_lifeos_connection(classification, mcp_context)

    # --- 6. Source Trail ---
    sections["source_trail"] = _build_source_trail(capture_record)

    # --- 7. Related Concepts ---
    sections["related_concepts"] = _build_related_concepts(text, classification)

    # --- 8. Review Notes ---
    sections["review_notes"] = _build_review_notes()

    return sections

def _build_summary(text: str) -> str:
    """Extract a 2-4 sentence summary from the text."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    # Skip headings for summary extraction
    content_lines = [l for l in lines if not l.startswith("#")]

    if not content_lines:
        return "_No content available for summarization._"

    # Take first 3 substantive sentences
    full_text = " ".join(content_lines)
    sentences = re.split(r'(?<=[.!?])\s+', full_text)
    summary_sentences = sentences[:3]
    summary = " ".join(summary_sentences)

    if len(summary) < 50:
        summary = full_text[:200].rsplit(" ", 1)[0] + "..."

    return f"This note captures knowledge about: {summary}"

def _build_definition(text: str) -> str:
    """
    Extract definition/context from text.
    Looks for: first paragraph after heading, or lines containing definition patterns.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip() and not p.strip().startswith("#")]
    if paragraphs:
        first_para = paragraphs[0]
        if len(first_para) > 30:
            return first_para[:500]

    # Fallback
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    return "\n".join(lines[:5])[:500] if lines else "_No definition extracted._"

def _build_key_details(text: str) -> str:
    """Extract key details: bullet points, numbered items, code blocks, and significant facts."""
    lines = text.split("\n")
    details = []

    # Extract bullet points and numbered items
    for line in lines:
        stripped = line.strip()
        if re.match(r'^[-*+]\s', stripped) or re.match(r'^\d+[.)]\s', stripped):
            details.append(stripped)

    if details:
        return "\n".join(details[:20])
    else:
        # Fallback: list key sentences
        full_text = " ".join(l for l in lines if l.strip() and not l.startswith("#"))
        sentences = re.split(r'(?<=[.!?])\s+', full_text)
        key_sentences = [s for s in sentences if len(s) > 40][:5]
        return "\n".join(f"- {s.strip()}" for s in key_sentences) if key_sentences else "_No structured details extracted._"

def _build_why_matters(
    text: str,
    classification: ClassificationResult,
    mcp_context: Dict[str, dict],
) -> str:
    """
    Determine why this knowledge matters.
    Uses heuristics: mentions of 'important', 'critical', 'best practice', etc.
    Also checks against current working state for relevance.
    """
    text_lower = text.lower()
    reasons = []

    if re.search(r'\b(important|critical|crucial|essential|vital|key)\b', text_lower):
        reasons.append("- This content is flagged as containing important/critical information.")

    if re.search(r'\b(best practice|recommended|standard|convention)\b', text_lower):
        reasons.append("- Contains best practices or recommended approaches.")

    if re.search(r'\b(common|frequent|often|typical)\b', text_lower):
        reasons.append("- Addresses a commonly encountered scenario or question.")

    if classification.get("confidence") == "high":
        reasons.append("- High-confidence classification suggests strong knowledge signal.")

    # Check if content relates to current working state topics
    ws = mcp_context.get("current_working_state", {})
    ws_preview = ws.get("content_preview", "")
    if ws_preview:
        # Naive keyword overlap check
        keywords = set(re.findall(r'[a-zA-Z]{4,}', text_lower))
        ws_keywords = set(re.findall(r'[a-zA-Z]{4,}', ws_preview.lower()))
        overlap = keywords & ws_keywords
        if len(overlap) > 5:
            reasons.append(f"- Shares {len(overlap)} keywords with current working state, indicating relevance to active work.")

    if not reasons:
        reasons.append("- General knowledge reference. Review relevance manually.")

    return "\n".join(reasons)

def _build_lifeos_connection(
    classification: ClassificationResult,
    mcp_context: Dict[str, dict],
) -> str:
    """Suggest how this knowledge connects to LifeOS structure."""
    connections = []
    subtype = classification.get("subtype", "general")

    # Based on subtype, suggest connections
    if subtype in ("tutorial", "guide"):
        connections.append("- May supplement existing project documentation as reference material.")
    elif subtype in ("concept", "pattern"):
        connections.append("- May inform architectural decisions recorded in project Decision.md files.")
    elif subtype in ("best_practice",):
        connections.append("- Can be referenced in project AI_Context.md files as constraints/guidance.")
    elif subtype in ("reference",):
        connections.append("- Serves as reference material for future project work or decisions.")

    # Check what templates exist
    templates = mcp_context.get("template_catalog", {}).get("templates", [])
    template_names = [t["name"] for t in templates]
    if "Knowledge_Note.md" in template_names:
        connections.append("- Follows Knowledge_Note.md template structure.")
    if "Decision.md" in template_names:
        connections.append("- May influence future decisions in the relevant domain.")

    if not connections:
        connections.append("- General LifeOS knowledge entry. Review for domain-specific connections.")

    return "\n".join(connections)

def _build_source_trail(capture_record: CaptureRecord) -> str:
    """Build source traceability section."""
    cid = capture_record.get("capture_id", "unknown")
    source = capture_record.get("source", "unknown")
    capture_type = capture_record.get("capture_type", "unknown")
    received = capture_record.get("received_at", capture_record.get("timestamp", "unknown"))
    event_id = capture_record.get("event_id", "unknown")
    url = capture_record.get("url", "")

    lines = [
        f"- **Capture ID:** {cid}",
        f"- **Source:** {source}",
        f"- **Capture Type:** {capture_type}",
        f"- **Received:** {received}",
        f"- **Event ID:** {event_id}",
    ]
    if url:
        lines.append(f"- **Source URL:** {url}")
    lines.append(f"- **Curated By:** LifeOS Knowledge Curator (deterministic, V0)")
    lines.append(f"- **Curation Date:** {_utcnow_iso_date()}")

    return "\n".join(lines)

def _build_related_concepts(text: str, classification: ClassificationResult) -> str:
    """Suggest related concepts based on keyword extraction."""
    text_lower = text.lower()
    concepts = set()

    # Domain keyword mapping
    DOMAIN_MAP = {
        "docker": "Docker, Containerization",
        "kubernetes": "Kubernetes, Orchestration",
        "python": "Python Programming",
        "rust": "Rust Programming",
        "go": "Go Programming",
        "javascript": "JavaScript, Web Development",
        "typescript": "TypeScript, Web Development",
        "sql": "SQL, Databases",
        "api": "API Design, REST",
        "graphql": "GraphQL",
        "linux": "Linux, System Administration",
        "git": "Git, Version Control",
        "ai": "Artificial Intelligence",
        "machine learning": "Machine Learning, AI",
        "network": "Networking",
        "security": "Security, Cybersecurity",
        "database": "Databases, Data Storage",
        "cache": "Caching, Performance",
        "queue": "Message Queues, Event-Driven Architecture",
        "monitoring": "Monitoring, Observability",
    }

    for keyword, concepts_str in DOMAIN_MAP.items():
        if keyword in text_lower:
            concepts.add(concepts_str)

    if concepts:
        return "\n".join(f"- {c}" for c in sorted(concepts))
    else:
        subtype = classification.get("subtype", "general")
        return f"- Related to: {subtype} knowledge domain\n- Manual review suggested for cross-linking"

def _build_review_notes() -> str:
    """Generate review notes section for the human reviewer."""
    return (
        "_This curated note was generated deterministically by the LifeOS Knowledge Curator (V0). "
        "No AI/ML model was used in its creation. Content may require human review for accuracy, "
        "completeness, and appropriate cross-linking._\n\n"
        "**Review Checklist:**\n"
        "- [ ] Title accurately represents the content\n"
        "- [ ] Summary captures the key points\n"
        "- [ ] Classification and subtype are correct\n"
        "- [ ] Source trail is complete and accurate\n"
        "- [ ] Related concepts are appropriate\n"
        "- [ ] Content does not duplicate existing vault notes\n"
        "- [ ] Tags and frontmatter are correct"
    )
```

### 6.5 Assembling the Full Note

```python
def assemble_knowledge_note(curated: CuratedKnowledge) -> str:
    """Assemble a curated knowledge note into a full markdown string."""
    fm = curated["frontmatter"]
    body = curated["body_sections"]

    lines = ["---"]
    for key in [
        "type", "subtype", "status", "created", "updated",
        "source_type", "source", "capture_id", "classification_confidence",
        "template_version", "schema_version", "review_status", "tags",
    ]:
        val = fm.get(key, "")
        if isinstance(val, list):
            lines.append(f"{key}: [{', '.join(val)}]")
        else:
            lines.append(f"{key}: {val}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {curated['title']}")
    lines.append("")
    lines.append("## Summary")
    lines.append(body.get("summary", "_No summary available._"))
    lines.append("")
    lines.append("## Definition / Context")
    lines.append(body.get("definition_context", "_No context available._"))
    lines.append("")
    lines.append("## Key Details")
    lines.append(body.get("key_details", "_No details extracted._"))
    lines.append("")
    lines.append("## Why It Matters")
    lines.append(body.get("why_it_matters", "_Review manually._"))
    lines.append("")
    lines.append("## How It Connects to LifeOS")
    lines.append(body.get("lifeos_connection", "_Review manually._"))
    lines.append("")
    lines.append("## Source Trail")
    lines.append(body.get("source_trail", "_No source information._"))
    lines.append("")
    lines.append("## Related Concepts")
    lines.append(body.get("related_concepts", "_No related concepts identified._"))
    lines.append("")
    lines.append("## Review Notes")
    lines.append(body.get("review_notes", "_No review notes._"))
    lines.append("")

    return "\n".join(lines)
```

---

## 7. Import Planner

### 7.1 Conservative Category Selection

```python
from typing import Optional, Tuple

KNOWN_CATEGORIES = [
    "AI",
    "Software",
    "Systems",
    "Networking",
    "Hardware",
    "LifeOS",
    "Reference",  # fallback
]

CATEGORY_KEYWORDS = {
    "AI": [
        "ai", "artificial intelligence", "machine learning", "deep learning",
        "neural network", "llm", "gpt", "transformer", "nlp", "computer vision",
        "reinforcement learning", "prompt engineering", "embedding", "vector",
    ],
    "Software": [
        "software", "programming", "code", "api", "sdk", "framework", "library",
        "docker", "kubernetes", "git", "database", "sql", "python", "rust",
        "go", "javascript", "typescript", "devops", "ci/cd", "testing",
    ],
    "Systems": [
        "linux", "kernel", "operating system", "systemd", "process", "memory",
        "cpu", "filesystem", "syscall", "scheduler", "io", "storage",
        "distributed systems", "concurrency",
    ],
    "Networking": [
        "network", "tcp", "udp", "http", "dns", "tls", "ssl", "firewall",
        "proxy", "vpn", "routing", "subnet", "ip", "packet", "websocket",
        "grpc", "rest", "api gateway",
    ],
    "Hardware": [
        "hardware", "cpu", "gpu", "ram", "motherboard", "ssd", "disk",
        "server", "raspberry pi", "arduino", "microcontroller", "embedded",
    ],
    "LifeOS": [
        "lifeos", "obsidian", "capture", "telegram", "n8n", "opencode",
        "paperless", "qdrant", "backup", "vault", "git", "mcp",
    ],
}

def plan_import_path(
    curated_title: str,
    classification: ClassificationResult,
    capture_text: str,
    vault_root: str = "/home/lifeos/10_Vaults/LifeOS",
) -> Tuple[str, str]:
    """
    Propose a destination path under the Knowledge directory.

    Returns:
        (category, full_path)

    Strategy:
    1. Score each category based on keyword matches in text
    2. Select highest-scoring category
    3. If no clear winner, use Reference (fallback)
    4. Sanitize title to safe filename
    5. Assemble full path
    """
    text_lower = capture_text.lower()

    # Score categories
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for kw in keywords:
            if kw in text_lower:
                score += 1
            # Bonus for word boundary matches
            if re.search(r'\b' + re.escape(kw) + r'\b', text_lower):
                score += 2
        scores[cat] = score

    # Select category
    max_score = max(scores.values()) if scores else 0
    if max_score >= 3:
        top_cats = [c for c, s in scores.items() if s == max_score]
        category = top_cats[0]  # Take first alphabetically if tie
    else:
        # Check classification subtype for hints
        subtype = classification.get("subtype", "general")
        if subtype in ("tutorial", "reference", "concept", "best_practice"):
            # Still try to find a category, but be more lenient
            if max_score >= 1:
                top_cats = [c for c, s in scores.items() if s == max_score]
                category = top_cats[0]
            else:
                category = "Reference"
        else:
            category = "Reference"

    # Sanitize filename
    safe_filename = sanitize_filename(curated_title) + ".md"

    # Assemble path
    knowledge_base = os.path.join(vault_root, "04_KNOWLEDGE")
    full_path = os.path.join(knowledge_base, category, safe_filename)

    return category, full_path

def sanitize_filename(title: str) -> str:
    """
    Convert a title to a safe filename.

    Rules:
    - Replace spaces with underscores
    - Remove characters unsafe for most filesystems: / \ : * ? " < > | #
    - Collapse multiple underscores
    - Trim leading/trailing underscores and dots
    - Limit to 200 chars max
    - Preserve CamelCase and PascalCase (don't lowercase)
    """
    # Replace spaces and common separators with underscore
    safe = re.sub(r'[\s\-–—]+', '_', title)
    # Remove unsafe characters
    safe = re.sub(r'[\\/:*?"<>|#!@$%^&()+={}\[\];,\'`~]', '', safe)
    # Collapse multiple underscores
    safe = re.sub(r'_+', '_', safe)
    # Trim
    safe = safe.strip('_.')
    # Limit length (reserve room for .md extension)
    if len(safe) > 200:
        safe = safe[:197] + "..."
    # Ensure not empty
    if not safe:
        safe = "Untitled"
    return safe
```

### 7.2 Path Safety Validation

```python
def validate_import_path(proposed_path: str, vault_root: str) -> Tuple[bool, str]:
    """
    Validate that a proposed import path is safe.

    Checks:
    1. Resolves to within the vault root (no path traversal)
    2. Under 04_KNOWLEDGE directory
    3. Has .md extension
    4. Is a new file (no overwrite without explicit update mode)
    """
    vault_root = os.path.realpath(vault_root)
    real_path = os.path.realpath(proposed_path)

    # Check 1: No path traversal
    if not real_path.startswith(vault_root + os.sep):
        return False, f"Path traversal detected: {proposed_path} resolves outside vault root"

    # Check 2: Under 04_KNOWLEDGE
    knowledge_dir = os.path.join(vault_root, "04_KNOWLEDGE")
    if not real_path.startswith(knowledge_dir + os.sep):
        return False, f"Path not under 04_KNOWLEDGE: {proposed_path}"

    # Check 3: .md extension
    if not real_path.endswith(".md"):
        return False, f"Not a markdown file: {proposed_path}"

    # Check 4: Existing file check (caller should handle overwrite policy)
    if os.path.exists(real_path):
        return False, f"File already exists: {real_path} (overwrite requires --update flag)"

    return True, ""
```

---

## 8. QA Verifier

### 8.1 Verifier Function

```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class QAResult:
    verdict: str           # "pass" | "pass_with_warnings" | "fail"
    checks: List[dict]     # [{name, status, detail}, ...]
    warnings: List[str]
    errors: List[str]
    proposal_id: str = ""

    def to_dict(self):
        return {
            "verdict": self.verdict,
            "checks": self.checks,
            "warnings": self.warnings,
            "errors": self.errors,
            "proposal_id": self.proposal_id,
        }

def verify_proposal(
    proposal_frontmatter: dict,
    proposal_body: str,
    proposal_path: str,
    vault_root: str,
) -> QAResult:
    """
    Run all QA checks against a proposal packet.

    Returns QAResult with verdict (pass/pass_with_warnings/fail) and detailed checks.
    """
    result = QAResult(
        verdict="pass",
        checks=[],
        warnings=[],
        errors=[],
        proposal_id=proposal_frontmatter.get("proposal_id", ""),
    )

    # === CRITICAL CHECKS (fail on any) ===

    # C1: Proposal has approval_required flag
    _check(result, "approval_required_flag",
           proposal_frontmatter.get("approval_required") is True,
           critical=True)

    # C2: Proposal has source trail
    _check(result, "source_trail",
           "source_trail" in proposal_frontmatter or "source" in proposal_frontmatter,
           critical=True,
           detail="Frontmatter must include source information")

    # C3: Proposal has content hash
    _check(result, "content_hash",
           "content_hash" in proposal_frontmatter and proposal_frontmatter["content_hash"].startswith("sha256:"),
           critical=True,
           detail="Frontmatter must include sha256: content hash")

    # C4: Import path under allowed root
    dest = proposal_frontmatter.get("import_destination", "")
    path_ok, path_err = validate_import_path(dest, vault_root)
    _check(result, "import_path_safe",
           path_ok,
           critical=True,
           detail=path_err if not path_ok else f"Destination: {dest}")

    # C5: Body contains required sections
    required_sections = [
        "Summary",
        "Definition",
        "Key Details",
        "Why It Matters",
        "How It Connects",
        "Source Trail",
        "Related Concepts",
        "Review Notes",
    ]
    for section in required_sections:
        section_pattern = re.compile(rf'^##\s+{re.escape(section)}', re.MULTILINE | re.IGNORECASE)
        _check(result, f"section_{section.lower().replace(' ', '_')}",
               bool(section_pattern.search(proposal_body)),
               critical=True,
               detail=f"Body must contain ## {section} section")

    # C6: No overwrite without update mode
    if not proposal_frontmatter.get("update_mode", False):
        _check(result, "no_overwrite",
               not os.path.exists(dest) if dest else True,
               critical=True,
               detail="File must not already exist; use update mode to overwrite")

    # === NON-CRITICAL CHECKS (warnings only) ===

    # W1: Has uncertainty section
    uncertainty_sig = any(kw in proposal_body.lower() for kw in [
        "uncertain", "unknown", "unclear", "review", "verify", "unsure",
        "may require", "pending", "to be determined"
    ])
    _check(result, "uncertainty_section",
           uncertainty_sig,
           critical=False,
           is_warning=True,
           detail="Content should acknowledge uncertainty or areas needing review")

    # W2: Has version
    _check(result, "proposal_version",
           "proposal_version" in proposal_frontmatter,
           critical=False,
           is_warning=True,
           detail="Proposal should include proposal_version field")

    # W3: Has approval checklist
    checklist_pattern = re.search(r'\[ \]|checklist', proposal_body, re.IGNORECASE)
    _check(result, "approval_checklist",
           bool(checklist_pattern),
           critical=False,
           is_warning=True,
           detail="Proposal should include an approval checklist")

    # W4: Status is explicitly set
    status = proposal_frontmatter.get("status", "")
    _check(result, "status_field",
           status in ("proposed", "revision_requested", "approved_for_import", "rejected", "imported"),
           critical=False,
           is_warning=True,
           detail=f"Status should be a valid state, got: '{status}'")

    # Determine verdict
    if result.errors:
        result.verdict = "fail"
    elif result.warnings:
        result.verdict = "pass_with_warnings"
    else:
        result.verdict = "pass"

    return result

def _check(result: QAResult, name: str, condition: bool, critical: bool = False,
           is_warning: bool = False, detail: str = ""):
    """Record a check result."""
    status = "pass"
    if not condition:
        if critical:
            status = "fail"
            result.errors.append(f"[{name}] {detail}")
        elif is_warning:
            status = "warning"
            result.warnings.append(f"[{name}] {detail}")
    result.checks.append({
        "name": name,
        "status": status,
        "detail": detail,
        "critical": critical,
    })
```

### 8.2 Verdict Format

```python
# Example QA output (--output json)
QA_OUTPUT_EXAMPLE = {
    "verdict": "pass_with_warnings",
    "checks": [
        {"name": "approval_required_flag", "status": "pass", "detail": "", "critical": True},
        {"name": "source_trail", "status": "pass", "detail": "Frontmatter includes source information", "critical": True},
        {"name": "content_hash", "status": "pass", "detail": "Frontmatter includes sha256: content hash", "critical": True},
        {"name": "import_path_safe", "status": "pass", "detail": "Destination: /home/lifeos/10_Vaults/LifeOS/04_KNOWLEDGE/Software/...", "critical": True},
        {"name": "section_summary", "status": "pass", "detail": "Body contains ## Summary section", "critical": True},
        # ... more section checks ...
        {"name": "uncertainty_section", "status": "warning", "detail": "Content should acknowledge uncertainty", "critical": False},
        {"name": "proposal_version", "status": "warning", "detail": "Proposal should include proposal_version field", "critical": False},
        {"name": "approval_checklist", "status": "pass", "detail": "", "critical": False},
        {"name": "status_field", "status": "pass", "detail": "Status: 'proposed'", "critical": False},
    ],
    "warnings": [
        "[uncertainty_section] Content should acknowledge uncertainty or areas needing review",
        "[proposal_version] Proposal should include proposal_version field",
    ],
    "errors": [],
    "proposal_id": "prop_20260708T120000Z_550e84_knowledge_docker_compose_best_practices",
}
```

---

## 9. Proposal Packet Schema

### 9.1 Exact YAML Frontmatter

```yaml
---
# === Proposal Identification ===
type: proposal
proposal_id: "prop_20260708T120000Z_550e84_knowledge_docker_compose_best_practices"
proposal_version: 1
schema_version: 1
template_version: "1.0"

# === Capture Traceability ===
capture_id: "cap_20260708_113939_9b9b341a"
capture_ref: "cap_20260708_113939_9b9b341a"    # same as capture_id for V0
source: "desktop"                                # from capture record
source_type: "text"                              # from capture record
captured_at: "2026-07-08T11:39:39Z"             # from capture record
resolution_method: "latest"                      # how capture was resolved

# === Classification ===
classification_type: "knowledge"                 # from classifier
classification_subtype: "reference"               # from classifier
classification_confidence: "high"                 # from classifier
classification_rationale: "Technical content about Docker Compose..."
classification_rules_matched:
  - "technical_terms"
  - "structured_content"
  - "educational_content"

# === Proposed Note ===
proposed_note_type: "knowledge"                  # V0: always knowledge
proposed_title: "Docker Compose Best Practices"
proposed_filename: "Docker_Compose_Best_Practices.md"
import_category: "Software"                      # from import planner
import_destination: "/home/lifeos/10_Vaults/LifeOS/04_KNOWLEDGE/Software/Docker_Compose_Best_Practices.md"

# === Integrity ===
content_hash: "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
content_hash_algorithm: "sha256"

# === Approval State ===
status: "proposed"                               # proposed | revision_requested | approved_for_import | rejected | imported
approval_required: true                          # always true for V0

# === Status Tracking ===
proposed_at: "2026-07-08T12:00:00Z"
proposed_by: "lifeos-orchestrator-v0"
reviewed_at: ""
reviewed_by: ""
approved_at: ""
approved_by: ""
rejected_at: ""
rejection_reason: ""
revision_instruction: ""
revision_requested_at: ""

# === Import State ===
import_status: "not_imported"                     # not_imported | imported
import_event_id: ""
imported_at: ""
import_destination_path: ""

# === QA State ===
qa_verdict: "pass_with_warnings"
qa_warnings:
  - "[uncertainty_section] Content should acknowledge uncertainty"
  - "[proposal_version] Proposal should include proposal_version field"
qa_errors: []

# === Vault Context ===
vault_root: "/home/lifeos/10_Vaults/LifeOS"
template_version_used: "1.0"
mcp_tools_used:
  - "lifeos.status"
  - "lifeos.capture_summary"
  - "lifeos.capture_metadata"
  - "lifeos.template_catalog"
  - "lifeos.current_working_state_summary"
---
```

### 9.2 Python Types

```python
from typing import TypedDict, List, Optional, Literal

class ProposalFrontmatter(TypedDict, total=False):
    # Identification
    type: Literal["proposal"]
    proposal_id: str
    proposal_version: int
    schema_version: int
    template_version: str

    # Traceability
    capture_id: str
    capture_ref: str
    source: str
    source_type: str
    captured_at: str
    resolution_method: str

    # Classification
    classification_type: str
    classification_subtype: str
    classification_confidence: str
    classification_rationale: str
    classification_rules_matched: List[str]

    # Proposed Note
    proposed_note_type: Literal["knowledge"]
    proposed_title: str
    proposed_filename: str
    import_category: str
    import_destination: str

    # Integrity
    content_hash: str          # "sha256:hex"
    content_hash_algorithm: Literal["sha256"]

    # Approval State
    status: str                # proposed | revision_requested | approved_for_import | rejected | imported
    approval_required: bool

    # Timestamps
    proposed_at: str
    proposed_by: str
    reviewed_at: str
    reviewed_by: str
    approved_at: str
    approved_by: str
    rejected_at: str
    rejection_reason: str
    revision_instruction: str
    revision_requested_at: str

    # Import
    import_status: str
    import_event_id: str
    imported_at: str
    import_destination_path: str

    # QA
    qa_verdict: str
    qa_warnings: List[str]
    qa_errors: List[str]

    # Context
    vault_root: str
    template_version_used: str
    mcp_tools_used: List[str]
```

### 9.3 Required Markdown Sections

The proposal body must follow this structure:

```markdown
# Review Packet: {proposed_title}

## Capture Summary
(capture metadata: id, source, type, timestamp, content preview)

## Proposed Changes
### Files to Create
| File | Destination | Type | Size |
|---|---|---|---|
| ... | ... | knowledge | ~{bytes} |

### Files to Update
(None for V0 create-only)

### Files Explicitly Not Touched
- All other files in the canonical vault

## Agent Outputs
### Knowledge Curator Output
(full curated knowledge note — the assembled markdown from Knowledge Curator)

## Summary of Changes
(2-4 sentences describing what this import does)

## Source Trail
(traceability from capture → proposal → import)

## Risks
| Risk | Severity | Description | Mitigation |
|---|---|---|---|
| Content accuracy | Medium | Deterministic curation may miss nuance | Human review before approval |
| Duplicate content | Low | May overlap with existing notes | Manual cross-reference during review |

## QA Result
- Verdict: {pass | pass_with_warnings | fail}
- Checks: {summary of checks}
- Warnings: {list}
- Errors: {list}

## Human Approval Checklist
- [ ] I have reviewed the curated content for accuracy
- [ ] Title and classification are appropriate
- [ ] Import destination is correct
- [ ] Content does not duplicate existing vault notes
- [ ] Tags and frontmatter are appropriate
- [ ] I understand this import CANNOT be automatically rolled back

## Import Command
```
lifeos_orchestrator approve-import --proposal-id {proposal_id}
```

## Rollback Procedure
1. Manually delete the imported file from the canonical vault
2. Update event log with rollback entry
3. No automated rollback is available for V0

---

## Safety Notice
**IMPORTANT:** This proposal packet was generated by the LifeOS Capture-to-Vault
Orchestrator V0, a deterministic rules-based system. No AI/ML model was used in
the curation of this content. However, deterministic curation may miss context,
nuance, or connections that a human reviewer would catch.

**This content has NOT been imported into the canonical LifeOS vault yet.**
No files have been created or modified outside the buffer vault.

**Approval is required before any import occurs.** Review carefully.
```

### 9.4 Content Hash Calculation

```python
import hashlib

def compute_content_hash(body: str, algorithm: str = "sha256") -> str:
    """
    Compute a content hash of the proposal body.

    The body is the complete markdown body (excluding YAML frontmatter).
    We normalize line endings to \n before hashing.
    """
    normalized = body.replace("\r\n", "\n").replace("\r", "\n")
    h = hashlib.new(algorithm)
    h.update(normalized.encode("utf-8"))
    return f"{algorithm}:{h.hexdigest()}"

def verify_content_hash(body: str, expected_hash: str) -> bool:
    """Verify that the body matches the expected content hash."""
    algo, _, hexdigest = expected_hash.partition(":")
    if not algo or not hexdigest:
        return False
    actual = compute_content_hash(body, algo)
    return actual == expected_hash
```

### 9.5 Safety Notice

The safety notice is appended at the end of every proposal packet body:

```python
SAFETY_NOTICE = """---

## Safety Notice
**IMPORTANT:** This proposal packet was generated by the LifeOS Capture-to-Vault
Orchestrator V0, a deterministic rules-based system. No AI/ML model was used in
the curation of this content. However, deterministic curation may miss context,
nuance, or connections that a human reviewer would catch.

**This content has NOT been imported into the canonical LifeOS vault yet.**
No files have been created or modified outside the buffer vault.

**Approval is required before any import occurs.** Review carefully.
"""

def build_proposal_packet(
    frontmatter: ProposalFrontmatter,
    curated_note: str,
    capture_summary_text: str,
    qa_result: QAResult,
) -> str:
    """Assemble the complete proposal packet markdown."""
    body_sections = []

    body_sections.append(f"# Review Packet: {frontmatter.get('proposed_title', 'Untitled')}")
    body_sections.append("")
    body_sections.append("## Capture Summary")
    body_sections.append(capture_summary_text)
    body_sections.append("")
    body_sections.append("## Proposed Changes")
    body_sections.append("### Files to Create")
    body_sections.append(f"| File | Destination | Type | Size |")
    body_sections.append(f"|---|---|---|---|")
    body_sections.append(f"| {frontmatter.get('proposed_filename', 'unknown.md')} | `{frontmatter.get('import_destination', 'unknown')}` | knowledge | ~{len(curated_note)} bytes |")
    body_sections.append("")
    body_sections.append("### Files to Update")
    body_sections.append("_None — V0 only supports creating new Knowledge notes._")
    body_sections.append("")
    body_sections.append("### Files Explicitly Not Touched")
    body_sections.append("- All other files in the canonical LifeOS vault")
    body_sections.append("")
    body_sections.append("## Agent Outputs")
    body_sections.append("### Knowledge Curator Output")
    body_sections.append(curated_note)
    body_sections.append("")
    body_sections.append("## Summary of Changes")
    body_sections.append(f"Creates one new Knowledge note: **{frontmatter.get('proposed_title', 'Untitled')}** under `04_KNOWLEDGE/{frontmatter.get('import_category', 'Reference')}/`. No existing files are modified or deleted.")
    body_sections.append("")
    body_sections.append("## Source Trail")
    body_sections.append(f"- Capture ID: {frontmatter.get('capture_id', 'unknown')}")
    body_sections.append(f"- Source: {frontmatter.get('source', 'unknown')}")
    body_sections.append(f"- Curated by: LifeOS Knowledge Curator V0 (deterministic)")
    body_sections.append(f"- Proposal generated: {frontmatter.get('proposed_at', 'unknown')}")
    body_sections.append("")
    body_sections.append("## Risks")
    body_sections.append("| Risk | Severity | Description | Mitigation |")
    body_sections.append("|---|---|---|---|")
    body_sections.append("| Content accuracy | Medium | Deterministic curation may miss nuance | Human review before approval |")
    body_sections.append("| Duplicate content | Low | May overlap with existing vault notes | Manual cross-reference during review |")
    body_sections.append("")
    body_sections.append("## QA Result")
    body_sections.append(f"- **Verdict:** {qa_result.verdict}")
    body_sections.append(f"- **Checks passed:** {sum(1 for c in qa_result.checks if c['status'] == 'pass')}/{len(qa_result.checks)}")
    if qa_result.warnings:
        body_sections.append("- **Warnings:**")
        for w in qa_result.warnings:
            body_sections.append(f"  - {w}")
    if qa_result.errors:
        body_sections.append("- **Errors:**")
        for e in qa_result.errors:
            body_sections.append(f"  - {e}")
    body_sections.append("")
    body_sections.append("## Human Approval Checklist")
    body_sections.append("- [ ] I have reviewed the curated content for accuracy")
    body_sections.append("- [ ] Title and classification are appropriate")
    body_sections.append("- [ ] Import destination is correct")
    body_sections.append("- [ ] Content does not duplicate existing vault notes")
    body_sections.append("- [ ] Tags and frontmatter are appropriate")
    body_sections.append("- [ ] I understand this import CANNOT be automatically rolled back")
    body_sections.append("")
    body_sections.append("## Import Command")
    body_sections.append("```")
    body_sections.append(f"lifeos_orchestrator approve-import --proposal-id {frontmatter.get('proposal_id', 'unknown')}")
    body_sections.append("```")
    body_sections.append("")
    body_sections.append("## Rollback Procedure")
    body_sections.append("1. Manually delete the imported file from the canonical vault")
    body_sections.append("2. Update event log with rollback entry")
    body_sections.append("3. No automated rollback is available for V0")
    body_sections.append("")

    body = "\n".join(body_sections)

    # Compute hash of body (without safety notice) for consistency
    content_hash = compute_content_hash(body)

    # Add safety notice
    body += SAFETY_NOTICE

    # Assemble full packet: YAML frontmatter + body
    frontmatter["content_hash"] = content_hash
    yaml_block = _dict_to_yaml(frontmatter)
    full_packet = f"---\n{yaml_block}---\n\n{body}"

    return full_packet
```

### 9.6 Simple YAML Serialization (stdlib only)

```python
def _dict_to_yaml(d: dict, indent: int = 0) -> str:
    """Simple YAML serializer for proposal frontmatter. stdlib only."""
    lines = []
    prefix = "  " * indent
    for key, value in d.items():
        if value is None or value == "":
            lines.append(f"{prefix}{key}:")
        elif isinstance(value, bool):
            lines.append(f"{prefix}{key}: {'true' if value else 'false'}")
        elif isinstance(value, int):
            lines.append(f"{prefix}{key}: {value}")
        elif isinstance(value, list):
            if not value:
                lines.append(f"{prefix}{key}: []")
            else:
                lines.append(f"{prefix}{key}:")
                for item in value:
                    lines.append(f"{prefix}  - {_yaml_scalar(item)}")
        elif isinstance(value, dict):
            lines.append(f"{prefix}{key}:")
            lines.append(_dict_to_yaml(value, indent + 1))
        else:
            lines.append(f"{prefix}{key}: {_yaml_scalar(str(value))}")
    return "\n".join(lines)

def _yaml_scalar(value: str) -> str:
    """Quote a YAML scalar if needed."""
    if not value:
        return '""'
    # Quote if contains special chars
    if any(c in value for c in ':{}[]&*?|>!%@`,\'"#'):
        return f'"{value}"'
    # Quote if it looks like a boolean/null/number
    if value.lower() in ("true", "false", "null", "yes", "no", "on", "off") or value.isdigit():
        return f'"{value}"'
    return value

def parse_simple_yaml(yaml_text: str) -> dict:
    """
    Parse a minimal YAML frontmatter block.
    Supports: key: value, key: "value", key: [list], nested dicts with indent.
    Not a full YAML parser — handles only the proposal packet format.
    """
    result = {}
    lines = yaml_text.strip().split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue

        # Check for key without value (next line starts a list)
        if ":" in line and line.strip().endswith(":"):
            key = line.split(":", 1)[0].strip()
            # Peek ahead for list items
            j = i + 1
            list_items = []
            while j < len(lines) and lines[j].strip().startswith("- "):
                item = lines[j].strip()[2:]
                list_items.append(_parse_yaml_value(item.strip()))
                j += 1
            if list_items:
                result[key] = list_items
                i = j
                continue

        # Key: value
        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            result[key] = _parse_yaml_value(value)
        i += 1

    return result

def _parse_yaml_value(value: str):
    """Parse a single YAML value."""
    value = value.strip().strip('"').strip("'")
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value == "[]":
        return []
    try:
        return int(value)
    except ValueError:
        pass
    return value
```

---

## 10. Importer Validation

### 10.1 Validator Function

```python
from dataclasses import dataclass

@dataclass
class ImportValidation:
    passed: bool
    checks: dict        # check_name -> (pass/fail, detail)
    errors: List[str]
    warnings: List[str]

def validate_for_import(proposal_frontmatter: dict, proposal_body: str, vault_root: str) -> ImportValidation:
    """
    Full validation suite before import execution.
    All checks must pass for import to proceed.
    """
    result = ImportValidation(passed=True, checks={}, errors=[], warnings=[])

    def check(name: str, condition: bool, detail: str = "", critical: bool = True):
        result.checks[name] = ("pass" if condition else "fail", detail)
        if not condition:
            if critical:
                result.errors.append(f"[{name}] {detail}")
                result.passed = False
            else:
                result.warnings.append(f"[{name}] {detail}")

    fm = proposal_frontmatter

    # C1: Type
    check("type_is_proposal",
          fm.get("type") == "proposal",
          f"Expected type=proposal, got '{fm.get('type')}'")

    # C2: Schema version
    check("schema_version",
          fm.get("schema_version") == 1,
          f"Expected schema_version=1, got '{fm.get('schema_version')}'")

    # C3: Status
    check("status_approved",
          fm.get("status") == "approved_for_import",
          f"Expected status=approved_for_import, got '{fm.get('status')}'")

    # C4: Approval required
    check("approval_required",
          fm.get("approval_required") is True,
          "approval_required must be true")

    # C5: Import status
    check("import_status",
          fm.get("import_status") == "not_imported",
          f"Expected import_status=not_imported, got '{fm.get('import_status')}'")

    # C6: Note type
    check("proposed_note_type",
          fm.get("proposed_note_type") == "knowledge",
          f"V0 only imports knowledge type, got '{fm.get('proposed_note_type')}'")

    # C7: Content hash valid
    expected_hash = fm.get("content_hash", "")
    hash_ok = verify_content_hash(proposal_body, expected_hash)
    check("content_hash_valid",
          hash_ok,
          f"Content hash verification {'passed' if hash_ok else 'FAILED'}")

    # C8: Proposal version
    version = fm.get("proposal_version", 0)
    check("proposal_version",
          version >= 1,
          f"proposal_version must be >= 1, got {version}")

    # C9: Path traversal detection
    dest = fm.get("import_destination", "")
    path_ok, path_err = validate_import_path(dest, vault_root)
    check("path_traversal",
          path_ok,
          path_err if not path_ok else "Path is safe")

    # C10: Overwrite refusal
    if dest and os.path.exists(dest):
        check("no_overwrite",
              False,
              f"File already exists: {dest}. V0 does not support overwrite.")
    else:
        check("no_overwrite", True, "File does not exist — safe to create")

    return result
```

### 10.2 Atomic Write

```python
import os
import tempfile
import shutil

def atomic_write(filepath: str, content: str) -> None:
    """
    Write content to filepath atomically.

    1. Write to temp file in the same directory
    2. Flush + fsync
    3. Rename temp to target (atomic on same filesystem)
    4. On failure, remove temp file
    """
    dirpath = os.path.dirname(filepath)
    # Ensure directory exists
    os.makedirs(dirpath, exist_ok=True)

    fd, tmp_path = tempfile.mkstemp(
        suffix=".md",
        prefix=".tmp_import_",
        dir=dirpath,
    )
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        # Atomic rename
        os.rename(tmp_path, filepath)
    except Exception:
        # Clean up temp file on failure
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise
```

### 10.3 Post-Import Status Update

```python
def update_proposal_post_import(
    proposal_path: str,
    import_destination: str,
    import_event_id: str,
) -> None:
    """
    Update the proposal packet after successful import.

    Updates frontmatter:
      - status: imported
      - import_status: imported
      - imported_at: <now>
      - import_destination_path: <real path>
      - import_event_id: <event id>
    """
    full_content = _read_file(proposal_path)
    fm_text, body = _split_frontmatter_and_body(full_content)

    fm = parse_simple_yaml(fm_text)
    fm["status"] = "imported"
    fm["import_status"] = "imported"
    fm["imported_at"] = _utcnow_iso()
    fm["import_destination_path"] = import_destination
    fm["import_event_id"] = import_event_id

    new_fm = _dict_to_yaml(fm)
    new_content = f"---\n{new_fm}---\n\n{body}"
    _write_file(proposal_path, new_content)
```

---

## 11. Idempotency

### 11.1 Idempotency Check

```python
def check_idempotency(
    capture_id: str,
    classification_type: str,
    template_version: str,
    proposals_dir: str,
    force_new: bool = False,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Check if a proposal already exists for this capture+type+template.

    Returns:
        (should_proceed, existing_proposal_id, existing_proposal_path)

    If should_proceed is False, an existing valid proposal was found.
    If force_new is True, always returns should_proceed=True.
    """
    if force_new:
        return True, None, None

    if not os.path.isdir(proposals_dir):
        return True, None, None

    for fname in os.listdir(proposals_dir):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(proposals_dir, fname)
        try:
            content = _read_file(fpath)
            fm_text, body = _split_frontmatter_and_body(content)
            fm = parse_simple_yaml(fm_text)
        except Exception:
            continue

        # Match: same capture_id, same type, same template version
        if (fm.get("capture_id") == capture_id and
            fm.get("proposed_note_type") == classification_type and
            fm.get("template_version_used") == template_version and
            fm.get("import_status") == "not_imported"):

            # Verify content hash still matches (stale detection)
            expected_hash = fm.get("content_hash", "")
            if expected_hash and verify_content_hash(body, expected_hash):
                # Valid existing proposal
                return False, fm.get("proposal_id"), fpath
            else:
                # Stale proposal — content hash mismatch; treat as expired
                return True, None, None  # proceed to create new

    return True, None, None

# Usage in propose-knowledge:
# should_proceed, existing_id, existing_path = check_idempotency(
#     capture_id, classification_type, template_version, proposals_dir, args.force_new)
# if not should_proceed:
#     print(f"Existing proposal found: {existing_id}\nPath: {existing_path}\nUse --force-new to override.")
#     return
```

### 11.2 Stale Proposal Detection

```python
def detect_stale_proposal(proposal_path: str) -> Tuple[bool, str]:
    """
    Check if a proposal is stale (content hash mismatch).

    Returns:
        (is_stale, reason)
    """
    try:
        content = _read_file(proposal_path)
        fm_text, body = _split_frontmatter_and_body(content)
        fm = parse_simple_yaml(fm_text)
    except Exception as e:
        return True, f"Cannot parse proposal: {e}"

    expected_hash = fm.get("content_hash", "")
    if not expected_hash:
        return True, "No content_hash in frontmatter"

    if verify_content_hash(body, expected_hash):
        return False, "Content hash valid"
    else:
        return True, f"Content hash mismatch: expected {expected_hash}, computed {compute_content_hash(body)}"
```

---

## 12. Test Plan

### 12.1 Test Fixtures

```python
# tests/fixtures.py — shared test fixtures

import json
import os
import tempfile
import shutil

class TestVaultFixture:
    """Create a minimal LifeOS vault structure for testing importer validation."""

    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="lifeos_test_vault_")
        self._setup()

    def _setup(self):
        """Create minimal vault structure."""
        vault = os.path.join(self.root, "10_Vaults", "LifeOS")
        dirs = [
            os.path.join(vault, "04_KNOWLEDGE", "AI"),
            os.path.join(vault, "04_KNOWLEDGE", "Software"),
            os.path.join(vault, "04_KNOWLEDGE", "Systems"),
            os.path.join(vault, "04_KNOWLEDGE", "Networking"),
            os.path.join(vault, "04_KNOWLEDGE", "Hardware"),
            os.path.join(vault, "04_KNOWLEDGE", "LifeOS"),
            os.path.join(vault, "04_KNOWLEDGE", "Reference"),
            os.path.join(vault, "08_TEMPLATES"),
            os.path.join(vault, "10_AI_UNIVERSE"),
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)

        # Write a minimal Current_Working_State.md
        ws_path = os.path.join(vault, "10_AI_UNIVERSE", "Current_Working_State.md")
        with open(ws_path, "w") as f:
            f.write("# Current Working State\n\n## Active Milestone\n\nFoundation Lock-In.\n")

        # Write template stubs
        for name in ["Knowledge_Note.md", "Project.md", "Decision.md"]:
            tmpl_path = os.path.join(vault, "08_TEMPLATES", name)
            with open(tmpl_path, "w") as f:
                f.write(f"# {name}\n\nTemplate content.\n")

        self.vault_root = vault

    def destroy(self):
        shutil.rmtree(self.root, ignore_errors=True)

class TestCaptureQueueFixture:
    """Create a minimal capture queue for testing capture resolution."""

    def __init__(self, records=None):
        self.dir = tempfile.mkdtemp(prefix="lifeos_test_queue_")
        self.queue_path = os.path.join(self.dir, "captures.jsonl")
        self.pending_dir = os.path.join(self.dir, "pending_review")
        os.makedirs(self.pending_dir, exist_ok=True)

        self._records = []
        if records:
            for rec in records:
                self.add_record(rec)

    def add_record(self, record: dict):
        """Add a record to the queue JSONL."""
        self._records.append(record)
        with open(self.queue_path, "w") as f:
            for rec in self._records:
                f.write(json.dumps(rec) + "\n")

    def add_pending_file(self, capture_id: str, content: str, frontmatter: dict = None):
        """Create a pending_review markdown file for a capture."""
        fm = frontmatter or {}
        lines = ["---"]
        for k, v in fm.items():
            lines.append(f"{k}: {v}")
        lines.append("---")
        lines.append("")
        lines.append(content)

        fname = f"{capture_id.replace('cap_', '')}_{_slugify(content[:30])}.md"
        fpath = os.path.join(self.pending_dir, fname)
        with open(fpath, "w") as f:
            f.write("\n".join(lines))
        return fpath

    def destroy(self):
        shutil.rmtree(self.dir, ignore_errors=True)

class TestProposalsFixture:
    """Create a proposals directory for testing."""

    def __init__(self):
        self.dir = tempfile.mkdtemp(prefix="lifeos_test_proposals_")
        self.proposals_dir = self.dir

    def add_proposal(self, proposal_id: str, frontmatter: dict, body: str):
        """Write a proposal packet to the test directory."""
        fm_text = _dict_to_yaml(frontmatter)
        full = f"---\n{fm_text}---\n\n{body}"
        fpath = os.path.join(self.proposals_dir, f"{proposal_id}.md")
        with open(fpath, "w") as f:
            f.write(full)
        return fpath

    def destroy(self):
        shutil.rmtree(self.dir, ignore_errors=True)
```

### 12.2 Component Test Matrix

```python
# Test plan — what to test for each component

TEST_PLAN = {
    "mcp_server": {
        "module": "lifeos_mcp_server",
        "tests": [
            # Transport
            "test_parse_valid_json_rpc_request",
            "test_parse_malformed_json_returns_parse_error",
            "test_missing_jsonrpc_field_returns_invalid_request",
            # initialize
            "test_initialize_returns_capabilities_and_server_info",
            "test_initialize_includes_tools_capability",
            # tools/list
            "test_tools_list_returns_exactly_5_tools",
            "test_tools_list_includes_all_allowed_tool_names",
            "test_tools_list_each_tool_has_name_description_inputschema",
            "test_tools_list_inputschema_is_valid_json_schema",
            # tools/call
            "test_tools_call_unknown_tool_returns_method_not_found",
            "test_tools_call_missing_required_param_returns_invalid_params",
            "test_tools_call_invalid_param_type_returns_invalid_params",
            "test_tools_call_each_tool_returns_valid_content",
            # Error handling
            "test_internal_error_returns_internal_error_code",
            "test_notification_initialized_returns_no_response",
            "test_unknown_method_returns_method_not_found",
            # Content
            "test_lifeos_status_returns_all_expected_keys",
            "test_capture_summary_returns_counts_and_breakdowns",
            "test_capture_metadata_valid_id_returns_record",
            "test_capture_metadata_invalid_id_raises_value_error",
            "test_template_catalog_lists_templates",
            "test_current_working_state_returns_preview",
        ],
    },

    "capture_resolution": {
        "module": "capture_resolver",
        "tests": [
            "test_resolve_latest_returns_newest_by_timestamp",
            "test_resolve_latest_empty_queue_raises_error",
            "test_resolve_index_1_returns_oldest_record",
            "test_resolve_index_n_returns_nth_record",
            "test_resolve_index_0_raises_out_of_range",
            "test_resolve_index_beyond_length_raises_out_of_range",
            "test_resolve_by_id_exact_match_returns_record",
            "test_resolve_by_id_partial_match_returns_record",
            "test_resolve_by_id_not_found_raises_error",
            "test_resolve_by_id_invalid_format_raises_error",
            "test_enrich_record_adds_content_from_pending_file",
            "test_enrich_record_missing_file_still_returns_metadata",
        ],
    },

    "classifier": {
        "module": "classifier",
        "tests": [
            # Knowledge detection
            "test_technical_documentation_classified_as_knowledge",
            "test_tutorial_content_classified_as_knowledge",
            "test_concept_explanation_classified_as_knowledge",
            "test_best_practices_classified_as_knowledge",
            # Other types
            "test_url_only_classified_as_source_capture",
            "test_github_repo_classified_as_tool_repo_candidate",
            "test_task_list_classified_as_task",
            "test_project_update_classified_as_project_update",
            "test_brainstorm_classified_as_idea",
            # Edge cases
            "test_empty_text_classified_as_unknown",
            "test_short_ambiguous_text_classified_as_unknown",
            "test_mixed_signals_uses_highest_scoring_rule",
            # Subtypes
            "test_tutorial_subtype_detected",
            "test_reference_subtype_detected",
            "test_concept_subtype_detected",
            # Confidence
            "test_high_confidence_when_score_above_80",
            "test_medium_confidence_when_score_40_to_80",
            "test_low_confidence_when_score_below_40",
            # V0 restriction
            "test_v0_only_knowledge_passes_validation",
            "test_v0_non_knowledge_type_fails_validation",
        ],
    },

    "knowledge_curator": {
        "module": "knowledge_curator",
        "tests": [
            # Title generation
            "test_title_from_heading",
            "test_title_from_first_line",
            "test_title_fallback_for_short_text",
            "test_title_sanitization_removes_markdown_chars",
            # Section generation
            "test_summary_extracted_from_first_paragraphs",
            "test_summary_fallback_for_no_text",
            "test_definition_extracted_from_content",
            "test_key_details_extracts_bullet_points",
            "test_key_details_fallback_to_sentences",
            "test_why_matters_detects_important_keywords",
            "test_why_matters_includes_default_if_no_signals",
            "test_lifeos_connection_based_on_subtype",
            "test_source_trail_includes_all_fields",
            "test_related_concepts_maps_domain_keywords",
            "test_review_notes_includes_checklist",
            # Assembly
            "test_assemble_note_includes_all_sections",
            "test_assemble_note_frontmatter_has_required_fields",
        ],
    },

    "import_planner": {
        "module": "import_planner",
        "tests": [
            "test_software_keywords_map_to_Software_category",
            "test_ai_keywords_map_to_AI_category",
            "test_systems_keywords_map_to_Systems_category",
            "test_networking_keywords_map_to_Networking_category",
            "test_hardware_keywords_map_to_Hardware_category",
            "test_lifeos_keywords_map_to_LifeOS_category",
            "test_no_keywords_falls_back_to_Reference",
            "test_filename_sanitization_replaces_spaces",
            "test_filename_sanitization_removes_unsafe_chars",
            "test_filename_sanitization_preserves_case",
            "test_import_path_within_knowledge_dir",
            "test_import_path_traversal_detected",
            "test_import_path_not_markdown_rejected",
            "test_import_path_existing_file_rejected",
        ],
    },

    "qa_verifier": {
        "module": "qa_verifier",
        "tests": [
            "test_pass_when_all_checks_pass",
            "test_warning_when_no_uncertainty_section",
            "test_warning_when_no_proposal_version",
            "test_warning_when_no_approval_checklist",
            "test_fail_when_missing_content_hash",
            "test_fail_when_missing_source_trail",
            "test_fail_when_import_path_unsafe",
            "test_fail_when_missing_required_section",
            "test_verdict_fail_trumps_warnings",
            "test_verdict_pass_with_warnings_before_pass",
        ],
    },

    "proposal_packet": {
        "module": "proposal_packet",
        "tests": [
            "test_frontmatter_has_all_required_fields",
            "test_body_has_all_required_sections",
            "test_content_hash_is_sha256_hex",
            "test_safety_notice_appended",
            "test_proposal_id_format_is_correct",
            "test_build_proposal_packet_assembles_complete_document",
            "test_verify_content_hash_detects_match",
            "test_verify_content_hash_detects_tampering",
            "test_simple_yaml_roundtrip",
            "test_simple_yaml_parses_lists",
            "test_simple_yaml_parses_booleans",
        ],
    },

    "importer": {
        "module": "importer",
        "tests": [
            # Validation
            "test_validate_passes_on_valid_proposal",
            "test_validate_fails_on_wrong_type",
            "test_validate_fails_on_wrong_schema_version",
            "test_validate_fails_on_not_approved",
            "test_validate_fails_on_already_imported",
            "test_validate_fails_on_wrong_note_type",
            "test_validate_fails_on_content_hash_mismatch",
            "test_validate_fails_on_path_traversal",
            "test_validate_fails_on_overwrite_existing",
            # Atomic write
            "test_atomic_write_creates_file",
            "test_atomic_write_content_is_exact",
            "test_atomic_write_does_not_leave_temp_file",
            "test_atomic_write_creates_parent_directory",
            # Post-import update
            "test_post_import_updates_status_to_imported",
            "test_post_import_sets_imported_at_timestamp",
            "test_post_import_records_destination_path",
        ],
    },

    "idempotency": {
        "module": "idempotency",
        "tests": [
            "test_no_existing_proposal_returns_proceed_true",
            "test_existing_valid_proposal_returns_proceed_false",
            "test_force_new_overrides_existing_proposal",
            "test_different_capture_id_proceeds",
            "test_different_template_version_proceeds",
            "test_stale_proposal_content_hash_mismatch_proceeds",
            "test_already_imported_proposal_does_not_block_new",
        ],
    },

    "orchestrator_cli": {
        "module": "lifeos_orchestrator",
        "tests": [
            # propose-knowledge
            "test_propose_knowledge_dry_run_no_file_written",
            "test_propose_knowledge_creates_proposal_packet",
            "test_propose_knowledge_json_output_valid_json",
            "test_propose_knowledge_force_new_bypasses_idempotency",
            "test_propose_knowledge_invalid_capture_ref_error",
            "test_propose_knowledge_non_knowledge_type_error",
            # view-proposal
            "test_view_proposal_returns_formatted_output",
            "test_view_proposal_json_returns_parsed_structure",
            "test_view_proposal_missing_proposal_error",
            # reject-proposal
            "test_reject_proposal_updates_status_to_rejected",
            "test_reject_proposal_records_rejection_reason",
            "test_reject_proposal_missing_reason_error",
            # revise-proposal
            "test_revise_proposal_updates_status_to_revision_requested",
            "test_revise_proposal_records_instruction",
            # approve-import
            "test_approve_import_validates_before_import",
            "test_approve_import_refuses_unapproved_proposal",
            "test_approve_import_atomic_write_to_vault",
            "test_approve_import_updates_proposal_post_import",
            "test_approve_import_refuses_path_traversal",
        ],
    },
}
```

### 12.3 Mock Strategies

```python
# === Mock strategies for MCP server in orchestrator tests ===

# Strategy A: Direct function call (preferred for unit tests)
# Instead of starting a real MCP server over stdio, test the handler functions directly.
#
# Example:
# def test_classifier_calls_mcp_handlers():
#     """Test that the orchestrator correctly calls MCP handler functions."""
#     # Arrange
#     mock_mcp_context = {
#         "lifeos.template_catalog": handle_template_catalog({}),
#         "lifeos.current_working_state_summary": handle_current_working_state_summary({}),
#         "lifeos.capture_metadata": {
#             "capture_id": "cap_test",
#             "source": "desktop",
#             ...
#         },
#         "lifeos.capture_summary": {"count": 1, ...},
#     }
#     # Act
#     curator.curate_knowledge(capture_record, classification, mock_mcp_context)
#     # Assert
#     ...

# Strategy B: MCPClient wrapper class (integration tests)
# A lightweight MCPClient class that can operate in two modes:
#   1. "live" — connects to real MCP server over stdio
#   2. "mock" — returns canned responses from a dict

class MCPClient:
    """MCP JSON-RPC client with mock support."""

    def __init__(self, mode: str = "mock", mock_responses: dict = None):
        self.mode = mode
        self.mock_responses = mock_responses or {}
        self._next_id = 0

    def call_tool(self, tool_name: str, arguments: dict = None) -> dict:
        """Call an MCP tool and return the result."""
        self._next_id += 1
        if self.mode == "mock":
            key = f"{tool_name}:{json.dumps(arguments or {}, sort_keys=True)}"
            return self.mock_responses.get(key, {"error": f"No mock for {key}"})
        else:
            # Real subprocess call to MCP server
            return self._subprocess_call(tool_name, arguments or {})

    def gather_context(self) -> dict:
        """Gather all MCP context needed for curation."""
        return {
            "lifeos.status": self.call_tool("lifeos.status"),
            "lifeos.capture_summary": self.call_tool("lifeos.capture_summary"),
            "lifeos.template_catalog": self.call_tool("lifeos.template_catalog"),
            "lifeos.current_working_state_summary": self.call_tool("lifeos.current_working_state_summary"),
        }

# Example usage in tests:
# client = MCPClient(mode="mock", mock_responses={
#     'lifeos.template_catalog:{}': {"templates": [...]},
#     'lifeos.capture_summary:{}': {"count": 5, ...},
# })
# context = client.gather_context()
```

### 12.4 Test File Organization

```
40_Services/capture_to_vault_orchestrator/
├── lifeos_mcp_server.py          # MCP JSON-RPC server
├── lifeos_orchestrator.py        # Main CLI entry point
├── capture_resolver.py           # Capture resolution logic
├── classifier.py                 # Deterministic classifier
├── knowledge_curator.py          # Knowledge note curation
├── import_planner.py             # Path planning and validation
├── qa_verifier.py                # Proposal verification
├── proposal_packet.py            # Packet assembly and serialization
├── importer.py                   # Import validation and execution
├── idempotency.py                # Idempotency and stale detection
├── utils.py                      # Shared utilities (hashes, yaml, fs helpers)
├── README.md
└── tests/
    ├── __init__.py
    ├── fixtures.py               # TestVaultFixture, TestCaptureQueueFixture, TestProposalsFixture
    ├── test_lifeos_mcp_server.py
    ├── test_capture_resolver.py
    ├── test_classifier.py
    ├── test_knowledge_curator.py
    ├── test_import_planner.py
    ├── test_qa_verifier.py
    ├── test_proposal_packet.py
    ├── test_importer.py
    ├── test_idempotency.py
    └── test_orchestrator_cli.py
```

---

## Appendix A: Utility Functions

```python
# utils.py — shared utilities used across modules

import os
import re
import hashlib
import json
from datetime import datetime, timezone

HOME = os.path.expanduser("~")

def _utcnow_iso() -> str:
    """Return current UTC time as ISO 8601 string with Z suffix."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _utcnow_iso_date() -> str:
    """Return current UTC date."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def _read_file(path: str) -> str:
    """Read a file and return its contents."""
    with open(path, "r") as f:
        return f.read()

def _write_file(path: str, content: str) -> None:
    """Write content to a file."""
    dirpath = os.path.dirname(path)
    if dirpath:
        os.makedirs(dirpath, exist_ok=True)
    with open(path, "w") as f:
        f.write(content)

def _read_head(path: str, lines: int = 100) -> str:
    """Read first N lines of a file."""
    with open(path, "r") as f:
        return "".join(f.readline() for _ in range(lines))

def _split_frontmatter_and_body(content: str) -> tuple:
    """Split a markdown file into (frontmatter_text, body_text)."""
    content = content.lstrip()
    if not content.startswith("---"):
        return "", content
    # Find closing ---
    end = content.find("---", 3)
    if end == -1:
        return "", content
    fm_text = content[3:end].strip()
    body = content[end + 3:].lstrip()
    return fm_text, body

def _parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from a markdown string."""
    fm_text, _ = _split_frontmatter_and_body(content)
    if not fm_text:
        return {}
    return parse_simple_yaml(fm_text)

def _slugify(text: str, max_len: int = 50) -> str:
    """Create a URL-safe slug from text."""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'\s+', '-', text)
    text = re.sub(r'-+', '-', text)
    text = text.strip('-')
    if len(text) > max_len:
        text = text[:max_len].rsplit("-", 1)[0]
    return text or "untitled"

def _capture_queue_summary() -> dict:
    """Read capture queue and return metadata summary."""
    queue_path = os.path.join(HOME, "LifeOS_Capture_Buffer", "00_Raw", "captures.jsonl")
    try:
        from lifeos_capture_summary import get_summary, to_dict
        s = get_summary(queue_path)
        return to_dict(s)
    except Exception:
        return {
            "exists": False,
            "count": 0,
            "error": "Could not read queue",
        }

def _event_log_summary() -> dict:
    """Read event log and return metadata summary."""
    log_path = os.path.join(HOME, "50_Event_Log", "events.jsonl")
    if not os.path.isfile(log_path):
        return {"exists": False, "line_count": 0}
    count = 0
    last_event = {}
    with open(log_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                last_event = json.loads(line)
            except json.JSONDecodeError:
                continue
            count += 1
    return {
        "exists": True,
        "line_count": count,
        "last_event_id": last_event.get("event_id", ""),
        "last_event_type": last_event.get("event_type", ""),
        "last_event_time": last_event.get("occurred_at", ""),
    }

def _scan_templates() -> list:
    """List templates in the vault template directory."""
    tmpl_dir = os.path.join(HOME, "10_Vaults", "LifeOS", "08_TEMPLATES")
    if not os.path.isdir(tmpl_dir):
        return []
    templates = []
    for name in sorted(os.listdir(tmpl_dir)):
        if name.endswith(".md"):
            fpath = os.path.join(tmpl_dir, name)
            templates.append({
                "name": name,
                "path": fpath,
                "exists": True,
                "size_bytes": os.path.getsize(fpath),
            })
    return templates

def generate_proposal_id(classification_type: str, curated_title: str) -> str:
    """Generate a unique proposal ID."""
    import secrets
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rand = secrets.token_hex(3)  # 6 hex chars
    slug = _slugify(curated_title, 40)
    return f"prop_{ts}_{rand}_{classification_type}_{slug}"

def generate_event_id(prefix: str) -> str:
    """Generate a LifeOS event ID."""
    import secrets
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rand = secrets.token_hex(3)
    return f"evt_{ts}_{prefix}_{rand}"

def _is_valid_capture_id(ref: str) -> bool:
    """Validate capture_id format: cap_YYYYMMDD_HHMMSS_hex or cap_YYYYMMDD_HHMMSS_hex_slug."""
    return bool(re.match(r'^cap_\d{8}_\d{6}_[a-f0-9]{4,}', ref))

def _lookup_capture_metadata(capture_id: str) -> dict:
    """Look up a capture in the queue and return metadata (no content)."""
    queue_path = os.path.join(HOME, "LifeOS_Capture_Buffer", "00_Raw", "captures.jsonl")
    if not os.path.isfile(queue_path):
        raise ValueError(f"Queue not found: {queue_path}")

    with open(queue_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("capture_id") == capture_id:
                # Also check pending_review for file info
                pending_dir = os.path.join(HOME, "30_Capture", "pending_review")
                rec = dict(rec)
                rec["file_exists"] = False
                rec["status"] = "unknown"
                if os.path.isdir(pending_dir):
                    for fname in os.listdir(pending_dir):
                        if capture_id in fname and fname.endswith(".md"):
                            rec["file_path"] = f"30_Capture/pending_review/{fname}"
                            rec["file_exists"] = True
                            rec["status"] = "pending_review"
                            break
                return rec

    raise ValueError(f"Capture not found: {capture_id}")
```

---

## Appendix B: JSON Schema Validation (stdlib)

```python
# json_schema_validator.py — minimal JSON Schema validator (stdlib only)
# Supports: type, properties, required, enum, minimum, maximum, minLength, maxLength, pattern

def validate_params(params: dict, schema: dict) -> Optional[str]:
    """
    Validate params against a JSON Schema (object type only).
    Returns None if valid, or an error message string.
    """
    # Top-level type check
    if schema.get("type") != "object":
        return None  # We only handle object schemas

    properties = schema.get("properties", {})
    required = schema.get("required", [])

    # Check required fields
    for field in required:
        if field not in params:
            return f"Missing required field: {field}"

    # Check each provided field
    for field, value in params.items():
        if field not in properties:
            continue  # Additional properties allowed for now
        prop_schema = properties[field]
        err = _validate_value(value, prop_schema, field)
        if err:
            return err

    return None

def _validate_value(value, schema: dict, path: str) -> Optional[str]:
    """Validate a single value against its schema."""
    expected_type = schema.get("type")
    if expected_type:
        if not _check_type(value, expected_type):
            return f"{path}: expected {expected_type}, got {type(value).__name__}"

    if expected_type == "string":
        min_len = schema.get("minLength")
        max_len = schema.get("maxLength")
        if min_len is not None and len(value) < min_len:
            return f"{path}: minLength {min_len}, got {len(value)}"
        if max_len is not None and len(value) > max_len:
            return f"{path}: maxLength {max_len}, got {len(value)}"
        pattern = schema.get("pattern")
        if pattern and not re.match(pattern, value):
            return f"{path}: does not match pattern {pattern}"
        enum_vals = schema.get("enum")
        if enum_vals and value not in enum_vals:
            return f"{path}: must be one of {enum_vals}, got '{value}'"

    if expected_type in ("integer", "number"):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if minimum is not None and value < minimum:
            return f"{path}: minimum {minimum}, got {value}"
        if maximum is not None and value > maximum:
            return f"{path}: maximum {maximum}, got {value}"

    return None

def _check_type(value, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "null":
        return value is None
    return True  # unknown type, skip
```
