# Sync and Backup Policy

## Vault Sync

Use Git first for the vault and control-plane text files.

## Later Capture Sync

Use Syncthing later if multi-device raw capture movement is needed.

## Git Targets

- `10_Vaults/LifeOS/`
- `60_AI_Runtime/`
- `40_Services/compose/`
- `40_Services/config/` excluding secrets
- `50_Event_Log/` schemas and selected text logs

## Do Not Commit

- real secrets
- Docker runtime data
- large raw documents
- Paperless data volumes
- raw old-user imports
- temporary migration working folders

## Backup Direction

Use Git for Markdown/config history. Add restic later for encrypted full backups of documents, service data, event logs, and vault snapshots.
