# LifeOS Telegram Automation Operator — Architecture Design

## 1. Executive Summary

The LifeOS Telegram Automation Operator replaces the offline Python Telegram bot with a persistent n8n-based webhook service. Telegram messages arrive via HTTPS webhook, n8n authenticates the sender against an allowlist, routes commands to controlled LifeOS API endpoints, and replies back through Telegram — all without shell execution, vault writes, Docker socket exposure, or broad AI capabilities.

The system adds two new components to the existing hardened stack:
- **Caddy reverse proxy** — provides TLS termination for Telegram webhook ingress
- **LifeOS Action API** — provides controlled read-write operations for captures and event log

The existing LifeOS Status API stays read-only. n8n orchestrates the flow between Telegram, the Status API, and the Action API.

## 2. Difference From Manual-Only Status API Test

| Dimension | Status API Test (current) | Telegram Operator (planned) |
|---|---|---|
| Trigger | Manual (n8n UI button) | Telegram webhook ingress |
| Direction | n8n → API only | Telegram ↔ n8n ↔ API |
| HTTP methods | GET only | GET + POST |
| Filesystem access | Read-only mounts | Read-write for captures + event log |
| User input | None | Telegram commands with parameters |
| Output | n8n output panel | Telegram replies |
| Network exposure | `lifeos_internal` only | Public HTTPS (TLS-terminated) |
| Execution model | Manual, inactive | Active webhook listener (inactive schedule) |

## 3. Final Feature List

1. Public HTTPS webhook ingress for Telegram via Caddy reverse proxy
2. Telegram user allowlist (n8n variables, checked per message)
3. `/start` — welcome message with available commands
4. `/help` — list all commands with descriptions
5. `/status` — capture queue counts + event log status (via Status API)
6. `/capture <text>` — create a pending capture file
7. `/pending` — list pending captures with numbered index
8. `/view <number>` — show a specific pending capture details
9. `/approve <number>` — approve a pending capture
10. `/reject <number>` — reject a pending capture
11. Scheduled status digest (future, requires explicit approval)
12. Telegram replies for every command
13. Event/audit logging for all operations
14. Documentation and rollback/checklists

## 4. Explicitly Removed Features

- CPIM tutoring or studying functionality
- Image generation or Dall-E integration
- Broad AI agent tools or project assistant
- Qdrant/vector memory or RAG/vault search
- Dashboard panels or visualization
- Local LLM routing or model API calls
- Arbitrary shell execution or Execute Command nodes
- Git commands from n8n
- Direct n8n writes to random LifeOS files
- Docker socket access from any container
- Direct n8n credential store or database file access
- Webhook-triggered schedule activation (schedule stays manual-approval gated)

