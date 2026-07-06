# Job Queue SQLite Schema (Future)

When the job queue outgrows flat Markdown files, migrate to SQLite.

## Example Schema

```sql
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    goal TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    approval_state TEXT NOT NULL DEFAULT 'not_requested',
    risk_level TEXT DEFAULT 'unclassified',
    created_at TEXT NOT NULL,
    updated_at TEXT,
    source TEXT DEFAULT 'cli',
    job_file_path TEXT,
    result_summary TEXT
);

CREATE TABLE job_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    log_level TEXT NOT NULL DEFAULT 'info',
    message TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);
```

## Current Status

Not active. Job queue uses flat Markdown files in `jobs/`.
