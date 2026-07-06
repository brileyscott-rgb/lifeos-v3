# LifeOS Status Scripts

Read-only system status reporting for LifeOS V3.

## Scripts

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

## Safety

- Does not read `.env` or secret files.
- Does not inspect `40_Services/secrets/`.
- Does not modify any files.
- Does not write to any log.
- Does not run git write commands.
- Does not start, stop, restart, pull, or build Docker containers.
- Does not call any model API.
