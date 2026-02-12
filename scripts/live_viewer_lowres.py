#!/usr/bin/env python3
"""
Visualizador com resolucao REDUZIDA para teste de banda.
Usa ROI para capturar apenas parte central da imagem.
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
    # RESOLUCAO REDUZIDA PARA TESTE
    # ========================================

    # Guardar resolucao original
    max_width = nodemap['Width'].max
    max_height = nodemap['Height'].max
    print(f"Resolucao maxima: {max_width}x{max_height}")

    # REDUZIR PARA 640x480 (centro da imagem)
    target_width = 640
    target_height = 480

    # Calcular offset para centralizar ROI
    offset_x = (max_width - target_width) // 2
    offset_y = (max_height - target_height) // 2

    # Configurar ROI
    try:
        nodemap['Width'].value = target_width
        nodemap['Height'].value = target_height
        nodemap['OffsetX'].value = offset_x
        nodemap['OffsetY'].value = offset_y
        print(f"ROI configurado: {target_width}x{target_height} (offset: {offset_x}, {offset_y})")
    except Exception as e:
        print(f"Erro configurando ROI: {e}")
        print("Usando resolucao padrao")

    # Formato Mono8 para maximo FPS
    nodemap['PixelFormat'].value = 'Mono8'
    print("Formato: Mono8")

    # Desativar limite de frame rate
    try:
        nodemap['AcquisitionFrameRateEnable'].value = False
    except Exception:
        pass

    # Exposicao automatica
    nodemap['ExposureAuto'].value = 'Continuous'
    try:
        nodemap['GainAuto'].value = 'Continuous'
    except Exception:
        pass

    w = nodemap['Width'].value
    h = nodemap['Height'].value
    print(f"Resolucao final: {w}x{h}")
    print("")
    print("Calculo de banda:")
    print(f"  Mono8: {w}x{h} = {w*h/1024/1024:.2f} MB/frame")
    print(f"  FPS teorico max (GigE 125MB/s): {125*1024*1024/(w*h):.1f} FPS")
    print("")
    print("Controles: 'q'=sair, 'r'=restaurar resolucao full")
    print("")

    # Configurar stream
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

    cv2.namedWindow('Lucid Camera LOW RES TEST', cv2.WINDOW_NORMAL)

    try:
        while True:
            buf = device.get_buffer(timeout=2000)

            arr = np.ctypeslib.as_array(
                buf.pdata,
                shape=(buf.height, buf.width)
            ).copy()
            display_arr = cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)

            device.requeue_buffer(buf)

            # Calcular FPS
            frames_since_update += 1
            current_time = time.time()
            elapsed = current_time - last_time
            if elapsed >= fps_update_interval:
                fps = frames_since_update / elapsed
                frames_since_update = 0
                last_time = current_time

            # Info
            w_now = nodemap['Width'].value
            h_now = nodemap['Height'].value
            info = f"FPS: {fps:.1f} | {w_now}x{h_now} Mono8 | Frame: {frame_count}"
            cv2.putText(display_arr, info, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

            cv2.imshow('Lucid Camera LOW RES TEST', display_arr)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('r'):
                # Restaurar resolucao full
                device.stop_stream()
                nodemap['OffsetX'].value = 0
                nodemap['OffsetY'].value = 0
                nodemap['Width'].value = max_width
                nodemap['Height'].value = max_height
                print(f"Resolucao restaurada: {max_width}x{max_height}")
                device.start_stream()

            frame_count += 1

    except KeyboardInterrupt:
        pass
    finally:
        device.stop_stream()
        # Restaurar resolucao original
        try:
            nodemap['OffsetX'].value = 0
            nodemap['OffsetY'].value = 0
            nodemap['Width'].value = max_width
            nodemap['Height'].value = max_height
        except:
            pass
        cv2.destroyAllWindows()
        system.destroy_device(device)
        print(f"\nTotal frames: {frame_count}")
        print(f"FPS final: {fps:.1f}")


if __name__ == "__main__":
    main()
