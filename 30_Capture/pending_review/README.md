# Pending Review

## What goes here

Copies or symlinks of all captures awaiting human approval. This is the approval queue.

## What should not go here

Already-approved or processed captures.

## Filename format

Same as the original capture file.

## Processing

- `/approve <capture_id>` moves the file to `../approved/`
- `/reject <capture_id>` moves the file to `../rejected/`
- After vault integration, the approved file moves to `../processed/`

## Frontmatter

Each file should include approval frontmatter (see `40_Services/config/telegram/approval_format.md`).
