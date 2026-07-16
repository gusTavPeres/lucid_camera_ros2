FROM osrf/ros:humble-desktop

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-opencv \
    ros-humble-cv-bridge \
    ros-humble-image-transport \
    ros-humble-rqt-image-view \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /twizy_viewer

CMD ["bash"]
