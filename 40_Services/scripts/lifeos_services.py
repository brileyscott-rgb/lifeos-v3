#!/usr/bin/env python3
"""Read-only LifeOS service inventory script.

Usage:
  python3 lifeos_services.py          # text output (default)
  python3 lifeos_services.py --text   # text output
  python3 lifeos_services.py --json   # JSON output

Reports:
  - repo root and current git commit
  - git dirty count
  - docker available yes/no
  - running containers
  - dashboard containers (homepage, uptime-kuma, dozzle)
  - Telegram service status
  - known service paths exist/missing
  - n8n compose exists/missing
  - dashboard compose exists/missing
  - mcpo scaffold exists/missing
  - mcp catalog exists/missing
  - openhands scaffold exists/missing
  - Status API path exists/missing
  - Action API path exists/missing
  - suggested next action

Writes: nothing. Read-only by design.
No secrets printed. No mutation. No Docker/shell write commands.
"""

import json
import subprocess
import sys
from pathlib import Path

LIFEOS_ROOT = Path("/home/lifeos")

KNOWN_SERVICE_PATHS = {
    "status_api_source": LIFEOS_ROOT / "40_Services" / "status_api" / "app.py",
    "action_api_source": LIFEOS_ROOT / "40_Services" / "action_api" / "server.py",
    "telegram_bot_source": LIFEOS_ROOT / "40_Services" / "chatops" / "telegram" / "telegram_capture_bot.py",
    "n8n_compose_legacy": LIFEOS_ROOT / "40_Services" / "n8n" / "docker-compose.yml",
    "n8n_compose_unified": LIFEOS_ROOT / "40_Services" / "compose" / "lifeos.yaml",
    "ai_worker_source": LIFEOS_ROOT / "40_Services" / "ai_worker" / "ai_worker.py",
    "dashboard_compose": LIFEOS_ROOT / "40_Services" / "dashboard" / "docker-compose.yml",
    "mcpo_scaffold": LIFEOS_ROOT / "40_Services" / "mcpo" / "README.md",
    "mcp_catalog": LIFEOS_ROOT / "40_Services" / "mcp" / "catalog" / "MCP_Candidate_Catalog.md",
    "mcp_security_policy": LIFEOS_ROOT / "40_Services" / "docs" / "MCP_Security_Policy.md",
    "openhands_scaffold": LIFEOS_ROOT / "40_Services" / "openhands" / "README.md",
    "n8n_roadmap": LIFEOS_ROOT / "40_Services" / "docs" / "N8N_Automation_Roadmap.md",
    "uptime_kuma_monitor_plan": LIFEOS_ROOT / "40_Services" / "docs" / "Uptime_Kuma_Monitor_Plan.md",
    "telegram_config": LIFEOS_ROOT / "40_Services" / "config" / "telegram",
    "secrets_dir": LIFEOS_ROOT / "40_Services" / "secrets",
    "event_log": LIFEOS_ROOT / "50_Event_Log" / "events.jsonl",
    "capture_dir": LIFEOS_ROOT / "30_Capture",
    "vault_dir": LIFEOS_ROOT / "10_Vaults",
}


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


def _run_userctl(cmd, timeout=10):
    """Run systemctl --user command. Never raises."""
    full_cmd = ["systemctl", "--user"] + cmd
    return _run(full_cmd, timeout=timeout)


def _check_path(path):
    """Check if a path exists. Return True/False."""
    try:
        return path.exists()
    except (OSError, PermissionError):
        return False


def get_git_info():
    """Get git repo root and current commit. Never reads secrets."""
    root_stdout, _, rc = _run(["git", "rev-parse", "--show-toplevel"])
    repo_root = root_stdout if rc == 0 else "unknown"

    commit_stdout, _, rc = _run(["git", "rev-parse", "HEAD"])
    commit = commit_stdout[:12] if rc == 0 else "unknown"

    dirty_stdout, _, rc = _run(["git", "status", "--short"])
    dirty_lines = [l for l in dirty_stdout.splitlines() if l.strip()] if rc == 0 else []
    dirty_count = len(dirty_lines)

    return {
        "repo_root": repo_root,
        "commit": commit,
        "dirty_count": dirty_count,
        "dirty": dirty_count > 0,
    }


def get_docker_info():
    """Check if Docker is available and list running containers."""
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

    compose_version = "unknown"
    compose_stdout, _, rc = _run(["docker-compose", "--version"], timeout=10)
    if rc == 0:
        compose_version = compose_stdout

    return {
        "docker_available": docker_available,
        "compose_version": compose_version,
        "running_containers": containers,
        "container_count": len(containers),
    }


