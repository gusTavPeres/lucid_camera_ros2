#!/bin/bash
# start_receiver.sh — Inicia o viewer no notebook receptor via VPN
#
# Pré-requisitos no notebook:
#   - ROS2 Humble instalado
#   - rmw_fastrtps_cpp instalado
#   - Netbird conectado (IP 100.107.107.160)
#   - cv_bridge e image_transport instalados
#
# Uso:
#   bash start_receiver.sh                                  # câmera 1
#   bash start_receiver.sh /camera_2/image_new              # câmera 2
#   bash start_receiver.sh /camera_1/image_new --record     # gravar

set -e

TOPIC=${1:-"/camera_1/image_new"}
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
CONFIG_DIR="$REPO_DIR/config"

# ── Ambiente ROS2 + FastDDS ──────────────────────────────────────────────
source /opt/ros/humble/setup.bash 2>/dev/null || true
[ -f "$REPO_DIR/ros2_ws/install/setup.bash" ] && source "$REPO_DIR/ros2_ws/install/setup.bash"

export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-0}
export ROS_DISCOVERY_SERVER=${ROS_DISCOVERY_SERVER:-100.107.134.30:11811}
export FASTRTPS_DEFAULT_PROFILES_FILE="$CONFIG_DIR/fastdds_subscriber.xml"

echo "========================================"
echo "  Camera Receiver (Discovery Server)"
echo "========================================"
echo "  Topic:      $TOPIC/compressed"
echo "  Discovery:  $ROS_DISCOVERY_SERVER"
echo "  Profile:    $FASTRTPS_DEFAULT_PROFILES_FILE"
echo "  Record:     $RECORD"
echo "========================================"
echo ""

# Verificar que o profile existe
if [ ! -f "$FASTRTPS_DEFAULT_PROFILES_FILE" ]; then
    echo "ERRO: Profile FastDDS não encontrado: $FASTRTPS_DEFAULT_PROFILES_FILE"
    echo "Execute: ./config/setup_fastdds.sh subscriber wt0"
    exit 1
fi

# Kill old processes
pkill -f stream_viewer 2>/dev/null || true
pkill -f record_video 2>/dev/null || true
sleep 1

VIEWER_SCRIPT="$SCRIPT_DIR/stream_viewer.py"

if [ "$RECORD" = true ]; then
    [ -z "$OUTPUT" ] && OUTPUT="recording_$(date +%Y%m%d_%H%M%S).mp4"
    RECORD_ARGS="--topic ${TOPIC}/compressed --output $OUTPUT"
    [ -n "$DURATION" ] && RECORD_ARGS="$RECORD_ARGS --duration $DURATION"

    echo "Starting recorder: $OUTPUT"
    python3 "$REPO_DIR/scripts/record_video.py" $RECORD_ARGS &
    RECORD_PID=$!
    echo "  Recorder PID: $RECORD_PID"
    sleep 1
fi

echo "Starting viewer: $TOPIC/compressed"
python3 "$VIEWER_SCRIPT" --topic "$TOPIC" --compressed

if [ "$RECORD" = true ] && kill -0 $RECORD_PID 2>/dev/null; then
    echo "Stopping recorder..."
    kill $RECORD_PID
    wait $RECORD_PID 2>/dev/null
fi
