#!/bin/bash
#
# Script para configurar variáveis de ambiente do ArenaSDK + ROS2
# Use: source setup_env.sh
#
# Este script configura os paths necessários para rodar os scripts de câmera
# tanto dentro do container Docker quanto em instalações nativas.
#

# Detectar se está em container Docker ou nativo
if [ -f /.dockerenv ]; then
    ARENA_ROOT="/ArenaSDK_Linux_x64"
else
    # Instalação nativa (distrobox, toolbox, etc)
    ARENA_ROOT="/ArenaSDK_Linux_x64"
fi

# Configurar variáveis de ambiente do ArenaSDK
export ARENA_ROOT
export GENICAM_GENTL64_PATH="${ARENA_ROOT}/lib64"
export LD_LIBRARY_PATH="${ARENA_ROOT}/lib64:${ARENA_ROOT}/GenICam/library/lib/Linux64_x64:${ARENA_ROOT}/ffmpeg:${ARENA_ROOT}/Metavision/lib:${ARENA_ROOT}/OpenCV/lib:${LD_LIBRARY_PATH}"

# Source ROS2 se disponível
if [ -f "/opt/ros/humble/setup.bash" ]; then
    source /opt/ros/humble/setup.bash
fi

# Source workspace local se existir
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="${SCRIPT_DIR}/../ros2_ws"

if [ -f "${WORKSPACE_DIR}/install/setup.bash" ]; then
    source "${WORKSPACE_DIR}/install/setup.bash"
fi

echo "✅ Ambiente ArenaSDK + ROS2 configurado"
echo "   ARENA_ROOT: ${ARENA_ROOT}"
echo "   Workspace: ${WORKSPACE_DIR}"
