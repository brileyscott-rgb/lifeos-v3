# Planner Prompt (Future)

Convert a user goal into an implementation plan.

## Input

A natural-language goal or feature request.

## Output

```yaml
interpreted_goal: "summary of what the user wants"
files_likely_affected:
  - path/to/file (reason)
risks:
  - description of risk
  - severity: low/medium/high
test_plan:
  - test command or check
approval_tier: A0/A1/A2/A3/A4
do_not_touch:
  - .env
  - 10_Vaults/
  - 40_Services/secrets/
```

## Evaluation Criteria

- Is the goal clear and unambiguous?
- Are the affected files within scope?
- Are there any safety concerns?
- Is the test plan sufficient?
- What approval tier is required?
