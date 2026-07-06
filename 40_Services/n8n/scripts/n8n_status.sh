#!/usr/bin/env bash
# Check n8n container status
# Usage: ./scripts/n8n_status.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "n8n container status:"
cd "$DIR"
docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || docker-compose ps

echo ""
echo "Port binding check:"
ss -tlnp 2>/dev/null | grep -E '5678' || echo "No process listening on port 5678 (container not running)"
