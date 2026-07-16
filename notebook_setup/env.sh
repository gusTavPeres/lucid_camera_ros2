#!/bin/bash
# Source este arquivo antes de usar qualquer ferramenta ROS2 no notebook receptor.
# Uso:
#   source env.sh                     # usa defaults
#   source env.sh 192.168.1.10:11811  # override discovery server IP
#
# Depois rode o que quiser:
#   rqt_image_view
#   ros2 topic list --no-daemon
#   python3 stream_viewer.py --topic /camera_1/image_new --compressed

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

# Discovery Server — obrigatório: passe IP:porta como argumento
# ou exporte ROS_DISCOVERY_SERVER antes de dar source.
if [ -n "$1" ]; then
    export ROS_DISCOVERY_SERVER="$1"
elif [ -z "$ROS_DISCOVERY_SERVER" ]; then
    echo "[ERRO] Informe o Discovery Server: source env.sh <IP_DO_SERVIDOR>:11811"
    return 1 2>/dev/null || exit 1
fi
export ROS_SUPER_CLIENT=true
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp

# Profile FastDDS — restringe tráfego à interface VPN/LAN
if [ -f "$REPO_DIR/config/fastdds_subscriber.xml" ]; then
    export FASTRTPS_DEFAULT_PROFILES_FILE="$REPO_DIR/config/fastdds_subscriber.xml"
else
    echo "[WARN] Profile não encontrado: $REPO_DIR/config/fastdds_subscriber.xml"
    echo "       Execute: ./config/setup_fastdds.sh subscriber wt0"
fi

# ROS2
source /opt/ros/humble/setup.bash 2>/dev/null
[ -f "$REPO_DIR/ros2_ws/install/setup.bash" ] && source "$REPO_DIR/ros2_ws/install/setup.bash"

# Daemon interfere com Discovery Server
ros2 daemon stop 2>/dev/null

echo "ROS2 Discovery Server: $ROS_DISCOVERY_SERVER"
echo "Profile: ${FASTRTPS_DEFAULT_PROFILES_FILE:-nenhum}"
echo "Pronto. Use: rqt_image_view, ros2 topic list --no-daemon, etc."
