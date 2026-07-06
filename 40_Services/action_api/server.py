"""LifeOS Action API — read-write capture and event log operations."""

import json
import os
import re
import secrets
import shutil
import time
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

CAPTURE_BASE = Path("/lifeos/capture")
EVENT_LOG = Path("/lifeos/event-log/events.jsonl")

PENDING_DIR = CAPTURE_BASE / "pending_review"
APPROVED_DIR = CAPTURE_BASE / "approved"
REJECTED_DIR = CAPTURE_BASE / "rejected"
PROCESSED_DIR = CAPTURE_BASE / "processed"

SERVICE_NAME = "lifeos-action-api"
MODE = "read_write"

ALLOWED_DIRS = {PENDING_DIR, APPROVED_DIR, REJECTED_DIR, PROCESSED_DIR}
_SUBDIRS = {PENDING_DIR, APPROVED_DIR, REJECTED_DIR, PROCESSED_DIR}
_ALL_PARENT = CAPTURE_BASE
_VALID_CAPTURE_ID_RE = re.compile(r'^cap_[A-Za-z0-9_-]+$')


def _ensure_dirs():
    for d in _SUBDIRS:
        d.mkdir(parents=True, exist_ok=True)
    EVENT_LOG.parent.mkdir(parents=True, exist_ok=True)


def _slugify(text):
    s = text.lower().strip()
    s = re.sub(r'[^a-z0-9\s-]', '', s)
    s = re.sub(r'[\s-]+', '-', s)
    return s[:40]


def _make_capture_id(text):
    now = datetime.now(timezone.utc)
    date_part = now.strftime('%Y%m%d_%H%M%S')
    rand_suffix = secrets.token_hex(3)
    slug = _slugify(text)
    return f"cap_{date_part}_{rand_suffix}_{slug}"


def _load_event_ids():
    if not EVENT_LOG.exists():
        return set()
    ids = set()
    try:
        raw = EVENT_LOG.read_text("utf-8")
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                eid = obj.get("event_id")
                if eid:
                    ids.add(eid)
            except json.JSONDecodeError:
                continue
    except (OSError, PermissionError):
        pass
    return ids


def _make_event_id(event_type):
    existing = _load_event_ids()
    now = datetime.now(timezone.utc)
    suffix = event_type.replace(".", "_")
    base = f"evt_{now.strftime('%Y%m%dT%H%M%SZ')}_{suffix}"
    candidate = base
    counter = 1
    while candidate in existing:
        candidate = f"{base}_{counter}"
        counter += 1
    return candidate


def _append_event(event_type, details):
    event_id = _make_event_id(event_type)
    event = {
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "actor": {"type": "service", "id": SERVICE_NAME},
        "approval_tier": "A0",
        "status": "completed",
        "summary": "",
        "details": details,
    }
    try:
        with open(EVENT_LOG, "a+") as f:
            f.seek(0, os.SEEK_END)
            pos = f.tell()
            needs_newline = True
            if pos > 0:
                f.seek(pos - 1)
                needs_newline = f.read(1) != "\n"
            if needs_newline:
                f.write("\n")
            f.write(json.dumps(event, ensure_ascii=False))
        return event_id
    except (OSError, PermissionError):
        return None


def _safe_resolve(path):
    try:
        resolved = path.resolve()
        cap_base = CAPTURE_BASE.resolve()
        if cap_base not in resolved.parents and resolved != cap_base:
            return None
        return resolved
    except (RuntimeError, OSError):
        return None


def _is_within_allowed(resolved):
    for d in ALLOWED_DIRS:
        d_resolved = d.resolve()
        if resolved == d_resolved or d_resolved in resolved.parents:
            return True
    return False


def _read_capture_file(filepath):
    try:
        text = filepath.read_text("utf-8", errors="replace")
    except (OSError, PermissionError):
        return None
    lines = text.splitlines()
    frontmatter = {}
    content_lines = []
    in_frontmatter = False
    in_content = False
    for line in lines:
        stripped = line.rstrip("\n").rstrip("\r")
        if stripped == "---" and not in_frontmatter:
            in_frontmatter = True
            continue
        if stripped == "---" and in_frontmatter and not in_content:
            in_content = True
            continue
        if in_frontmatter and not in_content:
            if ":" in stripped:
                key, _, val = stripped.partition(":")
                frontmatter[key.strip()] = val.strip()
        elif in_content:
            content_lines.append(stripped)
    return {
        "frontmatter": frontmatter,
        "content": "\n".join(content_lines).strip(),
    }