## 5. System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Internet                                 │
│  Telegram (mobile) ─── HTTPS webhook ───→ bot.example.com:443   │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│  Host (lifeos user)                                             │
│                                                                  │
│  ┌──────────────────────┐     ┌──────────────────────────────┐  │
│  │  Caddy (container)   │────→│  n8n (container)             │  │
│  │  Port 443 → TLS      │     │  127.0.0.1:5678             │  │
│  │  lifeos_internal     │     │  Webhook node + routing      │  │
│  └──────────────────────┘     │  Variable: allowlist         │  │
│                               │  HTTP Request → APIs          │  │
│                               └──────────┬───────────────────┘  │
│                                          │                       │
│                    ┌─────────────────────┼──────────────┐       │
│                    ▼                     ▼              │       │
│  ┌────────────────────────┐  ┌──────────────────────┐   │       │
│  │  Status API (existing) │  │  Action API (new)    │   │       │
│  │  lifeos-status-api:8787│  │  lifeos-action-api:8788│  │       │
│  │  read_only: true       │  │  read-write: captures │   │       │
│  │  no docker socket      │  │  append: event log    │   │       │
│  │  cap_drop: ALL         │  │  cap_drop: ALL        │   │       │
│  └────────────────────────┘  └──────────────────────┘   │       │
│                    │                    │                │       │
│                    ▼                    ▼                │       │
│  ┌──────────────────────────────────────────────────┐    │       │
│  │  30_Capture/ (read-only for Status,              │    │       │
│  │               read-write for Action)              │    │       │
│  │  50_Event_Log/events.jsonl (append for Action)   │    │       │
│  └──────────────────────────────────────────────────┘    │       │
└──────────────────────────────────────────────────────────────────┘
```

All containers share the `lifeos_internal` Docker network.

## 6. Required n8n Workflows

### 6.1 LifeOS Telegram Bot Webhook (active, webhook-triggered)

```
Telegram Webhook node
  → Code node (extract sender ID, message text, chat ID)
  → IF node (check user ID against allowlist)
    ├── FALSE → No reply or log unauthorized event (stop)
    └── TRUE → Switch node (route by command text)
         ├── /start     → Telegram Send Message (welcome)
         ├── /help      → Telegram Send Message (help text)
         ├── /status    → HTTP Request → Status API → Telegram Send Message
         ├── /capture   → HTTP Request → Action API POST /captures → Telegram Send Message
         ├── /pending   → HTTP Request → Action API GET /captures/pending → Telegram Send Message
         ├── /view      → parse index → HTTP Request → Action API GET /captures/pending/<index> → Telegram Send Message
         ├── /approve   → parse index → HTTP Request → Action API POST /captures/<id>/approve → Telegram Send Message
         └── /reject    → parse index → HTTP Request → Action API POST /captures/<id>/reject → Telegram Send Message
```

### 6.2 LifeOS Status Digest (existing, inactive, manual trigger)

```
Manual Trigger → HTTP Request → GET http://lifeos-status-api:8787/status
```
Kept as-is. No activation. Used for manual testing.

### 6.3 LifeOS Scheduled Digest (future, requires explicit approval)

```
Schedule Trigger (e.g., daily 08:00) → HTTP Request → Status API → Telegram Send Message
```
Not created until explicitly approved. Referenced in checklist.

## 7. Telegram Command Inventory

| Command | Parameters | Description | API Call |
|---|---|---|---|
| `/start` | none | Welcome message | None |
| `/help` | none | List commands | None |
| `/status` | none | Capture queue + event log status | `GET /status` (Status API) |
| `/capture` | `<text>` | Create pending capture | `POST /captures` (Action API) |
| `/pending` | none | List pending captures with index | `GET /captures/pending` (Action API) |
| `/view` | `<number>` or `latest` | Show capture details | `GET /captures/pending/<index>` (Action API) |
| `/approve` | `<number>` or `latest` | Approve pending capture | `POST /captures/<id>/approve` (Action API) |
| `/reject` | `<number>` or `latest` | Reject pending capture | `POST /captures/<id>/reject` (Action API) |

All replies go through n8n's Telegram Send Message node.

## 8. Webhook Ingress Design Options

### Option A: Caddy Reverse Proxy (Recommended)

A Caddy v2 container on `lifeos_internal`, bound to host port 443, terminates TLS via Let's Encrypt, and proxies `https://telegram.lifeos.example.com/` → `http://n8n:5678/`.

- **Pros**: Production-grade TLS, auto-renewal, no third-party tunnel dependency
- **Cons**: Requires DNS (public `A` record pointing to the host), port 443 reachable
- **Config**: Caddyfile with `reverse_proxy` to `n8n:5678`
- **DNS requirement**: `telegram.lifeos.example.com` → host public IP

### Option B: n8n Built-in Tunnel (Simplest for Testing)

Run n8n with `N8N_TUNNEL_SUBDOMAIN` and `N8N_TUNNEL_SUBDOMAIN_TOKEN`. n8n creates a temporary `https://<subdomain>.n8n.cloud/` URL.

- **Pros**: No DNS, no reverse proxy, instant public URL
- **Cons**: Temporary URL, dependency on n8n cloud tunnel service, not suitable for production
- **Use**: Initial testing only

