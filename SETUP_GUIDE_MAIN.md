# Setup Guide — Main Branch

Pipeline de câmeras Lucid Vision com compressão JPEG e streaming via VPN.

---

## Pré-requisitos

- PC com Ubuntu, Docker e Docker Compose instalados
- Câmeras Lucid Vision Triton conectadas via adaptadores Ethernet (MTU 9000)
- NetBird VPN ativo em ambos os lados (`netbird up --mtu 1420`)
- Notebook com distrobox `ros2-humble` configurado

---

## PC — Configuração

### 1. Arquivo de câmeras

Edite `config/cameras.yaml` com os seriais e tópicos das suas câmeras:

```yaml
cameras:
  - name: camera_1
    serial: '243901923'
    topic: /camera/cam1/image_raw
    pixelformat: bayer_rggb8
    width: 1024        # reduzir resolução se adaptadores forem 100 Mbps
    height: 768
    exposure_time: 25000.0
    gain: 20.0
    frame_rate: 10.0
    qos_reliability: best_effort

  - name: camera_2
    serial: '243901918'
    topic: /camera/cam2/image_raw
    pixelformat: bayer_rggb8
    width: 1024
    height: 768
    exposure_time: 25000.0
    gain: 20.0
    frame_rate: 10.0
    qos_reliability: best_effort
```

> Para 4–6 câmeras, adicione mais entradas seguindo o mesmo padrão.
> Com portas GigE nativas (carro), use `width: 2048`, `height: 1536`, `frame_rate: 33.0` para resolução máxima.

### 2. Routing (apenas se houver 2+ câmeras em interfaces diferentes)

Edite `scripts/setup_routes.sh` com o IP e interface da câmera que não está na rota padrão:

```bash
CAM2_IP="169.254.153.193"    # IP da câmera problema
CAM2_IFACE="enx5c5310faf11f" # interface correta para ela
CAM2_SRC="169.254.42.30"     # IP local dessa interface
```

### 3. Subir o sistema

```bash
cd ~/lucid_camera_ros2
docker compose up -d
```

O container inicia automaticamente:
1. Corrige routing das câmeras
2. Sobe o relay de compressão (participantId 0 — descobrível remotamente)
3. Sobe o pipeline de câmeras com retry automático

Acompanhar logs:
```bash
docker logs -f lucid_camera_dev
```

Parar:
```bash
docker compose down
```

---

## Notebook — Visualização via VPN

### Ver uma câmera

```bash
# Câmera 1
python3 notebook_setup/stream_viewer.py --camera 1

# Câmera 2
python3 notebook_setup/stream_viewer.py --camera 2

# Tópico customizado
python3 notebook_setup/stream_viewer.py --topic /camera/cam3/compressed
```

Teclas: `s` salva frame, `r` alterna RAW/RGB, `q` sai.

### Ver duas câmeras lado a lado

```bash
python3 notebook_setup/dual_viewer.py \
    --title "cam1 | cam2" \
    /camera/cam1/compressed \
    /camera/cam2/compressed
```

### Variáveis de ambiente necessárias

```bash
export FASTRTPS_DEFAULT_PROFILES_FILE=~/.collab_fastdds.xml
export ROS_DOMAIN_ID=0
export RMW_IMPLEMENTATION=rmw_fastrtps_cpp
source /opt/ros/humble/setup.bash
```

---

## Notas técnicas

**Por que o relay sobe antes do pipeline?**
FastDDS atribui `participantId` sequencialmente. O subscriber remoto (notebook) só descobre peers com ID baixo (porta 7411). O relay precisa do ID 0 para ser visível via VPN.

**Por que RELIABLE nos tópicos comprimidos?**
JPEG de 100 KB vira ~70 fragmentos UDP. Com BEST_EFFORT, qualquer fragmento perdido derruba o frame inteiro. RELIABLE retransmite fragmentos perdidos, eliminando drops.

**FPS vs resolução vs adaptadores:**
| Adaptador | Res. máxima a 10 FPS | Res. máxima a 33 FPS |
|---|---|---|
| 100 Mbps (USB 2.0) | 1024×768 | não suportado |
| 1 Gbps (USB 3.0 / nativo) | 2048×1536 | 2048×1536 |

**Reconexão VPN:**
Automática. O FastDDS redescobre o peer via `initialPeersList` em ~15 s após VPN reconectar.
