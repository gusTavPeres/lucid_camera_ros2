#!/usr/bin/env python3
"""
Visualizador ao vivo da câmera Lucid Vision em modo RAW (BayerRG8).
Abre uma janela OpenCV com a imagem da câmera em tempo real.
Pressione 'q' para sair, 's' para salvar um frame.
Pressione 'r' para alternar entre RAW e RGB (demosaiced).
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

    # Configurar câmera em modo RAW BayerRG8
    nodemap['PixelFormat'].value = 'BayerRG8'
    nodemap['ExposureAuto'].value = 'Continuous'
    try:
        nodemap['GainAuto'].value = 'Continuous'
    except Exception:
        pass

    w = nodemap['Width'].value
    h = nodemap['Height'].value
    print(f"Camera: {device_infos[0]['model']} - {w}x{h} BayerRG8")
    print("Pressione 'q' para sair, 's' para salvar frame (RAW)")
    print("Pressione 'r' para alternar entre RAW e RGB")

    # Configurar stream para performance
    tl_stream = device.tl_stream_nodemap
    tl_stream['StreamAutoNegotiatePacketSize'].value = True
    tl_stream['StreamPacketResendEnable'].value = True

    device.start_stream()

    frame_count = 0
    show_raw = False  # Por padrão mostra RGB (demosaiced)

    try:
        while True:
            buf = device.get_buffer(timeout=2000)

            # BayerRG8 é 1 canal, 8 bits por pixel
            raw_arr = np.ctypeslib.as_array(
                buf.pdata,
                shape=(buf.height, buf.width)
            ).copy()
            device.requeue_buffer(buf)

            # Converter Bayer para RGB usando demosaicing
            if show_raw:
                # Mostrar RAW (em escala de cinza)
                display_arr = raw_arr
                mode_text = "RAW"
            else:
                # Converter BayerRG para RGB
                rgb_arr = cv2.cvtColor(raw_arr, cv2.COLOR_BayerRG2RGB)
                display_arr = rgb_arr
                mode_text = "RGB (demosaiced)"

            # Mostrar info no frame
            info_text = f"Exp: {nodemap['ExposureTime'].value:.0f}us | Frame: {frame_count} | Mode: {mode_text}"
            if len(display_arr.shape) == 2:
                # Adicionar texto em imagem monocromática
                display_color = cv2.cvtColor(display_arr, cv2.COLOR_GRAY2BGR)
            else:
                display_color = display_arr.copy()

            cv2.putText(display_color, info_text, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # Redimensionar para tela (imagem é 2048x1536, pode ser grande)
            display = cv2.resize(display_color, (1024, 768))
            cv2.imshow('Lucid Camera RAW - TRI032S', display)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Salvar RAW e RGB
                cv2.imwrite(f'/arena_camera_ros2/bags/frame_{frame_count}_raw.png', raw_arr)
                rgb_arr = cv2.cvtColor(raw_arr, cv2.COLOR_BayerRG2RGB)
                cv2.imwrite(f'/arena_camera_ros2/bags/frame_{frame_count}_rgb.png', rgb_arr)
                print(f"Frame {frame_count} salvo! (RAW e RGB)")
            elif key == ord('r'):
                show_raw = not show_raw
                print(f"Modo alterado para: {'RAW' if show_raw else 'RGB (demosaiced)'}")

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
