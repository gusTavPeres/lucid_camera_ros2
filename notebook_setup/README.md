# Setup do Notebook (Fedora Kinoite) - Receptor de Stream

Este guia configura seu notebook Fedora Kinoite/Silverblue para receber o stream da câmera Lucid Vision via ROS2.

## 📋 Pré-requisitos

- Fedora Kinoite/Silverblue 43 ou superior
- Toolbox instalado (geralmente vem pré-instalado)
- Conexão de rede com o PC transmissor (ou Tailscale VPN)

---

## 🚀 Instalação Rápida (3 passos)

### 1️⃣ Configurar Toolbox com ROS2 Humble

Baixe e execute o script de setup:

```bash
# Clonar o repositório (se ainda não tiver)
git clone https://github.com/gusTavPeres/lucid_camera_ros2.git
cd lucid_camera_ros2/notebook_setup

# Executar setup do Toolbox
bash setup_toolbox.sh
```

Este script vai:
- ✅ Criar um container Toolbox com Ubuntu 22.04
- ✅ Instalar ROS2 Humble Desktop
- ✅ Instalar cv_bridge, rqt, OpenCV e outras dependências
- ✅ Configurar auto-source do ROS2

⏱️ **Tempo estimado:** 5-10 minutos (depende da conexão de internet)

---

### 2️⃣ Configurar Rede ROS2

Entre no Toolbox e configure a rede:

```bash
# Entrar no Toolbox
toolbox enter ros2-humble

# Configurar rede
bash configure_network.sh
```

O script vai perguntar:
1. **Modo de descoberta:** Multicast, Discovery Server ou Tailscale VPN
2. **ROS_DOMAIN_ID:** Deve ser o mesmo do PC transmissor (padrão: 42)
3. **IP do servidor:** Se usar Discovery Server ou Tailscale

**Qual modo escolher?**

| Modo | Quando usar |
|------|------------|
| **Multicast** | Mesma rede local (switch/roteador), configuração mais simples |
| **Discovery Server** | Rede corporativa ou quando multicast não funciona |
| **Tailscale VPN** | Simular ambiente Synkar ou teste remoto |

---

### 3️⃣ Testar Conexão

Ainda dentro do Toolbox:

```bash
# Ativar configuração de rede
source ~/.ros2_network_config

# Verificar se ROS2 está ativo
ros2 --version

# Listar tópicos disponíveis (deve ver os tópicos da câmera do PC transmissor)
ros2 topic list

# Testar multicast (em outro terminal no PC transmissor, rode: ros2 multicast send)
ros2 multicast receive
```

Se você vir `/camera/image_raw` na lista de tópicos, **está funcionando!** 🎉

---

## 📹 Visualizar o Stream

### Opção 1: Viewer Otimizado (Recomendado)

Usa o script Python customizado com suporte a Bayer RAW:

```bash
# Dentro do Toolbox
python3 stream_viewer.py --topic /camera/image_raw
```

**Features:**
- ✅ Auto-detecta formato (Bayer RAW, RGB, compressed)
- ✅ Faz demosaicing automático de imagens Bayer
- ✅ Mostra FPS e banda em tempo real
- ✅ Salva frames com tecla 's'
- ✅ Alterna entre RAW e RGB com tecla 'r'

**Teclas:**
- `s` - Salvar frame
- `r` - Alternar RAW/RGB (apenas para Bayer)
- `q` ou `ESC` - Sair

### Opção 2: rqt_image_view (Padrão ROS2)

```bash
ros2 run rqt_image_view rqt_image_view
```

Na interface gráfica, selecione o tópico `/camera/image_raw` no dropdown.

**Nota:** O rqt faz demosaicing automático de imagens Bayer.

### Opção 3: Visualizar Stream Comprimido

Se o PC transmissor estiver publicando `/camera/image_raw/compressed`:

```bash
# Com viewer otimizado
python3 stream_viewer.py --topic /camera/image_raw --compressed

# Ou com rqt
ros2 run rqt_image_view rqt_image_view /camera/image_raw/compressed
```

**Vantagem:** Menor banda de rede (imagens JPEG comprimidas).

---

## 🔧 Troubleshooting

### ❌ Problema: `ros2 topic list` não mostra tópicos da câmera

**Possíveis causas:**

1. **ROS_DOMAIN_ID diferente**
   ```bash
   # Verificar
   echo $ROS_DOMAIN_ID

   # Deve ser 42 (ou o mesmo do PC transmissor)
   export ROS_DOMAIN_ID=42
   ```

2. **Firewall bloqueando**
   ```bash
   # No Fedora (host), permitir multicast
   sudo firewall-cmd --zone=public --add-service=mdns --permanent
   sudo firewall-cmd --reload
   ```

3. **Multicast não funciona na rede**
   - Solução: usar Discovery Server (ver seção "Configurar Rede")

