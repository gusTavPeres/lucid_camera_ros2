#!/bin/bash
# Rotas /32 para câmeras GigE em adaptadores USB com subnets sobrepostas (169.254.0.0/16).
#
# Problema: múltiplos adaptadores USB-Ethernet na mesma subnet 169.254.0.0/16.
# Sem rotas /32, o kernel usa a rota /16 com menor métrica, enviando
# pacotes para a interface errada.
#
# Este script cria rotas host (/32) para cada câmera, forçando o tráfego
# pela interface USB correta. O IP de origem é detectado automaticamente.
#
# === CARRO ===
# Com portas gigabit dedicadas, cada câmera terá sua própria subnet.
# Este script não será necessário (ou será simplificado).

set -e

# --- Mapeamento câmera -> interface ---
# Atualize os IPs se as câmeras mudarem de endereço (ver list_cameras.py)
CAM1_IP="169.254.10.197"
CAM1_IFACE="enx5c5310faf11f"

CAM2_IP="169.254.153.193"
CAM2_IFACE="enxdc3262cf8709"

get_iface_ip() {
    local iface="$1"
    ip -4 addr show "$iface" 2>/dev/null | grep -oP '(?<=inet )169\.254\.\d+\.\d+' | head -1
}

setup_camera_route() {
    local cam_name="$1"
    local cam_ip="$2"
    local cam_iface="$3"

    local src_ip
    src_ip=$(get_iface_ip "$cam_iface")

    if [[ -z "$src_ip" ]]; then
        echo "[WARN] ${cam_name}: interface ${cam_iface} sem IP 169.254.x.x — pulando"
        return 1
    fi

    # Rota /32 garante que pacotes para esta câmera usem a interface correta
    ip route replace "${cam_ip}/32" dev "${cam_iface}" src "${src_ip}" 2>/dev/null || true
    echo "[OK] ${cam_name}: ${cam_ip} via ${cam_iface} (src ${src_ip})"
}

echo "=== Configurando rotas para câmeras GigE ==="
setup_camera_route "Camera 1 (${CAM1_IP})" "$CAM1_IP" "$CAM1_IFACE"
setup_camera_route "Camera 2 (${CAM2_IP})" "$CAM2_IP" "$CAM2_IFACE"
echo "=== Rotas configuradas ==="
