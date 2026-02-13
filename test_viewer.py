#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy
from sensor_msgs.msg import Image
import cv2
from cv_bridge import CvBridge

class TestViewer(Node):
    def __init__(self):
        super().__init__('test_viewer')
        qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
            depth=10
        )
        self.bridge = CvBridge()
        self.sub = self.create_subscription(Image, '/camera/image_raw', self.callback, qos)
        print('✅ Subscribed to /camera/image_raw')

    def callback(self, msg):
        print(f'📸 Frame received: {msg.width}x{msg.height} {msg.encoding}')
        try:
            img = self.bridge.imgmsg_to_cv2(msg, 'passthrough')
            if msg.encoding.startswith('bayer'):
                img = cv2.cvtColor(img, cv2.COLOR_BayerBG2BGR)
            cv2.imshow('Camera Stream', img)
            cv2.waitKey(1)
        except Exception as e:
            print(f'❌ Error: {e}')

rclpy.init()
node = TestViewer()
try:
    rclpy.spin(node)
except KeyboardInterrupt:
    print('\n🛑 Stopping...')
finally:
    cv2.destroyAllWindows()
    node.destroy_node()
    rclpy.shutdown()
