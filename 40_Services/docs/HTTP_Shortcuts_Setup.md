# HTTP Shortcuts Capture Setup (iOS)

## Status

**Tailscale binding is LIVE.** The Capture API is bound to the Tailscale network and reachable from iPhone.

## Overview

Use iOS Shortcuts to capture text, URLs, or ideas directly to LifeOS via the Capture API on your Tailscale network.

## Prerequisites

- LifeOS Capture API running (verify: `systemctl --user status lifeos-capture-api`)
- Tailscale installed on both iPhone and LifeOS host
- iPhone on the same Tailscale tailnet as LifeOS host
- Bearer token from `/home/lifeos/40_Services/capture_api/.env` (mode 600)

## Your Capture API URL

```
http://lenovog3-mint.tail7687a5.ts.net:8789
```

Or using the raw Tailscale IP (changes if you re-auth Tailscale):
```
http://100.114.67.45:8789
```

## Shortcut Setup

1. Open Shortcuts app on iPhone.
2. Create a new shortcut (tap +).
3. Add "Get Contents of URL" action:
   - **Method:** POST
   - **URL:** `http://lenovog3-mint.tail7687a5.ts.net:8789/captures`
   - Tap "Request Body" and select "JSON"
   - Tap "Add new header" twice:
     - First header: `Authorization` = `Bearer <your-token>`
     - Second header: `Content-Type` = `application/json`
   - Body JSON:
     ```json
     {
       "content": "Shortcut Input",
       "source": "http_shortcuts",
       "client": "ios_shortcuts"
     }
     ```
4. In the body JSON, tap "Shortcut Input" and replace it with a variable:
   - Tap the field, then tap "Select Variable"
   - Choose "Shortcut Input" or "Provided Input"
5. Optionally add "Show Notification" action with the response.

## Quick Text Capture Shortcut

- **Name:** "LifeOS Capture"
- **Receives:** Any (text, URL, shared content)
- **Steps:**
  1. Get text from input
  2. Post to `http://lenovog3-mint.tail7687a5.ts.net:8789/captures` as JSON
  3. Show notification "Captured" or check for errors

## Testing from iPhone

1. Connect iPhone to Tailscale (open Tailscale app, ensure connected).
2. Open Safari on iPhone.
3. Navigate to: `http://lenovog3-mint.tail7687a5.ts.net:8789/health`
4. You should see: `{"status": "ok", "service": "lifeos_capture_api", "mode": "queue_only"}`
5. If this works, the Shortcut will work.

## Security

- The bearer token is stored in the Shortcuts app on your iPhone.
- Only one token exists currently. Keep it secret.
- Do not share the Shortcut or its token with untrusted devices.
- The Shortcut works only when connected to Tailscale.
- Consider rotating the token periodically (edit `.env`, restart service).
