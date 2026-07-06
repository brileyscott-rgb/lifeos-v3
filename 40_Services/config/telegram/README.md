# Telegram ChatOps Config Scaffold

This directory defines the planned Telegram ChatOps integration for LifeOS V3.

## Purpose

Telegram is the **first ChatOps front door** for LifeOS. It provides a fast mobile interface for:

- Capturing links, notes, ideas, and project updates from anywhere
- Sending approval/rejection replies for pending captures
- Checking system status

## Design Principle

**Telegram is the front door, not the brain.**

All messages are captured as raw records, queued for review, and only integrated into the vault after human approval. Telegram has no direct write access to projects, knowledge, or system state.

## Current Status

- Config scaffold only
- No real bot token configured
- No bot process running
- No Docker service started
- No n8n workflow active

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

A minimal local Telegram capture bot test handler is available at:

`40_Services/chatops/telegram/telegram_capture_bot.py`

See the README there for usage:

```bash
python3 40_Services/chatops/telegram/telegram_capture_bot.py --help
```

This is a manual foreground test tool, not a daemon or service. n8n integration
is not yet active.

## Safe to Send

- links, quick notes, project updates, ideas, non-sensitive reminders
- approval/rejection commands

## Unsafe to Send

- passwords, SSH keys, API keys, personal financial info
- private identity documents, highly sensitive journal entries
- anything that should not appear in logs
