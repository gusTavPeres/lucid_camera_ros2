#!/usr/bin/env python3
"""
Top-level launch — brings up Lucid cameras and/or Ouster LiDAR.

Args:
    enable_camera        (bool) — include the lucid camera stack. Default: true.
    enable_lidar         (bool) — include the ouster_ros driver.  Default: true.
    enable_remote_bridge (bool) — placeholder for a future foxglove_bridge.
                                  Default: false (we do pure FastDDS today).
    camera_config        (path) — cameras.yaml for multi_camera.launch.py.
                                  Default: /arena_camera_ros2/config/cameras.yaml.
    lidar_params         (path) — Ouster params yaml (rendered by entrypoint).
                                  Default: /tmp/lidar_params.yaml.

For beginners — what this file does:
    A ROS 2 launch file is a Python function that returns a LaunchDescription:
    a list of "actions". Here the actions are mostly IncludeLaunchDescription
    objects — they pull in OTHER launch files (the existing lucid one, plus
    Ouster's sensor.composite.launch.py from the installed ouster_ros package).
    `IfCondition` makes each include conditional on a boolean launch arg.
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, LogInfo
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    # ---- Declare the launch-level args (with documented defaults) ---------
    args = [
        DeclareLaunchArgument(
            'enable_camera', default_value='true',
            description='Include the Lucid camera stack (multi_camera.launch.py)'),
        DeclareLaunchArgument(
            'enable_lidar', default_value='true',
            description='Include the Ouster LiDAR driver'),
        DeclareLaunchArgument(
            'enable_remote_bridge', default_value='false',
            description='Placeholder for a future bridge (foxglove/rosbridge). '
                        'Disabled today — remote viz uses raw FastDDS over Netbird.'),
        DeclareLaunchArgument(
            'camera_config',
            default_value='/arena_camera_ros2/config/cameras.yaml',
            description='YAML config consumed by multi_camera.launch.py'),
        DeclareLaunchArgument(
            'lidar_params',
            default_value='/tmp/lidar_params.yaml',
            description='Ouster driver params YAML (rendered by entrypoint)'),
    ]

    # ---- Camera include -----------------------------------------------------
    # The existing multi_camera.launch.py spawns one arena_camera_node per
    # entry in cameras.yaml. We pass its path through as a launch argument.
    camera_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            '/arena_camera_ros2/launch/multi_camera.launch.py'
        ),
        launch_arguments={
            'config_file': LaunchConfiguration('camera_config'),
        }.items(),
        condition=IfCondition(LaunchConfiguration('enable_camera')),
    )

    # ---- LiDAR include ------------------------------------------------------
    # ouster_ros ships a composite Python launch that:
    #   - creates a LifecycleNode for os_driver
    #   - reads its params from `params_file`
    #   - drives the lifecycle: configure -> activate
    #   - shuts down cleanly if the sensor can't be reached
    # We disable its rviz (we run no viz inside the container).
    ouster_pkg = get_package_share_directory('ouster_ros')
    ouster_launch_path = os.path.join(ouster_pkg, 'launch',
                                      'sensor.composite.launch.py')
    lidar_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(ouster_launch_path),
        launch_arguments={
            'params_file': LaunchConfiguration('lidar_params'),
            'viz': 'False',
            'ouster_ns': 'ouster',
        }.items(),
        condition=IfCondition(LaunchConfiguration('enable_lidar')),
    )

    # ---- Diagnostic banner --------------------------------------------------
    banner = LogInfo(msg=[
        '[sensor_stack] enable_camera=', LaunchConfiguration('enable_camera'),
        ' enable_lidar=', LaunchConfiguration('enable_lidar'),
        ' enable_remote_bridge=', LaunchConfiguration('enable_remote_bridge'),
    ])

    return LaunchDescription(args + [banner, camera_launch, lidar_launch])