4. **PCs em redes diferentes**
   - Solução: usar Tailscale VPN

---

### ❌ Problema: `toolbox: command not found`

Instalar Toolbox:

```bash
rpm-ostree install toolbox
systemctl reboot
```

---

### ❌ Problema: Janela do viewer não abre

Liberar acesso X11 do Toolbox (rodar no **host**, não no Toolbox):

```bash
xhost +local:
```

Isso permite que containers abram janelas gráficas.

---

### ❌ Problema: Stream travando ou com lag

1. **Usar QoS "best_effort"** (já configurado no viewer otimizado)

2. **Subscrever tópico comprimido** para economizar banda:
   ```bash
   python3 stream_viewer.py --topic /camera/image_raw --compressed
   ```

3. **Verificar banda de rede:**
   ```bash
   # Instalar iperf3 (dentro do Toolbox)
   sudo apt install iperf3

   # No PC transmissor
   iperf3 -s

   # No notebook
   iperf3 -c <IP_DO_PC_TRANSMISSOR>
   ```

   **Banda mínima recomendada:**
   - RAW (bayer_rggb8): ~35 Mbps (1920x1200@35fps)
   - Compressed (JPEG): ~10-15 Mbps (dependendo da qualidade)

---

## 📚 Comandos Úteis (Cheat Sheet)

```bash
# Entrar no Toolbox
toolbox enter ros2-humble

# Ativar ROS2 (se não auto-carregar)
source /opt/ros/humble/setup.bash
source ~/.ros2_network_config

# Listar tópicos
ros2 topic list

# Ver FPS de um tópico
ros2 topic hz /camera/image_raw

# Ver informações de um tópico
ros2 topic info /camera/image_raw --verbose

# Ver mensagem em tempo real (modo texto)
ros2 topic echo /camera/image_raw --no-arr

# Gravar bag local (opcional)
ros2 bag record /camera/image_raw -o stream_local

# Visualizar stream
python3 stream_viewer.py --topic /camera/image_raw
```

---

## 🌐 Modos de Rede Detalhados

### Modo 1: Multicast (Rede Local)

**Setup:**
```bash
export ROS_DOMAIN_ID=42
export ROS_LOCALHOST_ONLY=0
```

**Testar:**
```bash
# Terminal 1 (PC transmissor)
ros2 multicast send

# Terminal 2 (Notebook)
ros2 multicast receive
```

---

### Modo 2: Discovery Server

**No PC transmissor:**
```bash
# Instalar FastDDS (se não tiver)
sudo apt install ros-humble-fastrtps

# Iniciar servidor de descoberta
fastdds discovery -i 0 -l 0.0.0.0 -p 11888
```

**No notebook (Toolbox):**
```bash
export ROS_DOMAIN_ID=42
export ROS_DISCOVERY_SERVER="<IP_DO_PC>:11888"

# Reiniciar daemon
ros2 daemon stop
ros2 daemon start
```

---

### Modo 3: Tailscale VPN

**Instalar Tailscale (no host, não no Toolbox):**
```bash
# Fedora Kinoite
sudo dnf install tailscale
sudo systemctl enable --now tailscaled
sudo tailscale up
```

**Configurar ROS2 (dentro do Toolbox):**
```bash
export ROS_DOMAIN_ID=42
export ROS_LOCALHOST_ONLY=0

# Opcional: usar Discovery Server via Tailscale
# export ROS_DISCOVERY_SERVER="100.x.x.x:11888"
```

**Obter IP Tailscale:**
```bash
tailscale ip -4
# Exemplo: 100.101.102.103
```

Use esse IP para configurar o Discovery Server ou simplesmente deixe o multicast funcionar pela VPN.

---

## 🔄 Atualizações e Manutenção

### Atualizar ROS2 no Toolbox

```bash
toolbox enter ros2-humble
sudo apt update
sudo apt upgrade
```

### Recriar Toolbox do Zero

```bash
toolbox rm ros2-humble
bash setup_toolbox.sh
```

---

## 📖 Próximos Passos

Depois de conseguir visualizar o stream:

1. **Gravar bags locais** (opcional):
   ```bash
   ros2 bag record /camera/image_raw -o stream_test
   ```

2. **Processar imagens em tempo real** - Criar nodes ROS2 customizados

3. **Integrar com pipeline de visão computacional** - YOLO, segmentação, etc.

---

## 💡 Dicas

- **Toolbox vs Docker:** Toolbox é mais integrado com Fedora, mas você também pode usar Podman/Docker se preferir
- **Performance:** Para melhor performance, use tópico comprimido em redes WiFi
- **Desenvolvimento:** Clone este repositório também dentro do Toolbox para ter acesso aos scripts
- **Sair do Toolbox:** Digite `exit` ou pressione `Ctrl+D`

---

**Dúvidas?** Veja a documentação completa no README principal do repositório.
