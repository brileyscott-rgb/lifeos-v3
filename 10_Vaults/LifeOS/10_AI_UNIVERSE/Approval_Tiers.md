# Approval Tiers

## A0 - Read, Observe, Index, Summarize

Read existing accessible content, observe state, index metadata, and summarize without writing trusted content.

## A1 - Write Logs, Summaries, Low-Risk Generated Notes

Write logs, summaries, and low-risk generated notes in designated locations.

## A2 - Create Files in Approved Inboxes/Staging/Generated Output

Create new files in approved inboxes, staging areas, or generated-output folders.

## A3 - Modify Approved Vault or Project Files

Modify approved vault or project files according to role and path permissions.

## A4 - Destructive/System/External/Financial/Credential Actions

Destructive actions, credential changes, external publishing, financial actions, system-level changes, permanent deletion, or migration deletion.

A4 always requires explicit human approval.

## Direct Mutation Rule

Direct mutation allowed only if:

1. agent role permits the action;
2. target path is inside `allowed_paths` and outside `prohibited_paths`;
3. action risk is less than or equal to `approval_ceiling`;
4. required approval has been granted if the action is A3/A4 or otherwise configured as approval-required;
5. the action is logged.

## Approval Request Fields

- requester
- requested action
- affected paths
- tier
- risk
- expected outcome
- event IDs
