#!/usr/bin/env python3
"""
Script para listar todas as câmeras Lucid Vision conectadas.
Útil para identificar seriais e configurar múltiplas câmeras.
"""

import sys

try:
    from arena_api.system import system
except ImportError:
    print("ERRO: arena_api não encontrado.")
    print("Certifique-se de que o arena_api está instalado.")
    sys.exit(1)


def list_cameras():
    """Lista todas as câmeras conectadas."""
    print("\n" + "=" * 60)
    print("  Buscando câmeras Lucid Vision...")
    print("=" * 60 + "\n")

    # Configurar timeout para descoberta
    system.DEVICE_INFOS_TIMEOUT_MILLISEC = 5000

    # Descobrir dispositivos (a propriedade device_infos faz a descoberta)
    device_infos = system.device_infos

    if not device_infos:
        print("Nenhuma câmera encontrada!")
        print("\nVerifique:")
        print("  1. A câmera está conectada e ligada")
        print("  2. A interface de rede está configurada corretamente")
        print("  3. O IP da câmera está na mesma subnet")
        return []

    print(f"Encontrada(s) {len(device_infos)} câmera(s):\n")

    cameras = []
    for i, info in enumerate(device_infos, 1):
        camera_data = {
            "index": i,
            "model": info.get("model", "N/A"),
            "serial": info.get("serial", "N/A"),
            "ip": info.get("ip", "N/A"),
            "mac": info.get("mac", "N/A"),
            "vendor": info.get("vendor", "N/A"),
        }
        cameras.append(camera_data)

        print(f"  Câmera {i}:")
        print(f"    Modelo:  {camera_data['model']}")
        print(f"    Serial:  {camera_data['serial']}")
        print(f"    IP:      {camera_data['ip']}")
        print(f"    MAC:     {camera_data['mac']}")
        print(f"    Vendor:  {camera_data['vendor']}")
        print()

    print("-" * 60)
    print("\nPara usar uma câmera específica no ROS2:")
    print("  ros2 run arena_camera_node start --ros-args -p serial:=<SERIAL>")
    print("\nExemplo para múltiplas câmeras:")
    for cam in cameras:
        print(f"  ros2 run arena_camera_node start --ros-args \\")
        print(f"    -p serial:={cam['serial']} \\")
        print(f"    -p topic:=/camera_{cam['index']}/image_raw")
        print()

    return cameras


def main():
    try:
        cameras = list_cameras()
        print(f"\nTotal: {len(cameras)} câmera(s) encontrada(s)")
    except Exception as e:
        print(f"Erro ao listar câmeras: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
