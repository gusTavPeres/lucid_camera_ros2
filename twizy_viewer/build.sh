#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_BIN="${DOCKER_BIN:-docker}"
if ! $DOCKER_BIN info >/dev/null 2>&1; then
    DOCKER_BIN="sudo docker"
fi

exec $DOCKER_BIN build -t twizy_viewer:humble "$HERE"
