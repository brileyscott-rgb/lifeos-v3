# Status API Security Boundaries

## Hard Boundaries

1. **Read-only by design** — the API never writes files, modifies captures, or alters the event log.
2. **No secrets access** — the API does not read vault, secrets, .env, or n8n runtime files.
3. **No Docker socket** — the API has no access to /var/run/docker.sock.
4. **No host exposure** — the container joins the internal n8n_default network only.
5. **No shell commands** — the API uses Python standard library exclusively.
6. **No external APIs** — the API does not call model, webhook, or Telegram endpoints.

## Container Hardening

- `read_only: true` — filesystem is read-only except tmpfs for /tmp.
- `cap_drop: ALL` — no Linux capabilities granted.
- `security_opt: no-new-privileges:true` — prevents privilege escalation.
- Non-root user (uid 1001) — matches LifeOS host user for file read access.

## Allowed Reads

- `30_Capture/` — read-only directory listings and file existence checks.
- `50_Event_Log/events.jsonl` — read-only, parsed as JSONL.

## Mount Scope

- `../../30_Capture:/lifeos/capture:ro`
- `../../50_Event_Log:/lifeos/event-log:ro`

Not mounted:
- `/home/lifeos`
- `10_Vaults/`
- `40_Services/secrets/`
- `40_Services/n8n/.env`
- `/var/run/docker.sock`
- `.git`
