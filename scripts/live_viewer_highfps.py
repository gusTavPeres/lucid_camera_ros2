#!/usr/bin/env python3
"""
Visualizador de ALTA FPS para camera Lucid Vision.
Usa Mono8 para maximizar taxa de frames (3x mais rapido que BGR8).

Controles:
  'q' = sair
  's' = salvar frame
  'c' = alternar Mono8/BGR8
  'a' = toggle auto/manual exposure
  '+'/'-' = ajustar exposicao (modo manual)
"""
import sys
import time
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

    # ========================================
    # CONFIGURACOES PARA MAXIMO FPS
    # ========================================

    # USAR MONO8 PARA MAXIMO FPS (1 byte vs 3 bytes por pixel)
    use_color = False
    if use_color:
        nodemap['PixelFormat'].value = 'BGR8'
        pixel_format = 'BGR8'
    else:
        nodemap['PixelFormat'].value = 'Mono8'
        pixel_format = 'Mono8'

    print(f"Formato de pixel: {pixel_format}")
    print("(BGR8 = ~13 FPS max, Mono8 = ~40 FPS max na GigE)")
    print("")

    # Desativar limite de frame rate
    try:
        nodemap['AcquisitionFrameRateEnable'].value = False
    except Exception:
        pass

    # Exposicao automatica
    nodemap['ExposureAuto'].value = 'Continuous'

    # Gain automatico
    try:
        nodemap['GainAuto'].value = 'Continuous'
    except Exception:
        pass

    w = nodemap['Width'].value
    h = nodemap['Height'].value
    print(f"Camera: {device_infos[0]['model']} - {w}x{h} {pixel_format}")
    print("")
    print("Controles:")
    print("  'q' = sair")
    print("  's' = salvar frame")
    print("  'c' = alternar Mono8/BGR8 (requer reiniciar stream)")
    print("  'a' = toggle auto/manual exposure")
    print("  '+' = aumentar exposicao")
    print("  '-' = diminuir exposicao")
    print("")

    # Configurar stream para maxima performance
    tl_stream = device.tl_stream_nodemap
    tl_stream['StreamAutoNegotiatePacketSize'].value = True
    tl_stream['StreamPacketResendEnable'].value = True

    try:
        tl_stream['StreamBufferHandlingMode'].value = 'NewestOnly'
    except Exception:
        pass

    device.start_stream()

    frame_count = 0
    fps = 0.0
    last_time = time.time()
    fps_update_interval = 0.5
    frames_since_update = 0
    auto_exposure = True

    cv2.namedWindow('Lucid Camera HIGH FPS', cv2.WINDOW_NORMAL)

    try:
        while True:
            buf = device.get_buffer(timeout=2000)

            current_format = nodemap['PixelFormat'].value
            if current_format == 'Mono8':
                arr = np.ctypeslib.as_array(
                    buf.pdata,
                    shape=(buf.height, buf.width)
                ).copy()
                # Converter para BGR para exibicao
                display_arr = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
            else:
                arr = np.ctypeslib.as_array(
                    buf.pdata,
                    shape=(buf.height, buf.width, 3)
                ).copy()
                display_arr = arr

            device.requeue_buffer(buf)

            # Calcular FPS real
            frames_since_update += 1
            current_time = time.time()
            elapsed = current_time - last_time
            if elapsed >= fps_update_interval:
                fps = frames_since_update / elapsed
                frames_since_update = 0
                last_time = current_time

            # Info no frame
            exp_mode = "AUTO" if auto_exposure else "MANUAL"
            exp_val = nodemap['ExposureTime'].value
            info_text = f"FPS: {fps:.1f} | {current_format} | Exp: {exp_val:.0f}us ({exp_mode})"
            cv2.putText(display_arr, info_text, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            cv2.imshow('Lucid Camera HIGH FPS', display_arr)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                filename = f'/arena_camera_ros2/bags/frame_{frame_count}.png'
                cv2.imwrite(filename, arr if current_format == 'Mono8' else display_arr)
                print(f"Frame salvo: {filename}")
            elif key == ord('c'):
                # Alternar formato (requer restart do stream)
                device.stop_stream()
                if current_format == 'Mono8':
                    nodemap['PixelFormat'].value = 'BGR8'
                    print("Formato: BGR8 (colorido, ~13 FPS max)")
                else:
                    nodemap['PixelFormat'].value = 'Mono8'
                    print("Formato: Mono8 (P&B, ~40 FPS max)")
                device.start_stream()
            elif key == ord('a'):
                auto_exposure = not auto_exposure
                if auto_exposure:
                    nodemap['ExposureAuto'].value = 'Continuous'
                    print("Exposicao: AUTO")
                else:
                    nodemap['ExposureAuto'].value = 'Off'
                    print(f"Exposicao: MANUAL ({nodemap['ExposureTime'].value:.0f}us)")
            elif key == ord('+') or key == ord('='):
                if not auto_exposure:
                    current_exp = nodemap['ExposureTime'].value
                    new_exp = min(current_exp + 2000.0, 100000.0)
                    nodemap['ExposureTime'].value = float(new_exp)
                    print(f"Exposicao: {new_exp:.0f}us")
            elif key == ord('-'):
                if not auto_exposure:
                    current_exp = nodemap['ExposureTime'].value
                    new_exp = max(current_exp - 2000.0, 500.0)
                    nodemap['ExposureTime'].value = float(new_exp)
                    print(f"Exposicao: {new_exp:.0f}us")

            frame_count += 1

    except KeyboardInterrupt:
        pass
    finally:
        device.stop_stream()
        cv2.destroyAllWindows()
        system.destroy_device(device)
        print(f"\nTotal frames: {frame_count}")
        print(f"FPS medio final: {fps:.1f}")


if __name__ == "__main__":
    main()
