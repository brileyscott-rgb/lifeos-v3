# Workflow Governor

## Purpose

Define how LifeOS workflows are selected, approved, logged, and recovered.

## Standard Workflow Pattern

1. Receive trigger.
2. Classify input.
3. Load relevant context.
4. Check role permissions, path permissions, and approval tier.
5. Perform action or request approval.
6. Validate output.
7. Log event.
8. Notify user when required.

## Workflow Types

- capture
- document ingestion
- project creation
- agent task
- maintenance
- migration review

## Permission Checks

Direct mutation allowed only when role, path, approval tier, and logging all allow it. A4 always requires explicit human approval.

## Failure Behavior

- log failure
- preserve inputs
- notify user
- avoid silent retries for risky actions
- never delete source material during failure handling

## AI Mirror Boundary

The AI Mirror may observe and suggest. It must not enforce restrictions, block project creation, shame behavior, impose mandatory life rules, diagnose, or create punitive friction.

## Migration Boundary

Old LifeOS content must not be bulk imported into the trusted vault. Migration deletion is A4 and requires audit trail before action.
