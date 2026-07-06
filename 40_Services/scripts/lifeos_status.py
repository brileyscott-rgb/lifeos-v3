#!/usr/bin/env python3
"""Read-only LifeOS system status reporter.

Usage:
  python3 lifeos_status.py          # text output (default)
  python3 lifeos_status.py --text   # text output
  python3 lifeos_status.py --json   # JSON output (for n8n consumption)

Reads:
  - 30_Capture/ directory counts (pending_review, approved, rejected, processed)
  - 50_Event_Log/events.jsonl (last event summary)
  - git status --short (dirty/clean)
  - df -h / (disk usage)
  - docker ps (n8n container check)
  - filesystem scaffold presence checks

Writes: nothing. Read-only.
"""

import json
import subprocess
import sys
from pathlib import Path

LIFEOS_ROOT = Path("/home/lifeos")

CAPTURE_DIR = LIFEOS_ROOT / "30_Capture"
EVENT_LOG = LIFEOS_ROOT / "50_Event_Log" / "events.jsonl"
SCRIPTS_DIR = LIFEOS_ROOT / "40_Services" / "scripts"
N8N_DIR = LIFEOS_ROOT / "40_Services" / "n8n"
AI_WORKER_DIR = LIFEOS_ROOT / "40_Services" / "ai_worker"
TELEGRAM_DIR = LIFEOS_ROOT / "40_Services" / "chatops" / "telegram"


def count_files(directory: Path) -> int:
    """Count files in a directory, excluding README.md."""
    if not directory.is_dir():
        return 0
    return sum(1 for p in directory.iterdir() if p.is_file() and p.name != "README.md")


def read_last_event(event_log: Path) -> dict | None:
    """Read the last valid JSON line from the event log."""
    if not event_log.is_file():
        return None
    try:
        text = event_log.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    last_valid = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            last_valid = json.loads(stripped)
        except json.JSONDecodeError:
            return None
    return last_valid


def get_git_status(root: Path) -> tuple[bool, int]:
    """Check git dirty status using git status --short."""
    try:
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True, text=True, check=False,
            cwd=str(root), timeout=15,
        )
        lines = [l for l in result.stdout.splitlines() if l.strip()]
        dirty = len(lines) > 0
        return dirty, len(lines)
    except (subprocess.SubprocessError, OSError):
        return False, 0


def get_disk_status(root: Path) -> dict:
    """Get disk usage for the root filesystem."""
    try:
        result = subprocess.run(
            ["df", "-h", str(root)],
            capture_output=True, text=True, check=False, timeout=10,
        )
        lines = result.stdout.splitlines()
        if len(lines) < 2:
            return {"free": "unknown", "used_percent": "unknown%"}
        parts = lines[1].split()
        if len(parts) >= 5:
            return {"free": parts[3], "used_percent": parts[4]}
        return {"free": "unknown", "used_percent": "unknown%"}
    except (subprocess.SubprocessError, OSError):
        return {"free": "unknown", "used_percent": "unknown%"}


