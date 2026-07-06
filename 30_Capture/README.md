# Capture Intake

All raw inbound captures land here before human review and vault integration.

## Rules

- Every subdirectory has a specific purpose — use the right one.
- No file in this tree is vault content. Nothing here is trusted until approved.
- After approval, files move through `pending_review/` -> `approved/|rejected/` -> `processed/`.
- Filename format: `YYYYMMDD_HHMMSS_source_type_short-title.md` or `.json` or original extension.

## Folder Layout

| Folder | Purpose |
|---|---|
| `inbox/` | Everything that does not match a specific type |
| `links/` | URLs with optional notes |
| `notes/` | Quick text captures |
| `ideas/` | Ideas and proposals |
| `project_updates/` | Project status updates |
| `screenshots/` | Image captures |
| `files/` | Non-image file attachments |
| `pending_review/` | Captures awaiting human approval |
| `approved/` | Human-approved captures ready for vault integration |
| `rejected/` | Human-rejected captures (keep for audit) |
| `processed/` | Captures fully integrated into vault |

## Source Types

- `telegram` — From Telegram ChatOps
- `manual` — Direct filesystem write
- `web` — From future web capture form
- `cli` — From future CLI tool
