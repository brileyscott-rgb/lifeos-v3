#!/usr/bin/env bash
# Start n8n container
# Usage: ./scripts/n8n_start.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [ ! -f "$DIR/.env" ]; then
    echo "ERROR: .env not found at $DIR/.env"
    echo ""
    echo "Copy .env.example to .env and set real local credentials before starting:"
    echo "  cp $DIR/.env.example $DIR/.env"
    echo "  nano $DIR/.env"
    echo ""
    exit 1
fi

echo "Starting n8n..."
cd "$DIR"
docker-compose up -d
echo "n8n started. Access at http://localhost:5678"