def _list_capture_files(directory):
    try:
        files = sorted(
            [f for f in directory.iterdir() if f.is_file() and f.name != "README.md"],
            key=lambda f: f.stat().st_mtime,
        )
    except (FileNotFoundError, PermissionError, OSError):
        return []
    result = []
    for idx, f in enumerate(files, start=1):
        data = _read_capture_file(f)
        result.append({
            "index": idx,
            "file_name": f.name,
            "capture_id": data["frontmatter"].get("capture_id", "") if data else "",
            "status": data["frontmatter"].get("status", "") if data else "",
            "created_at": data["frontmatter"].get("created_at", "") if data else "",
            "preview": data["content"][:200] if data and data["content"] else "",
        })
    return result


def _resolve_by_index(directory, index_str):
    files = _list_capture_files(directory)
    if index_str == "latest":
        if not files:
            return None
        return files[-1]
    try:
        idx = int(index_str)
    except ValueError:
        return None
    for f in files:
        if f["index"] == idx:
            return f
    return None


def _resolve_by_id(directory, capture_id):
    for f in _list_capture_files(directory):
        if f["capture_id"] == capture_id:
            return f
    return None


def _move_capture(file_name, source_dir, target_dir, new_status, processor_type):
    src = source_dir / file_name
    dst = target_dir / file_name
    if not src.exists():
        return None, "capture_not_found"
    try:
        text = src.read_text("utf-8", errors="replace")
    except (OSError, PermissionError):
        return None, "read_error"
    now_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = text.splitlines()
    inside = False
    new_lines = []
    for line in lines:
        stripped = line.rstrip("\n").rstrip("\r")
        if stripped == "---" and not inside:
            inside = True
            new_lines.append(line)
            continue
        if stripped == "---" and inside:
            inside = False
            new_lines.append(line)
            continue
        if inside:
            if stripped.startswith("status:"):
                new_lines.append(f"status: {new_status}")
            elif stripped.startswith("processed_at:"):
                new_lines.append(f"processed_at: {now_ts}")
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)
    new_text = "\n".join(new_lines)
    try:
        dst.write_text(new_text, "utf-8")
        src.unlink()
    except (OSError, PermissionError):
        return None, "write_error"
    event_type = f"telegram.capture_{new_status}"
    details = {
        "capture_id": "",
        "file_name": file_name,
        "source": "telegram_operator",
        "previous_status": "pending_review",
        "new_status": new_status,
    }
    for line in text.splitlines():
        if line.startswith("capture_id:"):
            details["capture_id"] = line.split(":", 1)[1].strip()
            break
    event_id = _append_event(event_type, details)
    if event_id is None:
        return None, "event_append_failed"
    return {"capture_id": details["capture_id"], "file_name": file_name, "event_id": event_id}, None


def _write_capture_file(capture_id, text, source="telegram_operator"):
    now_ts = datetime.now(timezone.utc)
    file_name = f"{now_ts.strftime('%Y%m%d_%H%M%S')}_{_slugify(text)}.md"
    file_path = PENDING_DIR / file_name
    content = f"""---
capture_id: {capture_id}
source: {source}
capture_type: note
status: pending_review
approval_required: true
created_at: {now_ts.isoformat()}
processed_at:
target_domain:
target_project:
event_id:
---

# Capture Summary

## Raw Message

```
{text}
```

## Parsed Intent

Quick note capture.

## Suggested Routing

Pending human review.

## Approval Decision

Pending.

## Processing Notes

Captured by {SERVICE_NAME}.
"""
    try:
        file_path.write_text(content, "utf-8")
    except (OSError, PermissionError):
        return None
    return file_name


