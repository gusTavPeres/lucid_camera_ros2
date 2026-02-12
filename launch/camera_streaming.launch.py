#!/usr/bin/env python3
"""
Launch file otimizado para streaming de câmera Lucid Vision.

Este launch:
1. Inicia a câmera em modo RAW (bayer_rggb8) a 35fps
2. Opcionalmente publica versão comprimida (Bayer → RGB → JPEG)

Uso:
    # Streaming RAW (padrão - menor banda, demosaicing no receptor)
    ros2 launch /arena_camera_ros2/launch/camera_streaming.launch.py serial:=SEU_SERIAL

    # Streaming com compressão JPEG (maior processamento, compatível com mais viewers)
    ros2 launch /arena_camera_ros2/launch/camera_streaming.launch.py \
        serial:=SEU_SERIAL \
        enable_compressed:=true \
        jpeg_quality:=80

Parâmetros:
    serial            - Serial da câmera
    topic_base        - Tópico base (padrão: /camera/image_raw)
    pixelformat       - Formato do pixel (padrão: bayer_rggb8)
    width             - Largura (padrão: 0 = máximo da câmera)
    height            - Altura (padrão: 0 = máximo da câmera)
    enable_compressed - Publicar versão comprimida (padrão: false)
    jpeg_quality      - Qualidade JPEG 1-100 (padrão: 80)
    qos_reliability   - best_effort ou reliable (padrão: best_effort para streaming)
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, GroupAction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import Node, ComposableNodeContainer
from launch_ros.descriptions import ComposableNode


def generate_launch_description():
    # Argumentos do launch
    serial_arg = DeclareLaunchArgument(
        'serial',
        default_value='',
        description='Serial da câmera Lucid'
    )

    topic_base_arg = DeclareLaunchArgument(
        'topic_base',
        default_value='/camera/image_raw',
        description='Tópico base para publicação de imagens'
    )

    pixelformat_arg = DeclareLaunchArgument(
        'pixelformat',
        default_value='bayer_rggb8',
        description='Formato do pixel (bayer_rggb8, rgb8, bgr8, mono8)'
    )

    width_arg = DeclareLaunchArgument(
        'width',
        default_value='0',
        description='Largura da imagem (0 = máximo da câmera)'
    )

    height_arg = DeclareLaunchArgument(
        'height',
        default_value='0',
        description='Altura da imagem (0 = máximo da câmera)'
    )

    enable_compressed_arg = DeclareLaunchArgument(
        'enable_compressed',
        default_value='false',
        description='Habilitar publicação de imagem comprimida (JPEG)'
    )

    jpeg_quality_arg = DeclareLaunchArgument(
        'jpeg_quality',
        default_value='80',
        description='Qualidade de compressão JPEG (1-100)'
    )

    qos_reliability_arg = DeclareLaunchArgument(
        'qos_reliability',
        default_value='best_effort',
        description='QoS reliability: best_effort (streaming) ou reliable (gravação)'
    )

    exposure_time_arg = DeclareLaunchArgument(
        'exposure_time',
        default_value='10000',
        description='Tempo de exposição em microsegundos'
    )

    gain_arg = DeclareLaunchArgument(
        'gain',
        default_value='0.0',
        description='Ganho da câmera'
    )

    # Node da câmera
    camera_node = Node(
        package='arena_camera_node',
        executable='start',
        name='arena_camera_node',
        parameters=[{
            'serial': LaunchConfiguration('serial'),
            'topic': LaunchConfiguration('topic_base'),
            'pixelformat': LaunchConfiguration('pixelformat'),
            'width': LaunchConfiguration('width'),
            'height': LaunchConfiguration('height'),
            'qos_reliability': LaunchConfiguration('qos_reliability'),
            'exposure_time': LaunchConfiguration('exposure_time'),
            'gain': LaunchConfiguration('gain'),
        }],
        output='screen'
    )

    # Node de compressão (condicional)
    # Este node faz: Bayer → RGB → JPEG compress
    compress_node = Node(
        package='image_transport',
        executable='republish',
        name='image_compress_node',
        arguments=[
            'raw',
            'compressed',
            '--ros-args',
            '--remap', 'in:=' + LaunchConfiguration('topic_base').perform(None),
            '--remap', 'out/compressed:=' + LaunchConfiguration('topic_base').perform(None) + '/compressed',
            '-p', 'compressed.format:=jpeg',
            '-p', 'compressed.jpeg_quality:=' + LaunchConfiguration('jpeg_quality').perform(None),
        ],
        condition=IfCondition(LaunchConfiguration('enable_compressed')),
        output='screen'
    )

    return LaunchDescription([
        # Declarar argumentos
        serial_arg,
        topic_base_arg,
        pixelformat_arg,
        width_arg,
        height_arg,
        enable_compressed_arg,
        jpeg_quality_arg,
        qos_reliability_arg,
        exposure_time_arg,
        gain_arg,

        # Iniciar nodes
        camera_node,
        compress_node,
    ])
