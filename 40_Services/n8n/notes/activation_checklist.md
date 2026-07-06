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
- [ ] Test with a simple manual-trigger workflow first
- [ ] Never store credentials in workflow JSON
- [ ] Get explicit user approval per workflow

## Never

- Do not expose n8n publicly
- Do not configure Telegram webhook trigger
- Do not give n8n vault write authority
- Do not give n8n git commit authority
- Do not commit `.env` or any file containing real secrets
