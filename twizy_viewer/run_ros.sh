#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$HERE/twizy_ros_env.sh"

IMAGE="${TWIZY_VIEWER_IMAGE:-twizy_viewer:humble}"
DOCKER_BIN="${DOCKER_BIN:-docker}"
if ! $DOCKER_BIN info >/dev/null 2>&1; then
    DOCKER_BIN="sudo docker"
fi

DISPLAY_ARGS=()
if [ -n "${DISPLAY:-}" ]; then
    DISPLAY_ARGS+=("-e" "DISPLAY=${DISPLAY}" "-v" "/tmp/.X11-unix:/tmp/.X11-unix:rw")
fi
if [ -n "${XAUTHORITY:-}" ] && [ -f "${XAUTHORITY:-}" ]; then
    DISPLAY_ARGS+=("-e" "XAUTHORITY=/tmp/.docker.xauth" "-v" "${XAUTHORITY}:/tmp/.docker.xauth:ro")
fi

TTY_ARGS=("-i")
if [ -t 0 ] && [ -t 1 ]; then
    TTY_ARGS=("-it")
fi

exec $DOCKER_BIN run --rm "${TTY_ARGS[@]}" \
    --network host \
    --ipc host \
    "${DISPLAY_ARGS[@]}" \
    -e ROS_DOMAIN_ID="$ROS_DOMAIN_ID" \
    -e RMW_IMPLEMENTATION="$RMW_IMPLEMENTATION" \
    -e ROS_LOCALHOST_ONLY=0 \
    -e FASTDDS_DEFAULT_PROFILES_FILE=/twizy_viewer/fastdds_super_client.xml \
    -e FASTRTPS_DEFAULT_PROFILES_FILE=/twizy_viewer/fastdds_super_client.xml \
    -v "$HERE:/twizy_viewer:ro" \
    "$IMAGE" \
    bash -lc "source /opt/ros/humble/setup.bash && unset ROS_DISCOVERY_SERVER ROS_SUPER_CLIENT && cd /twizy_viewer && $*"
