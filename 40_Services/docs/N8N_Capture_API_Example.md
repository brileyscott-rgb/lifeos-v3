# n8n Capture API HTTP Request

## Overview

Use n8n HTTP Request nodes to send captures from n8n workflows to the LifeOS Capture API.

## Prerequisites

- Capture API running
- n8n running and accessible
- Both services on the `lifeos_internal` Docker network
- Bearer token configured for internal services

## HTTP Request Node Configuration

### Simple Capture Node

```
Method: POST
URL: http://lifeos-capture-api:8789/captures
Authentication: Generic Credential Type
Generic Auth Type: Header Auth
Header Name: Authorization
Header Value: Bearer {{ $env.CAPTURE_INTERNAL_TOKEN }}
Body Content Type: JSON

Body:
{
  "content": "{{ $json.summary }}",
  "source": "n8n",
  "client": "n8n_workflow",
  "metadata": {
    "workflow_name": "{{ $workflow.name }}",
    "node_name": "Capture API"
  }
}
```

### With Full Fields

```
Body:
{
  "content": "{{ $json.text }}",
  "url": "{{ $json.url }}",
  "title": "{{ $json.title }}",
  "source": "n8n",
  "tags": ["n8n", "automated"],
  "priority": "normal",
  "client": "n8n_workflow",
  "metadata": {
    "workflow_id": "{{ $workflow.id }}",
    "execution_id": "{{ $execution.id }}"
  }
}
```

## Environment Variable

Set `CAPTURE_INTERNAL_TOKEN` in your n8n environment:

```bash
# In n8n .env (gitignored)
CAPTURE_INTERNAL_TOKEN=your-capture-api-bearer-token
```

## Response Handling

The Capture API returns:
```json
{"success": true, "capture_id": "cap_...", "status": "queued", "source": "n8n"}
```

Use n8n's "Respond to Webhook" or "IF" node to check `success` field.

## Warnings

- **Do not activate n8n workflows that write captures automatically** until the capture pipeline and review flow are fully validated.
- **Do not loop captures** — ensure n8n workflows don't create infinite capture-loops.
- **Do not capture secrets** — n8n workflow data may include credentials. Filter sensitive fields before sending.
- **Do not capture raw Telegram messages** — use the existing Telegram bot's path through Action API, not direct n8n capture.
- **The Capture API is queue-only** — captures from n8n go to the same JSONL queue as all other sources.
