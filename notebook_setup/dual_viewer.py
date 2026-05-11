#!/usr/bin/env python3
"""Visualizador dual câmera via ROS2 CompressedImage."""
import sys
import argparse
import threading
import numpy as np
import cv2
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from sensor_msgs.msg import CompressedImage


class DualViewer(Node):
    def __init__(self, topic1, topic2):
        super().__init__('dual_viewer')
        qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
        )
        self._frames = [None, None]
        self._lock = threading.Lock()
        self.create_subscription(CompressedImage, topic1, lambda m: self._cb(m, 0), qos)
        self.create_subscription(CompressedImage, topic2, lambda m: self._cb(m, 1), qos)
        self.get_logger().info(f'Subscribed: {topic1}  {topic2}')

    def _cb(self, msg, idx):
        buf = np.frombuffer(msg.data, dtype=np.uint8)
        img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
        if img is not None:
            with self._lock:
                self._frames[idx] = img

    def get_frames(self):
        with self._lock:
            return list(self._frames)


def main():
    parser = argparse.ArgumentParser(description='Dual camera viewer')
    parser.add_argument('--title', default='Dual Camera', help='Window title')
    parser.add_argument('topic1', nargs='?', default='/camera/cam1/compressed')
    parser.add_argument('topic2', nargs='?', default='/camera/cam2/compressed')
    args = parser.parse_args()

    rclpy.init()
    node = DualViewer(args.topic1, args.topic2)

    spin_thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    spin_thread.start()

    window_name = args.title
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    print(f"Janela: '{window_name}' | Pressione 'q' para sair")
    while True:
        frames = node.get_frames()
        parts = []
        labels = [args.topic1.split('/')[-2] if '/' in args.topic1 else 'cam1',
                  args.topic2.split('/')[-2] if '/' in args.topic2 else 'cam2']
        for i, f in enumerate(frames):
            if f is not None:
                disp = cv2.resize(f, (640, 480))
            else:
                disp = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(disp, f'{labels[i]}: aguardando...', (20, 240),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 100, 100), 2)
            parts.append(disp)
        combined = np.hstack(parts)
        cv2.imshow(window_name, combined)
        key = cv2.waitKey(30) & 0xFF
        if key == ord('q'):
            break

    cv2.destroyAllWindows()
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
