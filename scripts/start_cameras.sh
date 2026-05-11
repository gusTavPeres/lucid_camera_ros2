#!/bin/bash
# Startup script for lucid_camera_ros2 container.
# Launch order: relay first (gets low FastDDS participantId → discoverable remotely),
# then camera pipeline. Retries on GigE heartbeat lock (AccessException).

set -eo pipefail

CAMERA_CONFIG="${CAMERA_CONFIG:-/arena_camera_ros2/config/cameras.yaml}"
RELAY_QUALITY="${RELAY_QUALITY:-80}"
RELAY_WORKERS="${RELAY_WORKERS:-4}"
MAX_RETRIES=5
HEARTBEAT_WAIT=15  # seconds to wait for GigE heartbeat to expire after AccessException

echo "[start_cameras] === Lucid Camera ROS2 Startup ==="

# Step 1: fix routing for cameras on overlapping link-local subnets
/arena_camera_ros2/scripts/setup_routes.sh

# Step 2: source ROS
source /opt/ros/humble/setup.bash
source /arena_camera_ros2/ros2_ws/install/setup.bash

# Step 3: start relay in background FIRST → gets participantId 0 → always discoverable
echo "[start_cameras] Starting compress relay..."
python3 /arena_camera_ros2/scripts/multi_compress_relay.py \
    --config "$CAMERA_CONFIG" \
    --quality "$RELAY_QUALITY" \
    --workers "$RELAY_WORKERS" \
    &
RELAY_PID=$!
echo "[start_cameras] Relay PID=$RELAY_PID"

# Give relay time to register with DDS before pipeline starts
sleep 3

# Step 4: start camera pipeline with retry loop
for attempt in $(seq 1 $MAX_RETRIES); do
    echo "[start_cameras] Starting camera pipeline (attempt $attempt/$MAX_RETRIES)..."
    ros2 launch /arena_camera_ros2/launch/multi_camera.launch.py \
        config_file:="$CAMERA_CONFIG" || true

    # If we get here, the pipeline exited. Check if relay is still alive.
    if ! kill -0 $RELAY_PID 2>/dev/null; then
        echo "[start_cameras] Relay died — exiting."
        exit 1
    fi

    if [ "$attempt" -lt "$MAX_RETRIES" ]; then
        echo "[start_cameras] Pipeline exited (GigE heartbeat lock?). Waiting ${HEARTBEAT_WAIT}s before retry..."
        sleep "$HEARTBEAT_WAIT"
    fi
done

echo "[start_cameras] Camera pipeline failed after $MAX_RETRIES attempts."
kill $RELAY_PID 2>/dev/null
exit 1