### Option C: Cloudflare Tunnel (No Open Ports)

`cloudflared` container creates a tunnel to Cloudflare's edge, proxying `telegram.lifeos.example.com` → `localhost:5678`.

- **Pros**: No open firewall ports, works behind NAT, built-in DDoS protection
- **Cons**: Requires Cloudflare DNS management, additional `cloudflared` setup
- **Use**: If Cloudflare is already the DNS provider

### Option D: Direct Host Proxy (Simple if Port 443 Available)

Run Caddy on the host (not in container), proxy to `127.0.0.1:5678`.

- **Pros**: Simplest network topology, no container-for-proxy
- **Cons**: Adds host-level dependency, manual Caddy install
- **Use**: Minimalist alternative to Option A

### Recommendation

**Option A** (Caddy container) for production. **Option B** (n8n tunnel) for initial testing and validation. Document both in the deployment checklist.

## 9. User Allowlist Design

### Storage

- Telegram user IDs stored as an n8n **Variable** named `telegram_allowed_user_ids`
- Format: JSON array of integers, e.g., `[123456789, 987654321]`
- Managed through n8n UI (Settings → Variables)
- Never committed to git, never in workflow JSON

### Enforcement

1. Webhook trigger receives Telegram update
2. n8n **Code node** extracts `message.from.id` from the webhook payload
3. n8n **IF node** checks if `id` is in the allowlist array
4. If not allowed: log event, send no reply (or polite "unauthorized" message), stop execution
5. If allowed: proceed to command routing

### Initial Setup

- First authorized user ID configured in `telegram_allowed_user_ids` variable
- The bot creator (Telegram bot admin) is added during initial setup
- Additional users added through n8n UI Variables panel as needed

## 10. LifeOS Tool/API Design

### 10.1 LifeOS Status API (existing, no changes)

- Base URL: `http://lifeos-status-api:8787`
- Endpoints: `GET /health`, `GET /status`
- Status: Verified, hardened, read-only
- Used by: `/status` command, scheduled digest

### 10.2 LifeOS Action API (new)

Purpose: Safe, auditable read-write operations for captures and event logging.

#### Container

- Image: Python 3.12+ (slim)
- Base: Same pattern as Status API (Python stdlib http.server)
- Network: `lifeos_internal`
- Port: `8788` (internal only, no host port)
- User: non-root (uid 1001)
- `cap_drop: ALL` + `security_opt: no-new-privileges:true`
- NOT `read_only: true` (needs write access to specific directories)
- Writable mounts:
  - `../30_Capture:/lifeos/capture:rw`
  - `../50_Event_Log:/lifeos/event-log:rw`
- No Docker socket, no .env access, no vault access

#### Endpoints

| Method | Path | Description | Filesystem Action |
|---|---|---|---|
| `GET` | `/health` | Health check | None |
| `GET` | `/captures/pending` | List pending captures with index | Read `pending_review/` directory |
| `GET` | `/captures/pending/<index>` | Get specific capture content | Read specific file |
| `GET` | `/captures/<id>` | Get capture by ID | Read file by ID match |
| `POST` | `/captures` | Create new capture | Write file to `pending_review/`, append event |
| `POST` | `/captures/<id>/approve` | Approve capture | Move file to `approved/`, update frontmatter, append event |
| `POST` | `/captures/<id>/reject` | Reject capture | Move file to `rejected/`, update frontmatter, append event |
| `GET` | `/captures/approved` | List approved captures | Read `approved/` directory |

#### Capture ID Format

`capture_<date>_<slug>` where slug is derived from the first few words of the capture text. Generated by the Action API when a capture is created.

#### Response Format

All responses return JSON with a consistent structure:

```json
{
  "success": true,
  "data": { ... },
  "event_id": "evt_20260706T180606Z_telegram_capture_created"
}
```

Error responses:
```json
{
  "success": false,
  "error": "capture_not_found",
  "message": "No capture found at index 5"
}
```

## 11. Event/Audit Logging Model

### Event Types

