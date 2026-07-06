# AI Worker Jobs

Job files are created by the `ai_worker.py` CLI and organized by status.

## Directory Structure

```text
jobs/
├── README.md
├── pending/       # Not yet approved
├── approved/      # Approved, waiting to run
├── running/       # Currently executing
├── completed/     # Finished successfully
└── rejected/      # Declined
```

## Current Status

**No active jobs.** The job queue is a dry-run scaffold.
