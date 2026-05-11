#!/bin/bash
# start.sh — one-line bringup. Run from anywhere; resolves paths via $0.

set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
cd "$REPO"

echo "[start] Step 1/3 — host network setup (sudo)"
sudo -E "$HERE/host_setup.sh"

echo "[start] Step 2/3 — docker compose up"
docker compose up -d sensor_stack

echo "[start] Step 3/3 — first 30 log lines after 5s..."
sleep 5
docker compose logs --tail 30 sensor_stack
echo ""
echo "[start] Follow with: docker compose logs -f sensor_stack"
echo "[start] Shell into:  docker compose exec sensor_stack bash"
