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

# 2. Configure GigE network interface (run on host, not in container)
sudo ./scripts/setup_network.sh <gige-interface>   # e.g., enp3s0

# 3. Set IP on the GigE interface (link-local works out of the box)
sudo ip addr add 169.254.1.1/16 dev <gige-interface>

# 4. Allow graphical windows from inside the container
xhost +local:docker

# 5. Build and start
docker compose build
docker compose up -d camera_dev
docker compose exec camera_dev bash

# Inside the container:
python3 /arena_camera_ros2/scripts/list_cameras.py   # verify camera is found
ros2 run arena_camera_node start --ros-args \
    -p serial:=<YOUR_SERIAL> \
    -p topic:=/camera/image_raw \
    -p pixelformat:=bayer_rggb8
```

---

## Directory Structure

```
lucid_camera_ros2/
├── Dockerfile                      # Container image (ROS2 Humble + ArenaSDK)
├── docker-compose.yml              # Service definitions
├── config/
│   ├── setup_fastdds.sh            # Generates FastDDS profiles for your network
│   ├── fastdds_publisher.xml.example
│   ├── fastdds_subscriber.xml.example
│   └── cameras_example.yaml        # Multi-camera config template
├── scripts/
│   ├── setup_network.sh            # GigE interface tuning (MTU, buffers, ring)
│   ├── list_cameras.py             # Detect connected cameras (model, serial, IP)
│   ├── start_camera.sh             # Camera node launcher with parameter support
│   ├── compress_bayer_stream.py    # JPEG compression relay (for streaming)
│   ├── receive_frames.py           # Headless frame receiver (no display needed)
│   ├── focus_helper.py             # Live focus score for lens adjustment
│   ├── live_viewer_ros_raw.py      # OpenCV viewer via ROS2 topic
│   ├── record_video.py             # Direct MP4 recording from camera topic
│   ├── bag_to_video.py             # Convert ROS2 bag to MP4
│   └── convert_bag.py              # One-command bag-to-video wrapper
├── notebook_setup/                 # Publisher-side tools (camera machine)
│   ├── setup_toolbox.sh            # ROS2 Humble container setup (toolbox/distrobox)
│   ├── compress_stream.sh          # Start compression relay for streaming
│   ├── throttle_camera.sh          # FPS limiter (simpler alternative to compression)
│   ├── setup_firewall_receiver.sh  # Accept ROS2 UDP traffic from LAN/VPN subnet
│   └── stream_viewer.py            # OpenCV viewer for remote viewing
├── launch/
│   ├── multi_camera.launch.py      # Launch multiple cameras from YAML config
│   └── camera_streaming.launch.py  # Streaming-optimized launch
└── ros2_ws/src/
    └── arena_camera_node/          # ROS2 package (C++ node wrapping ArenaSDK)
```

---

## Camera Node Parameters

| Parameter         | Description                                       | Default                 |
|-------------------|---------------------------------------------------|-------------------------|
| `serial`          | Camera serial number (integer)                    | first available         |
| `topic`           | ROS2 topic name                                   | `/arena_camera_node/images` |
| `pixelformat`     | `bayer_rggb8`, `rgb8`, `bgr8`, `mono8`, etc.     | `rgb8`                  |
| `width`           | Image width in pixels                             | camera maximum          |
| `height`          | Image height in pixels                            | camera maximum          |
| `gain`            | Sensor gain in dB                                 | `0.0`                   |
| `exposure_time`   | Exposure in microseconds                          | camera default          |
| `frame_rate`      | Target acquisition frame rate in FPS              | camera default          |
| `trigger_mode`    | `true` = triggered, `false` = continuous          | `false`                 |
| `qos_reliability` | `reliable` or `best_effort`                       | `reliable`              |

**Note:** All parameters are startup-only and cannot be changed at runtime without restarting the node.

**`frame_rate` and `exposure_time` interaction:** The actual frame rate is limited by whichever is lower: the `frame_rate` setting or `1 / exposure_time`. For maximum FPS, set `exposure_time` short enough to allow it. Example for 33 FPS: `frame_rate:=33.0 exposure_time:=25000` (25 ms exposure allows up to 40 FPS).

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
# This creates fastdds_publisher.xml with 127.0.0.1 (local) + <streaming-ip> (remote)

# Start camera node at full FPS
./scripts/start_camera.sh <serial> /camera/image_raw bayer_rggb8 "" "" 20.0 25000 33.0
#                          serial   topic             pixelformat  W  H  gain  exposure fps

# Start compression relay (in another terminal or background)
bash ./notebook_setup/compress_stream.sh /camera/image_raw
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
    --topic /camera/image_raw --compressed
```

### Bandwidth comparison

| Method               | Resolution  | Rate    | Bandwidth     | Notes                          |
|----------------------|-------------|---------|---------------|--------------------------------|
| RAW throttled        | 1024×768    | 15 FPS  | ~12 Mbps      | Low resolution only            |
| JPEG compressed q=80 | 2048×1536   | 33 FPS  | ~35-45 Mbps   | Full res at full rate (WiFi OK)|
| RAW full             | 2048×1536   | 33 FPS  | ~825 Mbps     | Requires 1 GbE link            |

JPEG compression is the recommended approach for streaming: it delivers full resolution at full frame rate within WiFi bandwidth. The compression relay (`compress_bayer_stream.py`) uses a multi-threaded encoder pool for throughput.

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

Scale to multiple cameras using a YAML configuration:

```bash
cp config/cameras_example.yaml config/cameras.yaml
# Edit cameras.yaml with your camera serials and topics

ros2 launch /arena_camera_ros2/launch/multi_camera.launch.py \
    config_file:=/arena_camera_ros2/config/cameras.yaml
```

For production deployments with many cameras:
- Use a **gigabit switch** with Jumbo Frame support between cameras and the host
- Configure **static IPs** on each camera
- Run `setup_network.sh` on each GigE interface

---

## Recording

**Direct MP4** (recommended):
```bash
python3 /arena_camera_ros2/scripts/record_video.py --output camera.mp4
# Ctrl+C to stop and finalize
```

**ROS2 bag** (lossless, for post-processing):
```bash
cd /arena_camera_ros2/bags
ros2 bag record /camera/image_raw -s mcap
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
7. **Added**: JPEG compression relay for bandwidth-efficient streaming, with multi-threaded encoder (`--workers N`) for full-rate throughput
8. **Added**: multi-camera launch, YAML config, focus helper, video recording/conversion
9. **FastDDS publisher profile**: now advertises both loopback (`127.0.0.1`) and the streaming interface IP, enabling local co-processes to communicate at full speed while remote subscribers use the network interface

---

## License

MIT — based on the official Lucid Vision Labs driver.
