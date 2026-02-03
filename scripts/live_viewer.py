#!/usr/bin/env python3
"""
Visualizador ao vivo da câmera Lucid Vision.
Abre uma janela OpenCV com a imagem da câmera em tempo real.
Pressione 'q' para sair, 's' para salvar um frame.
"""
import sys
import numpy as np
import cv2
from arena_api.system import system


def main():
    system.DEVICE_INFOS_TIMEOUT_MILLISEC = 5000
    device_infos = system.device_infos
    if not device_infos:
        print("Nenhuma camera encontrada!")
        sys.exit(1)

    devices = system.create_device(device_infos=device_infos)
    device = devices[0]
    nodemap = device.nodemap

    # Configurar câmera
    nodemap['PixelFormat'].value = 'BGR8'
    nodemap['ExposureAuto'].value = 'Continuous'
    try:
        nodemap['GainAuto'].value = 'Continuous'
    except Exception:
        pass

    w = nodemap['Width'].value
    h = nodemap['Height'].value
    print(f"Camera: {device_infos[0]['model']} - {w}x{h} BGR8")
    print("Pressione 'q' para sair, 's' para salvar frame")

    # Configurar stream para performance
    tl_stream = device.tl_stream_nodemap
    tl_stream['StreamAutoNegotiatePacketSize'].value = True
    tl_stream['StreamPacketResendEnable'].value = True

    device.start_stream()

    frame_count = 0
    try:
        while True:
            buf = device.get_buffer(timeout=2000)
            arr = np.ctypeslib.as_array(
                buf.pdata,
                shape=(buf.height, buf.width, 3)
            ).copy()
            device.requeue_buffer(buf)

            # Mostrar info no frame
            info_text = f"Exp: {nodemap['ExposureTime'].value:.0f}us | Frame: {frame_count}"
            cv2.putText(arr, info_text, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # Redimensionar para tela (imagem é 2048x1536, pode ser grande)
            display = cv2.resize(arr, (1024, 768))
            cv2.imshow('Lucid Camera - TRI032S', display)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                cv2.imwrite(f'/arena_camera_ros2/bags/frame_{frame_count}.png', arr)
                print(f"Frame {frame_count} salvo!")

            frame_count += 1
    except KeyboardInterrupt:
        pass
    finally:
        device.stop_stream()
        cv2.destroyAllWindows()
        system.destroy_device(device)
        print(f"\nTotal frames: {frame_count}")


if __name__ == "__main__":
    main()