def get_telegram_service_status():
    """Check systemd user service status for Telegram bot."""
    stdout, stderr, rc = _run_userctl(
        ["status", "lifeos-telegram-bot.service", "--no-pager"],
        timeout=10,
    )
    active = "active" in stdout.lower() and rc == 0
    enabled_stdout, _, _ = _run_userctl(
        ["is-enabled", "lifeos-telegram-bot.service"],
        timeout=10,
    )
    enabled = "enabled" in enabled_stdout.lower()

    return {
        "active": active,
        "enabled": enabled,
        "service_name": "lifeos-telegram-bot.service",
        "service_type": "systemd_user",
    }


def get_service_paths():
    """Check which known service paths exist."""
    paths = {}
    for name, path in KNOWN_SERVICE_PATHS.items():
        paths[name] = {
            "path": str(path),
            "exists": _check_path(path),
        }
    return paths


def get_suggested_action(service_state):
    """Determine the suggested next action based on current state."""
    issues = []

    docker = service_state.get("docker", {})
    telegram = service_state.get("telegram", {})
    paths = service_state.get("paths", {})

    if not docker.get("docker_available"):
        issues.append("Docker not available — check Docker daemon")
    else:
        n8n_containers = [
            c for c in docker.get("running_containers", [])
            if "n8n" in c.get("name", "").lower()
        ]
        if n8n_containers:
            issues.append("n8n running from legacy compose — adoption deferred")

        chroma = [
            c for c in docker.get("running_containers", [])
            if "chromadb" in c.get("name", "").lower()
        ]
        if chroma:
            issues.append("ChromaDB running without documented ownership")

    if not telegram.get("active"):
        issues.append("Telegram bot not running — check service status")

    if not paths.get("n8n_compose_unified", {}).get("exists"):
        issues.append("Unified compose missing — run baseline setup")

    dashboard_containers = [
        c for c in docker.get("running_containers", [])
        if any(n in c.get("name", "") for n in ("homepage", "uptime-kuma", "dozzle"))
    ]
    if dashboard_containers and paths.get("uptime_kuma_monitor_plan", {}).get("exists"):
        issues.append("Configure Uptime Kuma monitors per monitor plan (3001)")

    if not issues:
        return "All checks passed. Configure Uptime Kuma monitors from monitor plan."
    else:
        return "; ".join(issues)


def build_service_state():
    """Build complete service inventory dictionary."""
    git = get_git_info()
    docker = get_docker_info()
    telegram = get_telegram_service_status()
    paths = get_service_paths()

    state = {
        "git": git,
        "docker": docker,
        "telegram": telegram,
        "paths": paths,
    }
    state["suggested_action"] = get_suggested_action(state)
    return state


def print_text(state):
    """Print service inventory as human-readable text."""
    git = state["git"]
    docker = state["docker"]
    telegram = state["telegram"]
    paths = state["paths"]

    print("LifeOS Service Inventory")
    print("========================\n")

    print("Repository:")
    print(f"  Root:        {git['repo_root']}")
    print(f"  Commit:      {git['commit']}")
    print(f"  Dirty:       {git['dirty']} ({git['dirty_count']} files)")
    print()

    print("Docker:")
    print(f"  Available:   {docker['docker_available']}")
    print(f"  Compose:     {docker['compose_version']}")
    print(f"  Containers:  {docker['container_count']} running")
    if docker["running_containers"]:
        for c in docker["running_containers"]:
            print(f"    - {c['name']}: {c['status']} ({c['ports']})")
    print()

    print("Dashboard Stack:")
    dashboard_containers = [
        c for c in docker.get("running_containers", [])
        if any(n in c.get("name", "") for n in ("homepage", "uptime-kuma", "dozzle"))
    ]
    if dashboard_containers:
        for c in dashboard_containers:
            print(f"  {c['name']}: {c['status']} ({c['ports']})")
        print(f"  Dashboard: {len(dashboard_containers)}/3 services running")
    else:
        print("  Dashboard: not running (use dashboard/docker-compose.yml)")
    print()

    print("Telegram Bot:")
    print(f"  Service:     {telegram['service_name']}")
    print(f"  Active:      {telegram['active']}")
    print(f"  Enabled:     {telegram['enabled']}")
    print()

    print("Known Service Paths:")
    for name, info in sorted(paths.items()):
        status = "present" if info["exists"] else "MISSING"
        print(f"  {name}: {status}")
    print()

    print(f"Suggested Action: {state['suggested_action']}")


def print_json(state):
    """Print service inventory as JSON."""

    class PathEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, Path):
                return str(obj)
            return super().default(obj)

    print(json.dumps(state, indent=2, cls=PathEncoder))


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

    state = build_service_state()

    if mode == "json":
        print_json(state)
    else:
        print_text(state)

    return 0


if __name__ == "__main__":
    sys.exit(main())
