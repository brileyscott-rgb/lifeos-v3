# n8n Activation Checklist

## Prerequisites

- [ ] Copy `.env.example` to `.env` and fill in real values
- [ ] Set strong `N8N_BASIC_AUTH_USER` and `N8N_BASIC_AUTH_PASSWORD`
- [ ] Review compose file port bindings
- [ ] Verify `docker` and `docker-compose` are available

## First Start

```bash
cd /home/lifeos/40_Services/n8n
./scripts/n8n_start.sh
```

## Verification

- [ ] `./scripts/n8n_status.sh` shows container running
- [ ] `http://localhost:5678` loads n8n UI
- [ ] Basic auth prompts and accepts credentials
- [ ] No error logs in container output

## Before Activating Workflows

- [ ] Review `notes/security_boundaries.md`
- [ ] Review planned workflow documents in `workflows/planned/`
- [x] Test with a simple manual-trigger workflow first (LifeOS Status API — completed 2026-07-06)
- [ ] Never store credentials in workflow JSON
- [ ] Get explicit user approval per workflow

## First Workflow: LifeOS Status Digest

1. Open n8n UI at `http://localhost:5678`
2. Create a new workflow
3. Add a "Manual Trigger" node
4. Add an "HTTP Request" node
5. Set Method: `GET`
6. Set URL: `http://lifeos-status-api:8787/status` (shared `lifeos_internal` Docker network)
7. Authentication: None (internal Docker network only)
8. Click "Execute Workflow" to run manually
9. Inspect the returned JSON in the n8n output panel
10. If successful, optionally save as `40_Services/n8n/workflows/exported/lifeos_status_digest.json`
11. Get explicit user approval before adding schedule or Telegram notification

## Never

- Do not expose n8n publicly
- Do not configure Telegram webhook trigger
- Do not give n8n vault write authority
- Do not give n8n git commit authority
- Do not commit `.env` or any file containing real secrets

## Cloudflare Tunnel (Phase B1 Prerequisite)

Before Telegram webhook registration:

- [ ] Cloudflare Tunnel setup completed (cloudflared container running)
- [ ] Generic webhook test passed at `https://telegram.<your-domain>/webhook/test`
- [ ] n8n UI is NOT publicly reachable at `https://telegram.<your-domain>/`
- [ ] Status API is NOT publicly reachable via tunnel
- [ ] Action API is NOT publicly reachable via tunnel
- [ ] Catch-all returns 404 for non-webhook paths

## Future Checklist Notes (Do Not Act Yet)

The following items are placeholders for when the Telegram capture workflow is ready:

- [ ] Cloudflare Tunnel setup is a prerequisite for public webhook mode.
- [ ] Use `secret_token` when setting Telegram webhook later.
- [ ] `allowed_updates` starts as `["message"]` — expand later only for callback buttons, photos, voice, documents.
- [ ] No Telegram workflow activation until checklist is satisfied.
- [ ] Do not enable capture mode until the basic command router (start, help, capture, pending, view, approve, reject) works end-to-end.
- [ ] Do not enable AI extraction until raw capture and review flow is stable and tested.
- [ ] Do not enable file creation until a controlled proposal/approval processor is designed, implemented, and security-reviewed.
- [ ] These features require explicit step-by-step approval before activation.
