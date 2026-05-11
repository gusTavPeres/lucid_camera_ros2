#!/bin/bash
# stop.sh — tear it down. Pass --teardown-host to also revert MTU/IP alias.

set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
cd "$REPO"

echo "[stop] docker compose down"
docker compose down

if [ "${1:-}" = "--teardown-host" ]; then
    echo "[stop] Reverting host network config"
    sudo -E "$HERE/host_teardown.sh"
else
    echo "[stop] Host MTU + IP alias left in place. Pass --teardown-host to revert."
fi
