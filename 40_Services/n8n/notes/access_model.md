# n8n Access Model

## Current

- Local-only: `http://localhost:5678`
- Bound to `127.0.0.1` — not accessible from other machines
- Basic authentication enabled by default (see `.env.example`)
- No public webhooks, tunnels, or reverse proxies

## Cloudflare Tunnel Scaffold (Created, Not Active)

A Cloudflare Tunnel scaffold exists at `40_Services/n8n/cloudflared/`:

- `config.example.yml` — template with placeholder values
- `docker-compose.cloudflared.example.yml` — safe compose template
- `README.md` — setup outline, webhook test plan, rollback steps

**The tunnel is NOT active.** The scaffold is a ready-to-use template for when the user provides Cloudflare domain and tunnel credentials. Activation requires explicit step-by-step approval.

## Future Activation Steps

1. Review and set strong basic auth credentials in `.env`
2. Start n8n container
3. Access via browser at `http://localhost:5678`
4. Create workflows in the n8n editor
5. Configure credentials inside n8n (not in workflow JSON exports)
6. (Future) Activate Cloudflare Tunnel with real credentials after explicit approval
7. (Future) Register Telegram webhook after tunnel is verified

## Prohibited (Until Explicitly Approved)

- Active Cloudflare Tunnel (scaffold allowed, tunnel start requires approval)
- Caddy reverse proxy
- nginx reverse proxy
- Tailscale funnel
- Any other public exposure
- Telegram webhook trigger
- Production webhook URLs
