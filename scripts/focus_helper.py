#!/usr/bin/env python3
"""
Assistente de foco para câmera Lucid Vision.
Mostra a imagem ao vivo com indicador de nitidez (sharpness).
Gire o anel de foco da lente até o valor de sharpness ser o mais alto possível.

Controles:
  q     - Sair
  s     - Salvar frame
  +/-   - Aumentar/diminuir exposição
  z     - Zoom central (toggle)
"""
import sys
import numpy as np
import cv2
from arena_api.system import system


def laplacian_sharpness(gray):
    """Calcula sharpness usando variância do Laplaciano."""
    lap = cv2.Laplacian(gray, cv2.CV_64F)
    return lap.var()


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
    print(f"Camera: {device_infos[0]['model']} - {w}x{h}")
    print(f"")
    print(f"=== AJUSTE DE FOCO ===")
    print(f"Gire o anel de foco da lente lentamente.")
    print(f"O valor de SHARPNESS deve aumentar conforme a imagem fica mais nitida.")
    print(f"")
    print(f"Controles:")
    print(f"  q     - Sair")
    print(f"  s     - Salvar frame")
    print(f"  +/-   - Ajustar exposicao")
    print(f"  z     - Zoom central (toggle)")

    # Stream
    tl_stream = device.tl_stream_nodemap
    tl_stream['StreamAutoNegotiatePacketSize'].value = True
    tl_stream['StreamPacketResendEnable'].value = True

    device.start_stream()

    zoom_mode = False
    max_sharpness = 0
    frame_count = 0
    exposure_offset = 0

    try:
        while True:
            buf = device.get_buffer(timeout=2000)
            arr = np.ctypeslib.as_array(
                buf.pdata,
                shape=(buf.height, buf.width, 3)
            ).copy()
            device.requeue_buffer(buf)

            # Converter para grayscale para cálculo de sharpness
            gray = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
            sharpness = laplacian_sharpness(gray)
            max_sharpness = max(max_sharpness, sharpness)

            # Barra de sharpness
            bar_width = 400
            bar_height = 30
            bar_x, bar_y = 10, 50
            bar_fill = min(int((sharpness / max(max_sharpness, 1)) * bar_width), bar_width)

            # Cor da barra baseada no sharpness relativo
            if max_sharpness > 0:
                ratio = sharpness / max_sharpness
                if ratio > 0.8:
                    bar_color = (0, 255, 0)  # Verde = bom foco
                elif ratio > 0.5:
                    bar_color = (0, 255, 255)  # Amarelo = médio
                else:
                    bar_color = (0, 0, 255)  # Vermelho = fora de foco
            else:
                bar_color = (128, 128, 128)

            # Display
            if zoom_mode:
                # Crop central 512x384
                cy, cx = h // 2, w // 2
                crop = arr[cy-192:cy+192, cx-256:cx+256]
                display = cv2.resize(crop, (1024, 768), interpolation=cv2.INTER_NEAREST)
                cv2.putText(display, "ZOOM 4x", (10, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            else:
                display = cv2.resize(arr, (1024, 768))

            # Overlay info
            cv2.rectangle(display, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height),
                          (50, 50, 50), -1)
            cv2.rectangle(display, (bar_x, bar_y), (bar_x + bar_fill, bar_y + bar_height),
                          bar_color, -1)
            cv2.rectangle(display, (bar_x, bar_y), (bar_x + bar_width, bar_y + bar_height),
                          (255, 255, 255), 1)

            exp_time = nodemap['ExposureTime'].value
            cv2.putText(display, f"SHARPNESS: {sharpness:.1f} (max: {max_sharpness:.1f})",
                        (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(display, f"Exp: {exp_time:.0f}us | Frame: {frame_count} | 'z'=zoom 'q'=sair",
                        (10, bar_y + bar_height + 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            cv2.imshow('Focus Helper - Gire o anel de foco da lente', display)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('s'):
                cv2.imwrite(f'/arena_camera_ros2/bags/focused_{frame_count}.png', arr)
                print(f"Frame {frame_count} salvo! Sharpness: {sharpness:.1f}")
            elif key == ord('z'):
                zoom_mode = not zoom_mode
                print(f"Zoom: {'ON (4x)' if zoom_mode else 'OFF'}")
            elif key == ord('+') or key == ord('='):
                try:
                    nodemap['ExposureAuto'].value = 'Off'
                    curr = nodemap['ExposureTime'].value
                    nodemap['ExposureTime'].value = min(curr * 1.5, 100000)
                    print(f"Exposure: {nodemap['ExposureTime'].value:.0f}us")
                except Exception:
                    pass
            elif key == ord('-'):
                try:
                    nodemap['ExposureAuto'].value = 'Off'
                    curr = nodemap['ExposureTime'].value
                    nodemap['ExposureTime'].value = max(curr / 1.5, 100)
                    print(f"Exposure: {nodemap['ExposureTime'].value:.0f}us")
                except Exception:
                    pass
            elif key == ord('a'):
                nodemap['ExposureAuto'].value = 'Continuous'
                print("Auto-exposure: ON")

            frame_count += 1

    except KeyboardInterrupt:
        pass
    finally:
        device.stop_stream()
        cv2.destroyAllWindows()
        system.destroy_device(device)
        print(f"\nSharpness maximo alcancado: {max_sharpness:.1f}")
        print(f"Total frames: {frame_count}")


if __name__ == "__main__":
    main()
