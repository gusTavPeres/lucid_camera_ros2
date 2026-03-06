#!/usr/bin/env python3
# pyright: reportMissingImports=false
"""
Pipeline completo com arquivo único de configuração.

Uso:
  ros2 launch arena_camera_node camera_pipeline.launch.py
  ros2 launch arena_camera_node camera_pipeline.launch.py config_file:=/path/pipeline.yaml
"""

import os

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def _topic_to_transport_param_base(topic: str) -> str:
    return topic.lstrip("/").replace("/", ".")


def generate_pipeline_nodes(context):
    config_file = LaunchConfiguration("config_file").perform(context)
    nodes = []

    if config_file and os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}

        cameras = config.get("cameras", [])
        for cam in cameras:
            cam_name = cam.get("name", "camera")
            # Serial: .env tem precedência (CAMERA_1_SERIAL, CAMERA_2_SERIAL, etc)
            env_key = f"{cam_name.upper().replace('-', '_')}_SERIAL"
            serial_from_env = os.environ.get(env_key, "").strip()
            serial = serial_from_env if serial_from_env else cam.get("serial", "")
            if serial_from_env:
                print(f"[camera_pipeline] {cam_name}: serial from .env ({env_key}) = {serial}")
            camera_topic = cam.get("topic", "/arena_camera_node/images")
            camera_node = Node(
                package="arena_camera_node",
                executable="start",
                name=cam_name,
                output="screen",
                parameters=[
                    {
                        "serial": serial,
                        "topic": camera_topic,
                        "pixelformat": cam.get("pixelformat", "rgb8"),
                        "gain": cam.get("gain", 0.0),
                        "exposure_time": cam.get("exposure_time", 10000.0),
                        "exposure_auto": cam.get("exposure_auto", True),
                        "frame_rate": cam.get("frame_rate", -1.0),
                        "frame_id": cam.get("frame_id", "camera_optical_frame"),
                        "qos_reliability": cam.get("qos_reliability", "reliable"),
                        "trigger_mode": cam.get("trigger_mode", False),
                        "device_link_throughput_limit": cam.get(
                            "device_link_throughput_limit", 0
                        ),
                    }
                ],
            )
            nodes.append(camera_node)

            resizer = cam.get("resizer", {})
            if not resizer or not resizer.get("enabled", True):
                continue

            output_topic = resizer.get("output_topic", f"{camera_topic}_new")
            param_base = _topic_to_transport_param_base(output_topic)

            compression = resizer.get("compression", {})
            resizer_params = {
                "input_topic": resizer.get("input_topic", camera_topic),
                "output_topic": output_topic,
                "output_width": resizer.get("output_width", 640),
                "output_height": resizer.get("output_height", 480),
                "interpolation": resizer.get("interpolation", "linear"),
                "qos_reliability": resizer.get("qos_reliability", "best_effort"),
                f"{param_base}.compressed.format": compression.get("format", "jpeg"),
                f"{param_base}.compressed.jpeg_quality": compression.get(
                    "jpeg_quality", 80
                ),
                f"{param_base}.compressed.jpeg_compress_bayer": compression.get(
                    "jpeg_compress_bayer", False
                ),
                f"{param_base}.compressed.png_level": compression.get("png_level", 3),
            }

            resizer_node = Node(
                package="arena_camera_node",
                executable="image_resizer",
                name=resizer.get("name", f"{cam.get('name', 'camera')}_resizer"),
                output="screen",
                parameters=[resizer_params],
            )
            nodes.append(resizer_node)

    return nodes


def generate_launch_description():
    pkg_share = get_package_share_directory("arena_camera_node")
    default_config = os.path.join(pkg_share, "config", "cameras.yaml")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "config_file",
                default_value=default_config,
                description="Arquivo YAML único com câmera + resize/compressão",
            ),
            OpaqueFunction(function=generate_pipeline_nodes),
        ]
    )
