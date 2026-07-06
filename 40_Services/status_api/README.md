# LifeOS Status API

Read-only HTTP API exposing LifeOS health and status for n8n workflows.

## Architecture

```
n8n → HTTP Request → lifeos-status-api:8787 → returns JSON
```

Replaces the unsafe Execute Command pattern. n8n no longer needs direct filesystem mounts or shell access.

## Endpoints

### GET /health

```json
{"service": "lifeos-status-api", "status": "ok", "mode": "read_only"}
```

### GET /status

Returns capture queue counts, event log state, and path status.

## Docker

```bash
docker-compose up -d
```

The container joins `lifeos_internal` network and is reachable as `http://lifeos-status-api:8787/`.

## From n8n

Add an HTTP Request node configured as:

- Method: GET
- URL: `http://lifeos-status-api:8787/status`
- Authentication: None (internal network only)

## Security

See `notes/security_boundaries.md`.
