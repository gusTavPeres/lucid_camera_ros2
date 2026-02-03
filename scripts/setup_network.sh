#!/bin/bash
#
# Script para configurar a interface de rede para câmeras GigE Vision
# Execute este script no HOST (não dentro do container)
#
# Uso: sudo ./setup_network.sh [interface]
#      sudo ./setup_network.sh enp45s0
#

INTERFACE=${1:-enp45s0}

echo "=============================================="
echo "  Configuração de Rede para Câmeras GigE"
echo "=============================================="
echo ""
echo "Interface: $INTERFACE"
echo ""

# Verificar se a interface existe
if ! ip link show "$INTERFACE" &> /dev/null; then
    echo "ERRO: Interface $INTERFACE não encontrada!"
    echo ""
    echo "Interfaces disponíveis:"
    ip link show | grep -E "^[0-9]+:" | awk -F: '{print "  " $2}'
    exit 1
fi

# Configurar MTU para Jumbo Frames (importante para alta taxa de transferência)
echo "[1/5] Configurando MTU para 9000 (Jumbo Frames)..."
sudo ip link set "$INTERFACE" mtu 9000

# Desabilitar offloading (pode causar problemas com GigE Vision)
echo "[2/5] Desabilitando TX/RX offloading..."
sudo ethtool -K "$INTERFACE" tx off rx off gso off gro off tso off 2>/dev/null || echo "  Aviso: ethtool não disponível ou offloading já desabilitado"

# Configurar buffers de rede do sistema
echo "[3/5] Configurando buffers de rede do sistema..."
sudo sysctl -w net.core.rmem_default=33554432
sudo sysctl -w net.core.rmem_max=134217728
sudo sysctl -w net.core.wmem_default=33554432
sudo sysctl -w net.core.wmem_max=134217728

# Aumentar o buffer da interface (se suportado)
echo "[4/5] Aumentando buffer da interface..."
sudo ethtool -G "$INTERFACE" rx 4096 tx 4096 2>/dev/null || echo "  Aviso: Não foi possível ajustar buffers da interface"

# Tornar configurações de sysctl persistentes
echo "[5/5] Tornando configurações persistentes..."
SYSCTL_CONF="/etc/sysctl.d/99-gige-vision.conf"
sudo tee "$SYSCTL_CONF" > /dev/null << EOF
# Configurações de rede para câmeras GigE Vision
# Gerado por setup_network.sh

net.core.rmem_default=33554432
net.core.rmem_max=134217728
net.core.wmem_default=33554432
net.core.wmem_max=134217728
EOF

echo ""
echo "=============================================="
echo "  Configuração concluída!"
echo "=============================================="
echo ""
echo "Verificação da interface $INTERFACE:"
echo "  MTU: $(cat /sys/class/net/$INTERFACE/mtu)"
echo "  Status: $(cat /sys/class/net/$INTERFACE/operstate)"
echo ""
echo "Para aplicar as configurações de MTU na inicialização,"
echo "adicione ao /etc/network/interfaces ou configure via NetworkManager."
echo ""
echo "Se a câmera não for detectada, verifique:"
echo "  1. IP da câmera está na mesma subnet que a interface"
echo "  2. Firewall não está bloqueando tráfego GigE Vision"
echo "  3. A câmera está ligada e conectada"
echo ""
