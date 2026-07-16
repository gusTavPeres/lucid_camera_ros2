#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$HERE/run_ros.sh" '
set -e
echo "FASTDDS_DEFAULT_PROFILES_FILE=$FASTDDS_DEFAULT_PROFILES_FILE"
echo "--- topics ---"
ros2 topic list | sort | grep -E "camera|ouster|points|imu" || true
echo "--- camera hz quick check ---"
for t in /camera/left/image_raw /camera/right/image_raw /camera/top_front/image_raw /camera/top_left/image_raw /camera/top_right/image_raw /camera/back/image_raw; do
  echo "--- $t ---"
  timeout 4 ros2 topic hz "$t" || true
done
echo "--- lidar hz quick check ---"
timeout 5 ros2 topic hz /ouster/points || true
'
