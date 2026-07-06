# Decision Schema

## Required Fields

- `type`
- `project`
- `status`
- `date`
- `decision_owner`
- `supersedes`

## Valid Statuses

- proposed
- accepted
- rejected
- superseded

## Required Sections

- context
- decision
- alternatives
- consequences

## Example YAML

```yaml
type: decision
project: Example_Project
status: accepted
date: 2026-07-04
decision_owner: user
supersedes: null
```
