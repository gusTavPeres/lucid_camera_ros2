#!/bin/bash
# Entrypoint for the sensor_stack container.
#
# Order of operations:
#   1) Source ROS 2 Humble + ArenaSDK env
#   2) Stage ouster_ros into the workspace (first start only)
#   3) Build workspace if not built
#   4) Source workspace install/
#   5) Autodetect Netbird IP if unset
#   6) Render FastDDS XML and lidar params YAML from templates
#   7) Export RMW + FASTRTPS env vars
#   8) exec "$@"   (compose passes start_sensor_stack.sh)

set -e

# 1) ROS 2 + ArenaSDK env -----------------------------------------------------
source /opt/ros/humble/setup.bash
export ARENA_ROOT=/ArenaSDK_Linux_x64
export GENICAM_GENTL64_PATH=/ArenaSDK_Linux_x64/lib64
export LD_LIBRARY_PATH=/ArenaSDK_Linux_x64/lib64:/ArenaSDK_Linux_x64/GenICam/library/lib/Linux64_x64:/ArenaSDK_Linux_x64/ffmpeg:/ArenaSDK_Linux_x64/Metavision/lib:/ArenaSDK_Linux_x64/OpenCV/lib:${LD_LIBRARY_PATH}

cd /arena_camera_ros2/ros2_ws

# 2) Stage ouster_ros src from the vendored copy if absent --------------------
mkdir -p src
for pkg in ouster_ros ouster_sensor_msgs; do
    if [ ! -d "src/${pkg}" ]; then
        if [ -d "/opt/vendor/${pkg}" ]; then
            echo "[entrypoint] Staging ${pkg} from /opt/vendor -> src/"
            cp -r "/opt/vendor/${pkg}" "src/${pkg}"
        else
            echo "[entrypoint] WARN: /opt/vendor/${pkg} not found"
        fi
    fi
done

# 3) Build workspace if not built --------------------------------------------
if [ ! -f "install/local_setup.bash" ] && [ -d "src" ]; then
    echo "=============================================="
    echo "  First run — building workspace"
    echo "=============================================="
    rosdep install --from-paths src --ignore-src --rosdistro humble -r -y 2>/dev/null || true
    if colcon build --symlink-install \
                    --cmake-args -DCMAKE_BUILD_TYPE=Release \
                                 -DCMAKE_CXX_FLAGS='-Wno-deprecated-declarations'; then
        echo "[entrypoint] Build OK"
    else
        echo "[entrypoint] Build FAILED — dropping you in a shell for debugging."
        echo "             Run: cd /arena_camera_ros2/ros2_ws && colcon build --symlink-install"
    fi
fi

# 4) Source workspace --------------------------------------------------------
[ -f install/local_setup.bash ] && source install/local_setup.bash

# 5) Autodetect HOST_NETBIRD_IP if unset -------------------------------------
# Netbird CGNAT range is 100.64.0.0/10 — real values in your network start
# with 100.107.x.x. Pick the first matching IP from any iface.
if [ -z "${HOST_NETBIRD_IP:-}" ]; then
    HOST_NETBIRD_IP=$(ip -4 -o addr show \
        | awk '{print $4}' \
        | cut -d/ -f1 \
        | awk -F. '$1==100 && $2>=64 && $2<=127' \
        | head -n1)
fi
if [ -z "${HOST_NETBIRD_IP}" ]; then
    echo "[entrypoint] WARN: no Netbird IP found (100.64.0.0/10). DDS will work"
    echo "             locally but remote peers won't reach this host."
    # Fall back to loopback so the XML is still valid
    HOST_NETBIRD_IP="127.0.0.1"
fi
export HOST_NETBIRD_IP
echo "[entrypoint] HOST_NETBIRD_IP=${HOST_NETBIRD_IP}"

# 6a) Render REMOTE_PEER_IPS_XML from comma-separated REMOTE_PEER_IPS --------
REMOTE_PEER_IPS_XML=""
if [ -n "${REMOTE_PEER_IPS:-}" ]; then
    IFS=',' read -ra _peers <<< "${REMOTE_PEER_IPS}"
    for _p in "${_peers[@]}"; do
        _p=$(echo "$_p" | xargs)   # trim whitespace
        [ -z "$_p" ] && continue
        REMOTE_PEER_IPS_XML+="          <locator><udpv4><address>${_p}</address></udpv4></locator>"$'\n'
    done
fi
export REMOTE_PEER_IPS_XML
echo "[entrypoint] Remote DDS peers: ${REMOTE_PEER_IPS:-<none>}"

# 6b) Render FastDDS XML -----------------------------------------------------
FASTDDS_TEMPLATE="/arena_camera_ros2/config/fastdds_profile.xml.template"
FASTDDS_OUT="/tmp/fastdds_profile.xml"
if [ -f "${FASTDDS_TEMPLATE}" ]; then
    envsubst < "${FASTDDS_TEMPLATE}" > "${FASTDDS_OUT}"
    export FASTRTPS_DEFAULT_PROFILES_FILE="${FASTDDS_OUT}"
    echo "[entrypoint] Rendered FastDDS profile -> ${FASTDDS_OUT}"
else
    echo "[entrypoint] WARN: ${FASTDDS_TEMPLATE} missing; using DDS defaults"
fi

# 6c) Render lidar params YAML ----------------------------------------------
LIDAR_TEMPLATE="/arena_camera_ros2/config/lidar_params.yaml.template"
LIDAR_OUT="/tmp/lidar_params.yaml"
if [ -f "${LIDAR_TEMPLATE}" ]; then
    # Default the optional fields to empty strings so envsubst doesn't leave
    # literal "${VAR}" in the YAML.
    export LIDAR_HOSTNAME="${LIDAR_HOSTNAME:-192.168.1.200}"
    export LIDAR_UDP_DEST="${LIDAR_UDP_DEST:-}"
    export LIDAR_MODE="${LIDAR_MODE:-1024x10}"
    export LIDAR_TIMESTAMP_MODE="${LIDAR_TIMESTAMP_MODE:-TIME_FROM_ROS_TIME}"
    export LIDAR_UDP_PROFILE="${LIDAR_UDP_PROFILE:-RNG19_RFL8_SIG16_NIR16}"
    envsubst < "${LIDAR_TEMPLATE}" > "${LIDAR_OUT}"
    echo "[entrypoint] Rendered lidar params -> ${LIDAR_OUT}"
fi

# 7) Force ROS 2 RMW + domain ------------------------------------------------
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-0}"

echo ""
echo "=============================================="
echo "  sensor_stack ready"
echo "=============================================="
echo "  ROS_DOMAIN_ID=${ROS_DOMAIN_ID}  RMW=${RMW_IMPLEMENTATION}"
echo "  FASTRTPS_DEFAULT_PROFILES_FILE=${FASTRTPS_DEFAULT_PROFILES_FILE:-<unset>}"
echo "  HOST_NETBIRD_IP=${HOST_NETBIRD_IP}"
echo "  REMOTE_PEER_IPS=${REMOTE_PEER_IPS:-<none>}"
echo "  ENABLE_CAMERA=${ENABLE_CAMERA:-true}  ENABLE_LIDAR=${ENABLE_LIDAR:-true}"
echo "=============================================="
echo ""

# 8) Hand off to the compose command (start_sensor_stack.sh, or `bash`) ------
exec "$@"
