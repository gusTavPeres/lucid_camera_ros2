# Lucid Vision Camera — ROS2 Humble

ROS2 Humble driver for Lucid Vision Triton cameras (GigE Vision), packaged as a Docker container. Supports single and multi-camera setups, JPEG-compressed streaming over LAN or VPN, bag recording, and video export.

Adapted from the [official Lucid Vision ROS2 driver](https://github.com/lucidvisionlabs/arena_camera_ros2) (originally for Eloquent) to work on ROS2 Humble with additional tooling.

---

## Requirements

- **Docker** and **Docker Compose** (v2+)
- **Lucid Vision Triton camera** connected via GigE (Ethernet)
- **ArenaSDK** and **arena_api** — download from [Lucid downloads hub](https://thinklucid.com/downloads-hub/)
  - `ArenaSDK_Linux_x64.tar.gz` → place in `resources/ArenaSDK/linux64/`
  - `arena_api-*.whl` → place in `resources/arena_api/`
- Ubuntu 22.04 or later (host OS)

---

## Quick Start

```bash
git clone <repo-url> && cd lucid_camera_ros2

# 1. Place ArenaSDK and arena_api in resources/ (see Requirements above)

# 2. Configure .env (paths do ArenaSDK, ROS_DOMAIN_ID, discovery server)
# 3. Configure as câmeras (arquivo único: serial, ip/iface, exposição, fps,
#    resize, compressão) — copie o exemplo e edite (local, fora do git):
cp ros2_ws/src/arena_camera_node/config/cameras_example.yaml \
   ros2_ws/src/arena_camera_node/config/cameras.yaml

# 4. Configure GigE network interface (run on host, not in container)
sudo ./scripts/setup_network.sh <gige-interface>   # e.g., enp3s0

# 5. Set IP on the GigE interface (link-local works out of the box)
sudo ip addr add 169.254.1.1/16 dev <gige-interface>

# 6. Allow graphical windows from inside the container
xhost +local:docker

# 7. Build and start
docker compose build
docker compose up -d camera_dev

# The container automatically runs the unified pipeline (cameras + resize + compression)
# from ros2_ws/src/arena_camera_node/config/cameras.yaml

# Optional: run a single camera manually (inside container)
docker compose exec camera_dev bash
python3 /arena_camera_ros2/scripts/list_cameras.py   # verify camera is found
ros2 run arena_camera_node start --ros-args \
    -p serial:=<YOUR_SERIAL> \
    -p topic:=/camera/image_raw \
    -p pixelformat:=rgb8
```

---

## .env Configuration

`docker-compose.yml` now reads all build/runtime variables from `.env`.

Key variables:
- `ARENASDK_ROOT_ON_HOST` and `ARENA_API_ROOT_ON_HOST`: input files used at image build time.
- `FASTRTPS_DEFAULT_PROFILES_FILE`: DDS interface restriction profile used in container runtime.
- Setup por câmera (serial, ip/iface, exposição, resize, compressão): tudo em `ros2_ws/src/arena_camera_node/config/cameras.yaml`. `CAMERA_<NOME>_SERIAL` no `.env` é um override opcional de serial.

---

## Directory Structure

```
lucid_camera_ros2/
├── .env                            # Build/runtime variables used by docker compose
├── Dockerfile                      # Container image (ROS2 Humble + ArenaSDK)
├── docker-compose.yml              # Service definitions
├── config/
│   ├── setup_fastdds.sh            # Generates FastDDS profiles for your network
│   ├── fastdds_publisher.xml.example
│   └── fastdds_subscriber.xml.example
├── scripts/
│   ├── setup_network.sh            # GigE interface tuning (MTU, buffers, ring)
│   ├── list_cameras.py             # Detect connected cameras (model, serial, IP)
│   ├── compress_bayer_stream.py    # JPEG compression relay (for streaming)
│   ├── receive_frames.py           # Headless frame receiver (no display needed)
│   ├── focus_helper.py             # Live focus score for lens adjustment
│   ├── live_viewer_ros_raw.py      # OpenCV viewer via ROS2 topic
│   ├── record_video.py             # Direct MP4 recording from camera topic
│   ├── bag_to_video.py             # Convert ROS2 bag to MP4
│   └── convert_bag.py              # One-command bag-to-video wrapper
├── notebook_setup/                 # Multi-machine streaming tools (publisher + receiver)
│   ├── env.sh                      # Receiver env in one command (discovery server + profile)
│   ├── setup_toolbox.sh            # ROS2 Humble container setup (toolbox/distrobox)
│   ├── compress_stream.sh          # Start compression relay for streaming
│   ├── throttle_camera.sh          # FPS limiter (simpler alternative to compression)
│   ├── setup_firewall_receiver.sh  # Accept ROS2 UDP traffic from LAN/VPN subnet
│   └── stream_viewer.py            # OpenCV viewer for remote viewing
└── ros2_ws/src/
    └── arena_camera_node/          # ROS2 package (C++ node wrapping ArenaSDK)
        ├── launch/
        │   └── camera_pipeline.launch.py   # Unified pipeline (camera + resize + compression)
        └── config/
            └── cameras.yaml       # Single source: serial, ip/iface, capture, resize, compression
```

---

## Camera Node Parameters

| Parameter            | Description                                       | Default                 |
|----------------------|---------------------------------------------------|-------------------------|
| `serial`             | Camera serial number                              | first available         |
| `topic`              | ROS2 topic name (raw image)                        | `/camera/image_raw`     |
| `frame_id`           | TF frame id in message header                     | `camera_optical_frame`  |
| `pixelformat`        | `bayer_rggb8`, `rgb8`, `bgr8`, `mono8`, etc.     | `rgb8`                  |
| `gain`               | Sensor gain in dB                                 | `0.0`                   |
| `exposure_time`      | Exposure in microseconds                          | camera default          |
| `frame_rate`         | Target acquisition frame rate in FPS              | camera default          |
| `trigger_mode`       | `true` = triggered, `false` = continuous          | `false`                 |
| `qos_reliability`    | `reliable` or `best_effort`                       | `reliable`              |

**Message type:** the camera publishes full-sensor raw images as `sensor_msgs/msg/Image`. No cropping or compression is applied at the camera node; resize and JPEG compression (`/topic_new/compressed`) are handled by the pipeline's image_resizer nodes via image_transport.

**Note:** Parameters are startup-only and cannot be changed at runtime without restarting the node.

**`frame_rate` and `exposure_time` interaction:** The actual frame rate is limited by whichever is lower: the `frame_rate` setting or `1 / exposure_time`. For maximum FPS, set `exposure_time` short enough to allow it. Example for 33 FPS: `frame_rate:=33.0 exposure_time:=25000` (25 ms exposure allows up to 40 FPS).

**Pipeline structure:** For each camera, the pipeline can spawn an `image_resizer` node that subscribes to `/camera_X/image_raw`, resizes (no crop), and publishes `/camera_X/image_new` plus `/camera_X/image_new/compressed`. Configure via the `resizer` block in `cameras.yaml` — the same file also holds serial, `ip`/`iface` (host routes via `scripts/setup_routes.sh`) and capture settings, so one file defines the whole camera setup.

**Bayer RAW:** Triton cameras use BayerRG8 natively. Use `pixelformat:=bayer_rggb8` for zero-copy RAW data. When processing in OpenCV:
```python
# ROS2 bayer_rggb8 maps to OpenCV BayerBG (naming is inverted)
bgr = cv2.cvtColor(raw_img, cv2.COLOR_BayerBG2BGR)
```

---

## Multi-machine Streaming

Stream camera images from the camera machine to a remote receiver over LAN or VPN.

### Why FastDDS profiles are needed

When a machine has multiple network interfaces (e.g., GigE camera port + WiFi), FastDDS advertises all interface IPs as data locators. The remote subscriber may then try to send data to the GigE camera IP (169.254.x.x), which is not reachable. FastDDS unicast profiles restrict which IP is advertised.

The publisher profile also includes the loopback address (`127.0.0.1`) so that co-located processes on the same machine (e.g., the compression relay) can communicate at full speed without routing raw camera data over a physical network interface.

### Setup

**On the camera machine** (publisher):
```bash
# Generate FastDDS profile for the streaming interface
./config/setup_fastdds.sh publisher <streaming-interface>
# Example: ./config/setup_fastdds.sh publisher wlan0

# Start the unified pipeline (inside container)
# Edits cameras.yaml to set serials, topics, resize/compression
docker compose up camera_dev

# The pipeline publishes:
# - /camera_X/image_raw (full sensor)
# - /camera_X/image_raw/compressed (camera-side JPEG)
# - /camera_X/image_new (resized, no crop)
# - /camera_X/image_new/compressed (resized + compressed, ideal for streaming)
```

**On the receiver machine** (Docker):
```bash
# Generate FastDDS profile for the receiving interface
./config/setup_fastdds.sh subscriber <receiving-interface>
# Example: ./config/setup_fastdds.sh subscriber eth0

# Allow firewall traffic (if needed)
sudo bash ./notebook_setup/setup_firewall_receiver.sh 192.168.X.0/24

# Start container and viewer
xhost +local:docker
docker compose up -d camera_dev
docker compose exec camera_dev bash

# Inside container:
source /opt/ros/humble/setup.bash
python3 /arena_camera_ros2/notebook_setup/stream_viewer.py \
    --topic /camera_1/image_new --compressed
```

### Bandwidth comparison

| Method               | Resolution  | Rate    | Bandwidth     | Notes                          |
|----------------------|-------------|---------|---------------|--------------------------------|
| RAW throttled        | 1024×768    | 15 FPS  | ~12 Mbps      | Low resolution only            |
| JPEG compressed q=80 | 2048×1536   | 33 FPS  | ~35-45 Mbps   | Full res at full rate (WiFi OK)|
| RAW full             | 2048×1536   | 33 FPS  | ~825 Mbps     | Requires 1 GbE link            |

The unified pipeline resizes images (no crop) and compresses them via standard ROS2 image_transport. Use `/camera_X/image_new/compressed` for bandwidth-efficient streaming over WiFi or VPN.

### Streaming over VPN (WireGuard)

Multicast discovery does not work over WireGuard. Use FastDDS `initialPeersList` to specify the remote peer's VPN IP:

```xml
<!-- Add inside <rtps> in your fastdds_publisher.xml -->
<initialPeersList>
  <locator>
    <udpv4>
      <address>10.X.X.X</address>  <!-- remote peer VPN IP -->
      <port>11811</port>
    </udpv4>
  </locator>
</initialPeersList>
```

---

## Multiple Cameras

The unified pipeline supports multiple cameras via a single YAML file:

```bash
# Seriais: edite .env (CAMERA_1_SERIAL, CAMERA_2_SERIAL) — sem recompilar
# Outras opções: ros2_ws/src/arena_camera_node/config/cameras.yaml
vim ros2_ws/src/arena_camera_node/config/cameras.yaml

# Each camera entry can include a resizer block:
#   resizer:
#     enabled: true
#     output_topic: /camera_1/image_new
#     output_width: 960
#     output_height: 540
#     compression:
#       jpeg_quality: 35

# Start pipeline (reads cameras.yaml automatically)
docker compose up camera_dev
```

For production deployments with many cameras:
- Use a **gigabit switch** with Jumbo Frame support between cameras and the host
- Configure **static IPs** on each camera
- Run `setup_network.sh` on each GigE interface

---

## Recording

**Direct MP4** (recommended):
```bash
python3 /arena_camera_ros2/scripts/record_video.py --topic /camera_1/image_new/compressed --output camera.mp4
# Ctrl+C to stop and finalize
```

**ROS2 bag** (lossless, for post-processing):
```bash
cd /arena_camera_ros2/bags
ros2 bag record /camera_1/image_raw /camera_1/image_new -s mcap
```

**Convert bag to MP4:**
```bash
python3 /arena_camera_ros2/scripts/convert_bag.py ./my_bag --output video.mp4
```

---

## Troubleshooting

**Camera not detected:**
- Check Ethernet cable and camera power
- Run `sudo ./scripts/setup_network.sh <interface>` on the host
- Verify the host IP is on the same subnet as the camera: `ip addr show`
- Try: `ping <camera-ip>`

**Image is grey or out of focus:**
- Triton cameras ship without a lens — a C-mount lens must be installed separately
- Adjust focus using: `python3 /arena_camera_ros2/scripts/focus_helper.py`

**No graphical window:**
- Run `xhost +local:docker` on the host before starting the container

**Streaming: topic visible but 0 frames received:**
- The most common cause is FastDDS advertising the wrong interface IP
- Run `setup_fastdds.sh` on both machines with the correct interface
- Confirm with `tcpdump -i any udp port 7400` that packets are on the right interface
- Ensure the subscriber FastDDS profile uses the IP where packets physically arrive
  (check with `tcpdump` — it may differ from the default route interface)

**Compile error: `True not declared`:**
- Fixed in this repository (the upstream driver had Python `True` in C++ code)

**OpenCV link error during build:**
- The ArenaSDK ships its own OpenCV. The `Findarena_sdk.cmake` in this repo handles
  this automatically via `LD_LIBRARY_PATH` and explicit lib paths.

---

## Changes from the Official Driver

The upstream [arena_camera_ros2](https://github.com/lucidvisionlabs/arena_camera_ros2) targeted ROS2 Eloquent. Changes in this fork:

1. **Dockerfile** rebuilt for ROS2 Humble
2. **ArenaSDK installation** via `Arena_SDK.conf` (non-interactive)
3. **OpenCV linking** fixed in `Findarena_sdk.cmake`
4. **Bug fix**: `True` → `true` in `ArenaCameraNode.cpp`
5. **Added parameter**: `frame_rate` — sets `AcquisitionFrameRateEnable=true` and `AcquisitionFrameRate` on the camera hardware, enabling precise FPS control up to the camera's maximum (e.g., 33.5 FPS for TRI032S at 2048×1536)
6. **Added**: multi-machine streaming with FastDDS unicast profiles
7. **Added**: unified pipeline — single `camera_pipeline.launch.py` + `cameras.yaml` (cameras + resize + compression per camera)
8. **Added**: `image_resizer` node — subscribe raw, publish resized (no crop) + compressed via standard ROS2 image_transport
9. **Added**: focus helper, video recording/conversion
10. **FastDDS publisher profile**: advertises loopback (`127.0.0.1`) and the streaming interface IP for local and remote subscribers

---

## Twizy AIR-UFG (integração no carro)

Material da integração deste driver no Renault Twizy (6 câmeras GigE +
LiDAR Ouster + Fast DDS Discovery Server):

- `docs/tutorial-viewer.md` — passo a passo genérico para
  rodar o viewer (câmeras e LiDAR) em qualquer máquina via cabo Ethernet.
- `docs/twizy-alteracoes-2026-07-03.md` — registro das alterações feitas
  no PC do carro (rede, systemd, `.env`, launch) e seus motivos.
- `twizy_viewer/` — viewer em Docker (roda em qualquer máquina Linux;
  imagem `twizy_viewer:humble`; ver tutorial).

---

## License

MIT — based on the official Lucid Vision Labs driver.