| Event Type | Trigger | Details |
|---|---|---|
| `telegram.command_received` | Any valid command | `{command, user_id, username}` |
| `telegram.capture_created` | `/capture` | `{capture_id, text_preview, file_path}` |
| `telegram.capture_approved` | `/approve` | `{capture_id, index, target_file}` |
| `telegram.capture_rejected` | `/reject` | `{capture_id, index, target_file}` |
| `telegram.unauthorized_access` | Command from unauthorized user | `{user_id, username, command}` |
| `telegram.webhook_error` | Processing error | `{error, command, user_id}` |

### Log Format

Events follow the existing `50_Event_Log/events.jsonl` schema (one JSON object per line):

```json
{
  "event_id": "evt_20260706T180606Z_telegram_capture_created",
  "timestamp": "2026-07-06T18:06:06Z",
  "type": "telegram.capture_created",
  "source": "telegram_operator",
  "details": {
    "capture_id": "capture_20260706_quick_note",
    "text_preview": "Quick note about...",
    "file_path": "30_Capture/pending_review/capture_20260706_quick_note.md"
  }
}
```

### Append Mechanism

- The Action API appends events using atomic append (`open(path, 'a')`)
- Follows the same collision detection pattern as the existing Python bot
- Events are logged by the Action API (which performs the filesystem operation)

## 12. Security Boundaries

### Hard Boundaries

1. **No shell execution** — No Execute Command node in any n8n workflow. No shell=True in Python APIs.
2. **No Docker socket** — No container mounts `/var/run/docker.sock`.
3. **No vault writes** — Action API cannot write to `10_Vaults/`.
4. **No git commands** — No `git commit`, `git push`, or git operations from n8n.
5. **No secrets in workflows** — Telegram bot token stored in n8n credential store only, never in workflow JSON.
6. **No .env access** — No n8n workflow reads `.env` files.
7. **No credential store inspection** — No external process reads n8n database or credential files.
8. **Public webhook is read-only input** — Webhook triggers workflow execution but the workflow cannot be modified via webhook payload.
9. **User allowlist enforced per message** — Every message authenticated before processing.
10. **Action API operations are specific and bounded** — No arbitrary file create/delete/move. Only the documented capture lifecycle operations.

### Container Hardening (Action API)

| Setting | Value |
|---|---|
| `read_only` | `false` (needs writes) |
| `cap_drop` | `ALL` |
| `security_opt` | `no-new-privileges:true` |
| User | `1001:1001` (non-root) |
| `restart` | `unless-stopped` |
| Network | `lifeos_internal` only |

### Mount Scope (Action API)

| Host Path | Container Path | Mode |
|---|---|---|
| `30_Capture/` | `/lifeos/capture` | `rw` |
| `50_Event_Log/` | `/lifeos/event-log` | `rw` |

### Not Mounted

- `/home/lifeos` (root)
- `10_Vaults/`
- `40_Services/secrets/`
- `40_Services/n8n/.env`
- `/var/run/docker.sock`
- `.git`
- `40_Services/n8n/database/`

### Caddy Reverse Proxy Hardening

- Runs as non-root (Caddy v2 defaults to dropping capabilities)
- TLS via Let's Encrypt (automatic certificates)
- Only proxies known Host header (not an open relay)
- Rate limiting on webhook endpoint (n8n webhook settings)

## 13. Credential Model

| Variable | Where Stored | How Set | Usage |
|---|---|---|---|
| `TELEGRAM_BOT_TOKEN` | n8n Credential store (Telegram API) | n8n UI → Credentials → Telegram | Telegram Send Message node |
| `telegram_webhook_url` | n8n Variable | n8n UI → Variables | Webhook registration (one-time) |
| `telegram_allowed_user_ids` | n8n Variable | n8n UI → Variables | User allowlist check |
| `telegram_bot_username` | n8n Variable | n8n UI → Variables | Bot identification for webhook |

None of these values appear in workflow JSON, git, `.env`, or container environment variables exposed to n8n. The Action API has no credentials at all (internal network only).

