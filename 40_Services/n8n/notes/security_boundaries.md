# n8n Security Boundaries

## Hard Boundaries

1. **No public exposure** — n8n is local-only until explicitly reviewed and approved.
2. **No direct vault writes** — n8n workflows may read vault-adjacent data but must not write to `10_Vaults/`.
3. **No direct git commits** — n8n must not call git commit/push.
4. **No real secrets in workflows** — credentials use n8n credential store, not hardcoded values.
5. **No Telegram webhook triggers** — Telegram automation stays in the dedicated Python bot.
6. **Read-only mount by default** — event log and capture directories are mounted `:ro`.

## Network

n8n and the Status API communicate over the shared `lifeos_internal` Docker network.
The Status API is reachable at `http://lifeos-status-api:8787/status`.

## Allowed Reads

- `50_Event_Log/events.jsonl` via Status API (read-only HTTP)
- `30_Capture/` directory listings via Status API (read-only HTTP)

Direct filesystem mounts removed in favor of Status API calls.

## Disallowed Reads

- Direct filesystem access to `30_Capture/` or `50_Event_Log/` — route through Status API instead.
- Git status output — not available without repo mount inside container.

## Prohibited Writes

- `10_Vaults/` — no direct vault file creation or modification
- Git operations — no commit, push, branch operations
- `40_Services/secrets/` — no credential file writes
- `.env` files — no environment file modification

## Workflow Review Policy

Before any workflow is activated:

- [ ] Workflow JSON reviewed for embedded secrets
- [ ] Credentials use n8n credential store
- [ ] No public webhook triggers
- [ ] No direct vault writes
- [ ] No git operations
- [ ] Tested in isolated mode first
- [ ] Approved by LifeOS user
