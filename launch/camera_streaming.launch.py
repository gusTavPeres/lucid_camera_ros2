#!/usr/bin/env python3
"""
Launch file otimizado para streaming de câmera Lucid Vision.

Este launch:
1. Inicia a câmera em modo RAW (bayer_rggb8)
2. Opcionalmente inicia relay de compressão JPEG (Bayer → RGB → JPEG)

Uso:
    ros2 launch /arena_camera_ros2/launch/camera_streaming.launch.py serial:=SEU_SERIAL
    ros2 launch /arena_camera_ros2/launch/camera_streaming.launch.py \
        serial:=SEU_SERIAL enable_compressed:=true jpeg_quality:=80

Parâmetros:
    serial            - Serial da câmera
    topic_base        - Tópico base (padrão: /camera/image_raw)
    pixelformat       - Formato do pixel (padrão: bayer_rggb8)
    width             - Largura (padrão: 0 = máximo da câmera)
    height            - Altura (padrão: 0 = máximo da câmera)
    enable_compressed - Publicar versão comprimida (padrão: false)
    jpeg_quality      - Qualidade JPEG 1-100 (padrão: 80)
    qos_reliability   - best_effort ou reliable (padrão: best_effort para streaming)
    workers           - Número de workers JPEG (padrão: 4)
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_nodes(context):
    topic_base = LaunchConfiguration('topic_base').perform(context)
    jpeg_quality = LaunchConfiguration('jpeg_quality').perform(context)
    workers = LaunchConfiguration('workers').perform(context)
    enable_compressed = LaunchConfiguration('enable_compressed').perform(context).lower()

    # Find compress_bayer_stream.py relative to this launch file
    launch_dir = os.path.dirname(os.path.abspath(__file__))
    repo_dir = os.path.dirname(launch_dir)
    compress_script = os.path.join(repo_dir, 'scripts', 'compress_bayer_stream.py')

    nodes = [
        Node(
            package='arena_camera_node',
            executable='start',
            name='arena_camera_node',
            parameters=[{
                'serial': LaunchConfiguration('serial').perform(context),
                'topic': topic_base,
                'pixelformat': LaunchConfiguration('pixelformat').perform(context),
                'width': int(LaunchConfiguration('width').perform(context)),
                'height': int(LaunchConfiguration('height').perform(context)),
                'qos_reliability': LaunchConfiguration('qos_reliability').perform(context),
                'exposure_time': float(LaunchConfiguration('exposure_time').perform(context)),
                'gain': float(LaunchConfiguration('gain').perform(context)),
            }],
            output='screen'
        )
    ]

    if enable_compressed in ('true', '1', 'yes'):
        nodes.append(ExecuteProcess(
            cmd=[
                'python3', compress_script,
                '--input', topic_base,
                '--output', f'{topic_base}/compressed',
                '--quality', jpeg_quality,
                '--workers', workers,
            ],
            output='screen',
            name='compress_relay',
        ))

    return nodes


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('serial', default_value='', description='Serial da câmera Lucid'),
        DeclareLaunchArgument('topic_base', default_value='/camera/image_raw', description='Tópico base'),
        DeclareLaunchArgument('pixelformat', default_value='bayer_rggb8', description='Formato do pixel'),
        DeclareLaunchArgument('width', default_value='0', description='Largura (0=máximo)'),
        DeclareLaunchArgument('height', default_value='0', description='Altura (0=máximo)'),
        DeclareLaunchArgument('enable_compressed', default_value='false', description='Habilitar JPEG'),
        DeclareLaunchArgument('jpeg_quality', default_value='80', description='Qualidade JPEG (1-100)'),
        DeclareLaunchArgument('workers', default_value='4', description='Workers JPEG paralelos'),
        DeclareLaunchArgument('qos_reliability', default_value='best_effort', description='QoS reliability'),
        DeclareLaunchArgument('exposure_time', default_value='25000', description='Exposição em µs'),
        DeclareLaunchArgument('gain', default_value='0.0', description='Ganho da câmera'),
        OpaqueFunction(function=generate_nodes),
    ])
