# Runtime Artifact Tracking Policy

## Purpose

Define what LifeOS tracks in Git, what it treats as runtime operational data,
what must be archived or backed up separately, and what must never be committed.
Resolves the dirty-state ambiguity around captures, event logs, service runtime
files, and local operator config.

## Policy Type

Documentation and operating constraint. No `.gitignore` changes in this version.

## Classification Categories

| Category | Tracked in Git | Backed Up | Examples |
|---|---|---|---|
| Source and config | Yes (normal commits) | Via Git remotes | Code, tests, service templates, runbooks, policies, specs |
| Canonical operational records | No | Separate backup/export | `30_Capture/*.md`, `50_Event_Log/events.jsonl` |
| Local operator config | Yes (by explicit exception) | Via Git remotes | `.config/opencode/opencode.json` |
| Service runtime state | No | Separate backup if needed | Telegram offset files, n8n data, Docker volumes |
| Secrets and credentials | Never | Never | `.env`, tokens, SSH keys, `40_Services/secrets/` |
| Temporary and disposable | Never | Never | `__pycache__/`, `*.tmp`, logs |

## Category Details

### Git-Tracked (Normal Commits)

Code, documentation, service templates, tests, specs, policies, runbooks,
and similar authored content in these paths:

- `40_Services/**/*.py` (code)
- `40_Services/**/README.md` (documentation)
- `40_Services/**/systemd/*.service` (service templates)
- `40_Services/**/notes/*.md` (architecture/security notes)
- `40_Services/**/tests/` (tests)
- `docs/` (specs, plans, runbooks)
- `10_Vaults/LifeOS/10_AI_UNIVERSE/` (policies, decisions, current state)
- `10_Vaults/LifeOS/10_AI_UNIVERSE/Policies/*.md` (policy documents)
- `.gitignore`
- `.config/opencode/opencode.json` (by explicit exception — local operator config)
- `.config/opencode/OPENCODE_WORKFLOW.md`
- `.config/opencode/agents/` (agent definitions)

These files serve as the authoritative system specification and are committed
as part of normal development.

### Canonical Operational Records (Not Git-Tracked)

Canonical LifeOS operational records are **not committed** as part of normal
code development. They are authoritative runtime data with their own lifecycle:

| Path | Type | Sensitivity | Handling |
|------|------|-------------|----------|
| `30_Capture/pending_review/*.md` | Raw capture content | Medium-High | Not committed. Backed up/exported separately. Archived per capture retention rules. |
| `30_Capture/approved/*.md` | Approved capture content | Medium-High | Not committed. Backed up/exported separately. |
| `30_Capture/rejected/*.md` | Rejected capture content | Medium | Not committed. Backed up/exported separately. May be cleaned per deletion policy. |
| `30_Capture/notes/*.md` | Source note content | Medium-High | Not committed. Backed up/exported separately. |
| `50_Event_Log/events.jsonl` | Operational audit log | Medium (see privacy policy) | Not committed. Canonical audit record. Exported/archived separately. Preserved per retention rules. |

**Why they are not tracked:**
- Captures and event logs are operational data, not source code.
- They contain potentially sensitive user content (see Event Capture Privacy Policy).
- They grow continuously — committing them would bloat the Git history with
  data that has no place in a code repository.
- They have their own backup, archival, and retention lifecycle that is
  independent of Git commits.

**How they are preserved:**
- The `50_Event_Log/events.jsonl` file is a canonical audit record. It must be
  backed up or exported through a separate process (TBD — future backup policy).
- `30_Capture/` content is operational data. Archival and cleanup follow the
  Migration Deletion Policy (manual A4 approval every time, quarantine first)
  and the Event Capture Privacy Policy.

### Local Operator Config (Tracked by Explicit Exception)

`.config/opencode/opencode.json` is an explicit exception to the `.config/**`
gitignore pattern. It is tracked because:

- It configures the OpenCode agent environment for this repository.
- It is treated as part of the project's operator tooling, not personal config.
- Local deviations (e.g., tool permissions, model preferences) may exist and
  should be committed only when they represent intended project-wide settings.

Individual agents may add local-only OpenCode config files under
`.config/opencode/` that are not tracked (the glob `.config/**` is ignored
by default; only explicitly un-ignored files are tracked).

### Service Runtime State (Not Tracked)

Service runtime files are **not committed**. They are ephemeral or service-local
state with no place in the code repository:

