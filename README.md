# LifeOS V3 — Control Plane

Current milestone: **Foundation Lock-In**.

Implemented:

- **LifeOS Status API** — read-only endpoints at `40_Services/status_api/` (port 8787).
- **LifeOS Action API** — bounded read-write capture lifecycle at `40_Services/action_api/` (port 8788).
- **n8n Status API test** — manual trigger → HTTP Request, saved inactive.
- **Cloudflare Tunnel scaffold** — templates/runbook at `40_Services/n8n/cloudflared/`, no tunnel active.
- **Telegram Control Plane roadmap** — `docs/superpowers/specs/2026-07-06-lifeos-telegram-control-plane-roadmap.md`.
- **Long-term design doc** — `docs/superpowers/specs/2026-07-06-lifeos-telegram-automation-operator-design.md`.

Not yet active: Cloudflare Tunnel, Telegram webhook, n8n Telegram workflow, capture mode, AI extraction, file processor, retrieval, drift auditor, private dashboard.

Authoritative source: `/home/lifeos/LifeOS_V3_Source_of_Truth.md`
