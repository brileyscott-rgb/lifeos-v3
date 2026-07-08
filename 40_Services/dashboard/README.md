# LifeOS Dashboard Stack V1

## Purpose

Local-only dashboard for LifeOS V3 service visibility. Provides a single landing page
(Homepage), uptime monitoring (Uptime Kuma), and container log viewing (Dozzle).

All services bind `127.0.0.1` only. No public exposure.

## Services

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| Homepage | `ghcr.io/gethomepage/homepage:latest` | `127.0.0.1:3000` | Dashboard landing page |
| Uptime Kuma | `louislam/uptime-kuma:latest` | `127.0.0.1:3001` | Service health checks and alerts |
| Dozzle | `amir20/dozzle:latest` | `127.0.0.1:3002` | Read-only container log viewer |

## Start / Stop / Restart

Uses `docker compose` (plugin). Also compatible with Docker Compose V1 (`docker-compose`).

```bash
# Start
docker-compose -f /home/lifeos/40_Services/dashboard/docker-compose.yml up -d

# Stop
docker-compose -f /home/lifeos/40_Services/dashboard/docker-compose.yml down

# Restart
docker-compose -f /home/lifeos/40_Services/dashboard/docker-compose.yml restart

# View status
docker-compose -f /home/lifeos/40_Services/dashboard/docker-compose.yml ps

# View logs
docker-compose -f /home/lifeos/40_Services/dashboard/docker-compose.yml logs -f
```

## Volumes

| Volume | Service | Purpose |
|--------|---------|---------|
| `homepage_icons` | Homepage | Cached service icons |
| `homepage_data` | Homepage | Custom JS overrides |
| `uptime_kuma_data` | Uptime Kuma | Monitor definitions, status history, alert config |

Named Docker volumes — persistent across container restarts. No host path mounts.

## Security Notes

### Docker Socket Warning (Dozzle)

Dozzle mounts `/var/run/docker.sock` as **read-only** (`:ro`). This provides
container log visibility but is a controlled risk:

- **Allowed:** Reading container logs and metadata via Dozzle web UI.
- **Not allowed:** No container start/stop/restart/prune or any mutation through Dozzle.
- **Mitigation:** `security_opt: no-new-privileges:true`. Read-only socket mount.
- **Audit:** Dozzle access is localhost-only. Container logs may contain sensitive
  information — review logs before exposing Dozzle to any remote access path.

### No Docker Socket for Homepage

Homepage does not receive Docker socket access in V1. Container status is displayed
through inline state in `services.yaml`, not Docker API queries. If Docker socket
access is needed later for `server: my-docker` fields, add `:ro` with documented
justification.

### Mount Policy

- No `/home/lifeos` host directory mounts.
- No vault mount (`10_Vaults/`).
- No `~/.ssh` mount.
- No `~/.config` mount.
- No real `.env` files.
- No secret volumes.

### Network Policy

- All ports bound to `127.0.0.1` only.
- No `0.0.0.0` or public-facing bindings.
- No Cloudflare tunnel, no Tailscale funnel, no reverse proxy.
- Dashboard access requires SSH tunneling or local browser.

## How to Add Services

1. Add a new service definition to `docker-compose.yml`.
2. Add a corresponding entry in `config/homepage/services.yaml`.
3. Run `docker-compose -f ... up -d` to pull and start.
4. Verify localhost binding with `curl -I http://127.0.0.1:<port>`.

New services must follow the same security boundaries:
- Bind `127.0.0.1` unless documented and approved.
- No Docker socket unless documented and read-only.
- No vault, home, SSH, config, or secret mounts.
- Named volumes for persistence, not host path bind mounts.

## What Not to Expose

- Do not add `ports: "0.0.0.0:..."` or omit the bind address.
- Do not add Cloudflare tunnel or reverse proxy config without approval.
- Do not add live Telegram bot token or any real secret to config.
- Do not add auto-remediation or auto-restart triggers.
- Do not expose admin UIs to the network.

## Future Integration

This dashboard stack is designed to integrate with future LifeOS services:

- **Uptime Kuma monitors:** Defined in `40_Services/docs/Uptime_Kuma_Monitor_Plan.md`. Configure Core (Status API, Action API, n8n, Homepage, Uptime Kuma self, Dozzle) and Infrastructure (Status Full, ChromaDB) monitors manually through the Uptime Kuma web UI at `http://127.0.0.1:3001`. Monitor configuration status is not yet verified — assume monitors have not been created until confirmed.
- **MCP/mcpo:** Uptime Kuma will monitor MCP server health. Homepage will link to MCP tools once active.
- **OpenHands:** Homepage will link to OpenHands sandbox once active. Container visible in Dozzle.
- **n8n:** Uptime Kuma monitor for n8n is planned per `Uptime_Kuma_Monitor_Plan.md`. n8n workflows may push alerts to Uptime Kuma push monitor once configured.
- **Qdrant / Ollama / Open WebUI:** Planned sections in Homepage ready for activation. Uptime Kuma monitors planned.
