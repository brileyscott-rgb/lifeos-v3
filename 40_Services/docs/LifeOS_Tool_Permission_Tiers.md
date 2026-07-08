# LifeOS Tool Permission Tiers

Document of permission levels for all LifeOS tools, scripts, and services.

## Tier Definitions

| Tier | Name | Description | Requires Manual Approval | Example |
|------|------|-------------|-------------------------|---------|
| **A0** | Public Read-Only Status | Read publicly safe system status. No auth. | No | Status API /health |
| **A1** | Private Read-Only | Read internal system state. Token or local auth. | No | lifeos_services.py, observability |
| **A2** | Buffer Write | Write to external buffer vault only. No canonical vault. | No | Capture API POST, queue_to_markdown.py |
| **A3** | Staging / Review Write | Write to review packets, agent workspace. Still buffer-only. | Yes (implicit via review) | review_packet_builder.py |
| **A4** | Repository Write | Git commit, push, file creation in tracked paths. | **Yes — every mutation** | git commit, n8n workflows |
| **A5** | System Mutation | Docker start/stop, systemd enable/disable, iptables, package install. | **Yes — admin approval** | Docker control, systemd control |

## Boundary Rules

- **A0-A3** are buffer vault only. No canonical vault writes.
- **A4** requires explicit user prompt for every mutation.
- **A5** requires operator approval and audit logging.
- No tier may expose services publicly, bind to `0.0.0.0`, or mount canonical vault.
- Secrets and `.env` files are never readable by any tier.
