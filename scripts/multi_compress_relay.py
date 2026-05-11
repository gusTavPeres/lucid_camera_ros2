#!/usr/bin/env python3
"""
Multi-camera JPEG compression relay.
Runs multiple compress_bayer_stream subscribers/publishers in a single ROS2 node
(single DDS participant) to avoid FastDDS multi-participant discovery issues over VPN.

Usage:
    python3 multi_compress_relay.py \
        --cameras /cam1/raw:/cam1/compressed /cam2/raw:/cam2/compressed \
        --quality 70 --workers 4
"""

import argparse
import threading
import time
import yaml
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import CompressedImage, Image


class MultiCameraCompressor(Node):
    BAYER_MAP = {
        'bayer_rggb8': cv2.COLOR_BayerBG2BGR,
        'bayer_bggr8': cv2.COLOR_BayerRG2BGR,
        'bayer_gbrg8': cv2.COLOR_BayerGR2BGR,
        'bayer_grbg8': cv2.COLOR_BayerGB2BGR,
    }

    def __init__(self, cameras, jpeg_quality, workers, out_width=0, out_height=0):
        super().__init__('multi_compress_relay')

        self.jpeg_quality = jpeg_quality
        self.out_width = out_width
        self.out_height = out_height
        self._jpeg_pool = ThreadPoolExecutor(max_workers=workers)
        self._pub_lock = threading.Lock()
        self._stats = {}
        self._stats_lock = threading.Lock()

        sub_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            depth=5,
        )
        pub_qos = QoSProfile(
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.VOLATILE,
            depth=10,
        )

        self._pubs = {}
        self._encodings = {}

        for in_topic, out_topic in cameras:
            pub = self.create_publisher(CompressedImage, out_topic, pub_qos)
            self._pubs[in_topic] = pub
            self._encodings[in_topic] = None
            self._stats[in_topic] = {'fps': 0, 'bytes_in': 0, 'bytes_out': 0, 't': time.time()}

            # closure to capture in_topic
            def make_cb(t):
                def cb(msg):
                    self._image_cb(msg, t)
                return cb

            self.create_subscription(Image, in_topic, make_cb(in_topic), sub_qos)
            self.get_logger().info(f'Relay: {in_topic} -> {out_topic}')

        self.create_timer(2.0, self._log_stats)

    def _image_cb(self, msg, in_topic):
        enc = msg.encoding.lower()
        if self._encodings[in_topic] is None:
            self._encodings[in_topic] = enc
            self.get_logger().info(f'{in_topic}: encoding={enc}')

        data = bytes(msg.data)
        h, w = msg.height, msg.width
        header = msg.header
        bayer_conv = self.BAYER_MAP.get(enc)

        self._jpeg_pool.submit(
            self._encode_and_publish, data, h, w, enc, bayer_conv,
            header, in_topic, len(data)
        )

    def _encode_and_publish(self, data, h, w, enc, bayer_conv, header, in_topic, bytes_raw):
        try:
            flat = np.frombuffer(data, dtype=np.uint8)
            if bayer_conv is not None:
                bgr = cv2.cvtColor(flat.reshape(h, w), bayer_conv)
            elif enc == 'rgb8':
                bgr = cv2.cvtColor(flat.reshape(h, w, 3), cv2.COLOR_RGB2BGR)
            elif enc == 'bgr8':
                bgr = flat.reshape(h, w, 3)
            elif enc == 'mono8':
                bgr = cv2.cvtColor(flat.reshape(h, w), cv2.COLOR_GRAY2BGR)
            else:
                bgr = flat.reshape(h, w, 3)

            if self.out_width and self.out_height:
                bgr = cv2.resize(bgr, (self.out_width, self.out_height), interpolation=cv2.INTER_AREA)

            ok, buf = cv2.imencode('.jpg', bgr, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
            if not ok:
                return

            out = CompressedImage()
            out.header = header
            out.format = 'jpeg'
            out.data = buf.tobytes()

            pub = self._pubs[in_topic]
            with self._pub_lock:
                pub.publish(out)

            with self._stats_lock:
                s = self._stats[in_topic]
                s['fps'] += 1
                s['bytes_in'] += bytes_raw
                s['bytes_out'] += len(out.data)

        except Exception as e:
            self.get_logger().error(f'{in_topic} encoder error: {e}')

    def _log_stats(self):
        now = time.time()
        with self._stats_lock:
            for topic, s in self._stats.items():
                dt = now - s['t']
                if dt > 0 and s['fps'] > 0:
                    fps = s['fps'] / dt
                    mbps_in = s['bytes_in'] * 8 / dt / 1e6
                    mbps_out = s['bytes_out'] * 8 / dt / 1e6
                    self.get_logger().info(
                        f'{topic}: {fps:.1f} FPS | {mbps_in:.1f} Mbps -> {mbps_out:.1f} Mbps'
                    )
                s['fps'] = 0
                s['bytes_in'] = 0
                s['bytes_out'] = 0
                s['t'] = now

    def destroy_node(self):
        self._jpeg_pool.shutdown(wait=False)
        super().destroy_node()


def cameras_from_config(config_path):
    with open(config_path) as f:
        cfg = yaml.safe_load(f)
    pairs = []
    for cam in cfg.get('cameras', []):
        resizer = cam.get('resizer', {})
        if resizer.get('enabled') and 'output_topic' in resizer:
            in_topic = resizer['output_topic']
        else:
            in_topic = cam['topic']
        if in_topic.endswith('/image_raw'):
            compressed = in_topic[:-len('/image_raw')] + '/compressed'
        else:
            compressed = in_topic + '/compressed'
        pairs.append((in_topic, compressed))
    return pairs


def main():
    parser = argparse.ArgumentParser(description='Multi-camera JPEG relay (single DDS participant)')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--cameras', nargs='+',
                       help='in_topic:out_topic pairs, e.g. /cam1/raw:/cam1/compressed')
    group.add_argument('--config', metavar='FILE',
                       help='cameras YAML config file (derives topic pairs automatically)')
    parser.add_argument('--quality', type=int, default=70, help='JPEG quality (default: 70)')
    parser.add_argument('--workers', type=int, default=4, help='Encoder threads (default: 4)')
    parser.add_argument('--width', type=int, default=0, help='Resize width (0=original)')
    parser.add_argument('--height', type=int, default=0, help='Resize height (0=original)')

    args = parser.parse_args()
    cameras = []
    if args.config:
        cameras = cameras_from_config(args.config)
    else:
        for pair in args.cameras:
            parts = pair.split(':')
            if len(parts) != 2:
                raise ValueError(f'Invalid camera pair: {pair} (expected in_topic:out_topic)')
            cameras.append((parts[0], parts[1]))

    rclpy.init()
    node = MultiCameraCompressor(cameras, args.quality, args.workers, args.width, args.height)
    executor = MultiThreadedExecutor(num_threads=args.workers + 2)
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
