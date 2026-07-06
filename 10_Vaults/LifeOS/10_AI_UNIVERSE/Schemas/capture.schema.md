# Capture Schema

## Required Fields

- `type`
- `status`
- `source_type`
- `captured_at`
- `classification`
- `recommended_destination`
- `approval_required`

## Optional Fields

- `source_url`
- `source_path`
- `summary`
- `tags`
- `event_ids`

## Valid Statuses

- unprocessed
- classified
- pending_approval
- routed
- archived
- error

## Example YAML

```yaml
type: capture
status: unprocessed
source_type: link
captured_at: 2026-07-04T00:00:00Z
classification: pending
recommended_destination: pending
approval_required: true
```
