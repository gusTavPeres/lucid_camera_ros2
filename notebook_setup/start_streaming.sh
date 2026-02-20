#!/bin/bash
# start_streaming.sh
#
# Starts the full camera + compression pipeline on the publisher machine.
# Kills any existing camera/compression processes, then starts fresh.
#
# Usage:
#   bash start_streaming.sh [serial] [topic] [resolution] [gain]
#
#   serial     : camera serial number (default: first available)
#   topic      : base topic name (default: /camera/image_raw)
#   resolution : WxH e.g. 2048x1536 or 1024x768 (default: full/2048x1536)
#   gain       : sensor gain in dB (default: 0.0)
#
# Examples:
#   bash start_streaming.sh                          # full resolution, auto gain
#   bash start_streaming.sh 123456789                # specific serial
#   bash start_streaming.sh 123456789 /camera/image_raw 1024x768 10.0
#
# After starting, the receiver should run:
#   python3 stream_viewer.py --topic <topic> --compressed
#   python3 record_video.py  --topic <topic>/compressed --output video.mp4

SERIAL=${1:-""}
TOPIC=${2:-"/camera/image_raw"}
RESOLUTION=${3:-"2048x1536"}
GAIN=${4:-"0.0"}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

# Parse resolution
IFS='x' read -r WIDTH HEIGHT <<< "$RESOLUTION"

echo "========================================"
echo "  Camera Streaming Pipeline"
echo "========================================"
echo "  Serial:     ${SERIAL:-'(first available)'}"
echo "  Topic:      $TOPIC"
echo "  Resolution: ${WIDTH}x${HEIGHT}"
echo "  Gain:       $GAIN dB"
echo "  Compressed: ${TOPIC}/compressed"
echo "========================================"
echo ""

# --- Stop existing processes ---
echo "Stopping existing processes..."
pkill -f "arena_camera_node start" 2>/dev/null && echo "  Stopped: camera node" || true
pkill -f "compress_bayer_stream" 2>/dev/null && echo "  Stopped: compress relay" || true
pkill -f "topic_tools throttle" 2>/dev/null && echo "  Stopped: throttle" || true
sleep 2

# --- Source environment ---
source /opt/ros/humble/setup.bash
source "$REPO_DIR/ros2_ws/install/setup.bash" 2>/dev/null || true

export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-42}

# FastDDS profile
FASTDDS_PROFILE="$REPO_DIR/config/fastdds_publisher.xml"
[ ! -f "$FASTDDS_PROFILE" ] && FASTDDS_PROFILE="$REPO_DIR/config/fastdds_multipc.xml"
[ -f "$FASTDDS_PROFILE" ] && export FASTRTPS_DEFAULT_PROFILES_FILE="$FASTDDS_PROFILE"

# --- Start camera node in background (log to file) ---
echo "Starting camera node..."
CAMERA_LOG="/tmp/camera_node.log"

CAMERA_ARGS="-p topic:=$TOPIC -p pixelformat:=bayer_rggb8"
CAMERA_ARGS="$CAMERA_ARGS -p width:=$WIDTH -p height:=$HEIGHT"
CAMERA_ARGS="$CAMERA_ARGS -p gain:=$GAIN"
[ -n "$SERIAL" ] && CAMERA_ARGS="$CAMERA_ARGS -p serial:=$SERIAL"

ros2 run arena_camera_node start --ros-args $CAMERA_ARGS > "$CAMERA_LOG" 2>&1 &
CAMERA_PID=$!
echo "  Camera PID: $CAMERA_PID (log: $CAMERA_LOG)"

# Wait for first image
echo "  Waiting for camera to publish..."
for i in $(seq 1 15); do
    sleep 1
    if grep -q "image 1 published" "$CAMERA_LOG" 2>/dev/null; then
        echo "  Camera ready."
        break
    fi
    if ! kill -0 $CAMERA_PID 2>/dev/null; then
        echo "  ERROR: Camera process died. Log:"
        tail -20 "$CAMERA_LOG"
        exit 1
    fi
    echo -n "."
done
echo ""

# --- Start compression relay in background ---
echo "Starting compression relay..."
COMPRESS_LOG="/tmp/compress_relay.log"
python3 "$REPO_DIR/scripts/compress_bayer_stream.py" \
    --input "$TOPIC" --quality 80 > "$COMPRESS_LOG" 2>&1 &
COMPRESS_PID=$!
echo "  Compress PID: $COMPRESS_PID (log: $COMPRESS_LOG)"

sleep 2
if ! kill -0 $COMPRESS_PID 2>/dev/null; then
    echo "  ERROR: Compression relay died. Log:"
    tail -10 "$COMPRESS_LOG"
    exit 1
fi

echo ""
echo "========================================"
echo "  Pipeline running"
echo "  Camera PID:  $CAMERA_PID"
echo "  Compress PID: $COMPRESS_PID"
echo ""
echo "  Publishing:  $TOPIC  (RAW)"
echo "  Publishing:  ${TOPIC}/compressed  (JPEG)"
echo ""
echo "  On the receiver, run:"
echo "    python3 stream_viewer.py --topic $TOPIC --compressed"
echo "    python3 record_video.py  --topic ${TOPIC}/compressed"
echo ""
echo "  Logs:"
echo "    tail -f $CAMERA_LOG"
echo "    tail -f $COMPRESS_LOG"
echo ""
echo "  Stop: pkill -f arena_camera_node; pkill -f compress_bayer_stream"
echo "========================================"

# Keep script running to show live stats from compress relay
tail -f "$COMPRESS_LOG"
