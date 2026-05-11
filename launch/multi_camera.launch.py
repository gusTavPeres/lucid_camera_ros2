#!/usr/bin/env python3
"""
Launch file para múltiplas câmeras Lucid Vision.

Uso:
    ros2 launch /arena_camera_ros2/launch/multi_camera.launch.py

Com arquivo de configuração:
    ros2 launch /arena_camera_ros2/launch/multi_camera.launch.py config_file:=/path/to/cameras.yaml
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import yaml


def generate_camera_nodes(context):
    """Gera os nodes de câmera baseado na configuração."""
    config_file = LaunchConfiguration("config_file").perform(context)
    nodes = []

    if config_file and os.path.exists(config_file):
        # Carregar configuração do arquivo YAML
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        cameras = config.get("cameras", [])
        for cam in cameras:
            node = Node(
                package="arena_camera_node",
                executable="start",
                name=cam.get("name", f"camera_{cam.get('serial', 'unknown')}"),
                parameters=[
                    {
                        "serial": cam.get("serial", ""),
                        "topic": cam.get("topic", "/arena_camera_node/images"),
                        "width": cam.get("width", 0),
                        "height": cam.get("height", 0),
                        "pixelformat": cam.get("pixelformat", "rgb8"),
                        "gain": cam.get("gain", 0.0),
                        "exposure_time": cam.get("exposure_time", 10000.0),
                        "frame_rate": cam.get("frame_rate", 0.0),
                        "qos_reliability": cam.get("qos_reliability", "reliable"),
                        "trigger_mode": cam.get("trigger_mode", False),
                    }
                ],
                output="screen",
            )
            nodes.append(node)
    else:
        # Configuração padrão: uma câmera
        node = Node(
            package="arena_camera_node",
            executable="start",
            name="arena_camera_node",
            parameters=[
                {
                    "topic": "/arena_camera_node/images",
                    "pixelformat": "rgb8",
                    "qos_reliability": "reliable",
                }
            ],
            output="screen",
        )
        nodes.append(node)

    return nodes


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "config_file",
                default_value="",
                description="Caminho para arquivo YAML de configuração das câmeras",
            ),
            OpaqueFunction(function=generate_camera_nodes),
        ]
    )
