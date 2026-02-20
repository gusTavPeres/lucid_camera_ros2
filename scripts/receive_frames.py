#!/usr/bin/env python3
"""
Receptor de frames da câmera via ROS2.
- Assina /camera/image_raw_slow (5 FPS, throttled pelo notebook)
- Não precisa de display/X11
- Salva cada frame em /tmp/latest_frame.png (sobrescreve sempre)
- Mostra FPS e status no terminal

Uso (dentro do container no Ubuntu PC):
    source /opt/ros/humble/setup.bash
    python3 /arena_camera_ros2/scripts/receive_frames.py
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
import cv2
import numpy as np
from cv_bridge import CvBridge
import time

TOPIC = '/camera/image_raw_slow'

BAYER_MAP = {
    'bayer_rggb8': cv2.COLOR_BayerBG2BGR,
    'bayer_bggr8': cv2.COLOR_BayerRG2BGR,
    'bayer_gbrg8': cv2.COLOR_BayerGR2BGR,
    'bayer_grbg8': cv2.COLOR_BayerGB2BGR,
}


class FrameReceiver(Node):
    def __init__(self):
        super().__init__('frame_receiver')
        self.bridge = CvBridge()
        self.count = 0
        self.t0 = time.time()

        qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )

        self.sub = self.create_subscription(Image, TOPIC, self.callback, qos)
        print(f'Aguardando frames em {TOPIC} ...')
        print('Frames salvos em /tmp/latest_frame.png (atualizado a cada frame)\n')

    def callback(self, msg):
        self.count += 1
        elapsed = time.time() - self.t0
        fps = self.count / elapsed

        # Converter imagem
        try:
            raw = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
            enc = msg.encoding.lower()

            if enc in BAYER_MAP:
                bgr = cv2.cvtColor(raw, BAYER_MAP[enc])
            elif enc == 'rgb8':
                bgr = cv2.cvtColor(raw, cv2.COLOR_RGB2BGR)
            else:
                bgr = raw if len(raw.shape) == 3 else cv2.cvtColor(raw, cv2.COLOR_GRAY2BGR)

            # Salvar frame (sobrescreve sempre — pegar a foto mais recente)
            cv2.imwrite('/tmp/latest_frame.png', bgr)

            print(f'[{self.count:4d}] {msg.width}x{msg.height}  {enc}  {fps:.2f} FPS  -> /tmp/latest_frame.png')

        except Exception as e:
            print(f'[{self.count:4d}] ERRO: {e}')


def main():
    rclpy.init()
    node = FrameReceiver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        elapsed = time.time() - node.t0
        print(f'\nEncerrado. Total: {node.count} frames em {elapsed:.1f}s')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