## 14. Files That Should Be Created/Changed

### New Files

| File | Purpose |
|---|---|
| `40_Services/action_api/Dockerfile` | Action API container image |
| `40_Services/action_api/server.py` | Python HTTP server with all endpoints |
| `40_Services/action_api/tests/test_action_api.py` | Unit tests for Action API |
| `40_Services/action_api/README.md` | Action API documentation |
| `40_Services/action_api/notes/security_boundaries.md` | Action API security boundaries |
| `40_Services/n8n/workflows/planned/telegram_bot_webhook.md` | Planned Telegram bot webhook workflow doc |
| `40_Services/n8n/compose/caddy/Caddyfile` | Caddy reverse proxy configuration |
| `40_Services/n8n/compose/docker-compose.yml` or update `docker-compose.yml` | Add Action API and Caddy services |

### Changed Files

| File | Change |
|---|---|
| `40_Services/n8n/docker-compose.yml` | Add Action API service, add Caddy service, add `telegram` network or update ports |
| `40_Services/n8n/notes/activation_checklist.md` | Add Telegram webhook checklist items |
| `40_Services/n8n/notes/security_boundaries.md` | Add webhook and Action API boundaries |
| `40_Services/n8n/workflows/planned/lifeos_status_digest.md` | Reference Telegram bot workflow |
| `40_Services/status_api/notes/security_boundaries.md` | Add note about sibling Action API |
| `10_Vaults/LifeOS/10_AI_UNIVERSE/Current_Working_State.md` | Record as completed after implementation |
| `docs/superpowers/specs/2026-07-06-lifeos-telegram-automation-operator-design.md` | This design document |

### No Changes

- `40_Services/secrets/` — no new secrets config
- `40_Services/n8n/scripts/` — existing start/stop scripts work
- `40_Services/chatops/telegram/telegram_capture_bot.py` — remains as standalone testing tool
- `40_Services/status_api/` — no changes to existing Status API

## 15. Testing Checklist

### Pre-Deployment

- [ ] Action API unit tests pass (all endpoints, error cases)
- [ ] Action API container builds
- [ ] Action API starts correctly on `lifeos_internal`
- [ ] DNS `A` record for webhook hostname resolves to host public IP
- [ ] Port 443 reachable from internet (or tunnel functional)

### Caddy / Ingress

- [ ] Caddy reverse proxy starts and binds to host port 443
- [ ] TLS certificate issued by Let's Encrypt
- [ ] `https://telegram.lifeos.example.com/webhook/...` reaches n8n
- [ ] Direct `http://localhost:5678` still works (no regression)
- [ ] Port 5678 remains bound to 127.0.0.1 (not publicly exposed)

### Webhook Registration

- [ ] Telegram bot webhook URL configured via `setWebhook` API call (one-time curl)
- [ ] Telegram webhook test message received by n8n
- [ ] n8n webhook node returns 200 to Telegram
- [ ] Unauthorized user ID is rejected (no reply or logged)
- [ ] Authorized user ID proceeds to command routing

### Command Tests

- [ ] `/start` returns welcome message
- [ ] `/help` lists all commands
- [ ] `/status` returns status JSON formatted as Telegram message
- [ ] `/capture Test capture` creates a file in `pending_review/` and appends event
- [ ] `/capture` (no text) returns error message
- [ ] `/pending` lists pending captures with numbered index
- [ ] `/pending` with no pending captures returns empty message
- [ ] `/view 1` shows first pending capture
- [ ] `/view 999` returns "not found" error
- [ ] `/approve 1` moves file to `approved/`, updates frontmatter, appends event
- [ ] `/reject 1` moves file to `rejected/`, updates frontmatter, appends event
- [ ] `/approve` with no pending returns appropriate message
- [ ] `/approve latest` works (refers to newest pending)
- [ ] Unknown command returns "not recognized" message

### Event Log Verification

