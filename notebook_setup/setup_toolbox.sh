#!/bin/bash
# ============================================================================
# Setup do Toolbox com ROS2 Humble no Fedora Kinoite/Silverblue
# ============================================================================
#
# Este script:
# 1. Cria um container Toolbox com Ubuntu 22.04
# 2. Instala ROS2 Humble
# 3. Instala dependências necessárias (cv_bridge, rqt, etc)
# 4. Configura o ambiente ROS2
#
# Uso:
#   bash setup_toolbox.sh
#
# Depois de rodar este script, entre no toolbox com:
#   toolbox enter ros2-humble
#
# ============================================================================

set -e  # Sair em caso de erro

TOOLBOX_NAME="ros2-humble"
UBUNTU_VERSION="22.04"

echo "============================================"
echo "🚀 Setup ROS2 Humble Toolbox"
echo "============================================"
echo ""

# Verificar se Toolbox está instalado
if ! command -v toolbox &> /dev/null; then
    echo "❌ Toolbox não encontrado!"
    echo "   Instale com: rpm-ostree install toolbox"
    echo "   Depois reinicie o sistema."
    exit 1
fi

# Criar Toolbox com Ubuntu 22.04
echo "📦 Criando Toolbox '$TOOLBOX_NAME' com Ubuntu $UBUNTU_VERSION..."
if toolbox list | grep -q "$TOOLBOX_NAME"; then
    echo "⚠️  Toolbox '$TOOLBOX_NAME' já existe."
    read -p "   Deseja recriar? (apagará o atual) [y/N]: " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        toolbox rm -f "$TOOLBOX_NAME"
    else
        echo "✅ Usando Toolbox existente."
        exit 0
    fi
fi

toolbox create "$TOOLBOX_NAME" --image docker.io/library/ubuntu:$UBUNTU_VERSION

echo ""
echo "✅ Toolbox criado!"
echo ""
echo "📥 Instalando ROS2 Humble e dependências dentro do Toolbox..."
echo "   (Isso pode levar alguns minutos...)"
echo ""

# Executar comandos dentro do Toolbox
toolbox run -c "$TOOLBOX_NAME" bash -c '
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
echo "✅ Instalação completa!"
'

echo ""
echo "============================================"
echo "✅ Setup concluído com sucesso!"
echo "============================================"
echo ""
echo "Para entrar no Toolbox:"
echo "  toolbox enter $TOOLBOX_NAME"
echo ""
echo "Comandos úteis:"
echo "  ros2 topic list           - Listar tópicos disponíveis"
echo "  ros2 topic hz <topic>     - Ver FPS de um tópico"
echo "  ros2 run rqt_image_view rqt_image_view  - Visualizar câmera"
echo ""
echo "Próximo passo: configurar a rede (ver README.md)"
echo ""
