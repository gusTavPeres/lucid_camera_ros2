#!/bin/bash
# ============================================================================
# Configuração de rede ROS2 para streaming multi-PC
# ============================================================================
#
# Este script configura as variáveis de ambiente necessárias para comunicação
# ROS2 entre o PC com câmera e o notebook.
#
# Uso:
#   bash configure_network.sh
#
# Ou, para configurar manualmente, adicione ao ~/.bashrc:
#   export ROS_DOMAIN_ID=42
#   export ROS_LOCALHOST_ONLY=0
#
# ============================================================================

set -e

echo "============================================"
echo "🌐 Configuração de Rede ROS2"
echo "============================================"
echo ""

# Perguntar modo de descoberta
echo "Escolha o modo de descoberta ROS2:"
echo ""
echo "1) Multicast (padrão) - Rede local simples"
echo "   - Funciona na mesma rede/switch"
echo "   - Configuração mais fácil"
echo "   - Pode ter problemas em redes corporativas"
echo ""
echo "2) Discovery Server - Rede sem multicast"
echo "   - Para redes corporativas ou complexas"
echo "   - Requer servidor de descoberta no PC transmissor"
echo "   - Mais confiável em ambientes complexos"
echo ""
echo "3) Tailscale VPN - Rede remota"
echo "   - Para testar/simular ambiente Synkar"
echo "   - Funciona através da internet"
echo "   - Requer Tailscale instalado"
echo ""

read -p "Escolha [1/2/3]: " mode

# ROS_DOMAIN_ID padrão
DOMAIN_ID=42

# Perguntar se quer mudar o DOMAIN_ID
echo ""
read -p "ROS_DOMAIN_ID (0-101, padrão 42): " custom_domain
if [[ ! -z "$custom_domain" ]]; then
    DOMAIN_ID=$custom_domain
fi

# Arquivo de configuração
CONFIG_FILE="$HOME/.ros2_network_config"

case $mode in
    1)
        echo ""
        echo "📡 Configurando modo MULTICAST..."
        cat > "$CONFIG_FILE" << EOF
# ============================================
# ROS2 Network Config - Multicast Mode
# ============================================
export ROS_DOMAIN_ID=$DOMAIN_ID
export ROS_LOCALHOST_ONLY=0

# Discovery: Multicast (padrão)
# Nenhuma configuração adicional necessária

echo "🌐 ROS2 configurado: Multicast (Domain $DOMAIN_ID)"
EOF
        ;;

    2)
        echo ""
        read -p "IP do PC transmissor (com câmera): " server_ip
        read -p "Porta do Discovery Server (padrão 11888): " server_port
        server_port=${server_port:-11888}

        echo ""
        echo "🔍 Configurando modo DISCOVERY SERVER..."
        cat > "$CONFIG_FILE" << EOF
# ============================================
# ROS2 Network Config - Discovery Server Mode
# ============================================
export ROS_DOMAIN_ID=$DOMAIN_ID
export ROS_LOCALHOST_ONLY=0

# Discovery Server
export ROS_DISCOVERY_SERVER="$server_ip:$server_port"

echo "🌐 ROS2 configurado: Discovery Server ($server_ip:$server_port)"
EOF
        ;;

    3)
        echo ""
        echo "🔒 Configurando modo TAILSCALE VPN..."
        echo ""
        echo "ATENÇÃO: Certifique-se de que o Tailscale está instalado e ativo!"
        echo ""
        read -p "IP Tailscale do PC transmissor (100.x.x.x): " tailscale_ip

        cat > "$CONFIG_FILE" << EOF
# ============================================
# ROS2 Network Config - Tailscale VPN Mode
# ============================================
export ROS_DOMAIN_ID=$DOMAIN_ID
export ROS_LOCALHOST_ONLY=0

# Opcional: usar Discovery Server via Tailscale
# export ROS_DISCOVERY_SERVER="$tailscale_ip:11888"

echo "🌐 ROS2 configurado: Tailscale VPN ($tailscale_ip)"
EOF

        echo ""
        echo "💡 Para usar Discovery Server via Tailscale:"
        echo "   Descomente a linha ROS_DISCOVERY_SERVER no arquivo:"
        echo "   $CONFIG_FILE"
        ;;

    *)
        echo "❌ Opção inválida!"
        exit 1
        ;;
esac

# Adicionar source ao bashrc se ainda não existe
if ! grep -q "$CONFIG_FILE" ~/.bashrc; then
    echo "" >> ~/.bashrc
    echo "# ROS2 Network Configuration" >> ~/.bashrc
    echo "[ -f \"$CONFIG_FILE\" ] && source \"$CONFIG_FILE\"" >> ~/.bashrc
fi

echo ""
echo "✅ Configuração salva em: $CONFIG_FILE"
echo ""
echo "Para ativar agora:"
echo "  source $CONFIG_FILE"
echo ""
echo "Para testar a conexão (depois de ativar):"
echo "  ros2 topic list"
echo "  ros2 multicast receive  # Em um terminal"
echo "  ros2 multicast send     # Em outro terminal (no PC transmissor)"
echo ""
echo "A configuração será carregada automaticamente nos próximos logins."
echo ""
