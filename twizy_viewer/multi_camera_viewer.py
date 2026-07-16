#!/usr/bin/env python3
import math
import threading
import time

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import DurabilityPolicy, HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import Image


TOPICS = [
    "/camera/left/image_raw",
    "/camera/top_front/image_raw",
    "/camera/top_left/image_raw",
    "/camera/top_right/image_raw",
    "/camera/back/image_raw",
    "/camera/right/image_raw",
]

BAYER = {
    "bayer_rggb8": cv2.COLOR_BayerBG2BGR,
    "bayer_bggr8": cv2.COLOR_BayerRG2BGR,
    "bayer_gbrg8": cv2.COLOR_BayerGR2BGR,
    "bayer_grbg8": cv2.COLOR_BayerGB2BGR,
}


class MultiCameraViewer(Node):
    def __init__(self):
        super().__init__("twizy_multi_camera_viewer")
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            history=HistoryPolicy.KEEP_LAST,
            depth=2,
        )
        self.bridge = CvBridge()
        self.frames = {topic: None for topic in TOPICS}
        self.stats = {topic: [0, time.time(), 0.0] for topic in TOPICS}
        self.lock = threading.Lock()
        for topic in TOPICS:
            self.create_subscription(Image, topic, lambda msg, t=topic: self._cb(t, msg), qos)
            self.get_logger().info(f"subscribed: {topic}")

    def _cb(self, topic, msg):
        try:
            raw = self.bridge.imgmsg_to_cv2(msg, desired_encoding="passthrough")
            enc = msg.encoding.lower()
            if enc in BAYER:
                img = cv2.cvtColor(raw, BAYER[enc])
            elif enc == "rgb8":
                img = cv2.cvtColor(raw, cv2.COLOR_RGB2BGR)
            elif enc == "bgr8":
                img = raw
            else:
                img = cv2.cvtColor(raw, cv2.COLOR_GRAY2BGR) if len(raw.shape) == 2 else raw

            with self.lock:
                count, start, fps = self.stats[topic]
                count += 1
                now = time.time()
                if now - start >= 1.0:
                    fps = count / (now - start)
                    count = 0
                    start = now
                self.stats[topic] = [count, start, fps]
                self.frames[topic] = img
        except Exception as exc:
            self.get_logger().error(f"{topic}: {exc}")

    def snapshot(self):
        with self.lock:
            return dict(self.frames), {k: v[2] for k, v in self.stats.items()}


def make_tile(topic, frame, fps, size):
    w, h = size
    label = topic.split("/")[-2]
    if frame is None:
        tile = np.zeros((h, w, 3), dtype=np.uint8)
        cv2.putText(tile, f"{label}: aguardando", (20, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80, 80, 80), 2)
    else:
        tile = cv2.resize(frame, (w, h), interpolation=cv2.INTER_AREA)
    cv2.rectangle(tile, (0, 0), (w, 32), (0, 0, 0), -1)
    cv2.putText(tile, f"{label}  {fps:.1f} fps", (8, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
    return tile


def main():
    rclpy.init()
    node = MultiCameraViewer()
    thread = threading.Thread(target=rclpy.spin, args=(node,), daemon=True)
    thread.start()

    cols = 3
    rows = math.ceil(len(TOPICS) / cols)
    tile_size = (426, 320)
    window = "Twizy cameras"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)

    try:
        while rclpy.ok():
            frames, fps = node.snapshot()
            tiles = [make_tile(topic, frames[topic], fps[topic], tile_size) for topic in TOPICS]
            blank = np.zeros((tile_size[1], tile_size[0], 3), dtype=np.uint8)
            while len(tiles) < rows * cols:
                tiles.append(blank.copy())
            grid = np.vstack([np.hstack(tiles[r * cols:(r + 1) * cols]) for r in range(rows)])
            cv2.imshow(window, grid)
            if (cv2.waitKey(30) & 0xFF) in (27, ord("q")):
                break
    finally:
        cv2.destroyAllWindows()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
