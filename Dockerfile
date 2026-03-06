# Lucid Vision Camera - ROS2 Humble (minimum camera runtime)

FROM ros:humble-ros-core

ENV RMW_IMPLEMENTATION=rmw_fastrtps_cpp
ENV ROS_SUPER_CLIENT=true
ENV ROS_DOMAIN_ID=0

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    python3-colcon-common-extensions \
    python3-pip \
    ros-humble-rmw-fastrtps-cpp \
    libatomic1 \
    libcurl4 \
    librdmacm-dev \
    libibverbs-dev \
    iproute2 \
    iputils-ping \
    net-tools \
    ethtool \
    ros-humble-image-transport \
    ros-humble-image-transport-plugins \
    ros-humble-cv-bridge \
    ros-humble-rqt-image-view \
    ros-humble-rviz2 \
    && rm -rf /var/lib/apt/lists/*

ARG arenasdk_root_on_host=./resources/ArenaSDK/linux64
ARG arenasdk_parent=/
ARG arena_api_root_on_host=./resources/arena_api
ARG arena_api_parent=/arena_api

# ArenaSDK runtime
ADD ${arenasdk_root_on_host}/*.tar.gz ${arenasdk_parent}
RUN echo "/ArenaSDK_Linux_x64/lib64" > /etc/ld.so.conf.d/Arena_SDK.conf && \
    echo "/ArenaSDK_Linux_x64/GenICam/library/lib/Linux64_x64" >> /etc/ld.so.conf.d/Arena_SDK.conf && \
    echo "/ArenaSDK_Linux_x64/ffmpeg" >> /etc/ld.so.conf.d/Arena_SDK.conf && \
    echo "/ArenaSDK_Linux_x64/Metavision/lib" >> /etc/ld.so.conf.d/Arena_SDK.conf && \
    echo "/ArenaSDK_Linux_x64/OpenCV/lib" >> /etc/ld.so.conf.d/Arena_SDK.conf && \
    ldconfig

# ============================================================================
# CONFIGURAÇÃO DE REDE PARA CÂMERAS GigE
# ============================================================================

# Configurar buffers de rede para múltiplas câmeras de alta resolução
RUN echo 'net.core.rmem_default=33554432' >> /etc/sysctl.conf && \
    echo 'net.core.rmem_max=134217728' >> /etc/sysctl.conf && \
    echo 'net.core.wmem_default=33554432' >> /etc/sysctl.conf && \
    echo 'net.core.wmem_max=134217728' >> /etc/sysctl.conf

ENV ARENA_ROOT=/ArenaSDK_Linux_x64
ENV GENICAM_GENTL64_PATH=/ArenaSDK_Linux_x64/lib64
ENV LD_LIBRARY_PATH=/ArenaSDK_Linux_x64/lib64:/ArenaSDK_Linux_x64/GenICam/library/lib/Linux64_x64:/ArenaSDK_Linux_x64/ffmpeg:/ArenaSDK_Linux_x64/Metavision/lib:/ArenaSDK_Linux_x64/OpenCV/lib:${LD_LIBRARY_PATH:-}

# Optional Python SDK used by helper tools (list cameras, diagnostics)
ADD ${arena_api_root_on_host}/*.whl ${arena_api_parent}/
RUN pip3 install --no-cache-dir ${arena_api_parent}/*.whl

WORKDIR /arena_camera_ros2/ros2_ws
COPY ./ros2_ws/src ./src
RUN /bin/bash -lc "source /opt/ros/humble/setup.bash && colcon build --symlink-install"

# Copy and setup the entrypoint script
COPY entrypoint.sh /root/entrypoint.sh
RUN chmod +x /root/entrypoint.sh

# Set the entrypoint
ENTRYPOINT ["/root/entrypoint.sh"]

CMD ["bash"]