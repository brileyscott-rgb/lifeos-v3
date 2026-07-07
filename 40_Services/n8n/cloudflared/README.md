# Cloudflare Tunnel — LifeOS n8n Webhook Ingress

## Purpose

Cloudflare Tunnel (cloudflared) exposes only n8n webhook paths for Telegram, without opening firewall ports or exposing the n8n UI publicly.

## Target Architecture

```
Telegram (mobile)
  → HTTPS → Cloudflare Edge → cloudflared tunnel
    → http://n8n:5678/webhook/* (lifeos_internal)
```

### Public (tunneled)

- `https://telegram.<your-domain>/webhook/*` → n8n webhook handler

### Private (internal only, not tunneled)

- `http://localhost:5678` — n8n UI (local-only)
- `http://lifeos-status-api:8787` — Status API (internal only)
- `http://lifeos-action-api:8788` — Action API (internal only)

## Docker Compose Version Note

This tunnel setup uses Docker Compose V2 syntax (the `docker compose` command, with a space). If you are on Docker Compose V1 (the `docker-compose` command, with a hyphen), you may need to adjust the compose file or upgrade to V2. The compose file uses the `name:` field which requires V2+. To check your version:

```bash
docker compose version   # V2 — preferred
docker-compose version   # V1 — legacy, may need adapter
```

## Manual Prerequisites

Before activating the tunnel:

- [ ] Cloudflare account with active zone
- [ ] Domain managed by Cloudflare (DNS in-orange-cloud/proxied mode)
- [ ] Cloudflare Tunnel created in Zero Trust dashboard
- [ ] Tunnel token or credentials JSON generated via dashboard
- [ ] Public hostname chosen: `telegram.<your-domain>`
- [ ] No real secrets committed to git

## Setup Outline

1. **Create Cloudflare Tunnel**
   - Go to Cloudflare Zero Trust → Access → Tunnels
   - Create a new tunnel (named e.g., `lifeos-telegram`)
   - Note the tunnel ID for config.example.yml

2. **Configure Public Hostname**
   - In the tunnel dashboard, add a public hostname:
     - Hostname: `telegram.<your-domain>`
     - Path: `/webhook/*`
     - Service: `http://n8n:5678`

3. **Configure Catch-All 404**
   - Add a catch-all rule returning 404 for all non-matching paths
   - This prevents public access to n8n UI, Status API, and Action API

4. **Prepare Local Config**
   - Copy `config.example.yml` to `config.yml`
   - Replace all `<placeholder>` values with real values
   - Place credentials JSON at the path referenced in config.yml

5. **Keep Secrets Untracked**
   - `config.yml`, `*.json` (credentials), and tunnel tokens are gitignored
   - Only `config.example.yml` is committed

6. **Add WEBHOOK_URL to n8n Configuration** (during implementation step, not now)
   ```
   WEBHOOK_URL=https://telegram.<your-domain>/
   ```

7. **Restart n8n** (during implementation step, not now)
   - n8n reads WEBHOOK_URL at startup for correct webhook URL generation

## Generic Webhook Test First

Before registering the Telegram webhook, test the tunnel with a generic webhook:

```
https://telegram.<your-domain>/webhook/test
```

- [ ] Create a temporary n8n Webhook workflow with path `/webhook/test`
- [ ] Test the path with curl or browser
- [ ] Verify the response reaches n8n and returns 200
- [ ] Verify the n8n UI is NOT reachable at `https://telegram.<your-domain>/`
- [ ] Verify Status/Action APIs are NOT reachable via tunnel
- [ ] Delete/deactivate the test workflow after verification

## Telegram Webhook Registration (Later — Not Yet)

When ready to register the Telegram webhook:

```
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://telegram.<your-domain>/webhook/telegram",
    "secret_token": "<your-secret-token>",
    "allowed_updates": ["message"]
  }'
```

- Use `secret_token` for app-layer authentication
- n8n webhook node verifies `X-Telegram-Bot-Api-Secret-Token` header
- `allowed_updates` starts with `["message"]` only
- Expand `allowed_updates` later for callback buttons, photos, voice, documents

## Cloudflare Access Warning

**Do NOT put Cloudflare Access interactive login in front of the Telegram webhook path.** Telegram cannot complete login challenges. Instead:

- Use Telegram `secret_token` for app-layer authentication
- Use n8n allowlist for user authorization (check `message.from.id`)
- The webhook path must be publicly reachable but cryptographically verified

## Rollback

1. Delete Telegram webhook via `deleteWebhook` API call (if already registered later)
2. Deactivate n8n webhook workflow (if already active later)
3. Stop cloudflared container: `docker compose -f 40_Services/n8n/docker-compose.yml stop cloudflared`
4. Remove public hostname route from Cloudflare Zero Trust dashboard
5. Remove `WEBHOOK_URL` from n8n configuration (if added later)
6. Verify local n8n still works at `http://localhost:5678`
7. Verify Status API still internal at `http://lifeos-status-api:8787/health`
8. Verify Action API still internal at `http://lifeos-action-api:8788/health`
