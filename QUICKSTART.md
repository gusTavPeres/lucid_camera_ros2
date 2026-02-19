# Quick Start - Lucid Camera ROS2

Guia rápido para começar a usar a câmera Lucid Vision com ROS2 Humble.

## 🚀 Setup Inicial (5 minutos)

### 1. Pré-requisitos

- Ubuntu 22.04/24.04
- Docker e Docker Compose instalados
- Câmera Lucid Triton TRI032S conectada via Ethernet
- **Lente C-mount** montada na câmera (não vem incluída)

### 2. Baixar SDK da Lucid

Baixe do site oficial: https://thinklucid.com/downloads-hub/

Coloque os arquivos em:
```
resources/ArenaSDK/linux64/ArenaSDK_Linux_x64.tar.gz
resources/arena_api/arena_api-X.X.X-py3-none-any.whl
```

### 3. Configurar Rede

```bash
# Configure a interface Ethernet conectada à câmera
sudo ./scripts/setup_network.sh enp45s0  # substitua pela sua interface
```

### 4. Build Docker

```bash
xhost +local:docker
docker compose build
```

### 5. Iniciar Container

```bash
docker compose up -d camera_dev
docker compose exec camera_dev bash
```

---

## 📸 Usar a Câmera

### Detectar Câmera

```bash
python3 /arena_camera_ros2/scripts/list_cameras.py
```

Anote o **serial** da câmera.

### Iniciar Publicação de Imagens

```bash
source /opt/ros/humble/setup.bash
source /arena_camera_ros2/ros2_ws/install/setup.bash

ros2 run arena_camera_node start --ros-args \
  -p serial:=SEU_SERIAL_AQUI \
  -p topic:=/camera/image_raw \
  -p pixelformat:=bayer_rggb8
```

### Visualizar em Outro Terminal

```bash
docker compose exec camera_dev bash
source /opt/ros/humble/setup.bash && source /arena_camera_ros2/ros2_ws/install/setup.bash
python3 /arena_camera_ros2/scripts/live_viewer_ros_raw.py
# Pressione 'q' para sair, 'r' para alternar RAW/RGB, 's' para salvar frame
```

---

## 🎬 Gravar Vídeo

**Opção A — Gravar direto em MP4** (recomendado):
```bash
docker compose exec camera_dev bash
source /opt/ros/humble/setup.bash && source /arena_camera_ros2/ros2_ws/install/setup.bash
cd /arena_camera_ros2/bags
python3 /arena_camera_ros2/scripts/record_video.py --output camera.mp4
# Ctrl+C para parar e salvar automaticamente
```

**Opção B — Gravar bag ROS2**:
```bash
cd /arena_camera_ros2/bags
ros2 bag record /camera/image_raw -o minha_gravacao
# Ctrl+C para parar
```

**Converter bag para MP4** (único comando):
```bash
python3 /arena_camera_ros2/scripts/convert_bag.py ./minha_gravacao --output video.mp4
```

---

## 🔧 Troubleshooting

### Câmera não detectada
1. Verifique cabo Ethernet conectado
2. Rode `ip link show` e confirme interface UP
3. Verifique IP: `ip addr show enp45s0` (deve ter 169.254.x.x)

### Imagem cinza/sem foco
- **Você instalou a lente?** A câmera não vem com lente
- Use `python3 /arena_camera_ros2/scripts/focus_helper.py` para ajustar foco

### Erro "camera já em uso"
- Apenas um processo pode acessar a câmera por vez
- Pare o camera_node antes de rodar scripts que acessam a câmera diretamente

---

## 📚 Guias Completos

- **[README.md](README.md)** - Documentação completa
- **[STREAMING.md](STREAMING.md)** - Transmissão multi-PC
- **[notebook_setup/](notebook_setup/)** - Setup para Fedora Kinoite (alternativo)

---

## ⚡ Comandos Úteis

```bash
# Listar tópicos
ros2 topic list

# Ver FPS
ros2 topic hz /camera/image_raw

# Info do tópico
ros2 topic info /camera/image_raw --verbose

# Parar container
docker compose down
```
