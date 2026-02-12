#!/usr/bin/env python3
"""
Visualizador otimizado de stream ROS2 para notebook.

Suporta:
- Imagens RAW Bayer (bayer_rggb8, etc) - faz demosaicing automático
- Imagens RGB/BGR
- Imagens comprimidas (JPEG/PNG)

Features:
- Detecta formato automaticamente
- Mostra FPS em tempo real
- Mostra estatísticas de banda
- Salva frames com tecla 's'
- Alterna entre RAW e RGB com tecla 'r'

Uso:
    python3 stream_viewer.py --topic /camera/image_raw

Argumentos:
    --topic       : Tópico a subscrever (padrão: /camera/image_raw)
    --compressed  : Usar tópico comprimido (adiciona /compressed ao topic)
    --save-dir    : Diretório para salvar frames (padrão: ./saved_frames)

Teclas:
    's' - Salvar frame atual
    'r' - Alternar entre RAW e RGB (apenas para Bayer)
    'q' - Sair
    ESC - Sair
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from sensor_msgs.msg import Image, CompressedImage
from cv_bridge import CvBridge
import cv2
import argparse
import numpy as np
import time
from pathlib import Path
from datetime import datetime


class StreamViewer(Node):
    def __init__(self, topic, use_compressed, save_dir):
        super().__init__('stream_viewer')

        self.bridge = CvBridge()
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)

        # Controle de exibição
        self.show_raw = False  # Alterna entre RAW e RGB (para Bayer)
        self.current_frame = None
        self.current_frame_raw = None

        # Estatísticas
        self.frame_count = 0
        self.last_time = time.time()
        self.fps = 0
        self.bytes_received = 0
        self.bandwidth_mbps = 0

        # Detecção de formato
        self.encoding = None
        self.is_bayer = False
        self.bayer_conversion = None
        self.bayer_patterns = {
            'bayer_rggb8': cv2.COLOR_BayerRG2BGR,
            'bayer_bggr8': cv2.COLOR_BayerBG2BGR,
            'bayer_gbrg8': cv2.COLOR_BayerGB2BGR,
            'bayer_grbg8': cv2.COLOR_BayerGR2BGR,
        }

        # QoS para streaming (best effort = menor latência)
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            depth=10
        )

        # Subscrever tópico
        if use_compressed or '/compressed' in topic:
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

        self.get_logger().info('📁 Frames salvos em: {}'.format(self.save_dir))
        self.get_logger().info('')
        self.get_logger().info('Teclas:')
        self.get_logger().info('  s   - Salvar frame')
        self.get_logger().info('  r   - Alternar RAW/RGB (apenas Bayer)')
        self.get_logger().info('  q   - Sair')
        self.get_logger().info('  ESC - Sair')
        self.get_logger().info('')

    def compressed_callback(self, msg):
        """Callback para imagens comprimidas."""
        try:
            # Decodificar
            np_arr = np.frombuffer(msg.data, np.uint8)
            frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

            if frame is None:
                return

            # Atualizar estatísticas
            self.bytes_received += len(msg.data)
            self.update_stats()

            # Armazenar frame
            self.current_frame = frame
            self.encoding = 'compressed'

            # Exibir
            self.display_frame(frame)

        except Exception as e:
            self.get_logger().error(f'Erro: {e}')

    def image_callback(self, msg):
        """Callback para imagens raw."""
        try:
            # Detectar formato na primeira mensagem
            if self.encoding is None:
                self.encoding = msg.encoding.lower()

                # Verificar se é Bayer
                if self.encoding in self.bayer_patterns:
                    self.is_bayer = True
                    self.bayer_conversion = self.bayer_patterns[self.encoding]
                    self.get_logger().info(f'🎨 Formato Bayer detectado: {self.encoding}')
                    self.get_logger().info('   Pressione "r" para alternar entre RAW e RGB')

            # Converter para OpenCV
            if self.is_bayer:
                # Bayer: guardar RAW e versão RGB
                raw_img = self.bridge.imgmsg_to_cv2(msg, desired_encoding='mono8')
                rgb_img = cv2.cvtColor(raw_img, self.bayer_conversion)

                self.current_frame_raw = raw_img
                self.current_frame = rgb_img

                # Exibir RAW ou RGB conforme escolha do usuário
                frame_to_show = raw_img if self.show_raw else rgb_img
            else:
                # RGB/BGR: conversão direta
                frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
                self.current_frame = frame
                frame_to_show = frame

            # Atualizar estatísticas
            self.bytes_received += len(msg.data)
            self.update_stats()

            # Exibir
            self.display_frame(frame_to_show)

        except Exception as e:
            self.get_logger().error(f'Erro: {e}')

    def update_stats(self):
        """Atualiza estatísticas de FPS e banda."""
        self.frame_count += 1

        current_time = time.time()
        elapsed = current_time - self.last_time

        if elapsed >= 1.0:  # Atualizar a cada 1 segundo
            self.fps = self.frame_count / elapsed
            self.bandwidth_mbps = (self.bytes_received * 8) / (elapsed * 1_000_000)

            self.frame_count = 0
            self.bytes_received = 0
            self.last_time = current_time

    def display_frame(self, frame):
        """Exibe frame com overlay de informações."""
        # Criar cópia para não modificar o original
        display = frame.copy()

        # Se for imagem mono (RAW Bayer), converter para BGR para exibir colorido
        if len(display.shape) == 2:
            display = cv2.cvtColor(display, cv2.COLOR_GRAY2BGR)

        # Adicionar informações na tela
        font = cv2.FONT_HERSHEY_SIMPLEX
        scale = 0.6
        thickness = 2
        color = (0, 255, 0)  # Verde

        # FPS
        cv2.putText(
            display,
            f'FPS: {self.fps:.1f}',
            (10, 30),
            font, scale, color, thickness
        )

        # Banda
        cv2.putText(
            display,
            f'Banda: {self.bandwidth_mbps:.2f} Mbps',
            (10, 60),
            font, scale, color, thickness
        )

        # Formato
        mode_text = 'RAW' if self.show_raw else 'RGB'
        if self.is_bayer:
            cv2.putText(
                display,
                f'Modo: {mode_text} ({self.encoding})',
                (10, 90),
                font, scale, color, thickness
            )
        else:
            cv2.putText(
                display,
                f'Formato: {self.encoding}',
                (10, 90),
                font, scale, color, thickness
            )

        # Resolução
        h, w = frame.shape[:2]
        cv2.putText(
            display,
            f'{w}x{h}',
            (10, 120),
            font, scale, color, thickness
        )

        # Mostrar
        cv2.imshow('ROS2 Stream Viewer', display)

        # Processar teclas
        key = cv2.waitKey(1) & 0xFF

        if key == ord('q') or key == 27:  # 'q' ou ESC
            self.get_logger().info('🛑 Encerrando...')
            rclpy.shutdown()

        elif key == ord('s'):  # Salvar frame
            self.save_frame()

        elif key == ord('r'):  # Alternar RAW/RGB
            if self.is_bayer:
                self.show_raw = not self.show_raw
                mode = 'RAW' if self.show_raw else 'RGB'
                self.get_logger().info(f'🔄 Modo alterado: {mode}')

    def save_frame(self):
        """Salva frame atual em disco."""
        if self.current_frame is None:
            self.get_logger().warn('⚠️  Nenhum frame disponível para salvar')
            return

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')

        # Salvar versão RGB
        rgb_path = self.save_dir / f'frame_{timestamp}_rgb.png'
        cv2.imwrite(str(rgb_path), self.current_frame)
        self.get_logger().info(f'💾 Frame RGB salvo: {rgb_path}')

        # Se for Bayer, salvar também a versão RAW
        if self.is_bayer and self.current_frame_raw is not None:
            raw_path = self.save_dir / f'frame_{timestamp}_raw.png'
            cv2.imwrite(str(raw_path), self.current_frame_raw)
            self.get_logger().info(f'💾 Frame RAW salvo: {raw_path}')


def main(args=None):
    parser = argparse.ArgumentParser(
        description='Visualizador de stream ROS2 com suporte a Bayer RAW'
    )
    parser.add_argument(
        '--topic',
        type=str,
        default='/camera/image_raw',
        help='Tópico a subscrever (padrão: /camera/image_raw)'
    )
    parser.add_argument(
        '--compressed',
        action='store_true',
        help='Usar versão comprimida do tópico'
    )
    parser.add_argument(
        '--save-dir',
        type=str,
        default='./saved_frames',
        help='Diretório para salvar frames (padrão: ./saved_frames)'
    )

    parsed_args = parser.parse_args()

    # Se --compressed, adicionar /compressed ao tópico
    topic = parsed_args.topic
    if parsed_args.compressed and not topic.endswith('/compressed'):
        topic = topic + '/compressed'

    rclpy.init(args=args)
    node = StreamViewer(
        topic=topic,
        use_compressed=parsed_args.compressed,
        save_dir=parsed_args.save_dir
    )

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        print('\n🛑 Interrompido')
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
