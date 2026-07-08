# LifeOS Status Scripts

Read-only system status reporting for LifeOS V3.

## Scripts

### `lifeos_services.py`

Read-only service inventory script. Reports Docker containers, Telegram service status, known service path presence, git state, and suggested next actions.

**Reads:**
- `git rev-parse` (repo root, commit, dirty state)
- `docker ps` (running containers)
- `systemctl --user status` (Telegram bot)
- Filesystem path checks for known service files

**Writes: nothing.** Read-only by design. No Docker mutations, no git writes, no secrets printed.

**Usage:**
```bash
# Human-readable text (default)
python3 40_Services/scripts/lifeos_services.py

# Explicit text mode
python3 40_Services/scripts/lifeos_services.py --text

# JSON output (for n8n or MCP consumption)
python3 40_Services/scripts/lifeos_services.py --json
```

**JSON output fields:**
- `git.repo_root`, `git.commit`, `git.dirty`, `git.dirty_count`
- `docker.docker_available`, `docker.compose_version`, `docker.running_containers`
- `telegram.active`, `telegram.enabled`
- `paths.<name>.exists` for each known service path
- `suggested_action`

### `lifeos_status.py`

Read-only status reporter for n8n consumption and human inspection.

**Reads:**
- `30_Capture/` file counts (pending, approved, rejected, processed)
- `50_Event_Log/events.jsonl` last event
- `git status --short` dirty state
- `df -h /` disk usage
- `docker ps` n8n container status
- Filesystem scaffold presence checks

**Writes: nothing.** Read-only by design. No file modification, no git writes, no logs.

**Usage:**
```bash
# Human-readable text (default)
python3 40_Services/scripts/lifeos_status.py

# Explicit text mode
python3 40_Services/scripts/lifeos_status.py --text

# JSON output (for n8n)
python3 40_Services/scripts/lifeos_status.py --json
```

**JSON output fields:**
- `pending_captures`, `approved_unprocessed_captures`, `rejected_captures`, `processed_captures`
- `last_event_id`, `last_event_type`, `last_event_time`
- `event_log_valid`, `event_log_line_count`
- `git_dirty`, `git_dirty_count`
- `disk_free_root`, `disk_used_percent_root`
- `n8n_scaffold_present`, `n8n_container_running`, `n8n_status_error`
- `ai_worker_scaffold_present`, `telegram_bot_present`

### `lifeos_observability.py`

Read-only observability report script. Aggregates health data from Status API, Action API, Docker, systemd, and filesystem into a single report with warnings.

**Reads:**
- Status API `/health` and `/status` (HTTP)
- Action API `/health` (HTTP)
- `docker ps` (running containers)
- `systemctl --user status` (Telegram bot)
- `git status --short` (dirty count)
- `df -h /home/lifeos` (disk usage)

**Writes: nothing.** Read-only by design. No secrets printed. No mutation. Python stdlib only.

**Usage:**
```bash
# Human-readable text (default)
python3 40_Services/scripts/lifeos_observability.py

# Explicit text mode
python3 40_Services/scripts/lifeos_observability.py --text

# JSON output
python3 40_Services/scripts/lifeos_observability.py --json
```

**Warnings reported:**
- `status_api_unreachable`, `action_api_unreachable`
- `telegram_inactive`, `docker_unavailable`
- `n8n_running_legacy_compose_observed`
- `chromadb_provenance_unknown_observed`
- `git_dirty`, `disk_usage_high` (>= 90%)
- `event_log_invalid`, `pending_capture_count_high` (>= 10)

### Script Comparison

| Script | Scope | API-backed | Best for |
|--------|-------|-----------|----------|
| `lifeos_status.py` | Capture counts, event log, disk, git, n8n | No (local filesystem) | n8n workflow consumption |
| `lifeos_services.py` | Service inventory, Docker, paths, git | No (local CLI) | Service presence/ownership audit |
| `lifeos_observability.py` | Health checks, warnings, cross-service | Yes (Status + Action API) | Human operator health check |

## Safety

- Does not read `.env` or secret files.
- Does not inspect `40_Services/secrets/`.
- Does not modify any files.
- Does not write to any log.
- Does not run git write commands.
- Does not start, stop, restart, pull, or build Docker containers.
- Does not call any model API.

## Related

- `40_Services/docs/Storage_Triage_Runbook.md` — Safe disk cleanup procedures, Docker volume policy, and forbidden actions.
- `40_Services/docs/Observability_Control_Plane.md` — Monitoring policy and storage pressure thresholds.

**Do not run destructive Docker prune commands** (e.g. `docker system prune --volumes`, `docker volume rm`). Docker volumes contain n8n workflows, ChromaDB data, and service state. See Storage Triage Runbook for safe cleanup categories.

Observability scripts (`lifeos_observability.py`) **report** disk usage and warnings. They do not perform cleanup. Cleanup requires explicit human review and execution of the commands documented in the runbook.
