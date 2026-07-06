# OpenCode Handoff Prompt Template (Future)

Convert an approved job into a paste-ready OpenCode implementation prompt.

## Template

```
You are working inside LifeOS V3 at /home/lifeos.

## Goal

{interpreted_goal}

## Current Context

{current_context}

## Allowed Files

{exact_files_allowed}

## Forbidden Files

{exact_files_forbidden}

## Requirements

1. {requirement_1}
2. {requirement_2}
3. {requirement_3}

## Verification

{verification_commands}

## Output Format

Report:
- Files changed
- Verification results
- Remaining risks
- Rollback instructions

## Important

- Do not modify files outside the allowed list.
- Do not touch .env, secrets, or vault files.
- Do not commit or push.
- Follow existing code conventions.
```

## Usage

1. Generate this prompt from an approved job.
2. Paste into a new OpenCode session.
3. Review results before accepting.
