# HTTP Shortcuts Capture Setup (iOS)

## Overview

Use iOS Shortcuts to capture text, URLs, or ideas directly to LifeOS via the Capture API on your Tailscale network.

## Prerequisites

- LifeOS Capture API running (`curl -s http://127.0.0.1:8789/health` from the LifeOS host)
- Tailscale installed on both iPhone and LifeOS host
- iPhone on the same Tailscale tailnet as LifeOS host
- Bearer token configured (`LIFEOS_CAPTURE_BEARER_TOKEN`)
- Capture API reachable via Tailscale IP `http://100.xxx.xxx.xxx:8789`

## Shortcut Setup

1. Open Shortcuts app on iPhone.
2. Create a new shortcut.
3. Add "Get Contents of URL" action:
   - Method: POST
   - URL: `http://<tailscale-ip>:8789/captures`
   - Request Body: JSON
   - Add header: `Authorization: Bearer <your-token>`
   - Add header: `Content-Type: application/json`
   - Body:
     ```json
     {
       "content": "Shortcut Input",
       "source": "http_shortcuts",
       "client": "ios_shortcuts"
     }
     ```
4. Replace "Shortcut Input" with the actual input variable.
5. Optionally add a notification action showing the response.

## Quick Text Capture Shortcut

- **Name:** "LifeOS Capture"
- **Receives:** Any (text, URL, shared content)
- **Steps:**
  1. Get text from input
  2. Post to `http://<tailscale-ip>:8789/captures` as JSON
  3. Show notification "Captured" or "Failed"

## Security

- The bearer token is stored in the Shortcuts app on your iPhone.
- Use a dedicated token (not the internal service token) if possible.
- Consider using a VPN/on-device firewall to restrict Shortcuts network access.
- The Shortcut is only useful when connected to Tailscale.
