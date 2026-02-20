#!/bin/bash
# compress_stream.sh
#
# JPEG compression relay for bandwidth-efficient streaming over WiFi or VPN.
# Subscribes to a raw camera topic, converts frames to JPEG, republishes as
# CompressedImage. Enables full-resolution streaming at full frame rate.
#
# Bandwidth: ~35 Mbps (RAW) -> ~5-12 Mbps (JPEG q=80), depending on scene.
#
# Usage:
#   bash compress_stream.sh [input_topic] [jpeg_quality]
#
#   input_topic  : source topic (default: /camera/image_raw)
#   jpeg_quality : JPEG quality 1-100 (default: 80)
#
# Output topic: <input_topic>/compressed
# Receiver should subscribe to: <input_topic>/compressed  (use --compressed flag)
#
# Run on the publisher/camera machine, after the camera node is started.

INPUT=${1:-"/camera/image_raw"}
QUALITY=${2:-80}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

source /opt/ros/humble/setup.bash
source "$REPO_DIR/ros2_ws/install/setup.bash" 2>/dev/null || true

export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-42}

# FastDDS: restrict to the network interface used for streaming
FASTDDS_PROFILE="$REPO_DIR/config/fastdds_publisher.xml"
if [ ! -f "$FASTDDS_PROFILE" ]; then
    FASTDDS_PROFILE="$REPO_DIR/config/fastdds_multipc.xml"
fi
if [ -f "$FASTDDS_PROFILE" ]; then
    export FASTRTPS_DEFAULT_PROFILES_FILE="$FASTDDS_PROFILE"
fi

echo "Compression relay starting..."
echo "  Input:   $INPUT"
echo "  Output:  ${INPUT}/compressed"
echo "  Quality: JPEG q=$QUALITY"
echo ""
echo "Receiver command:"
echo "  python3 stream_viewer.py --topic $INPUT --compressed"
echo ""

python3 "$REPO_DIR/scripts/compress_bayer_stream.py" \
    --input "$INPUT" \
    --quality "$QUALITY"
