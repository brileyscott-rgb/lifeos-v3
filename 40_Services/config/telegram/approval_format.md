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

## Approval Commands

```
/approve cap_YYYYMMDD_HHMMSS_source_type_short-title
/reject cap_YYYYMMDD_HHMMSS_source_type_short-title
```

On approval, the file should be moved from `pending_review/` to `approved/`.
On rejection, the file should be moved from `pending_review/` to `rejected/`.
After vault integration, the file should be moved to `processed/`.
