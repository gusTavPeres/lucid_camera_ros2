#!/usr/bin/env python3
"""
Headless frame receiver — no display required.

Subscribes to a camera topic (raw or compressed), decodes frames, saves
the latest to /tmp/latest_frame.png, and prints live stats to the terminal.
Useful for verifying reception without a graphical environment.

Usage:
    python3 receive_frames.py [--topic TOPIC] [--compressed] [--save PATH]

Arguments:
    --topic      : ROS2 topic to subscribe (default: /camera/image_raw/compressed)
    --compressed : Expect CompressedImage messages (auto-detected from topic name)
    --save       : Output file path (default: /tmp/latest_frame.png)

Examples:
    python3 receive_frames.py --topic /camera/image_raw/compressed
    python3 receive_frames.py --topic /camera/image_raw
    python3 receive_frames.py --topic /camera/image_raw_slow
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CompressedImage
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
import cv2
import numpy as np
from cv_bridge import CvBridge
import time
import argparse

BAYER_MAP = {
    'bayer_rggb8': cv2.COLOR_BayerBG2BGR,
    'bayer_bggr8': cv2.COLOR_BayerRG2BGR,
    'bayer_gbrg8': cv2.COLOR_BayerGR2BGR,
    'bayer_grbg8': cv2.COLOR_BayerGB2BGR,
}


class FrameReceiver(Node):
    def __init__(self, topic, compressed, save_path):
        super().__init__('frame_receiver')
        self.bridge = CvBridge()
        self.save_path = save_path
        self.count = 0
        self.t0 = time.time()

        qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=1
        )

        if compressed:
            self.sub = self.create_subscription(CompressedImage, topic, self.callback_compressed, qos)
            print(f'Waiting for compressed frames on {topic} ...')
        else:
            self.sub = self.create_subscription(Image, topic, self.callback_raw, qos)
            print(f'Waiting for frames on {topic} ...')

        print(f'Saving to {save_path} (overwritten each frame)\n')

    def _save_and_print(self, bgr, width, height, enc):
        self.count += 1
        elapsed = time.time() - self.t0
        fps = self.count / elapsed
        cv2.imwrite(self.save_path, bgr)
        print(f'[{self.count:4d}] {width}x{height}  {enc}  {fps:.2f} FPS  -> {self.save_path}')

    def callback_raw(self, msg):
        try:
            enc = msg.encoding.lower()
            raw = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
            if enc in BAYER_MAP:
                bgr = cv2.cvtColor(raw, BAYER_MAP[enc])
            elif enc == 'rgb8':
                bgr = cv2.cvtColor(raw, cv2.COLOR_RGB2BGR)
            elif len(raw.shape) == 2:
                bgr = cv2.cvtColor(raw, cv2.COLOR_GRAY2BGR)
            else:
                bgr = raw
            self._save_and_print(bgr, msg.width, msg.height, enc)
        except Exception as e:
            print(f'[{self.count:4d}] Error: {e}')

    def callback_compressed(self, msg):
        try:
            buf = np.frombuffer(msg.data, dtype=np.uint8)
            bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            if bgr is None:
                print(f'[{self.count:4d}] Error: failed to decode compressed image')
                return
            h, w = bgr.shape[:2]
            self._save_and_print(bgr, w, h, f'compressed/{msg.format}')
        except Exception as e:
            print(f'[{self.count:4d}] Error: {e}')


def main():
    parser = argparse.ArgumentParser(description='Headless ROS2 camera frame receiver')
    parser.add_argument('--topic', default='/camera/image_raw/compressed',
                        help='Topic to subscribe (default: /camera/image_raw/compressed)')
    parser.add_argument('--compressed', action='store_true',
                        help='Expect CompressedImage messages')
    parser.add_argument('--save', default='/tmp/latest_frame.png',
                        help='Output file path (default: /tmp/latest_frame.png)')
    args = parser.parse_args()

    # Auto-detect compressed from topic name
    is_compressed = args.compressed or args.topic.endswith('/compressed')

    rclpy.init()
    node = FrameReceiver(args.topic, is_compressed, args.save)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        elapsed = time.time() - node.t0
        print(f'\nDone. {node.count} frames in {elapsed:.1f}s ({node.count/elapsed:.1f} FPS avg)')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
