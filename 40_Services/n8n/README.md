# n8n Automation Layer

Local n8n automation server for LifeOS V3.

**Runtime status: n8n container is currently running locally from legacy compose. It is tolerated temporarily as localhost-only drift. Workflow activation status is not verified. No public ingress, WEBHOOK_URL, or Cloudflare is configured. Future unified compose ownership/adoption remains deferred.**

## Quick Start

```bash
# Start n8n (requires local .env with secrets)
./scripts/n8n_start.sh

# Check status
./scripts/n8n_status.sh

# Stop n8n
./scripts/n8n_stop.sh
```

## Access

```text
http://localhost:5678
```

Local-only binding by default. No public webhooks, tunnels, or reverse proxies configured.

## Directory Structure

```text
40_Services/n8n/
├── README.md
├── docker-compose.yml        # Local n8n service definition
├── .env.example              # Example env vars (copy to .env, fill secrets)
├── workflows/
│   ├── README.md
│   ├── exported/             # Future n8n workflow JSON exports
│   └── planned/              # Documented workflow plans (not active)
├── notes/
│   ├── access_model.md
│   ├── security_boundaries.md
│   └── activation_checklist.md
└── scripts/
    ├── n8n_start.sh
    ├── n8n_status.sh
    └── n8n_stop.sh
```

## Security

- No public exposure configured.
- No Telegram webhooks configured.
- No real secrets committed.
- No direct vault write authority.
- No direct git commit authority.

See `notes/security_boundaries.md` for full boundaries.
