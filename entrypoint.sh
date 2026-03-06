#!/bin/bash
set -e

# Source ROS2 environment
source /opt/ros/humble/setup.bash

# Source workspace if it exists
if [ -f /root/ros2_ws/install/setup.bash ]; then
    source /root/ros2_ws/install/setup.bash
fi

exec "$@"