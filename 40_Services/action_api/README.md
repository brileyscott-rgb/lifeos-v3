# LifeOS Action API

Read-write HTTP API for LifeOS capture operations. Designed to be called by n8n workflows for Telegram capture bot operations.

## Architecture

```
n8n → HTTP Request → lifeos-action-api:8788 → capture create/approve/reject
```

## Endpoints

### GET /health

Health check.

```json
{"service": "lifeos-action-api", "status": "ok", "mode": "read_write"}
```

### GET /captures/pending

List pending review captures with 1-based indexes, sorted oldest-first.

### GET /captures/pending/<index>

Get a specific pending capture by index (numeric) or `latest`.

### GET /captures/<id>

Get a specific pending capture by capture_id.

### GET /captures/approved

List approved capture files.

### POST /captures

Create a new capture. Accepts JSON body: `{"text": "..."}`. Writes a markdown capture file to `pending_review/` and appends an event.

### POST /captures/<id>/approve

Move a pending capture to `approved/` and update frontmatter.

### POST /captures/<id>/reject

Move a pending capture to `rejected/` and update frontmatter.

## Docker

Added to `40_Services/n8n/docker-compose.yml` as `lifeos-action-api`.

## Security

See `notes/security_boundaries.md`.
