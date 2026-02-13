# 📡 Streaming Multi-PC com ROS2

Guia completo para transmitir vídeo da câmera Lucid Vision entre dois PCs usando ROS2.

## 📖 Índice

- [Visão Geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Setup PC Transmissor](#setup-pc-transmissor-com-câmera)
- [Setup PC Receptor](#setup-pc-receptor-notebook)
- [Configuração de Rede](#configuração-de-rede)
- [Uso](#uso)
- [Gravação de Bags e Conversão para Vídeo](#gravação-de-bags-e-conversão-para-vídeo)
- [Troubleshooting](#troubleshooting)
- [Otimização de Performance](#otimização-de-performance)

---

## Visão Geral

Este repositório suporta **dois modos de operação**:

### 1️⃣ Modo Local (uma máquina)
- Câmera conectada diretamente no PC
- Visualização e gravação no mesmo PC
- Setup via Docker (já documentado no README principal)

### 2️⃣ Modo Streaming (multi-PC)
- **PC Transmissor:** Conectado à câmera, publica tópicos ROS2
- **PC Receptor:** Notebook/outro PC, subscreve aos tópicos e visualiza
- Comunicação via rede local ou VPN

Este guia foca no **Modo Streaming**.

---

## Arquitetura

```
┌─────────────────────────────────┐         ┌─────────────────────────────────┐
│   PC TRANSMISSOR (com câmera)   │         │   PC RECEPTOR (notebook)        │
│                                 │         │                                 │
│  ┌────────────────────────────┐ │         │  ┌────────────────────────────┐ │
│  │ Câmera Lucid Vision        │ │         │  │ Toolbox (Ubuntu 22.04)     │ │
│  │ Triton TRI032S             │ │         │  │ + ROS2 Humble              │ │
│  └──────────┬─────────────────┘ │         │  └──────────┬─────────────────┘ │
│             │ GigE               │         │             │                   │
│  ┌──────────▼─────────────────┐ │   ROS2  │  ┌──────────▼─────────────────┐ │
│  │ Docker Container           │ │◄────────┼──┤ Subscriber Node            │ │
│  │ + ROS2 Humble              │ │  DDS    │  │ + Stream Viewer            │ │
│  │ + Arena Camera Node        │ │         │  │ + Demosaicing              │ │
│  └──────────┬─────────────────┘ │         │  └────────────────────────────┘ │
│             │                    │         │                                 │
│  ┌──────────▼─────────────────┐ │         │  Fedora Kinoite 43             │
│  │ Tópicos ROS2:              │ │         │  (Atomic/Immutable OS)          │
│  │ /camera/image_raw          │ │         │                                 │
│  │ /camera/image_raw/comp.    │ │         │                                 │
│  └────────────────────────────┘ │         │                                 │
│                                 │         │                                 │
│  Ubuntu 22.04 + Docker          │         │                                 │
└─────────────────────────────────┘         └─────────────────────────────────┘
```

**Fluxo de dados:**
1. Câmera captura frames (bayer_rggb8) a 35fps
2. Arena Camera Node publica em `/camera/image_raw`
3. Opcionalmente, compress node publica em `/camera/image_raw/compressed` (JPEG)
4. DDS (middleware ROS2) transmite pela rede
5. Notebook subscreve e visualiza em tempo real

---

## Setup PC Transmissor (com câmera)

### Pré-requisitos
- ✅ Câmera Lucid já funcionando (ver README principal)
- ✅ Docker container `camera_dev` rodando
- ✅ Rede configurada (mesma subnet do receptor ou VPN)

### Passo 1: Verificar que a câmera está funcionando

```bash
# Entrar no container
docker compose exec camera_dev bash

# Listar câmeras detectadas
python3 /arena_camera_ros2/scripts/list_cameras.py

# Testar câmera (substitua SERIAL pelo serial da sua câmera)
/arena_camera_ros2/scripts/start_camera.sh SERIAL /camera/image_raw
```

Se você vê frames sendo publicados (`ros2 topic hz /camera/image_raw`), está pronto!

### Passo 2: Configurar modo de streaming

**Opção A: Stream RAW (Bayer) - Menor banda, demosaicing no receptor**

Câmera em formato RAW usa ~1/3 da banda de RGB, ideal para WiFi ou redes limitadas.

```bash
# Dentro do container
ros2 run arena_camera_node start --ros-args \
    -p serial:=SEU_SERIAL \
    -p topic:=/camera/image_raw \
    -p pixelformat:=bayer_rggb8 \
    -p qos_reliability:=best_effort
```

**Opção B: Stream com compressão JPEG - Compatibilidade com mais viewers**

Para comprimir Bayer → RGB → JPEG automaticamente:

```bash
# Terminal 1: Iniciar câmera RAW
ros2 run arena_camera_node start --ros-args \
    -p serial:=SEU_SERIAL \
    -p topic:=/camera/image_raw \
    -p pixelformat:=bayer_rggb8 \
    -p qos_reliability:=best_effort

# Terminal 2: Iniciar compressor
python3 /arena_camera_ros2/scripts/compress_bayer_stream.py \
    --input /camera/image_raw \
    --quality 80
```

Isso cria dois tópicos:
- `/camera/image_raw` - RAW Bayer (menor banda)
- `/camera/image_raw/compressed` - JPEG comprimido (compatível)

**Opção C: Usar launch file (recomendado)**

```bash
ros2 launch /arena_camera_ros2/launch/camera_streaming.launch.py \
    serial:=SEU_SERIAL \
    enable_compressed:=true \
    jpeg_quality:=80 \
    qos_reliability:=best_effort
```

### Passo 3: Configurar variáveis de ambiente ROS2

**Para rede local (multicast):**

```bash
# Adicionar ao ~/.bashrc (dentro do container)
export ROS_DOMAIN_ID=42
export ROS_LOCALHOST_ONLY=0
```

**Para Discovery Server (rede sem multicast):**

```bash
# Iniciar servidor de descoberta (Terminal separado)
fastdds discovery -i 0 -l 0.0.0.0 -p 11888

# Adicionar ao ~/.bashrc
export ROS_DOMAIN_ID=42
export ROS_DISCOVERY_SERVER="0.0.0.0:11888"
```

**Reiniciar daemon ROS2:**

```bash
source ~/.bashrc
ros2 daemon stop && ros2 daemon start
```

### Passo 4: Verificar que está publicando

```bash
# Listar tópicos
ros2 topic list

# Verificar FPS
ros2 topic hz /camera/image_raw

# Verificar info
ros2 topic info /camera/image_raw --verbose
```

✅ **PC Transmissor configurado!**

---

## Setup PC Receptor (Notebook)

### Pré-requisitos
- Fedora Kinoite/Silverblue 43+ (ou qualquer distro com Toolbox)
- Conexão de rede com PC transmissor

### Instalação rápida

```bash
# Clonar repositório
git clone https://github.com/gusTavPeres/lucid_camera_ros2.git
cd lucid_camera_ros2/notebook_setup

# Executar setup (cria Toolbox + instala ROS2)
bash setup_toolbox.sh
```

⏱️ **Leva 5-10 minutos** (baixa e instala ROS2 Humble)

### Detalhes da instalação

O script `setup_toolbox.sh`:
1. Cria container Toolbox com Ubuntu 22.04
2. Instala ROS2 Humble Desktop
3. Instala cv_bridge, rqt, OpenCV
4. Configura auto-source do ROS2

**Documentação completa:** [notebook_setup/README.md](notebook_setup/README.md)

---

## Configuração de Rede

Existem **3 modos de descoberta** ROS2:

### Modo 1: Multicast (Padrão - Rede Local)

**Quando usar:** Mesma rede física (switch/roteador)

**Setup (em ambos os PCs):**

```bash
export ROS_DOMAIN_ID=42  # Deve ser igual nos dois
export ROS_LOCALHOST_ONLY=0

# Reiniciar daemon
ros2 daemon stop && ros2 daemon start
```

**Testar conexão:**

```bash
# PC Transmissor
ros2 multicast send

# PC Receptor (deve receber a mensagem)
ros2 multicast receive
```

Se recebeu a mensagem ✅, está funcionando!

**Possíveis problemas:**
- Firewall bloqueando multicast
- Switch sem suporte a multicast
- Redes WiFi corporativas bloqueando

**Solução:** Usar Discovery Server (Modo 2)

---

### Modo 2: Discovery Server (Sem Multicast)

**Quando usar:** Rede corporativa, VLANs, sem multicast

**Setup no PC Transmissor:**

```bash
# Iniciar servidor de descoberta
fastdds discovery -i 0 -l 0.0.0.0 -p 11888
```

**Setup em ambos os PCs:**

```bash
export ROS_DOMAIN_ID=42
export ROS_DISCOVERY_SERVER="<IP_DO_TRANSMISSOR>:11888"

ros2 daemon stop && ros2 daemon start
```

**Verificar:**

```bash
ros2 topic list  # Deve mostrar /camera/image_raw
```

---

### Modo 3: Tailscale VPN (Rede Remota)

**Quando usar:** Teste remoto, conexão via internet, redes diferentes

**Instalar Tailscale (ambos os PCs):**

```bash
# Fedora (host, não Toolbox)
sudo dnf install tailscale
sudo systemctl enable --now tailscaled
sudo tailscale up

# Ubuntu/Docker (PC transmissor)
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

**Obter IPs Tailscale:**

```bash
tailscale ip -4
# Exemplo: 100.101.102.103
```

**Configurar ROS2:**

Opção A - Multicast via VPN (simples):
```bash
export ROS_DOMAIN_ID=42
export ROS_LOCALHOST_ONLY=0
```

Opção B - Discovery Server via Tailscale (mais confiável):
```bash
# PC Transmissor: iniciar servidor no IP Tailscale
fastdds discovery -i 0 -l 100.x.x.x -p 11888

# Ambos os PCs:
export ROS_DISCOVERY_SERVER="100.x.x.x:11888"
```

---

### Script de configuração automática

Para facilitar, use o script interativo:

```bash
# No notebook (dentro do Toolbox)
bash configure_network.sh
```

Ele pergunta qual modo usar e configura tudo automaticamente.

---

## Uso

### Visualizar Stream no Notebook

**Opção 1: Viewer Otimizado (Recomendado)**

```bash
# Dentro do Toolbox
cd lucid_camera_ros2/notebook_setup
python3 stream_viewer.py --topic /camera/image_raw
```

**Features:**
- ✅ Auto-detecta formato (Bayer, RGB, compressed)
- ✅ Demosaicing automático de Bayer
- ✅ Mostra FPS e banda em tempo real
- ✅ Salva frames (tecla 's')
- ✅ Alterna RAW/RGB (tecla 'r')

**Teclas:**
- `s` - Salvar frame
- `r` - Alternar RAW/RGB
- `q` - Sair

**Opção 2: rqt_image_view (Padrão ROS2)**

```bash
ros2 run rqt_image_view rqt_image_view
```

Selecione `/camera/image_raw` no dropdown.

**Opção 3: Stream Comprimido (menor banda)**

```bash
python3 stream_viewer.py --topic /camera/image_raw --compressed
```

---

### Exemplos de Comandos Úteis

```bash
# Listar tópicos disponíveis
ros2 topic list

# Ver FPS de um tópico
ros2 topic hz /camera/image_raw

# Ver largura de banda (bytes/s)
ros2 topic bw /camera/image_raw

# Informações detalhadas do tópico
ros2 topic info /camera/image_raw --verbose

# Ver mensagem em tempo real (sem imagem)
ros2 topic echo /camera/image_raw --no-arr

# Gravar bag local no notebook (opcional)
ros2 bag record /camera/image_raw -o stream_test
```

---

## Gravação de Bags e Conversão para Vídeo

### Gravar Bag no PC Transmissor

```bash
# Dentro do container Docker
cd /arena_camera_ros2/bags

# Gravar tópico RAW
ros2 bag record /camera/image_raw -o minha_gravacao

# OU gravar tópico comprimido (economiza espaço)
ros2 bag record /camera/image_raw/compressed -o minha_gravacao
```

Pressione `Ctrl+C` para parar.

---

### Converter Bag em Vídeo MP4

Use o script otimizado `bag_to_video.py`:

```bash
# Terminal 1: Iniciar conversor
python3 /arena_camera_ros2/scripts/bag_to_video.py \
    --topic /camera/image_raw \
    --output video.mp4 \
    --quality 23

# Terminal 2: Reproduzir bag
ros2 bag play ./minha_gravacao
```

Quando a bag terminar, pressione `Ctrl+C` no Terminal 1.

**Features do script:**
- ✅ Auto-detecta resolução e FPS da bag
- ✅ Suporta Bayer RAW (faz demosaicing automático)
- ✅ Suporta RGB, BGR, compressed
- ✅ Codec H.264 (melhor compressão)
- ✅ Qualidade configurável (--quality 0-51)

**Exemplo com bag comprimida:**

```bash
python3 bag_to_video.py \
    --topic /camera/image_raw/compressed \
    --output video.mp4
```

---

### Especificar FPS manualmente

```bash
python3 bag_to_video.py \
    --topic /camera/image_raw \
    --output video.mp4 \
    --fps 35
```

---

## Troubleshooting

### ❌ `ros2 topic list` não mostra tópicos da câmera

**Causas possíveis:**

1. **ROS_DOMAIN_ID diferente**
   ```bash
   # Verificar
   echo $ROS_DOMAIN_ID
   # Deve ser igual nos dois PCs (ex: 42)
   ```

2. **Firewall bloqueando**
   ```bash
   # Fedora
   sudo firewall-cmd --zone=public --add-service=mdns --permanent
   sudo firewall-cmd --reload

   # Ubuntu/Debian
   sudo ufw allow from 192.168.0.0/16
   ```

3. **Multicast não funciona**
   - Solução: usar Discovery Server

4. **ROS2 daemon desatualizado**
   ```bash
   ros2 daemon stop && ros2 daemon start
   ```

---

### ❌ Stream travando ou com lag

**Soluções:**

1. **Usar QoS best_effort** (já configurado no viewer otimizado)

2. **Subscrever tópico comprimido:**
   ```bash
   python3 stream_viewer.py --topic /camera/image_raw --compressed
   ```

3. **Verificar banda da rede:**
   ```bash
   # Instalar iperf3
   sudo apt install iperf3

   # PC transmissor
   iperf3 -s

   # Notebook
   iperf3 -c <IP_DO_TRANSMISSOR>
   ```

   **Banda mínima recomendada:**
   - RAW (bayer_rggb8 1920x1200@35fps): ~35 Mbps
   - Compressed (JPEG quality 80): ~10-15 Mbps

4. **Reduzir qualidade de compressão:**
   ```bash
   # PC transmissor: reduzir qualidade JPEG
   python3 compress_bayer_stream.py --quality 60
   ```

---

### ❌ Janela do viewer não abre no Toolbox

**Solução (rodar no HOST, não no Toolbox):**

```bash
xhost +local:
```

Isso permite que o Toolbox abra janelas gráficas.

---

### ❌ `bag_to_video.py` resulta em vídeo corrompido

**Causas:**

1. **Interrompeu antes da bag terminar**
   - Solução: deixar a bag reproduzir até o fim antes de pressionar Ctrl+C

2. **Formato Bayer não detectado**
   - Verificar encoding: `ros2 topic echo /camera/image_raw --once`
   - Deve ser `bayer_rggb8`, `bayer_bggr8`, etc.

3. **VideoWriter não suporta codec**
   - Instalar codecs: `sudo apt install ffmpeg libavcodec-extra`

---

### ❌ FPS baixo (menor que 35fps)

**Causas possíveis:**

1. **Banda insuficiente** (ver acima)

2. **CPU sobrecarregada no receptor**
   - Demosaicing Bayer consome CPU
   - Solução: usar tópico comprimido (demosaicing no transmissor)

3. **Buffers de rede pequenos**
   ```bash
   # Aumentar buffers (PC transmissor)
   sudo sysctl -w net.core.rmem_max=26214400
   sudo sysctl -w net.core.wmem_max=26214400
   ```

---

## Otimização de Performance

### Para WiFi ou Rede Limitada

1. **Use stream comprimido:**
   ```bash
   # PC transmissor
   python3 compress_bayer_stream.py --quality 70
   ```

2. **Reduza resolução da câmera:**
   ```bash
   ros2 run arena_camera_node start --ros-args \
       -p width:=1280 -p height:=720
   ```

3. **Use QoS best_effort** (padrão nos scripts)

---

### Para Rede Cabeada (Gigabit)

1. **Use stream RAW (Bayer)** - maior qualidade, menor processamento

2. **Ative Jumbo Frames:**
   ```bash
   # Ambos os PCs
   sudo ip link set dev eth0 mtu 9000
   ```

3. **Use QoS reliable** se precisar garantir entrega:
   ```bash
   ros2 run arena_camera_node start --ros-args \
       -p qos_reliability:=reliable
   ```

---

### Comparação de Modos

| Modo | Banda (Mbps) | CPU Transmissor | CPU Receptor | Latência |
|------|--------------|-----------------|--------------|----------|
| **RAW Bayer** | ~35 | Baixo | Médio (demosaicing) | Baixa |
| **Compressed JPEG Q80** | ~12 | Alto (compressão) | Baixo | Média |
| **Compressed JPEG Q60** | ~8 | Alto | Baixo | Média |
| **RGB8 (sem compress)** | ~100 | Médio | Baixo | Baixa |

**Recomendação:**
- **Rede Cabeada:** RAW Bayer (melhor qualidade)
- **WiFi:** Compressed JPEG Q70-80
- **Internet/VPN:** Compressed JPEG Q60

---

## Resumo - Fluxo Completo

### PC Transmissor

```bash
# 1. Entrar no container
docker compose exec camera_dev bash

# 2. Configurar rede
export ROS_DOMAIN_ID=42
export ROS_LOCALHOST_ONLY=0
ros2 daemon stop && ros2 daemon start

# 3. Iniciar câmera + compressor
ros2 launch /arena_camera_ros2/launch/camera_streaming.launch.py \
    serial:=SEU_SERIAL \
    enable_compressed:=true \
    jpeg_quality:=80

# 4. (Opcional) Gravar bag
ros2 bag record /camera/image_raw -o gravacao_$(date +%Y%m%d_%H%M%S)
```

---

### PC Receptor (Notebook)

```bash
# 1. Entrar no Toolbox
toolbox enter ros2-humble

# 2. Configurar rede (mesmos valores do transmissor)
export ROS_DOMAIN_ID=42
export ROS_LOCALHOST_ONLY=0
ros2 daemon stop && ros2 daemon start

# 3. Verificar conexão
ros2 topic list  # Deve ver /camera/image_raw

# 4. Visualizar stream
cd lucid_camera_ros2/notebook_setup
python3 stream_viewer.py --topic /camera/image_raw --compressed
```

---

## Referências

- [ROS2 Humble Docs](https://docs.ros.org/en/humble/index.html)
- [FastDDS Discovery Server](https://fast-dds.docs.eprosima.com/en/latest/fastdds/discovery/discovery_server.html)
- [Tailscale](https://tailscale.com/)
- [Lucid Vision ArenaSDK](https://thinklucid.com/downloads-hub/)

---

**Dúvidas ou problemas?** Abra uma issue no GitHub!
