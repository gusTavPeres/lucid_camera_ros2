#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$HERE/run_ros.sh" 'python3 /twizy_viewer/multi_camera_viewer.py'
