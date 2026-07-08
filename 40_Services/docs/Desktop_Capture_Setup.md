# Capture API Client Setup

## Quick Start: curl

### Using the Tailscale URL (recommended)

The Capture API is bound to the Tailscale network. Use the MagicDNS name:

```bash
export CAPTURE_URL="http://lenovog3-mint.tail7687a5.ts.net:8789"
export CAPTURE_TOKEN="your-token-here"

curl -s $CAPTURE_URL/health
curl -s -X POST $CAPTURE_URL/captures \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CAPTURE_TOKEN" \
  -d '{"content": "Remember to configure Docker monitoring", "source": "desktop"}'
```

### Loading from .env (safest)

```bash
set -a && . /home/lifeos/40_Services/capture_api/.env && set +a

CAPTURE_URL="http://${LIFEOS_CAPTURE_HOST}:${LIFEOS_CAPTURE_PORT}"

curl -s $CAPTURE_URL/health
curl -s -X POST $CAPTURE_URL/captures \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${LIFEOS_CAPTURE_BEARER_TOKEN}" \
  -d '{"content": "Add queue monitoring to Uptime Kuma", "source": "desktop", "tags": ["monitoring", "devops"]}'
```

### Local-only (dev/test, `LIFEOS_CAPTURE_REQUIRE_AUTH=false`)

```bash
# Only works if service is bound to 127.0.0.1 (currently bound to Tailscale)
curl -s http://127.0.0.1:8789/health
```

### URL Capture

```bash
curl -s -X POST http://127.0.0.1:8789/captures \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $CAPTURE_TOKEN" \
  -d '{"url": "https://example.com/interesting-article", "title": "Interesting Article", "source": "desktop"}'
```

## Response Examples

### Health Check
```json
{"status": "ok", "service": "lifeos_capture_api", "mode": "queue_only"}
```

### Successful Capture
```json
{"success": true, "capture_id": "cap_20260108_120000_a1b2c3d4", "status": "queued", "source": "desktop"}
```

### Validation Error
```json
{"success": false, "error": "validation_error", "detail": "At least one of content, text, or url is required"}
```

### Auth Error
```json
{"success": false, "error": "unauthorized", "detail": "Missing or invalid authentication"}
```

## Warnings

- **NEVER expose the Capture API publicly.** It is designed for localhost/Tailscale only.
- **NEVER commit bearer tokens to Git.** Use environment variables or `.env` files (gitignored).
- **The Capture API is queue-only.** It stores captures in JSONL format. No processing happens at intake.
- **Do not send large files through the API.** Max payload is 65536 bytes by default.
