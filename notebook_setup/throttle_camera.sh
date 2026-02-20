#!/bin/bash
# throttle_camera.sh
#
# Rate-limits a camera topic to reduce network bandwidth.
# Useful as a simpler alternative to JPEG compression when latency or
# visual quality are less critical than simplicity.
#
# For full-resolution full-fps streaming, use compress_stream.sh instead.
#
# Usage:
#   bash throttle_camera.sh [fps] [input_topic] [output_topic]
#
# Defaults:
#   fps          : 5
#   input_topic  : /camera/image_raw
#   output_topic : /camera/image_raw_slow
#
# Run on the publisher/camera machine, after the camera node is running.

FPS=${1:-5}
INPUT=${2:-"/camera/image_raw"}
OUTPUT=${3:-"/camera/image_raw_slow"}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

source /opt/ros/humble/setup.bash
source "$REPO_DIR/ros2_ws/install/setup.bash" 2>/dev/null || true

export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-42}

echo "Throttle: $INPUT -> $OUTPUT @ ${FPS} FPS"
echo "(Receiver should subscribe to: $OUTPUT)"
echo ""

ros2 run topic_tools throttle messages "$INPUT" "$FPS" "$OUTPUT"
