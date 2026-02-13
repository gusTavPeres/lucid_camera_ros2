#!/usr/bin/env python3
"""
Script para comprimir stream Bayer em JPEG para economizar banda.

Este node:
1. Subscreve tópico RAW bayer_rggb8 (ex: /camera/image_raw)
2. Faz demosaicing (Bayer → RGB)
3. Comprime em JPEG
4. Publica em /camera/image_raw/compressed

Uso:
    python3 compress_bayer_stream.py --input /camera/image_raw --quality 80

Argumentos:
    --input    : Tópico de entrada (bayer_rggb8)
    --output   : Tópico de saída (padrão: <input>/compressed)
    --quality  : Qualidade JPEG 1-100 (padrão: 80)
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from sensor_msgs.msg import Image, CompressedImage
from cv_bridge import CvBridge
import cv2
import argparse


class BayerCompressor(Node):
    def __init__(self, input_topic, output_topic, jpeg_quality):
        super().__init__('bayer_compressor')

        self.bridge = CvBridge()
        self.jpeg_quality = jpeg_quality
        self.frame_count = 0

        # QoS para streaming (best effort)
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            depth=10
        )

        # Subscriber (Bayer RAW)
        self.sub = self.create_subscription(
            Image,
            input_topic,
            self.image_callback,
            qos_profile
        )

        # Publisher (Compressed JPEG)
        self.pub = self.create_publisher(
            CompressedImage,
            output_topic,
            qos_profile
        )

        # Detectar padrão Bayer
        # Nota: ROS2 Bayer naming é invertido vs OpenCV
        self.bayer_conversion = None
        self.bayer_patterns = {
            'bayer_rggb8': cv2.COLOR_BayerBG2BGR,
            'bayer_bggr8': cv2.COLOR_BayerRG2BGR,
            'bayer_gbrg8': cv2.COLOR_BayerGR2BGR,
            'bayer_grbg8': cv2.COLOR_BayerGB2BGR,
        }

        self.get_logger().info(f'📥 Subscrito: {input_topic}')
        self.get_logger().info(f'📤 Publicando: {output_topic}')
        self.get_logger().info(f'🗜️  Qualidade JPEG: {jpeg_quality}')

    def image_callback(self, msg):
        try:
            # Detectar padrão Bayer na primeira mensagem
            if self.bayer_conversion is None:
                encoding = msg.encoding.lower()
                if encoding in self.bayer_patterns:
                    self.bayer_conversion = self.bayer_patterns[encoding]
                    self.get_logger().info(f'🎨 Padrão Bayer detectado: {encoding}')
                else:
                    self.get_logger().error(
                        f'❌ Encoding não suportado: {encoding}. '
                        f'Esperado: bayer_rggb8, bayer_bggr8, bayer_gbrg8 ou bayer_grbg8'
                    )
                    return

            # Converter Bayer → BGR
            raw_img = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
            bgr_img = cv2.cvtColor(raw_img, self.bayer_conversion)

            # Comprimir em JPEG
            encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality]
            success, buffer = cv2.imencode('.jpg', bgr_img, encode_params)

            if not success:
                self.get_logger().warn('⚠️  Falha ao comprimir frame')
                return

            # Publicar mensagem comprimida
            compressed_msg = CompressedImage()
            compressed_msg.header = msg.header
            compressed_msg.format = 'jpeg'
            compressed_msg.data = buffer.tobytes()

            self.pub.publish(compressed_msg)

            self.frame_count += 1
            if self.frame_count % 100 == 0:
                original_size = len(msg.data) / 1024  # KB
                compressed_size = len(compressed_msg.data) / 1024  # KB
                ratio = (1 - compressed_size / original_size) * 100
                self.get_logger().info(
                    f'📊 Frames: {self.frame_count} | '
                    f'Original: {original_size:.1f}KB → '
                    f'Comprimido: {compressed_size:.1f}KB '
                    f'({ratio:.1f}% economia)'
                )

        except Exception as e:
            self.get_logger().error(f'❌ Erro: {e}')


def main(args=None):
    parser = argparse.ArgumentParser(
        description='Comprime stream Bayer em JPEG para economizar banda'
    )
    parser.add_argument(
        '--input',
        type=str,
        default='/camera/image_raw',
        help='Tópico de entrada (bayer_rggb8)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Tópico de saída (padrão: <input>/compressed)'
    )
    parser.add_argument(
        '--quality',
        type=int,
        default=80,
        help='Qualidade JPEG 1-100 (padrão: 80)'
    )

    parsed_args = parser.parse_args()

    # Definir tópico de saída
    output_topic = parsed_args.output
    if output_topic is None:
        output_topic = parsed_args.input + '/compressed'

    rclpy.init(args=args)
    node = BayerCompressor(
        input_topic=parsed_args.input,
        output_topic=output_topic,
        jpeg_quality=parsed_args.quality
    )

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        print('\n🛑 Interrompido pelo usuário')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
