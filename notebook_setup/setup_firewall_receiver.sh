#!/bin/bash
# setup_firewall_receiver.sh
# Libera tráfego ROS2/DDS no PC receptor (Ubuntu)
# Execute com sudo: sudo bash setup_firewall_receiver.sh

set -e

LAN_SUBNET="${1:-192.168.3.0/24}"
echo "Liberando tráfego ROS2 da sub-rede: $LAN_SUBNET"

# Libera UDP/TCP da LAN (DDS usa portas dinâmicas >1024)
iptables -C INPUT -s "$LAN_SUBNET" -p udp -j ACCEPT 2>/dev/null || \
    iptables -I INPUT -s "$LAN_SUBNET" -p udp -j ACCEPT

iptables -C INPUT -s "$LAN_SUBNET" -p tcp -j ACCEPT 2>/dev/null || \
    iptables -I INPUT -s "$LAN_SUBNET" -p tcp -j ACCEPT

# Salvar regras para persistir após reboot
if command -v netfilter-persistent &>/dev/null; then
    netfilter-persistent save
    echo "Regras salvas (netfilter-persistent)"
elif command -v iptables-save &>/dev/null; then
    iptables-save > /etc/iptables/rules.v4 2>/dev/null || true
    echo "Regras salvas em /etc/iptables/rules.v4"
fi

echo "OK - UDP/TCP da $LAN_SUBNET liberados"
echo "Para VPN (WireGuard), rode novamente com o subnet da VPN:"
echo "  sudo bash setup_firewall_receiver.sh <VPN_SUBNET>"
