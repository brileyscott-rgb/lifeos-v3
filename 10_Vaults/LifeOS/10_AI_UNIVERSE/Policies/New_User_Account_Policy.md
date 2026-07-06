# New User Account Policy

## Recommended Account

`lifeos`

## Purpose

Create a clean, dedicated LifeOS V3 environment with hard separation from old account drift.

## Final Root Layout

```text
/home/lifeos/
├── 00_Inbox/
├── 10_Vaults/
├── 20_Workspaces/
├── 30_Documents/
├── 40_Services/
├── 50_Event_Log/
├── 60_AI_Runtime/
├── 70_Backups/
└── 99_Archive/
```

## Groups

Add `lifeos` to these groups when available:

- `docker`
- `video`
- `render`

## Migration Rule

Do not mount or directly work from the old account's vault.

Use this flow:

```text
old account files
→ /home/lifeos/99_Archive/old-user-imports/
→ inventory
→ classify
→ review
→ keep/revise/summarize/merge/archive/delete/defer
→ approved result into new vault
```

## Setup Script

Run from the current account when ready:

```bash
sudo bash /home/lifeos/00_SETUP/create_lifeos_user_and_install_phase1.sh
```
