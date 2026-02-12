#!/usr/bin/env python3
"""
Visualizador ROS2 para imagens em formato BayerRG8.
Subscreve no tópico ROS2 e mostra a imagem convertida para RGB.
Pressione 'q' para sair, 's' para salvar um frame, 'r' para alternar RAW/RGB.
"""
import sys
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2
import numpy as np


class BayerImageViewer(Node):
    def __init__(self):
        super().__init__('bayer_image_viewer')

        # Declarar parâmetros
        self.declare_parameter('topic', '/camera/image_raw')
        topic_name = self.get_parameter('topic').value

        self.bridge = CvBridge()
        self.subscription = self.create_subscription(
            Image,
            topic_name,
            self.image_callback,
            10)

        self.frame_count = 0
        self.show_raw = False  # Por padrão mostra RGB (demosaiced)

        self.get_logger().info(f'Inscrito no tópico: {topic_name}')
        self.get_logger().info('Pressione "q" para sair, "s" para salvar, "r" para alternar RAW/RGB')

    def image_callback(self, msg):
        try:
            # Converter mensagem ROS para imagem OpenCV
            # Se for BayerRG8, vem como imagem mono de 1 canal
            if 'bayer' in msg.encoding.lower():
                # Imagem Bayer vem como mono8
                raw_arr = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')

                if self.show_raw:
                    # Mostrar RAW (escala de cinza)
                    display_arr = raw_arr
                    mode_text = "RAW"
                else:
                    # Converter BayerRG para RGB
                    # msg.encoding deve ser 'bayer_rggb8'
                    if 'rggb' in msg.encoding.lower():
                        rgb_arr = cv2.cvtColor(raw_arr, cv2.COLOR_BayerRG2RGB)
                    elif 'bggr' in msg.encoding.lower():
                        rgb_arr = cv2.cvtColor(raw_arr, cv2.COLOR_BayerBG2RGB)
                    elif 'gbrg' in msg.encoding.lower():
                        rgb_arr = cv2.cvtColor(raw_arr, cv2.COLOR_BayerGB2RGB)
                    elif 'grbg' in msg.encoding.lower():
                        rgb_arr = cv2.cvtColor(raw_arr, cv2.COLOR_BayerGR2RGB)
                    else:
                        # Fallback: tentar RG
                        rgb_arr = cv2.cvtColor(raw_arr, cv2.COLOR_BayerRG2RGB)

                    display_arr = rgb_arr
                    mode_text = "RGB (demosaiced)"
            else:
                # Se não for Bayer, apenas converter
                display_arr = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
                mode_text = "BGR8"

            # Adicionar informações na imagem
            info_text = f"Frame: {self.frame_count} | Encoding: {msg.encoding} | Mode: {mode_text}"

            # Garantir que temos uma imagem colorida para escrever texto
            if len(display_arr.shape) == 2:
                display_color = cv2.cvtColor(display_arr, cv2.COLOR_GRAY2BGR)
            else:
                display_color = display_arr.copy()

            cv2.putText(display_color, info_text, (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            # Redimensionar se muito grande
            h, w = display_color.shape[:2]
            if w > 1280:
                scale = 1280 / w
                display_color = cv2.resize(display_color, None, fx=scale, fy=scale)

            cv2.imshow('ROS2 Bayer Viewer', display_color)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                self.get_logger().info('Encerrando...')
                rclpy.shutdown()
            elif key == ord('s'):
                filename = f'/arena_camera_ros2/bags/ros_frame_{self.frame_count}.png'
                cv2.imwrite(filename, display_arr)
                self.get_logger().info(f'Frame salvo: {filename}')
            elif key == ord('r'):
                self.show_raw = not self.show_raw
                self.get_logger().info(f'Modo alterado: {"RAW" if self.show_raw else "RGB"}')

            self.frame_count += 1

        except Exception as e:
            self.get_logger().error(f'Erro ao processar imagem: {str(e)}')


def main(args=None):
    rclpy.init(args=args)
    viewer = BayerImageViewer()

    try:
        rclpy.spin(viewer)
    except KeyboardInterrupt:
        pass
    finally:
        viewer.destroy_node()
        cv2.destroyAllWindows()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
