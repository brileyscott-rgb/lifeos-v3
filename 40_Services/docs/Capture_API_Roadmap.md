# Capture API Roadmap

Status: **V1 implemented (2026-07-08)** — Queue-only API scaffold complete. See `40_Services/capture_api/app.py`.
Created: 2026-07-08
Updated: 2026-07-08 (V1 implementation complete)
Purpose: define the Tailscale-only Capture API that serves as the single entry point for all capture sources — Telegram, HTTP Shortcuts, bookmarklets, desktop scripts, n8n workflows, and future MCP tools.

## Overview

The Capture API is a private HTTP API accessible only on the Tailscale network interface. It accepts captures from any authorized source, writes them to the append-only raw capture queue, and returns a receipt. No processing, AI invocation, vault writes, or media downloads happen inside the request handler.

## Network Model

```
Internet → [PUBLIC: BLOCKED]
             │
    Tailscale Network (100.x.x.x)
             │
    Capture API (Tailscale IP:8789)
             │
    lifeos_internal Docker Network
             │
    Queue (00_Raw/captures.jsonl)
```

- **Listener:** Tailscale interface only (e.g., `100.xxx.xxx.xxx:8789`)
- **No public port mapping:** Never exposed via port forwarding, Cloudflare tunnel, or reverse proxy to the public internet
- **Internal fallback:** Also listens on `127.0.0.1:8789` for local services (Telegram bot, n8n) on the same host
- **Docker:** Runs on `lifeos_internal` network with Tailscale IP binding

## Input Channels

| Channel | Auth Method | Transport | Status |
|---|---|---|---|
| HTTP Shortcuts (iOS/Android) | HMAC-signed POST with pre-shared key | HTTPS over Tailscale | V1 Roadmap |
| Bookmarklet (desktop browser) | HMAC-signed POST with pre-shared key | HTTPS over Tailscale | V1 Roadmap |
| Desktop scripts (CLI, Alfred, Raycast) | HMAC-signed POST with pre-shared key | HTTP over Tailscale or localhost | V1 Roadmap |
| Telegram bot (migration path) | Internal network token | HTTP over localhost (same host) | V2 Roadmap |
| n8n workflows | Internal network token | HTTP over Docker network | V1 Roadmap |
| MCP tools (future) | Scoped MCP token | HTTP over Docker network | V3 Roadmap |

## Authentication Model

### HMAC-Signed Requests (External Clients)

HTTP Shortcuts, bookmarklets, and desktop scripts authenticate via HMAC-SHA256:

```
Authorization: HMAC-SHA256 {key_id}:{signature}
X-Capture-Timestamp: {unix_timestamp}
```

The signature is computed over:
```
{method}\n{path}\n{timestamp}\n{body_sha256}
```

- `key_id` identifies which pre-shared key was used
- Pre-shared keys are stored in the Capture API's environment (not in vault, not in Git)
- Timestamps must be within ±5 minutes of server time (replay protection)
- Each key may have different permissions (read, write, admin)

### Internal Network Token (Same-Host Services)

Telegram bot and n8n use a simpler bearer token:

```
Authorization: Bearer {internal_token}
```

- Single shared token for internal services on `lifeos_internal` or `localhost`
- Token stored in Capture API environment, not in source code
- Internal services are trusted to send valid capture data (they are already authenticated by their own mechanisms)

### Scoped MCP Tokens (Future)

MCP tools use scoped tokens:

```
Authorization: MCP {mcp_token}
```

- Each MCP token has a scope: `read`, `write`, `search`, `status`
- Most MCP tools are `read` or `search` only
- `write` scope requires explicit approval

## Request Schema

### POST /captures

Create a new capture.

**Headers:**
```
Content-Type: application/json
Authorization: HMAC-SHA256 {key_id}:{signature}
X-Capture-Timestamp: 1720444800
X-Idempotency-Key: {optional unique key}
```

**Body:**
```json
{
  "text": "Check out this article about container security: https://example.com/article",
  "source": "http_shortcuts",
  "source_detail": "iOS Shortcuts",
  "attachments": [],
  "metadata": {
    "client": "ios-shortcuts-v1",
    "location": null,
    "tags": ["containers", "security"]
  },
  "priority": "normal"
}
```

**Fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `text` | string | Yes | Capture text content (max 20000 chars) |
| `source` | string | Yes | Source channel: `telegram`, `http_shortcuts`, `bookmarklet`, `desktop_script`, `n8n`, `mcp` |
| `source_detail` | string | No | Human-readable source detail (e.g., "iOS Shortcuts", "Chrome Bookmarklet") |
| `attachments` | array | No | Array of attachment references (future: base64-encoded files, URLs to download) |
| `metadata` | object | No | Arbitrary key-value metadata (max 50 keys) |
| `priority` | string | No | `low`, `normal`, `high` (default: `normal`) |
| `callback_url` | string | No | URL to notify when processing is complete (future: n8n webhook) |

