#!/bin/bash
# Rotas para câmeras GigE em adaptadores USB com subnets sobrepostas

# Câmera 2: 169.254.153.193 via enx5c5310faf11f
CAM2_IP="169.254.153.193"
CAM2_IFACE="enx5c5310faf11f"
CAM2_SRC="169.254.42.30"
ip addr add "${CAM2_SRC}/16" dev "${CAM2_IFACE}" 2>/dev/null || true
ip route add "${CAM2_IP}/32" dev "${CAM2_IFACE}" src "${CAM2_SRC}" 2>/dev/null || true

# Câmera 1: 169.254.10.197 via enxdc3262cf8709
CAM1_IP="169.254.10.197"
CAM1_IFACE="enxdc3262cf8709"
CAM1_SRC="169.254.10.1"
ip addr add "${CAM1_SRC}/16" dev "${CAM1_IFACE}" 2>/dev/null || true
ip route add "${CAM1_IP}/32" dev "${CAM1_IFACE}" src "${CAM1_SRC}" 2>/dev/null || true
