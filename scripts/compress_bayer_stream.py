#!/usr/bin/env python3
"""
JPEG compression relay for bandwidth-efficient camera streaming.

Subscribes to a raw camera topic (Bayer or RGB), converts frames to JPEG,
and republishes as CompressedImage. Enables full-resolution streaming at
full frame rate over bandwidth-constrained links (WiFi, VPN).

Typical bandwidth reduction: ~35 Mbps (RAW) → ~5-12 Mbps (JPEG q=80)

Usage:
    python3 compress_bayer_stream.py [--input TOPIC] [--output TOPIC] [--quality 1-100]

Arguments:
    --input    : Input topic (default: /camera/image_raw)
    --output   : Output topic (default: <input>/compressed)
    --quality  : JPEG quality 1-100 (default: 80)
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from sensor_msgs.msg import Image, CompressedImage
from cv_bridge import CvBridge
import cv2
import argparse
import time


class BayerCompressor(Node):
    def __init__(self, input_topic, output_topic, jpeg_quality):
        super().__init__('bayer_compressor')

        self.bridge = CvBridge()
        self.jpeg_quality = jpeg_quality
        self.frame_count = 0
        self.bytes_in = 0
        self.bytes_out = 0
        self.t_last_log = time.time()
        self.fps_count = 0

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

        self.get_logger().info(f'Input:   {input_topic}')
        self.get_logger().info(f'Output:  {output_topic}')
        self.get_logger().info(f'Quality: JPEG q={jpeg_quality}')

    def image_callback(self, msg):
        try:
            enc = msg.encoding.lower()

            # Detect encoding on first frame
            if self.encoding is None:
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

            # Convert to BGR
            if self.bayer_conversion is not None:
                raw = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
                bgr = cv2.cvtColor(raw, self.bayer_conversion)
            elif enc == 'rgb8':
                rgb = self.bridge.imgmsg_to_cv2(msg, desired_encoding='rgb8')
                bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            else:
                bgr = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')

            # Compress to JPEG
            success, buf = cv2.imencode('.jpg', bgr, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])
            if not success:
                self.get_logger().warn('Failed to encode JPEG')
                return

            # Publish
            out = CompressedImage()
            out.header = msg.header
            out.format = 'jpeg'
            out.data = buf.tobytes()
            self.pub.publish(out)

            # Stats
            self.frame_count += 1
            self.fps_count += 1
            self.bytes_in += len(msg.data)
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
            self.get_logger().error(f'Error: {e}')


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

    parsed_args = parser.parse_args()
    output_topic = parsed_args.output or (parsed_args.input + '/compressed')

    rclpy.init(args=args)
    node = BayerCompressor(parsed_args.input, output_topic, parsed_args.quality)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
