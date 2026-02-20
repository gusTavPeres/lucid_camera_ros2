#!/bin/bash
# start_receiver.sh
#
# Starts the viewer and optionally the recorder on the receiver machine.
# Run this inside the Docker container (docker compose exec camera_dev bash).
#
# Usage:
#   bash start_receiver.sh [topic] [--record] [--output FILE] [--duration S]
#
#   topic      : base camera topic (default: /camera/image_raw)
#   --record   : also record to MP4
#   --output   : MP4 output file (default: recording_TIMESTAMP.mp4)
#   --duration : recording duration in seconds (default: unlimited)
#
# Examples:
#   bash start_receiver.sh                                     # view only
#   bash start_receiver.sh /camera/image_raw --record         # view + record
#   bash start_receiver.sh /camera/image_raw --record --duration 30

TOPIC=${1:-"/camera/image_raw"}
RECORD=false
OUTPUT=""
DURATION=""

shift 2>/dev/null || true
while [[ $# -gt 0 ]]; do
    case "$1" in
        --record)   RECORD=true; shift ;;
        --output)   OUTPUT="$2"; shift 2 ;;
        --duration) DURATION="$2"; shift 2 ;;
        *) shift ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
COMPRESSED_TOPIC="${TOPIC}/compressed"

echo "========================================"
echo "  Camera Receiver"
echo "========================================"
echo "  Topic:   $COMPRESSED_TOPIC"
[ "$RECORD" = true ] && echo "  Record:  yes"
echo "========================================"
echo ""

source /opt/ros/humble/setup.bash 2>/dev/null || true
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-42}

# Kill old processes
pkill -f stream_viewer 2>/dev/null || true
pkill -f record_video 2>/dev/null || true
sleep 1

VIEWER_SCRIPT="$REPO_DIR/notebook_setup/stream_viewer.py"

if [ "$RECORD" = true ]; then
    # Build record command
    if [ -z "$OUTPUT" ]; then
        OUTPUT="recording_$(date +%Y%m%d_%H%M%S).mp4"
    fi

    RECORD_ARGS="--topic $COMPRESSED_TOPIC --output $OUTPUT"
    [ -n "$DURATION" ] && RECORD_ARGS="$RECORD_ARGS --duration $DURATION"

    echo "Starting recorder: $OUTPUT"
    python3 "$REPO_DIR/scripts/record_video.py" $RECORD_ARGS &
    RECORD_PID=$!
    echo "  Recorder PID: $RECORD_PID"
    sleep 1
fi

echo "Starting viewer: $COMPRESSED_TOPIC"
python3 "$VIEWER_SCRIPT" --topic "$TOPIC" --compressed

# If viewer exits, stop recorder too
if [ "$RECORD" = true ] && kill -0 $RECORD_PID 2>/dev/null; then
    echo "Stopping recorder..."
    kill $RECORD_PID
    wait $RECORD_PID 2>/dev/null
fi
