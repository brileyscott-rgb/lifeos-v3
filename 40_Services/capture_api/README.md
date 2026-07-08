# Capture API

Tailscale-only HTTP API for LifeOS capture intake.

**Status:** architecture/scaffold — not yet implemented.

## Purpose

Single entry point for all capture sources: Telegram, HTTP Shortcuts, bookmarklets, desktop scripts, n8n workflows, and future MCP tools.

## Architecture

```
Capture Source → Capture API → Append-Only Queue → Dockerized Processors → Buffer Vault → Agents → Review → Approval → Canonical Import
```

## Key Safety Rules

- Tailscale-only listener (no public exposure)
- No processing inside request handler (queue write only)
- No vault writes (buffer vault and canonical vault)
- No AI invocation in the request path
- HMAC-signed authentication for external clients
- Bearer token for internal services

## Roadmap

See `40_Services/docs/Capture_API_Roadmap.md` for full specification.
