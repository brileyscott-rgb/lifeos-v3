#!/usr/bin/env python3
"""Read-only LifeOS observability report script.

Usage:
  python3 lifeos_observability.py          # text output (default)
  python3 lifeos_observability.py --text   # text output
  python3 lifeos_observability.py --json   # JSON output

Reports:
  - Status API health at http://localhost:8787/health
  - Status API status at http://localhost:8787/status
  - Action API health at http://localhost:8788/health
  - Docker availability
  - Running container names/status/ports
  - Telegram systemd user service active/enabled status
  - Git dirty count
  - Disk usage for /home/lifeos
  - Event log validity (from Status API)
  - Pending capture count (from Status API)
  - Warnings list

Writes: nothing. Read-only by design.
No secrets printed. No mutation.
Uses Python stdlib only (urllib, subprocess, pathlib, json).
"""

import json
import subprocess
import sys
import urllib.request
import urllib.error
from pathlib import Path

LIFEOS_ROOT = Path("/home/lifeos")
STATUS_API_URL = "http://localhost:8787"
ACTION_API_URL = "http://localhost:8788"
TELEGRAM_SERVICE = "lifeos-telegram-bot.service"

DISK_USAGE_WARN = 90       # warn when disk usage >= 90%
PENDING_CAPTURE_WARN = 10  # warn when pending captures >= 10


def _run(cmd, timeout=15):
    """Run a command and return stdout, stderr, returncode. Never raises."""
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except FileNotFoundError:
        return "", "command not found", 127
    except subprocess.TimeoutExpired:
        return "", "timed out", 124
    except (OSError, subprocess.SubprocessError) as e:
        return "", str(e), 1


def _fetch_json(url, timeout=5):
    """Fetch JSON from a URL. Returns (data | None, error | None)."""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read()), None
    except urllib.error.URLError as e:
        return None, str(e.reason) if e.reason else str(e)
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code}"
    except (json.JSONDecodeError, OSError, ValueError) as e:
        return None, str(e)


def check_status_api_health():
    """Check Status API /health endpoint."""
    data, err = _fetch_json(f"{STATUS_API_URL}/health")
    if err:
        return {"reachable": False, "error": err, "status": None, "mode": None}
    return {
        "reachable": True,
        "error": None,
        "status": data.get("status"),
        "mode": data.get("mode"),
    }


def check_status_api_status():
    """Check Status API /status endpoint."""
    data, err = _fetch_json(f"{STATUS_API_URL}/status")
    if err:
        return {"reachable": False, "error": err}
    return {
        "reachable": True,
        "error": None,
        "pending_captures": data.get("pending_captures", 0),
        "approved_captures": data.get("approved_unprocessed_captures", 0),
        "rejected_captures": data.get("rejected_captures", 0),
        "processed_captures": data.get("processed_captures", 0),
        "event_log_valid": data.get("event_log_valid"),
        "event_log_line_count": data.get("event_log_line_count", 0),
        "last_event_id": data.get("last_event_id"),
        "last_event_type": data.get("last_event_type"),
        "last_event_time": data.get("last_event_time"),
    }


def check_action_api_health():
    """Check Action API /health endpoint."""
    data, err = _fetch_json(f"{ACTION_API_URL}/health")
    if err:
        return {"reachable": False, "error": err, "status": None, "mode": None}
    return {
        "reachable": True,
        "error": None,
        "status": data.get("status"),
        "mode": data.get("mode"),
    }


def get_docker_info():
    """Check Docker availability and list running containers."""
    _, _, rc = _run(["docker", "ps"], timeout=10)
    docker_available = rc == 0

    containers = []
    if docker_available:
        stdout, _, rc = _run([
            "docker", "ps", "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}",
        ], timeout=10)
        if rc == 0:
            for line in stdout.splitlines():
                parts = line.split("\t")
                if len(parts) >= 2:
                    containers.append({
                        "name": parts[0],
                        "status": parts[1],
                        "ports": parts[2] if len(parts) > 2 else "",
                    })

    return {
        "docker_available": docker_available,
        "running_containers": containers,
        "container_count": len(containers),
    }


def get_telegram_status():
    """Check systemd user service status for Telegram bot."""
    stdout, _, rc = _run(
        ["systemctl", "--user", "status", TELEGRAM_SERVICE, "--no-pager"],
        timeout=10,
    )
    active = "active" in stdout.lower() and rc == 0

    enabled_stdout, _, _ = _run(
        ["systemctl", "--user", "is-enabled", TELEGRAM_SERVICE],
        timeout=10,
    )
    enabled = "enabled" in enabled_stdout.lower()

    return {"active": active, "enabled": enabled, "service_name": TELEGRAM_SERVICE}


def get_disk_usage():
    """Get disk usage for /home/lifeos."""
    stdout, _, rc = _run(["df", "-h", str(LIFEOS_ROOT)], timeout=10)
    if rc != 0:
        return {"available": False, "used_percent": -1, "free": "unknown"}

    lines = stdout.splitlines()
    if len(lines) < 2:
        return {"available": False, "used_percent": -1, "free": "unknown"}

    parts = lines[1].split()
    if len(parts) < 5:
        return {"available": False, "used_percent": -1, "free": "unknown"}

    used_str = parts[4].rstrip("%")
    try:
        used_pct = int(used_str)
    except ValueError:
        used_pct = -1

    return {"available": True, "used_percent": used_pct, "free": parts[3]}


