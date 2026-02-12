#!/usr/bin/env python3
"""
Visualizador de alta performance para camera Lucid Vision.
Otimizado para maximo FPS sem limites artificiais.
Pressione 'q' para sair, 's' para salvar frame, 'a' para toggle auto-exposure.
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

    # Formato de pixel
    nodemap['PixelFormat'].value = 'BGR8'

    # DESATIVAR limite de frame rate (IMPORTANTE!)
    try:
        nodemap['AcquisitionFrameRateEnable'].value = False
        print("Limite de frame rate: DESATIVADO")
    except Exception as e:
        print(f"Aviso AcquisitionFrameRateEnable: {e}")

    # Exposicao automatica para comecar (usuario pode ajustar)
    nodemap['ExposureAuto'].value = 'Continuous'
    print("Exposicao: AUTO (Continuous)")

    # Gain automatico
    try:
        nodemap['GainAuto'].value = 'Continuous'
        print("Gain: AUTO (Continuous)")
    except Exception:
        pass

    w = nodemap['Width'].value
    h = nodemap['Height'].value
    print(f"Camera: {device_infos[0]['model']} - {w}x{h} BGR8")
    print("")
    print("Controles:")
    print("  'q' = sair")
    print("  's' = salvar frame")
    print("  'a' = toggle auto/manual exposure")
    print("  '+' = aumentar exposicao (modo manual)")
    print("  '-' = diminuir exposicao (modo manual)")
    print("")

    # Configurar stream para maxima performance
    tl_stream = device.tl_stream_nodemap
    tl_stream['StreamAutoNegotiatePacketSize'].value = True
    tl_stream['StreamPacketResendEnable'].value = True

    # Buffer mode para performance - descarta frames antigos
    try:
        tl_stream['StreamBufferHandlingMode'].value = 'NewestOnly'
        print("Buffer mode: NewestOnly (sem atraso)")
    except Exception:
        pass

    device.start_stream()

    frame_count = 0
    fps = 0.0
    last_time = time.time()
    fps_update_interval = 0.5
    frames_since_update = 0
    auto_exposure = True

    # Janela
    cv2.namedWindow('Lucid Camera MAX FPS', cv2.WINDOW_NORMAL)

    try:
        while True:
            buf = device.get_buffer(timeout=2000)
            arr = np.ctypeslib.as_array(
                buf.pdata,
                shape=(buf.height, buf.width, 3)
            ).copy()
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
            info_text = f"FPS: {fps:.1f} | Exp: {exp_val:.0f}us ({exp_mode}) | Frame: {frame_count}"
            cv2.putText(arr, info_text, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            # Mostrar
            cv2.imshow('Lucid Camera MAX FPS', arr)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                filename = f'/arena_camera_ros2/bags/frame_{frame_count}.png'
                cv2.imwrite(filename, arr)
                print(f"Frame salvo: {filename}")
            elif key == ord('a'):
                # Toggle auto/manual exposure
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
