#!/bin/bash

# Source ROS2 Humble
source /opt/ros/humble/setup.bash

# Configurar variáveis do ArenaSDK
export ARENA_ROOT=/ArenaSDK_Linux_x64
export GENICAM_GENTL64_PATH=/ArenaSDK_Linux_x64/lib64
export LD_LIBRARY_PATH=/ArenaSDK_Linux_x64/lib64:/ArenaSDK_Linux_x64/GenICam/library/lib/Linux64_x64:/ArenaSDK_Linux_x64/ffmpeg:/ArenaSDK_Linux_x64/Metavision/lib:/ArenaSDK_Linux_x64/OpenCV/lib:${LD_LIBRARY_PATH}

# Navegar para o workspace
cd /arena_camera_ros2/ros2_ws

# Verificar se já foi construído
if [ ! -f "install/local_setup.bash" ] && [ -d "src" ]; then
    echo "=============================================="
    echo "  Primeira execução - Build do workspace"
    echo "=============================================="

    echo "Instalando dependências ROS2..."
    rosdep update --rosdistro humble 2>/dev/null || true
    rosdep install --from-paths src --ignore-src --rosdistro humble -r -y 2>/dev/null || true

    echo "Compilando workspace..."
    if colcon build --symlink-install; then
        echo "Build concluído com sucesso!"
    else
        echo ""
        echo "AVISO: Build falhou. Entrando em modo interativo para debug."
        echo "Execute 'colcon build --symlink-install' para tentar novamente."
        echo ""
    fi
fi

# Source o workspace se existir
if [ -f "install/local_setup.bash" ]; then
    source install/local_setup.bash
fi

echo ""
echo "=============================================="
echo "  Lucid Vision Camera - ROS2 Humble"
echo "=============================================="
echo "  ARENA_ROOT: $ARENA_ROOT"
echo "  ROS_DISTRO: $ROS_DISTRO"
echo ""
echo "  Comandos úteis:"
echo "    - Listar câmeras: python3 /arena_camera_ros2/scripts/list_cameras.py"
echo "    - Iniciar câmera: ros2 run arena_camera_node start"
echo "    - Visualizar:     ros2 run image_tools showimage --ros-args -r image:=/arena_camera_node/images"
echo "    - Gravar bag:     ros2 bag record /arena_camera_node/images"
echo "=============================================="
echo ""

exec "$@"
