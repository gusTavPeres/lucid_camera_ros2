#!/usr/bin/env bash
set -euo pipefail

TOPIC="${1:-/camera/left/image_raw}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$HERE/run_ros.sh" "ros2 run rqt_image_view rqt_image_view $TOPIC"
