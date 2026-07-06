# AI Worker Scaffold

Dry-run AI implementer worker scaffold for LifeOS V3.

**Status: scaffold only — no real model calls, file edits, or git operations.**

## Quick Start

```bash
# Show help
python3 ai_worker.py --help

# Show status
python3 ai_worker.py --status

# Create a dry-run job
python3 ai_worker.py --create-job "test implementation request"

# List pending jobs
python3 ai_worker.py --list-jobs
```

## Directory Structure

```text
40_Services/ai_worker/
├── README.md
├── ai_worker.py              # Dry-run CLI scaffold
├── job_queue.sqlite.example.md  # Future SQLite schema documentation
├── job_schema.md              # Job file format specification
├── prompts/                   # Future prompt templates
│   ├── implementer_system.md
│   ├── planner.md
│   ├── reviewer.md
│   └── opencode_handoff.md
├── jobs/                      # Job file storage
│   ├── pending/
│   ├── approved/
│   ├── running/
│   ├── completed/
│   ├── rejected/
│   └── README.md
├── logs/
│   └── README.md
└── tests/
    └── test_ai_worker_dry_run.py
```

## Safety Rules

- No real model API calls.
- No file editing.
- No OpenCode execution.
- No git operations.
- No direct vault writes.
- Dry-run only.

## Prompt Templates

Prompt templates in `prompts/` define future worker behavior:

- **implementer_system.md** — system prompt for the implementation worker
- **planner.md** — converts goals to plans
- **reviewer.md** — reviews proposed implementations
- **opencode_handoff.md** — converts approved jobs to OpenCode prompts

Templates contain no real secrets.