def check_n8n_container_running() -> tuple[bool, str | None]:
    """Check if the n8n Docker container is running."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True, check=False, timeout=10,
        )
        names = [n.strip() for n in result.stdout.splitlines() if n.strip()]
        for name in names:
            if "n8n" in name.lower():
                return True, None
        return False, None
    except (subprocess.SubprocessError, OSError) as e:
        return False, f"docker unavailable or permission denied: {e}"


def check_path(path: Path) -> bool:
    """Check if a path exists."""
    return path.exists()


def build_status() -> dict:
    """Build the complete status dictionary."""
    pending = count_files(CAPTURE_DIR / "pending_review")
    approved = count_files(CAPTURE_DIR / "approved")
    rejected = count_files(CAPTURE_DIR / "rejected")
    processed = count_files(CAPTURE_DIR / "processed")

    last_event = read_last_event(EVENT_LOG)
    event_log_valid = True
    event_log_line_count = 0

    if EVENT_LOG.is_file():
        try:
            text = EVENT_LOG.read_text(encoding="utf-8")
            event_log_line_count = len([l for l in text.splitlines() if l.strip()])
            if last_event is None and event_log_line_count > 0:
                event_log_valid = False
        except (OSError, UnicodeDecodeError):
            event_log_valid = False
    else:
        event_log_valid = False

    git_dirty, git_dirty_count = get_git_status(LIFEOS_ROOT)

    disk = get_disk_status(LIFEOS_ROOT)

    n8n_running, n8n_error = check_n8n_container_running()

    status = {
        "pending_captures": pending,
        "approved_unprocessed_captures": approved,
        "rejected_captures": rejected,
        "processed_captures": processed,
        "last_event_id": last_event.get("event_id") if last_event else None,
        "last_event_type": last_event.get("event_type") if last_event else None,
        "last_event_time": last_event.get("occurred_at") if last_event else None,
        "event_log_valid": event_log_valid,
        "event_log_line_count": event_log_line_count,
        "git_dirty": git_dirty,
        "git_dirty_count": git_dirty_count,
        "disk_free_root": disk["free"],
        "disk_used_percent_root": disk["used_percent"],
        "n8n_scaffold_present": check_path(N8N_DIR),
        "n8n_container_running": n8n_running,
        "n8n_status_error": n8n_error,
        "ai_worker_scaffold_present": check_path(AI_WORKER_DIR),
        "telegram_bot_present": check_path(TELEGRAM_DIR / "telegram_capture_bot.py"),
    }
    return status


def print_text(status: dict) -> None:
    """Print status as human-readable text."""
    print("LifeOS Status")
    print("=============\n")

    print("Capture Queue:")
    print(f"  Pending:                {status['pending_captures']}")
    print(f"  Approved (unprocessed): {status['approved_unprocessed_captures']}")
    print(f"  Rejected:               {status['rejected_captures']}")
    print(f"  Processed:              {status['processed_captures']}")
    print()

    print("Event Log:")
    print(f"  Valid:                  {status['event_log_valid']}")
    print(f"  Lines:                  {status['event_log_line_count']}")
    if status["last_event_id"]:
        print(f"  Last event ID:          {status['last_event_id']}")
        print(f"  Last event type:        {status['last_event_type']}")
        print(f"  Last event time:        {status['last_event_time']}")
    else:
        print("  Last event:             none")
    print()

    print("Git:")
    print(f"  Dirty:                  {status['git_dirty']}")
    print(f"  Dirty count:            {status['git_dirty_count']}")
    print()

    print("Disk:")
    print(f"  Free:                   {status['disk_free_root']}")
    print(f"  Used:                   {status['disk_used_percent_root']}")
    print()

    print("Services:")
    print(f"  n8n scaffold:           {status['n8n_scaffold_present']}")
    print(f"  n8n container running:  {status['n8n_container_running']}")
    if status["n8n_status_error"]:
        print(f"  n8n status error:       {status['n8n_status_error']}")
    print(f"  AI worker scaffold:     {status['ai_worker_scaffold_present']}")
    print(f"  Telegram bot:           {status['telegram_bot_present']}")


def print_json(status: dict) -> None:
    """Print status as JSON (n8n-friendly)."""
    print(json.dumps(status, indent=2, default=str))


def main() -> int:
    """Entry point."""
    mode = "text"
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--json":
            mode = "json"
        elif arg == "--text":
            mode = "text"
        elif arg in ("-h", "--help"):
            print(__doc__)
            return 0
        else:
            print(f"Unknown option: {arg}", file=sys.stderr)
            print(f"Usage: {sys.argv[0]} [--text|--json]", file=sys.stderr)
            return 1

    status = build_status()

    if mode == "json":
        print_json(status)
    else:
        print_text(status)

    return 0


if __name__ == "__main__":
    sys.exit(main())
