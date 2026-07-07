# Telegram ChatOps Config Scaffold

This directory defines the Telegram ChatOps integration for LifeOS V3.

## Purpose

Telegram is the **first ChatOps front door** for LifeOS. It provides a fast mobile interface for:

- Capturing links, notes, ideas, and project updates from anywhere
- Sending approval/rejection replies for pending captures
- Checking system status

## Design Principle

**Telegram is the front door, not the brain.**

All messages are captured as raw records, queued for review, and only integrated into the vault after human approval. Telegram has no direct write access to projects, knowledge, or system state.

## Current Status

- **Active interim mode: local polling** — the Telegram bot runs as a systemd
  user service (`lifeos-telegram-bot.service`) polling every 3 seconds.
  This is capture-first: `/capture` is validated through Action API.
  Review commands `/view`, `/a`, `/r` live validation is deferred.
- Real bot token is configured in the local `.env` (gitignored)
- Bot process is running as an enabled systemd user service during user session
- No Docker service started (Action API runs outside Docker in current mode)
- No n8n workflow active
- No Telegram webhook registered
- No Cloudflare tunnel required for local polling

## Future Integration

```
Telegram message
-> bot handler (Python or n8n)
-> raw capture file written to 30_Capture/
-> event appended to 50_Event_Log/events.jsonl
-> pending_review queue
-> human approval via /approve or /reject
-> vault integration after approval
```

## Local Bot Handler

The active Telegram capture bot handler is at:

`40_Services/chatops/telegram/telegram_capture_bot.py`

It runs as a local systemd user polling service (`--poll --interval 3`)
during the user session. See the README there for usage and operating mode.

```bash
python3 40_Services/chatops/telegram/telegram_capture_bot.py --help
```

n8n integration is not yet active.

## Safe to Send

- links, quick notes, project updates, ideas, non-sensitive reminders
- approval/rejection commands

## Unsafe to Send

- passwords, SSH keys, API keys, personal financial info
- private identity documents, highly sensitive journal entries
- anything that should not appear in logs
