#!/bin/bash
#
# Script para iniciar uma câmera Lucid Vision em modo RAW (BayerRG8)
# Uso: ./start_camera_raw.sh [serial] [topic]
#

SERIAL=${1:-""}
TOPIC=${2:-"/camera/image_raw"}

# Source ROS2
source /opt/ros/humble/setup.bash
source /arena_camera_ros2/ros2_ws/install/setup.bash 2>/dev/null || true

# Configurar LD_LIBRARY_PATH
export LD_LIBRARY_PATH=/ArenaSDK_Linux_x64/lib64:/ArenaSDK_Linux_x64/GenICam/library/lib/Linux64_x64:/ArenaSDK_Linux_x64/OpenCV/lib:${LD_LIBRARY_PATH}

# Configurar GENICAM
export GENICAM_GENTL64_PATH=/ArenaSDK_Linux_x64/lib64

if [ -z "$SERIAL" ]; then
    echo "Iniciando câmera (primeira disponível) em modo RAW BayerRG8..."
    echo "Tópico: $TOPIC"
    ros2 run arena_camera_node start --ros-args \
        -p topic:="$TOPIC" \
        -p pixelformat:=bayer_rggb8
else
    echo "Iniciando câmera serial: $SERIAL em modo RAW BayerRG8"
    echo "Tópico: $TOPIC"
    ros2 run arena_camera_node start --ros-args \
        -p serial:="$SERIAL" \
        -p topic:="$TOPIC" \
        -p pixelformat:=bayer_rggb8
fi
