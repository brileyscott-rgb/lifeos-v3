#!/usr/bin/env bash
# -------------------------------------------------------------------
# Temporary Cloudflare Quick Tunnel — LifeOS n8n webhook POC
# -------------------------------------------------------------------
# WARNING: This creates a TEMPORARY public URL for your local n8n.
#          Anyone with the URL can reach your n8n instance.
#          Stop with Ctrl+C when done.
#          Do NOT use for production.
#          Do NOT register Telegram webhook against this URL.
# -------------------------------------------------------------------
set -euo pipefail

echo ""
echo "============================================"
echo " WARNING: Temporary Public Tunnel"
echo "============================================"
echo ""
echo "This will create an ephemeral public URL via"
echo "Cloudflare Quick Tunnel (trycloudflare.com)."
echo ""
echo "Your local n8n at http://127.0.0.1:5678 will"
echo "be publicly accessible until you press Ctrl+C."
echo ""
echo "Do NOT:"
echo "  - Register Telegram webhook"
echo "  - Expose n8n UI intentionally"
echo "  - Route Status/Action APIs publicly"
echo "  - Use this as production"
echo ""
echo "Press Ctrl+C within 5 seconds to abort..."
sleep 5
echo ""
echo "Starting tunnel..."
echo ""

docker run --rm --network host cloudflare/cloudflared:latest tunnel --url http://127.0.0.1:5678
