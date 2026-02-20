#!/bin/bash
# start_camera.sh
#
# Starts the arena_camera_node ROS2 publisher for a Lucid Vision camera.
#
# Usage:
#   ./start_camera.sh [serial] [topic] [pixelformat] [width] [height] [gain] [exposure_us] [fps]
#
# Arguments (all optional):
#   serial      : Camera serial number (default: first available camera)
#   topic       : ROS2 topic to publish on (default: /camera/image_raw)
#   pixelformat : bayer_rggb8 | rgb8 | bgr8 | mono8 (default: bayer_rggb8)
#   width       : Image width in pixels (default: camera maximum)
#   height      : Image height in pixels (default: camera maximum)
#   gain        : Sensor gain in dB (default: 0.0)
#   exposure_us : Exposure time in microseconds (default: camera auto)
#                 Note: valid range varies by camera. For TRI032S: 30–29696 us.
#                 If exposure_auto is on, this sets the initial value only.
#   fps         : Target frame rate (default: camera max). Set AcquisitionFrameRate.
#                 Note: max FPS depends on resolution and sensor. For TRI032S at
#                 2048x1536: max ~33.5 FPS. Set exposure_us short enough to allow it.
#
# Examples:
#   ./start_camera.sh                                    # first camera, full resolution
#   ./start_camera.sh 123456789                          # specific camera by serial
#   ./start_camera.sh 123456789 /cam bayer_rggb8 "" "" 20.0 25000 33.0

SERIAL=${1:-""}
TOPIC=${2:-"/camera/image_raw"}
PIXELFORMAT=${3:-"bayer_rggb8"}
WIDTH=${4:-""}
HEIGHT=${5:-""}
GAIN=${6:-""}
EXPOSURE=${7:-""}
FPS=${8:-""}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

# Source ROS2 and workspace
source /opt/ros/humble/setup.bash
source "$REPO_DIR/ros2_ws/install/setup.bash" 2>/dev/null || \
    source /arena_camera_ros2/ros2_ws/install/setup.bash 2>/dev/null || true

export ROS_DOMAIN_ID=${ROS_DOMAIN_ID:-42}

# FastDDS: restrict to the streaming interface (prevents advertising GigE camera port)
FASTDDS_PROFILE="$REPO_DIR/config/fastdds_publisher.xml"
if [ ! -f "$FASTDDS_PROFILE" ]; then
    FASTDDS_PROFILE="$REPO_DIR/config/fastdds_multipc.xml"
fi
if [ -f "$FASTDDS_PROFILE" ]; then
    export FASTRTPS_DEFAULT_PROFILES_FILE="$FASTDDS_PROFILE"
fi

# Build ros-args
ARGS="-p topic:=$TOPIC -p pixelformat:=$PIXELFORMAT"
[ -n "$SERIAL" ]   && ARGS="$ARGS -p serial:=$SERIAL"
[ -n "$WIDTH" ]    && ARGS="$ARGS -p width:=$WIDTH"
[ -n "$HEIGHT" ]   && ARGS="$ARGS -p height:=$HEIGHT"
[ -n "$GAIN" ]     && ARGS="$ARGS -p gain:=$GAIN"
[ -n "$EXPOSURE" ] && ARGS="$ARGS -p exposure_time:=$EXPOSURE"
[ -n "$FPS" ]      && ARGS="$ARGS -p frame_rate:=$FPS"

echo "Starting camera node..."
[ -n "$SERIAL" ] && echo "  Serial:      $SERIAL" || echo "  Serial:      (first available)"
echo "  Topic:       $TOPIC"
echo "  Pixelformat: $PIXELFORMAT"
[ -n "$WIDTH" ]    && echo "  Resolution:  ${WIDTH}x${HEIGHT}"
[ -n "$GAIN" ]     && echo "  Gain:        $GAIN dB"
[ -n "$EXPOSURE" ] && echo "  Exposure:    $EXPOSURE us"
[ -n "$FPS" ]      && echo "  Frame rate:  $FPS FPS"
echo ""

ros2 run arena_camera_node start --ros-args $ARGS
