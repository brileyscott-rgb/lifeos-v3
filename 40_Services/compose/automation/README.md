# Automation Compose Scaffold

> **Note:** A unified compose file now exists at `40_Services/compose/lifeos.yaml`. This directory's compose file is preserved for reference and backward compatibility.

This directory contains the inert n8n compose scaffold for LifeOS V3 automation.

Status: scaffold only. Do not start services yet.

Forbidden until explicitly approved:

- `docker compose up`
- `docker compose start`
- `docker compose restart`
- `docker compose run`
- `docker compose build`
- `docker compose pull`
- `docker compose create`
- `docker pull`
- `docker run`
- `docker build`

Real secrets must stay outside Git under `/home/lifeos/40_Services/secrets/` and must not be copied into the vault, event log, prompts, examples, or commits.

The compose file uses the `manual-start-disabled` profile so this scaffold remains reviewable without implying service activation.

Before any future activation, pin `n8nio/n8n` to a reviewed version or digest and create `/home/lifeos/40_Services/secrets/n8n.env` from reviewed placeholder values. Do not copy real secret values into this directory.
