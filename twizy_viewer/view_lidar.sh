#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$HERE/run_ros.sh" 'rviz2 -d /twizy_viewer/twizy_lidar.rviz'
