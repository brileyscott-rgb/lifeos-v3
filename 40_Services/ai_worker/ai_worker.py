#!/usr/bin/env python3
"""
LifeOS AI Worker — Dry-run scaffold.

Creates and lists dry-run job files for the LifeOS AI implementer pipeline.
No real model API calls, file edits, git operations, or OpenCode execution.

Usage:
    python3 ai_worker.py --help
    python3 ai_worker.py --status
    python3 ai_worker.py --create-job "goal description"
    python3 ai_worker.py --list-jobs
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
JOBS_DIR = BASE_DIR / "jobs"
PENDING_DIR = JOBS_DIR / "pending"
LOG_DIR = BASE_DIR / "logs"


def log(message: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = f"[{timestamp}] {message}\n"
    sys.stdout.write(entry)


def ensure_dirs() -> None:
    for d in [JOBS_DIR, PENDING_DIR, LOG_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    for sub in ["approved", "running", "completed", "rejected"]:
        (JOBS_DIR / sub).mkdir(parents=True, exist_ok=True)


_job_counter: int = 0


def generate_job_id() -> str:
    global _job_counter
    _job_counter += 1
    now = datetime.now(timezone.utc)
    return f"job_{now.strftime('%Y%m%d_%H%M%S')}_{_job_counter:04d}"


def create_job(goal: str) -> str:
    ensure_dirs()
    job_id = generate_job_id()
    created = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    filename = f"{job_id}.md"
    filepath = PENDING_DIR / filename

    content = f"""---
job_id: {job_id}
status: pending
approval_state: not_requested
risk_level: unclassified
created_at: {created}
source: cli
---

# Goal

{goal}

# Proposed Scope

Not classified yet.

# Approval

Not approved.

# Notes

Dry-run scaffold job. No implementation has been executed.
"""
    filepath.write_text(content, encoding="utf-8")
    log(f"Created dry-run job: {job_id}")
    return job_id


def list_jobs() -> list[dict]:
    ensure_dirs()
    jobs = []
    if PENDING_DIR.exists():
        for f in sorted(PENDING_DIR.glob("*.md")):
            frontmatter = {}
            lines = f.read_text(encoding="utf-8").splitlines()
            in_frontmatter = False
            goal = ""
            for line in lines:
                if line.strip() == "---":
                    in_frontmatter = not in_frontmatter
                    continue
                if in_frontmatter and ":" in line:
                    key, _, value = line.partition(":")
                    frontmatter[key.strip()] = value.strip()
                elif not in_frontmatter and line.startswith("# Goal"):
                    pass
                elif not in_frontmatter and goal == "" and line.strip() and not line.startswith("#"):
                    goal = line.strip()
            jobs.append({
                "file": f.name,
                "job_id": frontmatter.get("job_id", "unknown"),
                "status": frontmatter.get("status", "unknown"),
                "approval": frontmatter.get("approval_state", "unknown"),
                "risk": frontmatter.get("risk_level", "unknown"),
                "created": frontmatter.get("created_at", "unknown"),
                "goal": goal if goal else frontmatter.get("goal", "see file"),
            })
    return jobs


def show_status() -> None:
    ensure_dirs()
    pending_count = len(list(PENDING_DIR.glob("*.md"))) if PENDING_DIR.exists() else 0
    approved_count = len(list((JOBS_DIR / "approved").glob("*.md"))) if (JOBS_DIR / "approved").exists() else 0
    running_count = len(list((JOBS_DIR / "running").glob("*.md"))) if (JOBS_DIR / "running").exists() else 0
    completed_count = len(list((JOBS_DIR / "completed").glob("*.md"))) if (JOBS_DIR / "completed").exists() else 0
    rejected_count = len(list((JOBS_DIR / "rejected").glob("*.md"))) if (JOBS_DIR / "rejected").exists() else 0

    print("AI Worker Status")
    print("=================")
    print(f"  State:         dry-run (no real execution)")
    print(f"  Model API:     not configured")
    print(f"  File editing:  disabled")
    print(f"  Git access:    disabled")
    print(f"  Vault access:  disabled")
    print()
    print("Jobs:")
    print(f"  Pending:       {pending_count}")
    print(f"  Approved:      {approved_count}")
    print(f"  Running:       {running_count}")
    print(f"  Completed:     {completed_count}")
    print(f"  Rejected:      {rejected_count}")
    print(f"  Total:         {pending_count + approved_count + running_count + completed_count + rejected_count}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="LifeOS AI Worker — Dry-run scaffold",
        epilog="No real model API calls, file edits, or git operations.",
    )
    parser.add_argument("--status", action="store_true", help="Show worker status")
    parser.add_argument("--create-job", type=str, metavar="GOAL", help="Create a new dry-run job file")
    parser.add_argument("--list-jobs", action="store_true", help="List pending jobs")

    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.create_job:
        job_id = create_job(args.create_job)
        print(f"Job created: {job_id}")
    elif args.list_jobs:
        jobs = list_jobs()
        if not jobs:
            print("No pending jobs.")
        else:
            print(f"{'Job ID':<30} {'Status':<12} {'Approval':<20} {'Risk':<16} {'Goal'}")
            print("-" * 120)
            for j in jobs:
                goal_short = j["goal"][:60] + "..." if len(j["goal"]) > 60 else j["goal"]
                print(f"{j['job_id']:<30} {j['status']:<12} {j['approval']:<20} {j['risk']:<16} {goal_short}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
