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

The Status API is now **owned by the unified compose baseline** at `40_Services/compose/lifeos.yaml`. The legacy compose file at `40_Services/status_api/docker-compose.yml` is preserved as reference only.

```bash
# Build and start from unified compose:
docker-compose -f 40_Services/compose/lifeos.yaml build lifeos-status-api
docker-compose -f 40_Services/compose/lifeos.yaml up -d lifeos-status-api
```

The container joins `lifeos_internal` network, binds `127.0.0.1:8787:8787`, and is reachable from the host as `http://localhost:8787/` or from other containers on `lifeos_internal` as `http://lifeos-status-api:8787/`.

## From n8n

Add an HTTP Request node configured as:

- Method: GET
- URL: `http://lifeos-status-api:8787/status`
- Authentication: None (internal network only)

## Security

See `notes/security_boundaries.md`.