class ActionHandler(BaseHTTPRequestHandler):

    def _send_json(self, data, status=200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return None
        try:
            raw = self.rfile.read(length)
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def _check_path_security(path_str):
        if not path_str or not isinstance(path_str, str):
            return False
        return bool(_VALID_CAPTURE_ID_RE.match(path_str))

    # --- GET handlers ---

    def _handle_health(self):
        self._send_json({
            "service": SERVICE_NAME,
            "status": "ok",
            "mode": MODE,
        })

    def _handle_captures_pending(self):
        files = _list_capture_files(PENDING_DIR)
        self._send_json({"success": True, "pending": files, "count": len(files)})

    def _handle_captures_pending_index(self, index_str):
        result = _resolve_by_index(PENDING_DIR, index_str)
        if result is None:
            self._send_json({"success": False, "error": "capture_not_found"}, 404)
            return
        file_path = PENDING_DIR / result["file_name"]
        data = _read_capture_file(file_path)
        if data is None:
            self._send_json({"success": False, "error": "read_error"}, 500)
            return
        self._send_json({
            "success": True,
            "capture": {
                **result,
                "frontmatter": data["frontmatter"],
                "content": data["content"],
            },
        })

    def _handle_captures_id(self, capture_id):
        result = _resolve_by_id(PENDING_DIR, capture_id)
        if result is None:
            self._send_json({"success": False, "error": "capture_not_found"}, 404)
            return
        file_path = PENDING_DIR / result["file_name"]
        data = _read_capture_file(file_path)
        if data is None:
            self._send_json({"success": False, "error": "read_error"}, 500)
            return
        self._send_json({
            "success": True,
            "capture": {
                **result,
                "frontmatter": data["frontmatter"],
                "content": data["content"],
            },
        })

    def _handle_captures_approved(self):
        files = _list_capture_files(APPROVED_DIR)
        self._send_json({"success": True, "approved": files, "count": len(files)})

    # --- POST handlers ---

    def _handle_captures_create(self):
        body = self._read_body()
        if body is None or not body.get("text") or not body["text"].strip():
            self._send_json({"success": False, "error": "text_required"}, 400)
            return
        text = body["text"].strip()
        capture_id = _make_capture_id(text)
        file_name = _write_capture_file(capture_id, text)
        if file_name is None:
            self._send_json({"success": False, "error": "write_error"}, 500)
            return
        event_id = _append_event("telegram.capture_created", {
            "capture_id": capture_id,
            "text_preview": text[:100],
            "file_name": file_name,
            "source": "telegram_operator",
        })
        if event_id is None:
            self._send_json({"success": False, "error": "event_append_failed"}, 500)
            return
        self._send_json({
            "success": True,
            "capture_id": capture_id,
            "file_name": file_name,
            "relative_path": f"30_Capture/pending_review/{file_name}",
            "event_id": event_id,
        }, 201)

    def _handle_captures_approve(self, capture_id):
        if not self._check_path_security(capture_id):
            self._send_json({"success": False, "error": "invalid_capture_id"}, 400)
            return
        result = _resolve_by_id(PENDING_DIR, capture_id)
        if result is None:
            self._send_json({"success": False, "error": "capture_not_found"}, 404)
            return
        data, err = _move_capture(result["file_name"], PENDING_DIR, APPROVED_DIR, "approved", SERVICE_NAME)
        if err:
            self._send_json({"success": False, "error": err}, 500)
            return
        self._send_json({"success": True, **data})

    def _handle_captures_reject(self, capture_id):
        if not self._check_path_security(capture_id):
            self._send_json({"success": False, "error": "invalid_capture_id"}, 400)
            return
        result = _resolve_by_id(PENDING_DIR, capture_id)
        if result is None:
            self._send_json({"success": False, "error": "capture_not_found"}, 404)
            return
        data, err = _move_capture(result["file_name"], PENDING_DIR, REJECTED_DIR, "rejected", SERVICE_NAME)
        if err:
            self._send_json({"success": False, "error": err}, 500)
            return
        self._send_json({"success": True, **data})

    def _handle_captures(self):
        self._send_json({
            "success": True,
            "message": "Action API is running. Valid endpoints: GET /captures/pending, GET /captures/pending/<index>, GET /captures/<id>, GET /captures/approved, POST /captures, POST /captures/<id>/approve, POST /captures/<id>/reject",
        })

    # --- Routing ---

    def do_GET(self):
        path = self.path.rstrip("/")
        if path == "/health":
            self._handle_health()
        elif path == "/captures/pending":
            self._handle_captures_pending()
        elif path == "/captures/approved":
            self._handle_captures_approved()
        elif path.startswith("/captures/pending/"):
            index_str = path[len("/captures/pending/"):]
            self._handle_captures_pending_index(index_str)
        elif path.startswith("/captures/") and len(path) > len("/captures/"):
            capture_id = path[len("/captures/"):]
            if "/" in capture_id or "approve" in capture_id or "reject" in capture_id:
                self._send_json({"error": "not_found"}, 404)
                return
            self._handle_captures_id(capture_id)
        elif path == "/captures":
            self._handle_captures()
        else:
            self._send_json({"error": "not_found"}, 404)

    def do_POST(self):
        path = self.path.rstrip("/")
        if path == "/captures":
            self._handle_captures_create()
        elif path.endswith("/approve"):
            base = path[: -len("/approve")]
            if base.startswith("/captures/"):
                capture_id = base[len("/captures/"):]
                self._handle_captures_approve(capture_id)
            else:
                self._send_json({"error": "not_found"}, 404)
        elif path.endswith("/reject"):
            base = path[: -len("/reject")]
            if base.startswith("/captures/"):
                capture_id = base[len("/captures/"):]
                self._handle_captures_reject(capture_id)
            else:
                self._send_json({"error": "not_found"}, 404)
        else:
            self._send_json({"error": "not_found"}, 404)

    def do_PUT(self):
        self._send_json({"error": "method_not_allowed"}, 405)

    def do_DELETE(self):
        self._send_json({"error": "method_not_allowed"}, 405)

    def log_message(self, format, *args):
        pass


def run(host="0.0.0.0", port=8788):
    _ensure_dirs()
    server = HTTPServer((host, port), ActionHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    run()
