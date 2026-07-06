# n8n Access Model

## Current

- Local-only: `http://localhost:5678`
- Bound to `127.0.0.1` — not accessible from other machines
- Basic authentication enabled by default (see `.env.example`)
- No public webhooks, tunnels, or reverse proxies

## Future Activation Steps

1. Review and set strong basic auth credentials in `.env`
2. Start n8n container
3. Access via browser at `http://localhost:5678`
4. Create workflows in the n8n editor
5. Configure credentials inside n8n (not in workflow JSON exports)

## Prohibited (Until Explicitly Approved)

- Cloudflare Tunnel
- Caddy reverse proxy
- nginx reverse proxy
- Tailscale funnel
- Any other public exposure
- Telegram webhook trigger
- Production webhook URLs
