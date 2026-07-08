# Capture API

Local-only HTTP API for LifeOS capture intake.

**Status:** V1 operational — deployed as systemd user service at `127.0.0.1:8789`.

## Purpose

Single entry point for all capture sources: Telegram, HTTP Shortcuts, bookmarklets, desktop scripts, n8n workflows, and future MCP tools.

## Quick Start

```bash
# Check health (no auth required)
curl -s http://127.0.0.1:8789/health

# Send a capture (requires bearer token from .env)
source <(grep BEARER_TOKEN /home/lifeos/40_Services/capture_api/.env)
curl -s -X POST http://127.0.0.1:8789/captures \
  -H "Authorization: Bearer ${LIFEOS_CAPTURE_BEARER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"content": "Your capture text here", "source": "desktop"}'
```

## Architecture

```
Capture Source → Capture API → Append-Only JSONL Queue → Processors → Buffer Vault → Review → Approval → Canonical Import
```

## Service Management

```bash
systemctl --user status lifeos-capture-api   # Check status
systemctl --user restart lifeos-capture-api  # Restart
journalctl --user -u lifeos-capture-api      # View logs
```

The service uses `EnvironmentFile=/home/lifeos/40_Services/capture_api/.env` (mode 600, gitignored).

## Auth Modes

- **Bearer token**: For internal services (Telegram bot, n8n) and local clients. Configured via `LIFEOS_CAPTURE_BEARER_TOKEN` in `.env`.
- **HMAC-SHA256**: Deferred to V2 when external clients exist.
- **Unauthenticated**: Dev/test only (`LIFEOS_CAPTURE_REQUIRE_AUTH=false`).

## Key Safety Rules

- Binds `127.0.0.1` only (no public exposure, no Tailscale Funnel)
- No processing inside request handler (queue write only)
- No canonical vault writes (buffer vault only)
- No AI invocation in the request path
- Buffer vault and media archive are gitignored (not in repo)
- `.env` file is gitignored, mode 600, never committed

## Phone/Cross-Device Access

To enable cross-device capture (e.g., iPhone Shortcuts), rebind to Tailscale IP:

1. Edit `LIFEOS_CAPTURE_HOST=100.114.67.45` in `.env`
2. Restart service: `systemctl --user restart lifeos-capture-api`
3. Verify binding: `ss -tlnp | grep 8789` should show `100.114.67.45:8789`
4. Phone URL: `http://100.114.67.45:8789/captures`

This exposes the API to all devices on your Tailscale network. The bearer token is your only protection. Keep the token secret.

## Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | None | Health check |
| POST | `/captures` | Bearer | Create capture, append to queue |

## Configuration

See `.env.example` for all environment variables.

## Roadmap

See `40_Services/docs/Capture_API_Roadmap.md` for full specification.

## Client Setup

- [Desktop/curl](40_Services/docs/Desktop_Capture_Setup.md)
- [iOS Shortcuts](40_Services/docs/HTTP_Shortcuts_Setup.md)
- [Browser Bookmarklet](40_Services/docs/Bookmarklet_Capture_Setup.md)
- [n8n Workflow](40_Services/docs/N8N_Capture_API_Example.md)
