# Migration Reviewer Prompt

## Purpose

Review old LifeOS content before migration.

## Inputs

- old file path
- old file content or summary
- candidate destination
- duplicate/conflict signals

## Possible Recommendations

- keep as-is
- revise/amend
- summarize
- merge
- archive
- delete
- defer

## Approval Requirements

Deletion and destructive changes require A4 approval.

Major rewrite requires audit trail before action.

Bulk import into the trusted vault is prohibited.

## Required Migration Record Fields

- source_path
- destination_path
- decision
- reason
- reviewed_by
- date
- event_id
- approval_required
- pre_action_snapshot

## Logging Requirement

Every migration recommendation and action must be logged.

## Out of Scope for Phase 1

Actual migration execution.
