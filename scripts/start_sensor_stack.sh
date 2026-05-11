#!/bin/bash
# start_sensor_stack.sh — container-side bringup.
# Runs INSIDE the container as the docker-compose `command:`.
#
# Order:
#   1) Apply route fix-up for dual GigE cameras (autodetect version).
#   2) Start compression relay in background (so it gets a low DDS participantId).
#   3) Launch the unified sensor_stack_bringup.launch.py with retries.

set -eo pipefail

CAMERA_CONFIG="${CAMERA_CONFIG:-/arena_camera_ros2/config/cameras.yaml}"
LIDAR_PARAMS="${LIDAR_PARAMS:-/tmp/lidar_params.yaml}"
RELAY_QUALITY="${RELAY_QUALITY:-80}"
RELAY_WORKERS="${RELAY_WORKERS:-4}"
ENABLE_CAMERA="${ENABLE_CAMERA:-true}"
ENABLE_LIDAR="${ENABLE_LIDAR:-true}"
MAX_RETRIES=5
HEARTBEAT_WAIT=15

echo "[start_sensor_stack] === sensor_stack bringup ==="

# 1) Route fix (only matters with cameras attached)
if [ "${ENABLE_CAMERA}" = "true" ] && [ -x /arena_camera_ros2/scripts/setup_routes_auto.sh ]; then
    /arena_camera_ros2/scripts/setup_routes_auto.sh || \
        echo "[start_sensor_stack] route fix-up returned non-zero — continuing"
fi

source /opt/ros/humble/setup.bash
source /arena_camera_ros2/ros2_ws/install/setup.bash

# 2) Compression relay (unchanged, runs only if cameras enabled)
RELAY_PID=""
if [ "${ENABLE_CAMERA}" = "true" ]; then
    echo "[start_sensor_stack] Starting compress relay..."
    python3 /arena_camera_ros2/scripts/multi_compress_relay.py \
        --config "$CAMERA_CONFIG" \
        --quality "$RELAY_QUALITY" \
        --workers "$RELAY_WORKERS" &
    RELAY_PID=$!
    echo "[start_sensor_stack] Relay PID=$RELAY_PID"
    sleep 3
fi

# 3) Launch (with retry for camera AccessException / lidar reconnect)
for attempt in $(seq 1 $MAX_RETRIES); do
    echo "[start_sensor_stack] Launch attempt $attempt/$MAX_RETRIES"
    ros2 launch /arena_camera_ros2/launch/sensor_stack_bringup.launch.py \
        enable_camera:="${ENABLE_CAMERA}" \
        enable_lidar:="${ENABLE_LIDAR}" \
        camera_config:="${CAMERA_CONFIG}" \
        lidar_params:="${LIDAR_PARAMS}" \
        || true

    # Relay still alive?
    if [ -n "$RELAY_PID" ] && ! kill -0 "$RELAY_PID" 2>/dev/null; then
        echo "[start_sensor_stack] Relay died — exiting."
        exit 1
    fi

    if [ "$attempt" -lt "$MAX_RETRIES" ]; then
        echo "[start_sensor_stack] Launch exited; waiting ${HEARTBEAT_WAIT}s..."
        sleep "$HEARTBEAT_WAIT"
    fi
done

echo "[start_sensor_stack] Failed after $MAX_RETRIES attempts."
[ -n "$RELAY_PID" ] && kill "$RELAY_PID" 2>/dev/null
exit 1
