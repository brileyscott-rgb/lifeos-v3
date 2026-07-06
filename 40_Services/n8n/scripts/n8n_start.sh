#!/usr/bin/env bash
# Start n8n container
# Usage: ./scripts/n8n_start.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [ ! -f "$DIR/.env" ]; then
    echo "WARNING: .env not found at $DIR/.env"
    echo "Copy .env.example to .env and fill in real values before starting."
    echo "Proceeding with environment defaults..."
fi

echo "Starting n8n..."
cd "$DIR"
docker-compose up -d
echo "n8n started. Access at http://localhost:5678"
