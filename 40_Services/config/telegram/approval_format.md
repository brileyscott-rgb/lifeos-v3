# Capture Approval Format

## Status Lifecycle

```
received -> pending_review -> approved -> processed
                            -> rejected (terminal)
                            -> failed (terminal)
```

## Pending Review Frontmatter

Every capture file moved to `pending_review` should include this frontmatter:

```yaml
---
capture_id: cap_YYYYMMDD_HHMMSS_source_type_short-title
source: telegram
capture_type: link|note|idea|project_update|file|screenshot|inbox
status: pending_review
approval_required: true
created_at: 2026-07-06T14:30:00-05:00
processed_at:
target_domain:
target_project:
event_id:
---
```

## Capture Body Sections

```markdown
# Capture Summary

## Raw Message

The original Telegram message text.

## Parsed Intent

What the system interpreted the message to mean.

## Suggested Routing

Which vault folder or project this should go to if approved.

## Approval Decision

Approved / Rejected by <actor> at <timestamp>.

## Processing Notes

What was done after approval (e.g., file moved, event logged, note created).
```

## Review State Definitions

- **approved**: The capture has been reviewed and approved for later processing.
  This is a staging state. Approval does **not** mean automatic vault
  integration. It means the capture is queued for the next pipeline phase.
- **rejected**: The capture has been reviewed and rejected. This is a terminal
  state. The file is preserved in `rejected/` for audit but will not proceed
  to vault integration.
- **processed**: Reserved for automated vault integration (future feature).
  When an approved capture is picked up by the pipeline and written into
  `10_Vaults/LifeOS/`, the file moves from `approved/` to `processed/`.

## Approval Commands

```
/list_pending
/approve cap_YYYYMMDD_HHMMSS_source_type_short-title
/reject cap_YYYYMMDD_HHMMSS_source_type_short-title
```

On approval, the file should be moved from `pending_review/` to `approved/`
with frontmatter `status` updated to `approved` and `processed_at` set.
On rejection, the file should be moved from `pending_review/` to `rejected/`
with frontmatter `status` updated to `rejected` and `processed_at` set.
After vault integration, the file should be moved to `processed/`.
