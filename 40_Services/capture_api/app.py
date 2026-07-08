#!/usr/bin/env python3
import fcntl
import hashlib
import hmac
import json
import os
import sys
import time
import uuid
from http.server import HTTPServer, BaseHTTPRequestHandler

HOST = os.environ.get("LIFEOS_CAPTURE_HOST", "127.0.0.1")
PORT = int(os.environ.get("LIFEOS_CAPTURE_PORT", "8789"))


def _get_queue_path():
    return os.environ.get(
        "LIFEOS_CAPTURE_QUEUE_PATH",
        os.path.expanduser("/home/lifeos/LifeOS_Capture_Buffer/00_Raw/captures.jsonl"),
    )


def _get_bearer_token():
    return os.environ.get("LIFEOS_CAPTURE_BEARER_TOKEN", "")


def _get_require_auth():
    return os.environ.get("LIFEOS_CAPTURE_REQUIRE_AUTH", "true").lower() == "true"


def _get_max_bytes():
    return int(os.environ.get("LIFEOS_CAPTURE_MAX_BYTES", "65536"))


def _get_max_content_chars():
    return int(os.environ.get("LIFEOS_CAPTURE_MAX_CONTENT_CHARS", "20000"))

VALID_SOURCES = {
    "telegram", "http_shortcuts", "bookmarklet", "desktop",
    "n8n", "mcp", "manual", "unknown",
}

VALID_CAPTURE_TYPES = {
    "text", "url", "article", "video", "audio", "image",
    "file", "github_repo", "pdf", "unknown",
}

SCHEMA_VERSION = 1


def _ensure_queue_dir():
    queue_path = _get_queue_path()
    d = os.path.dirname(os.path.abspath(queue_path))
    os.makedirs(d, exist_ok=True)


def _make_capture_id():
    ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
    rand = uuid.uuid4().hex[:8]
    return f"cap_{ts}_{rand}"


def _make_event_id(event_type):
    ts = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    rand = uuid.uuid4().hex[:6]
    return f"evt_{ts}_{event_type}_{rand}"


def _hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _append_queue(record):
    line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
    queue_path = _get_queue_path()
    with open(queue_path, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _append_event(event):
    try:
        event_log_path = os.path.expanduser("/home/lifeos/50_Event_Log/events.jsonl")
        line = json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n"
        with open(event_log_path, "a") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.write(line)
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except OSError:
        pass


def _infer_capture_type(data):
    if data.get("capture_type") in VALID_CAPTURE_TYPES:
        return data["capture_type"]
    if data.get("url") and not data.get("content") and not data.get("text"):
        return "url"
    return "text"


def _normalize_tags(data):
    tags = data.get("tags", [])
    if isinstance(tags, str):
        tags = [tags]
    if not isinstance(tags, list):
        return []
    return [str(t) for t in tags]


def _validate(data):
    max_content = _get_max_content_chars()
    errors = []
    content = (data.get("content") or "").strip()
    text = (data.get("text") or "").strip()
    url = (data.get("url") or "").strip()
    if not content and not text and not url:
        errors.append("At least one of content, text, or url is required")
    if content and len(content) > max_content:
        errors.append(f"Content exceeds maximum length of {max_content} characters")
    if text and len(text) > max_content:
        errors.append(f"Text exceeds maximum length of {max_content} characters")
    source = data.get("source", "unknown")
    if source not in VALID_SOURCES:
        errors.append(f"Invalid source: {source}")
    return errors


class CaptureHandler(BaseHTTPRequestHandler):

    def _read_body(self):
        max_bytes = _get_max_bytes()
        length = int(self.headers.get("Content-Length", 0))
        if length > max_bytes:
            self._error(413, "payload_too_large", f"Payload exceeds {max_bytes} byte limit")
            return None
        raw = self.rfile.read(length)
        try:
            return json.loads(raw.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._error(400, "invalid_json", "Body is not valid JSON")
            return None

    def _check_auth(self):
        if not _get_require_auth():
            return True, "none"
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:]
            if _get_bearer_token() and hmac.compare_digest(token, _get_bearer_token()):
                return True, "bearer"
        self._error(401, "unauthorized", "Missing or invalid authentication")
        return False, None

    def _error(self, code, error_type, message, detail=None):
        body = {"success": False, "error": error_type, "detail": message}
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode("utf-8"))

    def _json(self, code, body):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(body).encode("utf-8"))

    def _handle_health(self):
        self._json(200, {
            "status": "ok",
            "service": "lifeos_capture_api",
            "mode": "queue_only",
        })

    def _handle_capture(self):
        authed, auth_method = self._check_auth()
        if not authed:
            return
        data = self._read_body()
        if data is None:
            return
        errors = _validate(data)
        if errors:
            self._error(400, "validation_error", "; ".join(errors))
            return
        content = (data.get("content") or data.get("text") or "").strip()
        url = (data.get("url") or "").strip()
        capture_type = _infer_capture_type(data)
        capture_id = _make_capture_id()
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        record = {
            "capture_id": capture_id,
            "received_at": now,
            "source": data.get("source", "unknown"),
            "capture_type": capture_type,
            "content": content,
            "url": url,
            "title": (data.get("title") or "").strip(),
            "tags": _normalize_tags(data),
            "priority": data.get("priority", "normal"),
            "client": (data.get("client") or "").strip(),
            "metadata": data.get("metadata") or {},
            "status": "queued",
            "raw_payload": data if data.get("raw_payload") else {},
            "auth_method": auth_method,
            "schema_version": SCHEMA_VERSION,
        }
        _ensure_queue_dir()
        _append_queue(record)
        event = {
            "event_id": _make_event_id("capture_api_received"),
            "event_type": "capture_api.received",
            "timestamp": now,
            "capture_id": capture_id,
            "source": data.get("source", "unknown"),
            "capture_type": capture_type,
            "content_length": len(content),
            "has_url": bool(url),
        }
        _append_event(event)
        self._json(200, {"success": True, "capture_id": capture_id,
                         "status": "queued", "source": data.get("source", "unknown")})

    def do_GET(self):
        if self.path == "/health":
            self._handle_health()
        elif self.path == "/captures":
            self._json(405, {"success": False, "error": "method_not_allowed",
                             "detail": "Method not allowed"})
        else:
            self._json(404, {"success": False, "error": "not_found",
                             "detail": "Not found"})

    def do_POST(self):
        if self.path == "/captures":
            self._handle_capture()
        else:
            self._json(405 if self.path == "/captures" else 404,
                       {"success": False, "error": "method_not_allowed",
                        "detail": "Method not allowed"})

    def do_HEAD(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


class CaptureServer(HTTPServer):
    allow_reuse_address = True


def main():
    _ensure_queue_dir()
    server = CaptureServer((HOST, PORT), CaptureHandler)
    print(f"Capture API listening on {HOST}:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
