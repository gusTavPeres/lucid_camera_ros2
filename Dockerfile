# Lucid Vision Camera - ROS2 Humble
# Projeto: Carro Autônomo - Câmeras Triton TRI032S
# Suporte para múltiplas câmeras (escalável para 8+)

FROM osrf/ros:humble-desktop

# Evitar prompts interativos durante instalação
ENV DEBIAN_FRONTEND=noninteractive

# Atualizar sistema base
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-numpy \
    wget \
    curl \
    git \
    net-tools \
    iputils-ping \
    iproute2 \
    # Dependências do ArenaSDK
    g++ \
    make \
    libatomic1 \
    librdmacm-dev \
    libibverbs-dev \
    libcurl4 \
    # Dependências gráficas
    libxcb1-dev \
    libx11-xcb-dev \
    libglu1-mesa-dev \
    libxrender-dev \
    libxi-dev \
    libxkbcommon-dev \
    libxkbcommon-x11-dev \
    libglew-dev \
    libglm-dev \
    libglfw3-dev \
    # ROS2 ferramentas adicionais
    ros-humble-image-tools \
    ros-humble-image-transport \
    ros-humble-cv-bridge \
    ros-humble-rqt-image-view \
    ros-humble-rviz2 \
    ros-humble-rosbag2 \
    ros-humble-rosbag2-storage-mcap \
    && rm -rf /var/lib/apt/lists/*

# Instalar CMake 3.17+ (necessário para ArenaSDK)
RUN wget -qO- "https://cmake.org/files/v3.17/cmake-3.17.0-Linux-x86_64.tar.gz" | tar --strip-components=1 -xz -C /usr/local

# ============================================================================
# ARENA SDK
# ============================================================================

# Argumentos para localização dos arquivos SDK
ARG arenasdk_root_on_host=./resources/ArenaSDK/linux64
ARG arenasdk_parent=/
ARG arenasdk_root=${arenasdk_parent}/ArenaSDK_Linux_x64

ARG arena_api_root_on_host=./resources/arena_api
ARG arena_api_parent=/arena_api

# Copiar e extrair ArenaSDK
ADD ${arenasdk_root_on_host}/*.tar.gz ${arenasdk_parent}

# Configurar ArenaSDK manualmente (criar Arena_SDK.conf)
# Usando caminho fixo pois ARGs não expandem em RUN
RUN echo "/ArenaSDK_Linux_x64/lib64" > /etc/ld.so.conf.d/Arena_SDK.conf && \
    echo "/ArenaSDK_Linux_x64/GenICam/library/lib/Linux64_x64" >> /etc/ld.so.conf.d/Arena_SDK.conf && \
    echo "/ArenaSDK_Linux_x64/ffmpeg" >> /etc/ld.so.conf.d/Arena_SDK.conf && \
    echo "/ArenaSDK_Linux_x64/Metavision/lib" >> /etc/ld.so.conf.d/Arena_SDK.conf && \
    echo "/ArenaSDK_Linux_x64/OpenCV/lib" >> /etc/ld.so.conf.d/Arena_SDK.conf && \
    ldconfig && \
    echo "Arena_SDK.conf criado:" && cat /etc/ld.so.conf.d/Arena_SDK.conf

# Configurar variáveis de ambiente do ArenaSDK
ENV ARENA_ROOT=/ArenaSDK_Linux_x64
ENV GENICAM_GENTL64_PATH=/ArenaSDK_Linux_x64/lib64
ENV LD_LIBRARY_PATH=/ArenaSDK_Linux_x64/lib64:/ArenaSDK_Linux_x64/GenICam/library/lib/Linux64_x64:/ArenaSDK_Linux_x64/ffmpeg:/ArenaSDK_Linux_x64/Metavision/lib:/ArenaSDK_Linux_x64/OpenCV/lib:${LD_LIBRARY_PATH}

# ============================================================================
# ARENA API (Python)
# ============================================================================

ADD ${arena_api_root_on_host}/*.whl ${arena_api_parent}/
RUN pip3 install ${arena_api_parent}/*.whl

# ============================================================================
# CONFIGURAÇÃO DE REDE PARA CÂMERAS GigE
# ============================================================================

# Configurar buffers de rede para múltiplas câmeras de alta resolução
RUN echo 'net.core.rmem_default=33554432' >> /etc/sysctl.conf && \
    echo 'net.core.rmem_max=134217728' >> /etc/sysctl.conf && \
    echo 'net.core.wmem_default=33554432' >> /etc/sysctl.conf && \
    echo 'net.core.wmem_max=134217728' >> /etc/sysctl.conf

# ============================================================================
# WORKSPACE ROS2
# ============================================================================

WORKDIR /arena_camera_ros2/ros2_ws

# Copiar entrypoint
COPY ./scripts/arena_camera_ros_entrypoint.sh /
RUN chmod +x /arena_camera_ros_entrypoint.sh

# Copiar launch files
COPY ./launch /arena_camera_ros2/launch

ENTRYPOINT ["/arena_camera_ros_entrypoint.sh"]
CMD ["bash"]
