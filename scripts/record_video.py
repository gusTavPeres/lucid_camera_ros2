#!/usr/bin/env python3
"""
Grava o stream da câmera diretamente em MP4 (sem bag intermediário).

Uso:
    python3 record_video.py                          # grava indefinidamente, Ctrl+C para parar
    python3 record_video.py --output camera.mp4      # arquivo de saída específico
    python3 record_video.py --duration 60            # grava 60 segundos
    python3 record_video.py --topic /camera/image_raw --fps 30

Suporte:
    - Bayer RAW (bayer_rggb8, etc.) — demosaicing automático
    - RGB / BGR / mono8
    - QoS BEST_EFFORT (compatível com arena_camera_node)
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import argparse
import time
from collections import deque
from datetime import datetime


BAYER_PATTERNS = {
    'bayer_rggb8': cv2.COLOR_BayerBG2BGR,
    'bayer_bggr8': cv2.COLOR_BayerRG2BGR,
    'bayer_gbrg8': cv2.COLOR_BayerGR2BGR,
    'bayer_grbg8': cv2.COLOR_BayerGB2BGR,
}


class VideoRecorder(Node):
    def __init__(self, topic, output_file, target_fps, duration):
        super().__init__('video_recorder')

        self.bridge = CvBridge()
        self.output_file = output_file
        self.target_fps = target_fps
        self.duration = duration
        self.start_time = None
        self.writer = None
        self.frame_count = 0
        self.is_bayer = False
        self.bayer_code = None
        self.timestamps = deque(maxlen=60)

        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        self.sub = self.create_subscription(Image, topic, self.callback, qos)
        print(f'🎥 Aguardando frames em {topic}...')
        if duration:
            print(f'⏱️  Duração: {duration}s')
        print('   Pressione Ctrl+C para parar e salvar.')

    def callback(self, msg):
        now = time.time()

        # Inicialização no primeiro frame
        if self.writer is None:
            self.start_time = now
            encoding = msg.encoding

            if encoding in BAYER_PATTERNS:
                self.is_bayer = True
                self.bayer_code = BAYER_PATTERNS[encoding]

            fps = self.target_fps if self.target_fps else 30.0
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.writer = cv2.VideoWriter(
                self.output_file, fourcc, fps, (msg.width, msg.height)
            )
            if not self.writer.isOpened():
                self.get_logger().error('❌ Falha ao abrir VideoWriter. Verifique caminho de saída.')
                rclpy.shutdown()
                return

            print(f'✅ Gravando: {msg.width}x{msg.height} @ {fps:.0f} FPS → {self.output_file}')

        # Verificar duração
        if self.duration and (now - self.start_time) >= self.duration:
            print(f'\n⏱️  Duração atingida ({self.duration}s). Finalizando...')
            self.finalize()
            rclpy.shutdown()
            return

        # Converter frame
        try:
            if self.is_bayer:
                raw = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
                frame = cv2.cvtColor(raw, self.bayer_code)
            elif msg.encoding in ('rgb8',):
                frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            else:
                frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
                if len(frame.shape) == 2:
                    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        except Exception as e:
            self.get_logger().error(f'Erro ao converter frame: {e}')
            return

        self.writer.write(frame)
        self.frame_count += 1
        self.timestamps.append(now)

        # Log a cada 100 frames
        if self.frame_count % 100 == 0:
            elapsed = now - self.start_time
            fps_real = self.frame_count / elapsed if elapsed > 0 else 0
            size_mb = (msg.width * msg.height * 3 * self.frame_count) / (1024 * 1024)
            print(f'📼 {self.frame_count} frames | {fps_real:.1f} FPS | {elapsed:.0f}s gravados')

    def finalize(self):
        if self.writer:
            self.writer.release()
            elapsed = time.time() - self.start_time if self.start_time else 0
            fps_real = self.frame_count / elapsed if elapsed > 0 else 0
            print(f'\n✅ Vídeo salvo: {self.output_file}')
            print(f'   Frames: {self.frame_count} | FPS médio: {fps_real:.1f} | Duração: {elapsed:.1f}s')
            self.writer = None

    def destroy_node(self):
        self.finalize()
        super().destroy_node()


def main():
    parser = argparse.ArgumentParser(
        description='Grava stream da câmera diretamente em MP4'
    )
    parser.add_argument(
        '--topic', default='/camera/image_raw',
        help='Tópico ROS2 (padrão: /camera/image_raw)'
    )
    parser.add_argument(
        '--output', default=None,
        help='Arquivo de saída (padrão: recording_YYYYMMDD_HHMMSS.mp4)'
    )
    parser.add_argument(
        '--fps', type=float, default=None,
        help='FPS do vídeo (padrão: 30)'
    )
    parser.add_argument(
        '--duration', type=float, default=None,
        help='Duração em segundos (padrão: indefinido, Ctrl+C para parar)'
    )
    args = parser.parse_args()

    if args.output is None:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = f'recording_{ts}.mp4'

    rclpy.init()
    node = VideoRecorder(
        topic=args.topic,
        output_file=args.output,
        target_fps=args.fps,
        duration=args.duration
    )

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        print('\n🛑 Parado pelo usuário')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
