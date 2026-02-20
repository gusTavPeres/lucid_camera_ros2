#!/usr/bin/env python3
"""
Verifica recepção de frames SEM precisar de display/X11.
Imprime info de cada frame no terminal e salva os primeiros 3 em /tmp/.

Uso (dentro do container no Ubuntu PC):
    source /opt/ros/humble/setup.bash
    python3 /arena_camera_ros2/scripts/check_reception.py
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
import cv2
import numpy as np
from cv_bridge import CvBridge
import time

BAYER_MAP = {
    'bayer_rggb8': cv2.COLOR_BayerBG2BGR,
    'bayer_bggr8': cv2.COLOR_BayerRG2BGR,
    'bayer_gbrg8': cv2.COLOR_BayerGR2BGR,
    'bayer_grbg8': cv2.COLOR_BayerGB2BGR,
}


class ReceptionChecker(Node):
    def __init__(self):
        super().__init__('reception_checker')
        self.bridge = CvBridge()
        self.count = 0
        self.t0 = time.time()
        self.last_print = time.time()

        qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )
        self.sub = self.create_subscription(
            Image, '/camera/image_raw', self.callback, qos
        )
        print("Aguardando frames em /camera/image_raw (BEST_EFFORT)...")
        print("Primeiros 3 frames serão salvos em /tmp/frame_N.png")
        print("Ctrl+C para parar\n")

    def callback(self, msg):
        self.count += 1
        now = time.time()
        elapsed = now - self.t0
        fps = self.count / elapsed if elapsed > 0 else 0

        # Imprime a cada frame, mas throttle para não spammar
        if now - self.last_print >= 0.5 or self.count <= 5:
            print(f"[{self.count:4d}] {msg.width}x{msg.height}  enc={msg.encoding:<16}  {fps:.1f} FPS")
            self.last_print = now

        # Salva os primeiros 3 frames em disco (sem X11)
        if self.count <= 3:
            try:
                raw = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
                enc = msg.encoding.lower()
                if enc in BAYER_MAP:
                    bgr = cv2.cvtColor(raw, BAYER_MAP[enc])
                elif enc in ('rgb8', 'bgr8'):
                    bgr = cv2.cvtColor(raw, cv2.COLOR_RGB2BGR) if enc == 'rgb8' else raw
                else:
                    bgr = raw
                path = f'/tmp/frame_{self.count}.png'
                cv2.imwrite(path, bgr)
                print(f"       -> salvo em {path}")
            except Exception as e:
                print(f"       -> erro ao salvar: {e}")


def main():
    rclpy.init()
    node = ReceptionChecker()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        elapsed = time.time() - node.t0
        fps = node.count / elapsed if elapsed > 0 else 0
        print(f"\nTotal: {node.count} frames em {elapsed:.1f}s = {fps:.1f} FPS médio")
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
