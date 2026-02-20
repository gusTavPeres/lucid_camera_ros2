#!/usr/bin/env python3
"""
JPEG compression relay for bandwidth-efficient camera streaming.

Subscribes to a raw camera topic (Bayer or RGB), converts frames to JPEG,
and republishes as CompressedImage. Enables full-resolution streaming at
full frame rate over bandwidth-constrained links (WiFi, VPN).

Uses a thread pool for parallel JPEG encoding to keep up with high-FPS cameras.

Typical bandwidth reduction: ~35 Mbps (RAW) → ~5-12 Mbps (JPEG q=80)

Usage:
    python3 compress_bayer_stream.py [--input TOPIC] [--output TOPIC] [--quality 1-100] [--workers N]

Arguments:
    --input    : Input topic (default: /camera/image_raw)
    --output   : Output topic (default: <input>/compressed)
    --quality  : JPEG quality 1-100 (default: 80)
    --workers  : JPEG encoder threads (default: 2)
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from rclpy.executors import MultiThreadedExecutor
from sensor_msgs.msg import Image, CompressedImage
from cv_bridge import CvBridge
import cv2
import numpy as np
import argparse
import time
import threading
from concurrent.futures import ThreadPoolExecutor


class BayerCompressor(Node):
    def __init__(self, input_topic, output_topic, jpeg_quality, workers):
        super().__init__('bayer_compressor')

        self.bridge = CvBridge()
        self.jpeg_quality = jpeg_quality
        self.frame_count = 0
        self.bytes_in = 0
        self.bytes_out = 0
        self.t_last_log = time.time()
        self.fps_count = 0
        self._stats_lock = threading.Lock()

        # Thread pool for parallel JPEG encoding
        self._jpeg_pool = ThreadPoolExecutor(max_workers=workers)
        self._pub_lock = threading.Lock()

        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            depth=10
        )

        self.sub = self.create_subscription(Image, input_topic, self.image_callback, qos)
        self.pub = self.create_publisher(CompressedImage, output_topic, qos)

        # Bayer pattern mapping (ROS2 naming is inverted vs OpenCV)
        self.bayer_patterns = {
            'bayer_rggb8': cv2.COLOR_BayerBG2BGR,
            'bayer_bggr8': cv2.COLOR_BayerRG2BGR,
            'bayer_gbrg8': cv2.COLOR_BayerGR2BGR,
            'bayer_grbg8': cv2.COLOR_BayerGB2BGR,
        }
        self.bayer_conversion = None
        self.encoding = None
        self._encoding_lock = threading.Lock()

        self.get_logger().info(f'Input:   {input_topic}')
        self.get_logger().info(f'Output:  {output_topic}')
        self.get_logger().info(f'Quality: JPEG q={jpeg_quality}')
        self.get_logger().info(f'Workers: {workers} encoder threads')

    def image_callback(self, msg):
        # Detect encoding on first frame (synchronized)
        with self._encoding_lock:
            if self.encoding is None:
                enc = msg.encoding.lower()
                self.encoding = enc
                if enc in self.bayer_patterns:
                    self.bayer_conversion = self.bayer_patterns[enc]
                    self.get_logger().info(f'Bayer pattern detected: {enc}')
                elif enc in ('rgb8', 'bgr8', 'mono8'):
                    self.get_logger().info(f'Encoding detected: {enc}')
                else:
                    self.get_logger().error(
                        f'Unsupported encoding: {enc}. '
                        f'Expected: bayer_rggb8, bayer_bggr8, bayer_gbrg8, bayer_grbg8, rgb8, bgr8'
                    )
                    return

        # Copy raw bytes and submit everything to thread pool (keeps callback fast)
        try:
            # Minimal work in callback: copy data + submit
            data = bytes(msg.data)
            header = msg.header
            h, w = msg.height, msg.width
            bytes_raw = len(data)
            enc = self.encoding
            bayer_conv = self.bayer_conversion

            self._jpeg_pool.submit(
                self._process_and_publish, data, h, w, enc, bayer_conv, header, bytes_raw
            )

        except Exception as e:
            self.get_logger().error(f'Error in callback: {e}')

    def _process_and_publish(self, data, h, w, enc, bayer_conv, header, bytes_raw):
        try:
            # Demosaic
            raw = np.frombuffer(data, dtype=np.uint8).reshape(h, w)
            if bayer_conv is not None:
                bgr = cv2.cvtColor(raw, bayer_conv)
            elif enc == 'rgb8':
                bgr = cv2.cvtColor(raw.reshape(h, w, 3), cv2.COLOR_RGB2BGR)
            else:
                bgr = raw.reshape(h, w, 3)

            # JPEG encode
            success, buf = cv2.imencode('.jpg', bgr, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
            if not success:
                self.get_logger().warn('Failed to encode JPEG')
                return

            out = CompressedImage()
            out.header = header
            out.format = 'jpeg'
            out.data = buf.tobytes()
            with self._pub_lock:
                self.pub.publish(out)

            with self._stats_lock:
                self.frame_count += 1
                self.fps_count += 1
                self.bytes_in += bytes_raw
                self.bytes_out += len(out.data)

                now = time.time()
                dt = now - self.t_last_log
                if dt >= 1.0:
                    fps = self.fps_count / dt
                    mbps_in = self.bytes_in * 8 / dt / 1e6
                    mbps_out = self.bytes_out * 8 / dt / 1e6
                    ratio = (1 - self.bytes_out / max(self.bytes_in, 1)) * 100
                    self.get_logger().info(
                        f'{fps:.1f} FPS | '
                        f'RAW {mbps_in:.1f} Mbps -> JPEG {mbps_out:.1f} Mbps '
                        f'({ratio:.0f}% reduction)'
                    )
                    self.fps_count = 0
                    self.bytes_in = 0
                    self.bytes_out = 0
                    self.t_last_log = now

        except Exception as e:
            self.get_logger().error(f'Error in encoder: {e}')

    def destroy_node(self):
        self._jpeg_pool.shutdown(wait=False)
        super().destroy_node()


def main(args=None):
    parser = argparse.ArgumentParser(
        description='JPEG compression relay: raw camera topic -> compressed topic'
    )
    parser.add_argument('--input', default='/camera/image_raw',
                        help='Input topic (default: /camera/image_raw)')
    parser.add_argument('--output', default=None,
                        help='Output topic (default: <input>/compressed)')
    parser.add_argument('--quality', type=int, default=80,
                        help='JPEG quality 1-100 (default: 80)')
    parser.add_argument('--workers', type=int, default=4,
                        help='Number of JPEG encoder threads (default: 4)')

    parsed_args = parser.parse_args()
    output_topic = parsed_args.output or (parsed_args.input + '/compressed')

    rclpy.init(args=args)
    node = BayerCompressor(parsed_args.input, output_topic, parsed_args.quality, parsed_args.workers)
    mt_executor = MultiThreadedExecutor(num_threads=parsed_args.workers + 1)
    mt_executor.add_node(node)
    try:
        mt_executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
