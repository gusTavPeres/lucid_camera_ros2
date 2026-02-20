#!/bin/bash
# throttle_camera.sh
# Limita o FPS do tópico da câmera para não saturar o WiFi.
# Cria /camera/image_raw_slow com FPS limitado.
#
# Uso: bash throttle_camera.sh [fps]
# Padrão: 5 FPS
#
# Rode no notebook (distrobox), APÓS a câmera estar publicando.

FPS=${1:-5}

source /opt/ros/humble/setup.bash
source /var/home/tufg/lucid_camera_ros2/ros2_ws/install/setup.bash 2>/dev/null || true

export ROS_DOMAIN_ID=42

echo "Throttle: /camera/image_raw -> /camera/image_raw_slow @ ${FPS} FPS"
echo "(O subscriber no Ubuntu PC deve usar /camera/image_raw_slow)"
echo ""

# topic_tools throttle: republica com limite de FPS
ros2 run topic_tools throttle messages /camera/image_raw "$FPS" /camera/image_raw_slow