**Attachment object (future):**
```json
{
  "type": "url",
  "url": "https://example.com/image.png",
  "filename": "architecture-diagram.png",
  "mime_type": "image/png"
}
```

## Response Schema

### 201 Created

```json
{
  "status": "created",
  "capture_id": "cap_20260708_123456_abc123_container-security",
  "queue_position": 42,
  "receipt": {
    "received_at": "2026-07-08T12:34:00Z",
    "idempotency_key": null,
    "estimated_processing_time": "~30 seconds"
  }
}
```

### 202 Accepted (Large/Media Capture)

```json
{
  "status": "accepted",
  "capture_id": "cap_20260708_123456_def789_video-capture",
  "queue_position": 43,
  "receipt": {
    "received_at": "2026-07-08T12:34:05Z",
    "idempotency_key": null,
    "estimated_processing_time": "~5 minutes (media download + transcription)"
  }
}
```

### 400 Bad Request

```json
{
  "status": "error",
  "error": "bad_request",
  "message": "Missing required field: text",
  "capture_id": null
}
```

### 401 Unauthorized

```json
{
  "status": "error",
  "error": "unauthorized",
  "message": "Invalid or missing authentication",
  "capture_id": null
}
```

### 409 Conflict (Duplicate)

```json
{
  "status": "error",
  "error": "duplicate",
  "message": "Capture with idempotency_key 'abc123' already exists",
  "existing_capture_id": "cap_20260708_123400_xyz789",
  "capture_id": null
}
```

### 429 Rate Limited

```json
{
  "status": "error",
  "error": "rate_limited",
  "message": "Too many requests. Retry after 30 seconds.",
  "retry_after": 30,
  "capture_id": null
}
```

### 500 Internal Error

```json
{
  "status": "error",
  "error": "internal_error",
  "message": "A generic error message that does not leak internal details",
  "capture_id": null
}
```

## Queue Write Behavior

1. Validate authentication
2. Validate request schema (required fields, size limits)
3. Check rate limit for the auth key
4. Check idempotency key (if provided) — return 409 if duplicate
5. Generate capture ID
6. Append capture record to `00_Raw/captures.jsonl` (atomic append)
7. Log capture event to event log
8. Return 201 with capture ID and receipt

**No processing inside the request handler.** The handler writes to the queue and returns. Processors pull from the queue independently.

## Rate Limiting

- **Per-key rate limit:** 60 requests per minute
- **Global rate limit:** 300 requests per minute
- **Burst allowance:** 10 requests
- **Rate limit headers:** `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- **429 response** includes `retry_after` in seconds

## Logging

Every capture request is logged to the event log:
```json
{
  "event_id": "evt_20260708T123400Z_capture_api_received",
  "event_type": "capture_api.received",
  "timestamp": "2026-07-08T12:34:00Z",
  "capture_id": "cap_20260708_123456_abc123",
  "source": "http_shortcuts",
  "text_length": 85,
  "has_attachments": false,
  "auth_key_id": "ios_shortcuts_key",
  "client_ip": "100.xxx.xxx.xxx"
}
```

No raw capture text is logged to the event log (privacy). Only metadata about the request.

## Failure Handling

| Failure | Response | Behavior |
|---|---|---|
| Invalid auth | 401 | Log attempt, no capture created |
| Missing required field | 400 | Return field name, no capture created |
| Text too long | 400 | Return max length, no capture created |
| Invalid JSON body | 400 | Return parse error, no capture created |
| Rate limited | 429 | Return retry-after, no capture created |
| Queue write fails | 500 | Log error, return generic error, do NOT lose data (buffer in memory, retry) |
| Event log write fails | 500 | Capture is created but event log entry may be missing (best-effort) |
| Disk full | 503 | Return service unavailable, alert operator |

## Secret Handling

- Pre-shared HMAC keys stored in Capture API environment variables (never in source code, never in Git)
- Internal bearer token stored in Capture API environment
- Keys are rotated by updating environment and restarting the service
- No keys or secrets ever appear in responses, logs, or event log entries
- `.env.example` shows format but contains no real values

## Example Requests

### curl (HTTP Shortcuts, Bookmarklet, Desktop)

```bash
TIMESTAMP=$(date +%s)
BODY='{"text":"Interesting article: https://example.com/article","source":"desktop_script","source_detail":"bash script"}'
BODY_SHA256=$(echo -n "$BODY" | sha256sum | cut -d' ' -f1)
SIGNING_STRING="POST\n/captures\n${TIMESTAMP}\n${BODY_SHA256}"
SIGNATURE=$(echo -n "$SIGNING_STRING" | openssl dgst -sha256 -hmac "your-pre-shared-key" | cut -d' ' -f2)

