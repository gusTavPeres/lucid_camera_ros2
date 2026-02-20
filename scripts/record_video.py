#!/usr/bin/env python3
"""
Records a ROS2 camera topic directly to MP4. No intermediate bag needed.

Supports:
- Bayer RAW (bayer_rggb8, etc.) — automatic demosaicing
- RGB / BGR / mono8
- CompressedImage (JPEG/PNG) — auto-detected from topic name

Usage:
    python3 record_video.py [--topic TOPIC] [--output FILE] [--fps N] [--duration S]

Examples:
    python3 record_video.py                                  # compressed topic, until Ctrl+C
    python3 record_video.py --topic /camera/image_raw        # raw topic
    python3 record_video.py --duration 30 --output demo.mp4 # 30 seconds
    python3 record_video.py --fps 15                         # override output FPS
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy
from sensor_msgs.msg import Image, CompressedImage
from cv_bridge import CvBridge
import cv2
import numpy as np
import argparse
import time
from datetime import datetime


BAYER_PATTERNS = {
    'bayer_rggb8': cv2.COLOR_BayerBG2BGR,
    'bayer_bggr8': cv2.COLOR_BayerRG2BGR,
    'bayer_gbrg8': cv2.COLOR_BayerGR2BGR,
    'bayer_grbg8': cv2.COLOR_BayerGB2BGR,
}


class VideoRecorder(Node):
    def __init__(self, topic, output_file, target_fps, duration, compressed):
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
        self.t_last_log = time.time()
        self.fps_count = 0

        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        if compressed:
            self.sub = self.create_subscription(CompressedImage, topic, self.callback_compressed, qos)
            print(f'Recording from: {topic}  (compressed)')
        else:
            self.sub = self.create_subscription(Image, topic, self.callback_raw, qos)
            print(f'Recording from: {topic}  (raw)')

        if duration:
            print(f'Duration: {duration}s')
        print('Press Ctrl+C to stop and save.')
        print('')

    def _init_writer(self, width, height):
        fps = self.target_fps or 30.0
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        self.writer = cv2.VideoWriter(self.output_file, fourcc, fps, (width, height))
        if not self.writer.isOpened():
            self.get_logger().error(f'Failed to open VideoWriter: {self.output_file}')
            rclpy.shutdown()
            return False
        self.start_time = time.time()
        print(f'Recording: {width}x{height} @ {fps:.0f} FPS -> {self.output_file}')
        return True

    def _write(self, bgr):
        if self.writer is None:
            return

        if self.duration and (time.time() - self.start_time) >= self.duration:
            print(f'\nDuration reached ({self.duration}s). Stopping...')
            self.finalize()
            rclpy.shutdown()
            return

        self.writer.write(bgr)
        self.frame_count += 1
        self.fps_count += 1

        now = time.time()
        if now - self.t_last_log >= 1.0:
            fps = self.fps_count / (now - self.t_last_log)
            elapsed = now - self.start_time
            print(f'  {self.frame_count} frames | {fps:.1f} FPS | {elapsed:.0f}s', end='\r')
            self.fps_count = 0
            self.t_last_log = now

    def callback_raw(self, msg):
        try:
            enc = msg.encoding.lower()
            if self.writer is None:
                if enc in BAYER_PATTERNS:
                    self.is_bayer = True
                    self.bayer_code = BAYER_PATTERNS[enc]
                if not self._init_writer(msg.width, msg.height):
                    return

            if self.is_bayer:
                raw = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
                bgr = cv2.cvtColor(raw, self.bayer_code)
            elif enc == 'rgb8':
                bgr = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            else:
                frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
                bgr = frame if len(frame.shape) == 3 else cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

            self._write(bgr)
        except Exception as e:
            self.get_logger().error(f'Error: {e}')

    def callback_compressed(self, msg):
        try:
            buf = np.frombuffer(msg.data, dtype=np.uint8)
            bgr = cv2.imdecode(buf, cv2.IMREAD_COLOR)
            if bgr is None:
                return
            if self.writer is None:
                h, w = bgr.shape[:2]
                if not self._init_writer(w, h):
                    return
            self._write(bgr)
        except Exception as e:
            self.get_logger().error(f'Error: {e}')

    def finalize(self):
        if self.writer:
            self.writer.release()
            elapsed = time.time() - self.start_time if self.start_time else 0
            fps_avg = self.frame_count / elapsed if elapsed > 0 else 0
            print(f'\nSaved: {self.output_file}')
            print(f'  Frames: {self.frame_count}  |  Avg FPS: {fps_avg:.1f}  |  Duration: {elapsed:.1f}s')
            self.writer = None

    def destroy_node(self):
        self.finalize()
        super().destroy_node()


def main():
    parser = argparse.ArgumentParser(description='Record ROS2 camera topic to MP4')
    parser.add_argument('--topic', default='/camera/image_raw/compressed',
                        help='ROS2 topic (default: /camera/image_raw/compressed)')
    parser.add_argument('--output', default=None,
                        help='Output file (default: recording_YYYYMMDD_HHMMSS.mp4)')
    parser.add_argument('--fps', type=float, default=None,
                        help='Output FPS (default: 30)')
    parser.add_argument('--duration', type=float, default=None,
                        help='Duration in seconds (default: unlimited, Ctrl+C to stop)')
    args = parser.parse_args()

    if args.output is None:
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        args.output = f'recording_{ts}.mp4'

    is_compressed = args.topic.endswith('/compressed')

    rclpy.init()
    node = VideoRecorder(
        topic=args.topic,
        output_file=args.output,
        target_fps=args.fps,
        duration=args.duration,
        compressed=is_compressed
    )
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        print('\nStopped.')
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