- [ ] Each Telegram operation creates a corresponding event in `events.jsonl`
- [ ] Event format matches existing schema (event_id, timestamp, type, source, details)
- [ ] Event IDs are unique (no collisions)
- [ ] Unauthorized access attempts are logged

### Security Verification

- [ ] No Execute Command node in any n8n workflow
- [ ] No Docker socket mounted in any container
- [ ] No `.env` file readable from n8n or Action API
- [ ] Action API cannot access `10_Vaults/`
- [ ] Action API runs as non-root (uid 1001)
- [ ] Action API has `cap_drop: ALL`
- [ ] n8n port 5678 still bound to 127.0.0.1
- [ ] Status API still read-only and hardened (no regression)

## 16. Deployment Checklist

- [ ] DNS record created: `telegram.lifeos.example.com` → host public IP
- [ ] Port 443 allowed in host firewall (if applicable)
- [ ] Action API implemented and tested
- [ ] Caddy Dockerfile or compose service configured
- [ ] n8n `docker-compose.yml` updated with new services
- [ ] `telegram_allowed_user_ids` n8n variable created with admin user ID
- [ ] Telegram bot token credential created in n8n UI
- [ ] Webhook URL n8n variable set
- [ ] Telegram webhook registered via `setWebhook` API call
- [ ] Full command test run (testing checklist section 3)
- [ ] Event log verified
- [ ] Workflow saved and activated
- [ ] Security boundaries verified
- [ ] Rollback plan documented

## 17. Rollback Checklist

- [ ] Disable Telegram webhook via `deleteWebhook` API call (one-time curl)
- [ ] Deactivate n8n Telegram webhook workflow
- [ ] Remove Caddy reverse proxy container (`docker-compose stop caddy`)
- [ ] Remove Action API container (`docker-compose stop lifeos-action-api`)
- [ ] Verify n8n still works on `http://localhost:5678`
- [ ] Verify Status API still works on `lifeos_internal`
- [ ] Remove DNS record (if desired)
- [ ] Remove n8n Telegram credential
- [ ] Remove n8n variables (allowlist, webhook URL)
- [ ] Revert `docker-compose.yml` to previous commit
- [ ] Clean up any partial captures created during testing

## 18. Recommended Implementation Order

### Phase A: Action API (build first, test independently)

1. Create `40_Services/action_api/server.py` with all endpoints
2. Create `40_Services/action_api/tests/test_action_api.py` with unit tests
3. Create `40_Services/action_api/Dockerfile`
4. Add Action API service to `40_Services/n8n/docker-compose.yml`
5. Test Action API endpoints via `curl` from host
6. Create `40_Services/action_api/README.md` and `notes/security_boundaries.md`

### Phase B: Webhook Ingress (network setup)

7. Create `40_Services/n8n/compose/caddy/Caddyfile`
8. Add Caddy service to `40_Services/n8n/docker-compose.yml`
9. Configure DNS `telegram.lifeos.example.com` → host IP
10. Start Caddy and verify TLS certificate
11. Test webhook reachability

### Phase C: n8n Workflow (build in UI only, no automation import)

12. Create "LifeOS Telegram Bot Webhook" workflow manually in n8n UI
13. Add and configure each node: Webhook → Code → IF → Switch → [command branches]
14. Add Telegram Send Message nodes for replies
15. Create n8n credential for Telegram bot token
16. Create n8n variable for `telegram_allowed_user_ids`
17. Register Telegram webhook URL via curl
18. Test all commands end-to-end

### Phase D: Documentation and Closeout

19. Create `40_Services/n8n/workflows/planned/telegram_bot_webhook.md`
20. Update `activation_checklist.md` with webhook items
21. Update `security_boundaries.md` with new service boundaries
22. Run full testing checklist
23. Commit, push, update Current_Working_State.md
24. Export workflow JSON to `40_Services/n8n/workflows/exported/`

---

**Document Version**: 1.0
**Date**: 2026-07-06
**Status**: Phase A (Action API) implemented. Phase B (Caddy), C (n8n workflow), D (docs closeout) pending.
