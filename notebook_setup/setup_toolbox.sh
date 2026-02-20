#!/bin/bash
# ============================================================================
# ROS2 Humble container setup for Fedora Kinoite / Silverblue
# ============================================================================
#
# Creates an Ubuntu 22.04 container with ROS2 Humble and required dependencies.
# Supports both Toolbox and Distrobox (preferred on newer Fedora).
#
# Usage:
#   bash setup_toolbox.sh [--distrobox]
#
# After running, enter the container with:
#   distrobox enter ros2-humble    (if using distrobox)
#   toolbox enter ros2-humble      (if using toolbox)
#
# ============================================================================

set -e

CONTAINER_NAME="ros2-humble"
UBUNTU_VERSION="22.04"

# Prefer distrobox if available, fall back to toolbox
USE_DISTROBOX=false
if [[ "$1" == "--distrobox" ]] || command -v distrobox &>/dev/null; then
    USE_DISTROBOX=true
fi

echo "============================================"
echo "ROS2 Humble Container Setup"
echo "============================================"
echo ""

if $USE_DISTROBOX; then
    if ! command -v distrobox &>/dev/null; then
        echo "Error: distrobox not found."
        echo "Install with: rpm-ostree install distrobox  (then reboot)"
        echo "Or use toolbox: bash setup_toolbox.sh (without --distrobox)"
        exit 1
    fi

    echo "Using distrobox..."
    if distrobox list 2>/dev/null | grep -q "$CONTAINER_NAME"; then
        echo "Container '$CONTAINER_NAME' already exists."
        read -p "Recreate it? [y/N]: " -n 1 -r; echo
        [[ $REPLY =~ ^[Yy]$ ]] && distrobox rm -f "$CONTAINER_NAME" || { echo "Using existing."; exit 0; }
    fi

    distrobox create "$CONTAINER_NAME" \
        --image "docker.io/library/ubuntu:$UBUNTU_VERSION" \
        --home "$HOME"

    RUN_CMD="distrobox enter $CONTAINER_NAME --"
else
    if ! command -v toolbox &>/dev/null; then
        echo "Error: neither toolbox nor distrobox found."
        echo "Install distrobox: rpm-ostree install distrobox"
        exit 1
    fi

    echo "Using toolbox..."
    if toolbox list | grep -q "$CONTAINER_NAME"; then
        echo "Container '$CONTAINER_NAME' already exists."
        read -p "Recreate it? [y/N]: " -n 1 -r; echo
        [[ $REPLY =~ ^[Yy]$ ]] && toolbox rm -f "$CONTAINER_NAME" || { echo "Using existing."; exit 0; }
    fi

    toolbox create "$CONTAINER_NAME" --image "docker.io/library/ubuntu:$UBUNTU_VERSION"
    RUN_CMD="toolbox run -c $CONTAINER_NAME"
fi

echo ""
echo "Installing ROS2 Humble inside the container (this takes a few minutes)..."
echo ""

$RUN_CMD bash -c '
set -e

# Atualizar repositórios
echo "⏳ Atualizando repositórios..."
sudo apt update -qq

# Instalar dependências base
echo "📦 Instalando dependências base..."
sudo apt install -y -qq \
    software-properties-common \
    curl \
    gnupg \
    lsb-release \
    locales \
    git \
    wget

# Configurar locale
echo "🌍 Configurando locale..."
sudo locale-gen en_US.UTF-8
export LANG=en_US.UTF-8

# Adicionar repositório ROS2
echo "📥 Adicionando repositório ROS2..."
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# Atualizar novamente
sudo apt update -qq

# Instalar ROS2 Humble Desktop
echo "🤖 Instalando ROS2 Humble Desktop..."
sudo apt install -y -qq ros-humble-desktop

# Instalar ferramentas de desenvolvimento
echo "🛠️  Instalando ferramentas de desenvolvimento..."
sudo apt install -y -qq \
    python3-colcon-common-extensions \
    python3-rosdep \
    python3-argcomplete \
    python3-pip

# Instalar dependências Python
echo "🐍 Instalando dependências Python..."
sudo apt install -y -qq \
    ros-humble-cv-bridge \
    ros-humble-image-transport \
    ros-humble-image-transport-plugins \
    ros-humble-rqt-image-view \
    python3-opencv

# Inicializar rosdep
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    echo "🔧 Inicializando rosdep..."
    sudo rosdep init
fi
rosdep update

# Criar arquivo de setup automático
echo "📝 Configurando auto-source do ROS2..."
if ! grep -q "source /opt/ros/humble/setup.bash" ~/.bashrc; then
    cat >> ~/.bashrc << "EOF"

# ============================================
# ROS2 Humble Setup
# ============================================
source /opt/ros/humble/setup.bash

# Configuração de rede ROS2
export ROS_DOMAIN_ID=42  # Ajuste se necessário
export ROS_LOCALHOST_ONLY=0  # Permitir comunicação entre PCs

# Aliases úteis
alias ros2-topics="ros2 topic list"
alias ros2-nodes="ros2 node list"
alias ros2-stream="ros2 run rqt_image_view rqt_image_view"

echo "🤖 ROS2 Humble ativado!"
EOF
fi

echo ""
echo "Installation complete!"
'

echo ""
echo "============================================"
echo "Setup complete!"
echo "============================================"
echo ""
if $USE_DISTROBOX; then
    echo "Enter the container with:"
    echo "  distrobox enter $CONTAINER_NAME"
else
    echo "Enter the container with:"
    echo "  toolbox enter $CONTAINER_NAME"
fi
echo ""
echo "Next step: configure FastDDS for multi-machine streaming:"
echo "  See README.md -> Multi-machine streaming"
echo ""
