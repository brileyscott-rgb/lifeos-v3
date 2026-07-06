"""LifeOS Status API — read-only health and status endpoint."""

import json
import os
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

CAPTURE_BASE = Path("/lifeos/capture")
EVENT_LOG = Path("/lifeos/event-log/events.jsonl")

SERVICE_NAME = "lifeos-status-api"
MODE = "read_only"

LIMITATIONS = {
    "git_status": "unavailable_without_repo_mount",
    "docker_status": "unavailable_without_docker_socket",
    "disk_status": "unavailable_in_status_api_v1",
}


def _count_files(directory):
    """Count non-README files in a directory."""
    try:
        return sum(1 for f in directory.iterdir() if f.name != "README.md")
    except (FileNotFoundError, PermissionError, OSError):
        return -1


def _check_path_readable(path):
    """Check if a path exists and is readable."""
    return path.exists()


def _parse_event_log():
    """Parse events.jsonl and return validity and last-event fields."""
    if not EVENT_LOG.exists():
        return False, 0, None, None, None

    try:
        lines = EVENT_LOG.read_text("utf-8").strip().splitlines()
    except (OSError, PermissionError):
        return False, 0, None, None, None

    line_count = len(lines)
    if line_count == 0:
        return True, 0, None, None, None

    last_event = None
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            last_event = json.loads(stripped)
            break
        except json.JSONDecodeError:
            return False, line_count, None, None, None

    if last_event is None:
        return True, line_count, None, None, None

    return (
        True,
        line_count,
        last_event.get("event_id"),
        last_event.get("event_type"),
        last_event.get("occurred_at"),
    )


class StatusHandler(BaseHTTPRequestHandler):
    """HTTP request handler for LifeOS Status API."""

    def _send_json(self, data, status=200):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = self.path.rstrip("/")
        if parsed == "/health":
            self._handle_health()
        elif parsed == "/status":
            self._handle_status()
        else:
            self._send_json({"error": "not_found"}, 404)

    def _handle_health(self):
        self._send_json({
            "service": SERVICE_NAME,
            "status": "ok",
            "mode": MODE,
        })

    def _handle_status(self):
        pending = _count_files(CAPTURE_BASE / "pending_review")
        approved = _count_files(CAPTURE_BASE / "approved")
        rejected = _count_files(CAPTURE_BASE / "rejected")
        processed = _count_files(CAPTURE_BASE / "processed")

        event_log_valid, event_log_line_count, last_event_id, last_event_type, last_event_time = _parse_event_log()

        self._send_json({
            "service": SERVICE_NAME,
            "status": "ok",
            "mode": MODE,
            "pending_captures": pending,
            "approved_unprocessed_captures": approved,
            "rejected_captures": rejected,
            "processed_captures": processed,
            "event_log_valid": event_log_valid,
            "event_log_line_count": event_log_line_count,
            "last_event_id": last_event_id,
            "last_event_type": last_event_type,
            "last_event_time": last_event_time,
            "paths": {
                "capture_readable": _check_path_readable(CAPTURE_BASE / "pending_review"),
                "event_log_readable": _check_path_readable(EVENT_LOG),
            },
            "limitations": LIMITATIONS,
        })

    def log_message(self, format, *args):
        """Suppress default stderr logging."""
        pass


def run(host="0.0.0.0", port=8787):
    server = HTTPServer((host, port), StatusHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()


if __name__ == "__main__":
    run()