curl -X POST http://100.xxx.xxx.xxx:8789/captures \
  -H "Content-Type: application/json" \
  -H "Authorization: HMAC-SHA256 desktop_key:${SIGNATURE}" \
  -H "X-Capture-Timestamp: ${TIMESTAMP}" \
  -d "$BODY"
```

### HTTP Shortcuts (iOS Shortcuts App)

```
Method: POST
URL: http://100.xxx.xxx.xxx:8789/captures
Headers:
  Content-Type: application/json
  Authorization: HMAC-SHA256 ios_shortcuts_key:{signature}
  X-Capture-Timestamp: {timestamp}
Body (JSON):
{
  "text": "{Shortcut Input}",
  "source": "http_shortcuts",
  "source_detail": "iOS Shortcuts"
}
```

The signature is computed in a separate Shortcut step using the pre-shared key stored in the Shortcut (not synced to iCloud in plaintext).

### Bookmarklet (Browser JavaScript)

```javascript
javascript:(function(){
  var d=document,t=d.title,u=d.URL,b=JSON.stringify({text:t+' '+u,source:'bookmarklet',source_detail:'Chrome Bookmarklet'});
  var ts=Math.floor(Date.now()/1000);
  var sha=function(s){/* SHA-256 implementation */};
  var sig=hmac_sha256('POST\n/captures\n'+ts+'\n'+sha(b),'your-pre-shared-key');
  fetch('http://100.xxx.xxx.xxx:8789/captures',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'HMAC-SHA256 bookmarklet_key:'+sig,'X-Capture-Timestamp':''+ts},body:b})
    .then(r=>r.json()).then(j=>alert('Capture created: '+j.capture_id));
})();
```

**Note:** Bookmarklet HMAC signing is complex in pure JavaScript. Simplified version may use bearer token auth for bookmarklets (stored in the bookmarklet code itself — acceptable risk since the token is only valid on Tailscale network).

### n8n HTTP Request Node

```
Method: POST
URL: http://capture-api:8789/captures
Headers:
  Content-Type: application/json
  Authorization: Bearer {{INTERNAL_CAPTURE_TOKEN}}
Body (JSON):
{
  "text": "{{$json.capture_text}}",
  "source": "n8n",
  "source_detail": "{{workflow_name}}",
  "metadata": {
    "workflow_id": "{{$workflow.id}}",
    "execution_id": "{{$execution.id}}"
  }
}
```

## Future MCP Input

MCP tools may call the Capture API to create captures programmatically:

```json
{
  "text": "New repository discovered: https://github.com/example/project",
  "source": "mcp",
  "source_detail": "github-discovery-mcp",
  "metadata": {
    "mcp_tool": "discover_repos",
    "trigger": "automated_scan"
  },
  "priority": "low"
}
```

MCP tools with `write` scope may create captures. MCP tools without `write` scope are read-only.

## Health and Status

### GET /health

```json
{
  "status": "ok",
  "service": "lifeos-capture-api",
  "version": "1.0.0",
  "uptime": 3600,
  "queue_depth": 42,
  "queue_processing": 3,
  "queue_failed": 1
}
```

### GET /status/{capture_id}

```json
{
  "capture_id": "cap_20260708_123456_abc123",
  "status": "processing",
  "stage": "article_extraction",
  "created_at": "2026-07-08T12:34:00Z",
  "updated_at": "2026-07-08T12:34:30Z",
  "estimated_completion": "2026-07-08T12:35:00Z"
}
```

## Roadmap

| Phase | Deliverable | Timeline |
|---|---|---|
| V1 | API scaffold, auth, queue write, health endpoints, curl example | After architecture approval |
| V1 | HTTP Shortcuts integration (iOS + Android) | After V1 API |
| V1 | Bookmarklet integration (Chrome + Firefox) | After V1 API |
| V1 | n8n HTTP Request workflow integration | After V1 API |
| V2 | Telegram migration (from direct Action API call to Capture API) | After queue/processors stable |
| V2 | Attachment support (file upload, media URLs) | After media_downloader |
| V2 | Callback/webhook notification on processing complete | After review_packet_builder |
| V3 | MCP tool integration with scoped tokens | After MCP security policy implementation |
| V3 | Bulk capture import (reading list, bookmark export) | After duplicate_detector |
| V3 | Capture analytics and reporting | After observability foundation |
