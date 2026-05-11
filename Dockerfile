# Lucid Vision Camera + Ouster LiDAR — ROS 2 Humble
# Single container, single workspace. Both drivers built here.
#
# Build context: parent directory of the lucid repo (so COPY can reach
# both lucid_camera_ros2/ and ouster-ros-humble-devel/ side-by-side).
# This is configured in docker-compose.yml: build.context: ..
#
# Project: Autonomous car — Triton TRI032S cameras + Ouster LiDAR

FROM osrf/ros:humble-desktop

ENV DEBIAN_FRONTEND=noninteractive

# Base system upgrade
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# --------------------------------------------------------------------------- #
# System + ROS apt deps (lucid + ouster combined)
# --------------------------------------------------------------------------- #
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-numpy \
    wget \
    curl \
    git \
    net-tools \
    iputils-ping \
    iproute2 \
    ethtool \
    g++ \
    make \
    libatomic1 \
    librdmacm-dev \
    libibverbs-dev \
    libcurl4 \
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
    ros-humble-image-tools \
    ros-humble-image-transport \
    ros-humble-image-transport-plugins \
    ros-humble-topic-tools \
    ros-humble-cv-bridge \
    ros-humble-rqt-image-view \
    ros-humble-rviz2 \
    ros-humble-rosbag2 \
    ros-humble-rosbag2-storage-mcap \
    build-essential \
    cmake \
    python3-colcon-common-extensions \
    python3-rosdep \
    libpcap-dev \
    libjsoncpp-dev \
    libeigen3-dev \
    libcap-dev \
    libtins-dev \
    ros-humble-pcl-conversions \
    ros-humble-pcl-ros \
    ros-humble-tf2-eigen \
    ros-humble-tf2-ros \
    ros-humble-lifecycle-msgs \
    ros-humble-rclcpp-lifecycle \
    ros-humble-rclcpp-components \
    gettext-base \
    && rm -rf /var/lib/apt/lists/*

# CMake 3.17+ required by ArenaSDK (overrides the apt cmake)
RUN wget -qO- "https://cmake.org/files/v3.17/cmake-3.17.0-Linux-x86_64.tar.gz" \
    | tar --strip-components=1 -xz -C /usr/local

# --------------------------------------------------------------------------- #
# ArenaSDK
# --------------------------------------------------------------------------- #
ARG arenasdk_root_on_host=./lucid_camera_ros2/resources/ArenaSDK/linux64
ARG arenasdk_parent=/
ARG arenasdk_root=${arenasdk_parent}/ArenaSDK_Linux_x64

ARG arena_api_root_on_host=./lucid_camera_ros2/resources/arena_api
ARG arena_api_parent=/arena_api

ADD ${arenasdk_root_on_host}/*.tar.gz ${arenasdk_parent}

RUN echo "/ArenaSDK_Linux_x64/lib64" > /etc/ld.so.conf.d/Arena_SDK.conf && \
    echo "/ArenaSDK_Linux_x64/GenICam/library/lib/Linux64_x64" >> /etc/ld.so.conf.d/Arena_SDK.conf && \
    echo "/ArenaSDK_Linux_x64/ffmpeg" >> /etc/ld.so.conf.d/Arena_SDK.conf && \
    echo "/ArenaSDK_Linux_x64/Metavision/lib" >> /etc/ld.so.conf.d/Arena_SDK.conf && \
    echo "/ArenaSDK_Linux_x64/OpenCV/lib" >> /etc/ld.so.conf.d/Arena_SDK.conf && \
    ldconfig

ENV ARENA_ROOT=/ArenaSDK_Linux_x64
ENV GENICAM_GENTL64_PATH=/ArenaSDK_Linux_x64/lib64
ENV LD_LIBRARY_PATH=/ArenaSDK_Linux_x64/lib64:/ArenaSDK_Linux_x64/GenICam/library/lib/Linux64_x64:/ArenaSDK_Linux_x64/ffmpeg:/ArenaSDK_Linux_x64/Metavision/lib:/ArenaSDK_Linux_x64/OpenCV/lib:${LD_LIBRARY_PATH}

# Arena Python API
ADD ${arena_api_root_on_host}/*.whl ${arena_api_parent}/
RUN pip3 install ${arena_api_parent}/*.whl

# --------------------------------------------------------------------------- #
# Kernel buffers for GigE Vision (also set on host by host_setup.sh)
# --------------------------------------------------------------------------- #
RUN echo 'net.core.rmem_default=33554432' >> /etc/sysctl.conf && \
    echo 'net.core.rmem_max=134217728'     >> /etc/sysctl.conf && \
    echo 'net.core.wmem_default=33554432' >> /etc/sysctl.conf && \
    echo 'net.core.wmem_max=134217728'     >> /etc/sysctl.conf

# --------------------------------------------------------------------------- #
# Vendor ouster_ros into the image (NOT into ros2_ws/src yet — the host bind
# mount would hide it; entrypoint copies it into src/ on first start)
# --------------------------------------------------------------------------- #
COPY ./ouster-ros-humble-devel/ouster-ros          /opt/vendor/ouster_ros
COPY ./ouster-ros-humble-devel/ouster-sensor-msgs  /opt/vendor/ouster_sensor_msgs

# Pre-warm rosdep so first container start can resolve any extra deps offline
RUN rosdep update --rosdistro humble || true

# --------------------------------------------------------------------------- #
# Workspace + lucid sources (same shape as before)
# --------------------------------------------------------------------------- #
WORKDIR /arena_camera_ros2/ros2_ws

COPY ./lucid_camera_ros2/scripts/arena_camera_ros_entrypoint.sh /
RUN chmod +x /arena_camera_ros_entrypoint.sh

COPY ./lucid_camera_ros2/launch          /arena_camera_ros2/launch
COPY ./lucid_camera_ros2/scripts         /arena_camera_ros2/scripts
COPY ./lucid_camera_ros2/notebook_setup  /arena_camera_ros2/notebook_setup
COPY ./lucid_camera_ros2/config          /arena_camera_ros2/config

# Make every script executable in one shot (idempotent)
RUN find /arena_camera_ros2/scripts -name '*.sh' -exec chmod +x {} \;

ENTRYPOINT ["/arena_camera_ros_entrypoint.sh"]
CMD ["bash"]
