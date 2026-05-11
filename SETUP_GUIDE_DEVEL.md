# Setup Guide — Devel Branch (test_devel)

Pipeline com ImageResizerNode: câmeras → resize → compressed transport via image_transport.

---

## Diferenças em relação à main

| | Main | Devel |
|---|---|---|
| Launch | `multi_camera.launch.py` | `camera_pipeline.launch.py` |
| Compressão | `multi_compress_relay.py` (externo) | `image_transport` (embutido no resizer) |
| Pixel format | `bayer_rggb8` (Bayer) | `rgb8` (demosaicado na câmera) |
| Resize | no relay (`--width`/`--height`) | `ImageResizerNode` no pipeline |
| Tópicos raw | `/camera/camN/image_raw` | `/camera_N/image_raw` |
| Tópicos compressed | `/camera/camN/compressed` | `/camera_N/image_small/compressed` |

---

## PC — Dentro do container

### 1. Arquivo de câmeras

O arquivo de configuração do devel fica em `/devel_ws/cameras_devel.yaml` (dentro do container).

Exemplo para 2 câmeras:

```yaml
cameras:
  - name: camera_1
    serial: "243901923"
    topic: /camera_1/image_raw
    pixelformat: rgb8
    exposure_auto: true
    frame_rate: 3.0
    qos_reliability: best_effort
    resizer:
      enabled: true
      name: camera_1_resizer
      output_topic: /camera_1/image_small
      output_width: 640
      output_height: 480
      interpolation: area
      qos_reliability: best_effort
      compression:
        format: jpeg
        jpeg_quality: 50

  - name: camera_2
    serial: "243901918"
    topic: /camera_2/image_raw
    pixelformat: rgb8
    exposure_auto: true
    frame_rate: 3.0
    qos_reliability: best_effort
    resizer:
      enabled: true
      name: camera_2_resizer
      output_topic: /camera_2/image_small
      output_width: 640
      output_height: 480
      interpolation: area
      qos_reliability: best_effort
      compression:
        format: jpeg
        jpeg_quality: 50
```

### 2. Iniciar o relay (primeiro — participantId baixo)

```bash
# Dentro do container
source /opt/ros/humble/setup.bash
source /devel_ws/install/setup.bash

python3 /arena_camera_ros2/scripts/multi_compress_relay.py \
    --config /devel_ws/cameras_devel.yaml \
    --quality 70 --workers 4 &
```

> O `--config` lê os `topic` do YAML e deriva os pares: `/camera_N/image_small` → `/camera_N/image_small/compressed`.

### 3. Iniciar o pipeline

```bash
ros2 launch /devel_ws/install/arena_camera_node/share/arena_camera_node/launch/camera_pipeline.launch.py \
    config_file:=/devel_ws/cameras_devel.yaml
```

---

## Notebook — Visualização via VPN

### Ver uma câmera

```bash
python3 notebook_setup/stream_viewer.py \
    --topic /camera_1/image_small/compressed
```

### Ver duas câmeras lado a lado

```bash
python3 notebook_setup/dual_viewer.py \
    --title "DEVEL — cam1 | cam2" \
    /camera_1/image_small/compressed \
    /camera_2/image_small/compressed
```

---

## Build do workspace devel

```bash
# Dentro do container, em /devel_ws
source /opt/ros/humble/setup.bash
colcon build --packages-select arena_camera_node --cmake-args -DCMAKE_BUILD_TYPE=Release
source install/setup.bash
```

---

## Notas técnicas

**Por que rgb8 no devel?**
O `ImageResizerNode` recebe `rgb8` e faz resize via OpenCV. O resize de imagem Bayer (bayer_rggb8) exigiria demosaicing antes, que o resizer não implementa.

**Por que frame_rate menor (3 FPS)?**
No devel, o pixel format é `rgb8` (3 bytes/pixel vs 1 byte/pixel Bayer). Um frame 2048×1536 rgb8 = 9 MB. Com adaptadores 100 Mbps, o máximo é ~1 FPS. Com GigE nativo, até 11 FPS.
