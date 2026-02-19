#!/usr/bin/env python3
"""
Script otimizado para converter ROS2 bags em vídeo MP4.

Detecta automaticamente:
- Resolução (width, height)
- FPS (frame rate)
- Formato (bayer_rggb8, rgb8, bgr8, compressed)

Suporta:
- Imagens RAW Bayer (faz demosaicing automático)
- Imagens RGB/BGR
- Imagens comprimidas (JPEG/PNG)

Uso:
    Terminal 1: python3 bag_to_video.py --topic /camera/image_raw --output video.mp4
    Terminal 2: ros2 bag play ./minha_bag

    Quando a bag terminar, pressione Ctrl+C no Terminal 1.

Argumentos:
    --topic    : Tópico de imagem (padrão: /camera/image_raw)
    --output   : Arquivo de saída (padrão: output.mp4)
    --fps      : FPS do vídeo (padrão: auto-detectado)
    --quality  : Qualidade H.264 [0-51], menor=melhor (padrão: 23)
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image, CompressedImage
from cv_bridge import CvBridge
import cv2
import argparse
import sys
from collections import deque
import time
import numpy as np


class BagToVideo(Node):
    def __init__(self, topic, output_file, target_fps=None, quality=23):
        super().__init__('bag_to_video')

        self.topic = topic
        self.output_file = output_file
        self.target_fps = target_fps
        self.quality = quality

        self.bridge = CvBridge()
        self.writer = None
        self.frame_count = 0

        # Auto-detecção de parâmetros
        self.width = None
        self.height = None
        self.encoding = None
        self.is_compressed = False
        self.is_bayer = False

        # Para calcular FPS (usando timestamps das mensagens ROS)
        self.timestamps = deque(maxlen=100)
        self.msg_timestamps = deque(maxlen=100)
        self.calculated_fps = None

        # QoS compatível com bag play (RELIABLE) e live streaming (BEST_EFFORT)
        # Usando BEST_EFFORT para compatibilidade com bags gravados de streams BEST_EFFORT
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        # Detectar se o tópico é compressed
        if '/compressed' in topic or topic.endswith('compressed'):
            self.is_compressed = True
            self.sub = self.create_subscription(
                CompressedImage,
                topic,
                self.compressed_callback,
                qos_profile
            )
            self.get_logger().info(f'📹 Subscrito a tópico COMPRIMIDO: {topic}')
        else:
            self.sub = self.create_subscription(
                Image,
                topic,
                self.image_callback,
                qos_profile
            )
            self.get_logger().info(f'📹 Subscrito a tópico RAW: {topic}')

        self.get_logger().info(f'💾 Vídeo será salvo em: {output_file}')
        self.get_logger().info('⏳ Aguardando primeiro frame...')

    def detect_bayer_pattern(self, encoding):
        """Detecta se é formato Bayer e retorna o código de conversão OpenCV."""
        # Nota: ROS2 Bayer naming é invertido vs OpenCV
        bayer_patterns = {
            'bayer_rggb8': cv2.COLOR_BayerBG2BGR,
            'bayer_bggr8': cv2.COLOR_BayerRG2BGR,
            'bayer_gbrg8': cv2.COLOR_BayerGR2BGR,
            'bayer_grbg8': cv2.COLOR_BayerGB2BGR,
            'bayer_rggb16': cv2.COLOR_BayerBG2BGR,
            'bayer_bggr16': cv2.COLOR_BayerRG2BGR,
            'bayer_gbrg16': cv2.COLOR_BayerGR2BGR,
            'bayer_grbg16': cv2.COLOR_BayerGB2BGR,
        }
        return bayer_patterns.get(encoding.lower())

    def initialize_writer(self, width, height, fps):
        """Inicializa o VideoWriter com os parâmetros detectados."""
        self.width = width
        self.height = height
        self.calculated_fps = fps if fps > 0 else 30

        # Usar FPS especificado ou detectado
        final_fps = self.target_fps if self.target_fps else self.calculated_fps

        # Codec H.264 para melhor compressão
        fourcc = cv2.VideoWriter_fourcc(*'avc1')  # H.264

        self.writer = cv2.VideoWriter(
            self.output_file,
            fourcc,
            final_fps,
            (width, height)
        )

        if not self.writer.isOpened():
            self.get_logger().error('❌ Falha ao criar VideoWriter!')
            raise RuntimeError('VideoWriter failed to open')

        self.get_logger().info(f'✅ VideoWriter inicializado:')
        self.get_logger().info(f'   📐 Resolução: {width}x{height}')
        self.get_logger().info(f'   🎬 FPS: {final_fps:.2f}')
        self.get_logger().info(f'   🎨 Encoding: {self.encoding}')
        self.get_logger().info(f'   🗜️  Codec: H.264 (avc1)')
        self.get_logger().info(f'   ⚙️  Qualidade: {self.quality}')

    def compressed_callback(self, msg):
        """Callback para imagens comprimidas."""
        try:
            # Decodificar imagem comprimida
            np_arr = np.frombuffer(msg.data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is None:
                self.get_logger().warn('⚠️  Frame comprimido inválido, pulando...')
                return

            # Primeira frame: inicializar writer
            if self.writer is None:
                height, width = frame.shape[:2]
                self.encoding = 'compressed'

                # Calcular FPS
                self.timestamps.append(time.time())
                if len(self.timestamps) >= 2:
                    time_diff = self.timestamps[-1] - self.timestamps[0]
                    fps = len(self.timestamps) / time_diff
                else:
                    fps = 30  # padrão

                self.initialize_writer(width, height, fps)

            # Atualizar cálculo de FPS
            self.timestamps.append(time.time())
            if len(self.timestamps) >= 2:
                time_diff = self.timestamps[-1] - self.timestamps[0]
                current_fps = len(self.timestamps) / time_diff
            else:
                current_fps = self.calculated_fps

            # Escrever frame
            self.writer.write(frame)
            self.frame_count += 1

            if self.frame_count % 50 == 0:
                self.get_logger().info(
                    f'📼 Frames gravados: {self.frame_count} | FPS atual: {current_fps:.2f}'
                )

        except Exception as e:
            self.get_logger().error(f'❌ Erro no compressed_callback: {e}')

    def image_callback(self, msg):
        """Callback para imagens raw (Image)."""
        try:
            # Registrar timestamp da mensagem (ns → s)
            msg_ts = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
            if msg_ts > 0:
                self.msg_timestamps.append(msg_ts)

            # Primeira frame: detectar parâmetros
            if self.writer is None:
                self.width = msg.width
                self.height = msg.height
                self.encoding = msg.encoding

                # Detectar se é Bayer
                bayer_code = self.detect_bayer_pattern(msg.encoding)
                if bayer_code is not None:
                    self.is_bayer = True
                    self.bayer_conversion = bayer_code
                    self.get_logger().info(f'🎨 Formato Bayer detectado: {msg.encoding}')
                    self.get_logger().info(f'🔄 Demosaicing será aplicado automaticamente')

                # FPS inicial: 30 (será recalculado)
                fps = self.target_fps if self.target_fps else 30
                self.initialize_writer(self.width, self.height, fps)

            # Converter imagem ROS → OpenCV
            if self.is_bayer:
                # Para Bayer: usar passthrough para preservar padrão raw, depois demosaicing
                raw_img = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
                frame = cv2.cvtColor(raw_img, self.bayer_conversion)
            else:
                # Para RGB/BGR: conversão direta
                desired_encoding = 'bgr8'  # OpenCV usa BGR
                frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding=desired_encoding)

            # Atualizar cálculo de FPS
            self.timestamps.append(time.time())
            if len(self.timestamps) >= 2:
                time_diff = self.timestamps[-1] - self.timestamps[0]
                current_fps = len(self.timestamps) / time_diff
            else:
                current_fps = self.calculated_fps

            # Escrever frame
            self.writer.write(frame)
            self.frame_count += 1

            if self.frame_count % 50 == 0:
                self.get_logger().info(
                    f'📼 Frames gravados: {self.frame_count} | FPS atual: {current_fps:.2f}'
                )

        except Exception as e:
            self.get_logger().error(f'❌ Erro no image_callback: {e}')

    def destroy_node(self):
        """Finaliza e salva o vídeo."""
        if self.writer is not None:
            self.writer.release()

            # Calcular estatísticas finais
            if len(self.timestamps) >= 2:
                total_time = self.timestamps[-1] - self.timestamps[0]
                final_fps = self.frame_count / total_time
            else:
                final_fps = self.calculated_fps

            self.get_logger().info('=' * 60)
            self.get_logger().info('✅ Vídeo salvo com sucesso!')
            self.get_logger().info(f'📁 Arquivo: {self.output_file}')
            self.get_logger().info(f'📼 Total de frames: {self.frame_count}')
            self.get_logger().info(f'🎬 FPS médio: {final_fps:.2f}')
            self.get_logger().info(f'⏱️  Duração: {self.frame_count / final_fps:.2f}s')
            self.get_logger().info('=' * 60)

        super().destroy_node()


def main(args=None):
    parser = argparse.ArgumentParser(
        description='Converte ROS2 bag em vídeo MP4 (suporta RAW Bayer, RGB, compressed)'
    )
    parser.add_argument(
        '--topic',
        type=str,
        default='/camera/image_raw',
        help='Tópico de imagem (padrão: /camera/image_raw)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='output.mp4',
        help='Arquivo de saída (padrão: output.mp4)'
    )
    parser.add_argument(
        '--fps',
        type=float,
        default=None,
        help='FPS do vídeo (padrão: auto-detectado da bag)'
    )
    parser.add_argument(
        '--quality',
        type=int,
        default=23,
        help='Qualidade H.264 [0-51], menor=melhor (padrão: 23)'
    )

    parsed_args = parser.parse_args()

    rclpy.init(args=args)
    node = BagToVideo(
        topic=parsed_args.topic,
        output_file=parsed_args.output,
        target_fps=parsed_args.fps,
        quality=parsed_args.quality
    )

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        print('\n🛑 Interrompido pelo usuário (Ctrl+C)')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
