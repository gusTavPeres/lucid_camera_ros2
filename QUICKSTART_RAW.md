# Guia Rápido - Modo RAW (BayerRG8)

Este guia mostra como usar a câmera Lucid Vision Triton TRI032S em modo RAW (BayerRG8), capturando dados direto do sensor sem processamento de cor.

## Setup Inicial (uma vez só)

```bash
cd ~/lucid_camera_ros2

# 1. Configurar rede (substitua enp45s0 pela sua interface)
sudo ./scripts/setup_network.sh enp45s0

# 2. Liberar janelas gráficas
xhost +local:docker

# 3. Subir container
docker compose up -d camera_dev
```

## Workflow Diário

### 1. Listar câmeras conectadas
```bash
docker compose exec camera_dev python3 /arena_camera_ros2/scripts/list_cameras.py
```

Você verá algo como:
```
Câmera 1:
  Modelo:  TRI032S-C
  Serial:  243901923
  IP:      169.254.10.197
```

### 2. Iniciar câmera em modo RAW

**Terminal 1** (este vai ficar rodando):
```bash
docker compose exec camera_dev bash /arena_camera_ros2/scripts/start_camera_raw.sh 243901923 /camera/image_raw
```

Você verá logs como:
```
[INFO] PixelFormat set to BayerRG8
[INFO] image 1 published to /camera/image_raw
```

### 3. Visualizar imagens

Escolha UMA das opções abaixo:

**Opção A: Viewer ROS2 (recomendado)**
```bash
# Terminal 2
docker compose exec camera_dev bash -c "source /opt/ros/humble/setup.bash && python3 /arena_camera_ros2/scripts/live_viewer_ros_raw.py"
```
- Pressione **'r'** para alternar entre RAW (cinza) e RGB (colorido)
- Pressione **'s'** para salvar frame
- Pressione **'q'** para sair

**Opção B: Viewer direto da API Arena (mais rápido)**
```bash
# Terminal 2
docker compose exec camera_dev python3 /arena_camera_ros2/scripts/live_viewer_raw.py
```
- Pressione **'r'** para alternar entre RAW e RGB
- Pressione **'s'** para salvar (salva RAW.png e RGB.png)
- Pressione **'q'** para sair

**Opção C: rqt_image_view (mais simples)**
```bash
# Terminal 2
docker compose exec camera_dev bash -c "source /opt/ros/humble/setup.bash && ros2 run rqt_image_view rqt_image_view /camera/image_raw"
```

### 4. Verificar tópicos ROS2

```bash
# Listar tópicos
docker compose exec camera_dev bash -c "source /opt/ros/humble/setup.bash && ros2 topic list"

# Ver FPS da câmera
docker compose exec camera_dev bash -c "source /opt/ros/humble/setup.bash && ros2 topic hz /camera/image_raw"

# Ver detalhes do tópico
docker compose exec camera_dev bash -c "source /opt/ros/humble/setup.bash && ros2 topic info /camera/image_raw --verbose"
```

### 5. Gravar um bag

```bash
docker compose exec camera_dev bash -c "
  source /opt/ros/humble/setup.bash && \
  cd /arena_camera_ros2/bags && \
  ros2 bag record /camera/image_raw -s mcap
"
```

Pressione **Ctrl+C** para parar. O bag fica salvo em `~/lucid_camera_ros2/bags/`

## Formato de Dados

### BayerRG8 (RAW)
- **Encoding**: `bayer_rggb8`
- **Bits por pixel**: 8
- **Canais**: 1 (monocromático com padrão Bayer)
- **Resolução**: 2048x1536
- **Vantagens**:
  - Tamanho menor (~3 MB/frame vs ~9 MB em RGB8)
  - Maior FPS possível
  - Dados originais do sensor sem perda
  - Permite processamento customizado

### Conversão para RGB

**Python (OpenCV):**
```python
import cv2
raw = cv2.imread('image_raw.png', cv2.IMREAD_GRAYSCALE)
rgb = cv2.cvtColor(raw, cv2.COLOR_BayerRG2RGB)
cv2.imwrite('image_rgb.png', rgb)
```

**ROS2 (em tempo real):**
```bash
ros2 run image_proc debayer --ros-args \
    -r image_raw:=/camera/image_raw \
    -r image_color:=/camera/image_color
```

Isso cria um novo tópico `/camera/image_color` com imagem RGB.

## Comparação RGB8 vs BayerRG8

| Característica | RGB8 | BayerRG8 |
|---------------|------|----------|
| Tamanho/frame | ~9 MB | ~3 MB |
| FPS máximo | ~35 FPS | ~35 FPS* |
| Processamento | Já convertido | RAW do sensor |
| Bandwidth | Alta | Média |
| Uso | Visualização direta | Processamento posterior |

\* FPS depende da configuração de rede e exposure

## Troubleshooting

### Imagem aparece cinza/verde
- Isso é esperado se estiver vendo o RAW diretamente
- Use a conversão Bayer→RGB ou pressione 'r' no viewer

### "No image received"
```bash
# Verificar se o tópico existe
docker compose exec camera_dev bash -c "source /opt/ros/humble/setup.bash && ros2 topic list"

# Verificar se está publicando
docker compose exec camera_dev bash -c "source /opt/ros/humble/setup.bash && ros2 topic echo /camera/image_raw --once"
```

### Câmera não detectada
```bash
# Verificar rede
ping 169.254.10.197

# Reconfigurar rede
sudo ./scripts/setup_network.sh enp45s0

# Reiniciar container
docker compose restart camera_dev
```

## Próximos Passos

- Para usar múltiplas câmeras, veja o [README.md](README.md) seção "Usando varias cameras"
- Para gravar bags sincronizados, veja `launch/multi_camera.launch.py`
- Para processamento em tempo real, explore o pacote `image_proc` do ROS2
