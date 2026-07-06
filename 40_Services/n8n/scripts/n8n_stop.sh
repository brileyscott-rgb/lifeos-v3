#!/usr/bin/env bash
# Stop n8n container
# Usage: ./scripts/n8n_stop.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "Stopping n8n..."
cd "$DIR"
docker-compose down
echo "n8n stopped."
