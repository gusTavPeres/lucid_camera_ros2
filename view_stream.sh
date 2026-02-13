#!/bin/bash
#
# Script para visualizar stream da câmera
# Uso: ./view_stream.sh
#

docker compose exec camera_dev bash -c "source /opt/ros/humble/setup.bash && export ROS_DOMAIN_ID=42 && python3 /arena_camera_ros2/notebook_setup/stream_viewer.py --topic /camera/image_raw"
