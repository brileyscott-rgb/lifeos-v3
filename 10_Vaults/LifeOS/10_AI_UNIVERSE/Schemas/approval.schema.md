# Approval Schema

## Required Fields

- `type`
- `status`
- `requested_by`
- `approval_tier`
- `created`
- `requested_action`
- `affected_paths`
- `risk_level`

## Valid Responses

- approve
- reject
- revise
- defer
- archive
- escalate
- commit
- rerun

## A4 Requirement

A4 always requires explicit human approval.

Permanent deletion, migration deletion, credential changes, external publishing, financial actions, and system-level changes are A4.

## Example YAML

```yaml
type: approval_request
status: pending
requested_by: Migration Reviewer
approval_tier: A4
created: 2026-07-04T00:00:00Z
requested_action: delete migrated duplicate after snapshot
affected_paths: []
risk_level: high
```
