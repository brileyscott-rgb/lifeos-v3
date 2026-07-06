# Capture Routing Rules

## Command-to-Folder Mapping

| Command / Source | Target Folder |
|---|---|
| `/capture <text>` | `30_Capture/notes/` |
| `/link <url> [note]` | `30_Capture/links/` |
| `/idea <text>` | `30_Capture/ideas/` |
| `/project <name>: <update>` | `30_Capture/project_updates/` |
| Photo / file attachment | `30_Capture/screenshots/` or `30_Capture/files/` |
| Unrecognized text / no command | `30_Capture/inbox/` |

## Lifecycle Routing

| Status | Folder |
|---|---|
| All new captures | `30_Capture/pending_review/` (symlink or copy of original) |
| Approved | `30_Capture/approved/` |
| Rejected | `30_Capture/rejected/` |
| Processed into vault | `30_Capture/processed/` |

## Hard Rule

Nothing is written into the main vault folders (`10_Vaults/LifeOS/01_INBOX/`, `02_PROJECTS/`, `04_KNOWLEDGE/`, etc.) without human approval.

The capture intake folders are a write zone. The vault is a human-gated zone.
