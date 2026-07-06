# Action API Security Boundaries

## Hard Boundaries

1. **No shell execution** — Uses Python standard library exclusively. No subprocess, no shell=True.
2. **No Docker socket** — Container does not mount /var/run/docker.sock.
3. **No vault access** — Container cannot access 10_Vaults/.
4. **No secrets access** — Container does not read .env, secrets files, or n8n credential/database files.
5. **No arbitrary paths** — All path operations resolve within /lifeos/capture/ subdirectories only.
6. **Path traversal prevention** — Absolute paths and `../` sequences are rejected.
7. **Read-write scope limited** — Container writes only to 30_Capture/ and appends to 50_Event_Log/events.jsonl. No other write targets.

## Container Hardening

| Setting | Value |
|---|---|
| `cap_drop` | `ALL` |
| `security_opt` | `no-new-privileges:true` |
| User | uid 1001 (non-root) |
| Restart | `unless-stopped` |
| Network | `lifeos_internal` only |

## Mount Scope

| Host Path | Container Path | Mode |
|---|---|---|
| `30_Capture/` | `/lifeos/capture` | `rw` |
| `50_Event_Log/` | `/lifeos/event-log` | `rw` |

## Not Mounted

- `/home/lifeos` (root)
- `10_Vaults/`
- `40_Services/secrets/`
- `40_Services/n8n/.env`
- `/var/run/docker.sock`
- `.git/`
- n8n database or credential files

## Operates Only On

- `30_Capture/pending_review/`
- `30_Capture/approved/`
- `30_Capture/rejected/`
- `30_Capture/processed/`
- `50_Event_Log/events.jsonl`