def get_git_dirty():
    """Check git dirty count."""
    stdout, _, rc = _run(["git", "status", "--short"], timeout=15)
    if rc != 0:
        return -1
    lines = [l for l in stdout.splitlines() if l.strip()]
    return len(lines)


def build_warnings(status_health, status_data, action_health, docker,
                   telegram, disk, git_dirty):
    """Build a list of warning strings based on observability state."""
    warnings = []

    if not status_health.get("reachable"):
        warnings.append("status_api_unreachable")
    elif status_health.get("status") != "ok":
        warnings.append("status_api_unhealthy")

    if not action_health.get("reachable"):
        warnings.append("action_api_unreachable")
    elif action_health.get("status") != "ok":
        warnings.append("action_api_unhealthy")

    if not telegram.get("active"):
        warnings.append("telegram_inactive")

    if not docker.get("docker_available"):
        warnings.append("docker_unavailable")

    n8n_running_legacy = any(
        "n8n" in c.get("name", "").lower()
        for c in docker.get("running_containers", [])
    )
    if n8n_running_legacy:
        warnings.append("n8n_running_legacy_compose_observed")

    chromadb_observed = any(
        "chromadb" in c.get("name", "").lower()
        for c in docker.get("running_containers", [])
    )
    if chromadb_observed:
        warnings.append("chromadb_provenance_unknown_observed")

    if git_dirty > 0:
        warnings.append("git_dirty")

    if disk.get("available") and disk.get("used_percent", -1) >= DISK_USAGE_WARN:
        warnings.append("disk_usage_high")

    if status_data.get("reachable"):
        if status_data.get("event_log_valid") is False:
            warnings.append("event_log_invalid")
        pending = status_data.get("pending_captures", 0)
        if isinstance(pending, int) and pending >= PENDING_CAPTURE_WARN:
            warnings.append("pending_capture_count_high")

    return warnings


def build_report():
    """Build the complete observability report."""
    status_health = check_status_api_health()
    status_data = check_status_api_status()
    action_health = check_action_api_health()
    docker = get_docker_info()
    telegram = get_telegram_status()
    disk = get_disk_usage()
    git_dirty = get_git_dirty()

    warnings = build_warnings(
        status_health, status_data, action_health, docker,
        telegram, disk, git_dirty,
    )

    return {
        "status_api": status_health,
        "status_api_data": status_data,
        "action_api": action_health,
        "docker": docker,
        "telegram": telegram,
        "disk": disk,
        "git_dirty_count": git_dirty,
        "warnings": warnings,
        "warnings_count": len(warnings),
    }


def print_text(report):
    """Print observability report as human-readable text."""
    print("LifeOS Observability Report")
    print("===========================\n")

    print("Status API:")
    sh = report["status_api"]
    if sh["reachable"]:
        print(f"  Reachable:   yes")
        print(f"  Status:      {sh['status']}")
        print(f"  Mode:        {sh['mode']}")
    else:
        print(f"  Reachable:   NO — {sh['error']}")
    print()

    print("Status API Data:")
    sd = report["status_api_data"]
    if sd["reachable"]:
        print(f"  Pending:     {sd['pending_captures']}")
        print(f"  Approved:    {sd['approved_captures']}")
        print(f"  Rejected:    {sd['rejected_captures']}")
        print(f"  Processed:   {sd['processed_captures']}")
        print(f"  Event log:   {'valid' if sd['event_log_valid'] else 'INVALID'} ({sd['event_log_line_count']} lines)")
        if sd.get("last_event_id"):
            print(f"  Last event:  {sd['last_event_type']} at {sd['last_event_time']}")
    else:
        print(f"  Reachable:   NO — {sd['error']}")
    print()

    print("Action API:")
    ah = report["action_api"]
    if ah["reachable"]:
        print(f"  Reachable:   yes")
        print(f"  Status:      {ah['status']}")
        print(f"  Mode:        {ah['mode']}")
    else:
        print(f"  Reachable:   NO — {ah['error']}")
    print()

    print("Docker:")
    d = report["docker"]
    print(f"  Available:   {d['docker_available']}")
    print(f"  Containers:  {d['container_count']} running")
    for c in d["running_containers"]:
        print(f"    - {c['name']}: {c['status']} ({c['ports']})")
    print()

    print("Telegram Bot:")
    t = report["telegram"]
    print(f"  Active:      {t['active']}")
    print(f"  Enabled:     {t['enabled']}")
    print()

    print("Disk:")
    dk = report["disk"]
    if dk["available"]:
        print(f"  Used:        {dk['used_percent']}%")
        print(f"  Free:        {dk['free']}")
    else:
        print("  Unavailable")
    print()

    print(f"Git Dirty:       {report['git_dirty_count']} files")
    print()

    print("Warnings:")
    if report["warnings"]:
        for w in report["warnings"]:
            print(f"  - {w}")
    else:
        print("  (none)")
    print()


def print_json(report):
    """Print observability report as JSON."""
    print(json.dumps(report, indent=2, default=str))


def main():
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

    report = build_report()

    if mode == "json":
        print_json(report)
    else:
        print_text(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
