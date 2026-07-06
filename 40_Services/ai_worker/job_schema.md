# Job File Schema

Each job is a Markdown file with YAML frontmatter.

## Frontmatter Fields

| Field            | Description                                     | Example                          |
|------------------|-------------------------------------------------|----------------------------------|
| `job_id`         | Unique job identifier                           | `job_20260706_123000_000`        |
| `status`         | Current workflow state                          | `pending`                        |
| `approval_state` | Approval progress                               | `not_requested`                  |
| `risk_level`     | Risk classification (unclassified/low/medium/high) | `unclassified`                |
| `created_at`     | ISO 8601 timestamp of creation                  | `2026-07-06T12:30:00Z`           |
| `source`         | Origin of the job request                       | `cli`                            |

## Status Lifecycle

```
pending → approved → running → completed
pending → rejected
running → completed
running → rejected
```

## File Location

Jobs are stored in subdirectories matching their `status`:

- `jobs/pending/` — not yet approved
- `jobs/approved/` — approved, waiting to run
- `jobs/running/` — currently executing
- `jobs/completed/` — finished
- `jobs/rejected/` — declined
