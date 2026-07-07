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

## Cloudflare Tunnel

- Cloudflared scaffold exists at `40_Services/n8n/cloudflared/` — no active tunnel yet.
- cloudflared must expose only `/webhook/*` paths where practical.
- Catch-all ingress rule must return 404 to prevent public n8n UI exposure.
- n8n UI must remain local-only (bound to 127.0.0.1:5678).
- Status API (`lifeos-status-api:8787`) must not be publicly routed.
- Action API (`lifeos-action-api:8788`) must not be publicly routed.
- Cloudflare credentials, tunnel tokens, and credentials JSON are never committed.
- Cloudflare Access interactive login must not protect Telegram webhook path — Telegram cannot complete login challenges.
- Telegram `secret_token` + n8n allowlist provide app-layer protection instead.

## Proposal Approval Boundaries

1. **No stale proposal approval** — n8n must never route a proposal approval command that references a proposal version that does not match the current version.
2. **No unseen content approval** — n8n must only route `/approve` for proposals after the user has had the opportunity to view the full content or diff. The workflow must provide `/view` subcommands (summary, full, diff, per-file) before accepting an approval.
3. **n8n must not generate proposals** — Proposal generation is the AI processor's responsibility. n8n routes proposal data but does not construct, edit, or validate proposal packets.
4. **n8n must not bypass proposal gates** — No n8n workflow may write files to the vault or invoke a processor without an exact, version-matched user approval.
5. **No direct AI invocation from Telegram** — n8n must not embed AI model nodes or API calls directly in a Telegram-triggered workflow without intermediate user approval gates.

## Workflow Review Policy

Before any workflow is activated:

- [ ] Workflow JSON reviewed for embedded secrets
- [ ] Credentials use n8n credential store
- [ ] No public webhook triggers
- [ ] No direct vault writes
- [ ] No git operations
- [ ] No proposal bypass (approval must reference exact proposal version)
- [ ] Tested in isolated mode first
- [ ] Approved by LifeOS user