| Path | Content | Handling |
|------|---------|----------|
| `40_Services/config/telegram/runtime/update_offset.json` | Last processed Telegram update ID | Gitignored. Recreated by the service. Not backed up (re-fetched from Telegram). |
| `40_Services/n8n/data/` | n8n database, files, and working state | Gitignored. Backed up per n8n backup policy if needed. |
| `40_Services/n8n/.n8n/` | n8n encryption key and local config | Gitignored. Never committed. |
| `40_Services/n8n/logs/` | n8n runtime logs | Gitignored. Disposable (log rotation). |
| `40_Services/ai_worker/logs/*.log` | AI worker logs | Gitignored. Disposable (log rotation). |
| `40_Services/ai_worker/job_queue.sqlite` | AI worker job queue | Gitignored. Ephemeral state. |
| `~/.config/systemd/user/` | Copied systemd service files | Not in repository scope. The authoritative template is at `40_Services/chatops/telegram/systemd/lifeos-telegram-bot.service`. |
| `30_Capture/**/*.tmp` | Temporary capture working files | Gitignored. Disposable. |

### Secrets and Credentials (Never Committed)

These paths must never be staged or committed:

- `40_Services/config/telegram/.env` — Telegram bot token
- `40_Services/config/telegram/*.secret` — Any secret file
- `40_Services/config/telegram/*token*` — Any file with token in name
- `40_Services/n8n/.env` — n8n secrets
- `40_Services/secrets/` — All secret files
- `.ssh/` — SSH keys
- Any file matching secret/token/credential patterns regardless of location

### Temporary and Disposable (Never Committed)

- `__pycache__/` — Python bytecode
- `*.tmp`, `*.bak` — Temporary/backup files
- `.DS_Store`, `Thumbs.db` — OS metadata files
- `.lesshst`, `.xsession-errors.old` — Shell session state
- `.opencode/` — OpenCode runtime cache/state
- Docker volume data created at runtime

## Implementation Agent Guidance

When working in this repository:

1. **Expect dirty runtime files.** Running the system generates captures,
   event log entries, and service state. These will appear in `git status
   --short` as untracked or modified files. This is normal.

2. **Do not stage or commit runtime files.** The following paths must never
   appear in a commit:
   - `30_Capture/**/*.md`
   - `50_Event_Log/events.jsonl`
   - `40_Services/config/telegram/runtime/`
   - `40_Services/n8n/data/`
   - `40_Services/n8n/.n8n/`
   - `40_Services/n8n/logs/`
   - `40_Services/ai_worker/logs/*.log`
   - `40_Services/ai_worker/job_queue.sqlite`
   - `__pycache__/`
   - `.config/opencode/opencode.json` (unless the commit is explicitly about
     OpenCode configuration changes — and only with review)

3. **Use explicit `git add` paths.** Never use `git add .`, `git add -A`, or
   `git add --all` in this repository. Always stage specific files or use
   `git add <path>` for known-safe paths.

4. **Check staged content.** Before committing, run `git status --short` and
   `git diff --cached --stat` to verify only intended files are staged.

5. **Runtime artifact changes are not code defects.** A modified
   `50_Event_Log/events.jsonl` or new capture files in `30_Capture/` are
   expected operational state, not unauthorized changes. Do not flag them
   as issues.

## Backup and Archival

Canonical operational records and service runtime data have separate backup
and archival requirements from Git-tracked content:

| Data | Backup Method | Frequency | Notes |
|------|--------------|-----------|-------|
| Git-tracked content | Git push to remotes | Per commit | Standard Git workflow |
| `50_Event_Log/events.jsonl` | Separate export/backup process (TBD) | TBD | Canonical audit record. Must not be lost on system reset. |
| `30_Capture/` | Separate backup process (TBD) | TBD | Operational capture content. Archive before cleanup. |
| Service runtime state | Per-service backup if needed | Per-service | Telegram offset is re-fetched. n8n data may need backup. |

The backup/archival process for `50_Event_Log/events.jsonl` and
`30_Capture/` is **not yet implemented**. These are future work items
that will be designed after the foundation is stable.

## Relationship to Other Policies

| Policy | Relationship |
|--------|-------------|
| Event Capture Privacy Policy | Defines privacy handling for captures and event log data. This policy handles tracking/backup. |
| Migration Deletion Policy | Defines deletion rules (A4 approval, quarantine first). This policy handles what is tracked vs ignored. |
| Sync and Backup Policy | Future policy for backup methods and schedules. This policy identifies what needs backup. |
| `.gitignore` | Implements the ignore rules for files that must never be tracked. This policy documents intent. |

## Future Considerations

As the system grows, the following may require policy updates:

- **Capture archival automation**: A future controlled file processor may need
  rules for archiving reviewed captures.
- **Event log export**: A scheduled export of `50_Event_Log/events.jsonl` for
  long-term preservation.
- **Service data backup**: Per-service backup policies for n8n, Docker volumes,
  and AI worker state.
- **GitHub or external Git hosting**: If the repository is mirrored to a
  public or semi-public remote, ensure no operational data leaks.
- **`30_Capture/` in `.gitignore`**: If the current implicit untracked state
  causes confusion, adding `30_Capture/**/*.md` to `.gitignore` would make
  the policy explicit.

---

**Document Version**: 1.0
**Date**: 2026-07-07
**Status**: Locked
