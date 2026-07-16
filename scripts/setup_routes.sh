#!/bin/bash
# Rotas /32 para câmeras GigE em adaptadores com subnets sobrepostas (169.254.0.0/16).
#
# Problema: múltiplas interfaces na mesma subnet 169.254.0.0/16.
# Sem rotas /32, o kernel usa a rota /16 com menor métrica, enviando
# pacotes para a interface errada.
#
# Fonte de configuração: cameras.yaml — campos opcionais `ip` e `iface`
# de cada câmera. Câmeras sem esses campos são ignoradas.
# Para descobrir IPs e seriais: scripts/list_cameras.py

set -e

CONFIG="${CAMERA_CONFIG:-/arena_camera_ros2/ros2_ws/src/arena_camera_node/config/cameras.yaml}"

if [[ ! -f "$CONFIG" ]]; then
    echo "[setup_routes] config não encontrado: $CONFIG — nenhuma rota a configurar"
    exit 0
fi

ROUTES=$(python3 - "$CONFIG" <<'PYEOF' 2>/dev/null
import sys, yaml
with open(sys.argv[1], encoding="utf-8") as f:
    config = yaml.safe_load(f) or {}
for cam in config.get("cameras", []):
    ip, iface = cam.get("ip", ""), cam.get("iface", "")
    if ip and iface:
        print(f"{ip}:{iface}")
PYEOF
) || { echo "[setup_routes] python3/pyyaml indisponível — pulando rotas"; exit 0; }

if [[ -z "$ROUTES" ]]; then
    echo "[setup_routes] nenhuma câmera com ip/iface em $CONFIG — nada a configurar"
    exit 0
fi

get_iface_ip() {
    local iface="$1"
    ip -4 addr show "$iface" 2>/dev/null | grep -oP '(?<=inet )169\.254\.\d+\.\d+' | head -1
}

echo "=== Configurando rotas para câmeras GigE ==="
for route in $ROUTES; do
    cam_ip="${route%%:*}"
    cam_iface="${route#*:}"

    src_ip=$(get_iface_ip "$cam_iface")
    if [[ -z "$src_ip" ]]; then
        echo "[WARN] ${cam_iface} sem IP 169.254.x.x — pulando ${cam_ip}"
        continue
    fi

    ip route replace "${cam_ip}/32" dev "${cam_iface}" src "${src_ip}" 2>/dev/null || true
    echo "[OK] ${cam_ip} via ${cam_iface} (src ${src_ip})"
done
echo "=== Rotas configuradas ==="
