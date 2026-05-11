# Sensor Stack — Lucid camera + Ouster LiDAR in one container

Single ROS 2 Humble container that runs both drivers. Remote visualization
uses raw FastDDS over Netbird (no bridge).

## 0. Prereqs

On the **sensor host**:
- Docker + docker compose plugin
- Netbird installed and connected (IP in 100.64.0.0/10, typically 100.107.x.x)
- The lucid repo and `ouster-ros-humble-devel/` side-by-side in the same
  parent directory (the Dockerfile COPYs from both)

On the **remote viewer PC** (where you want to see topics):
- ROS 2 Humble + FastDDS
- Netbird, peered with the sensor host
- The same FastDDS profile pattern (see "Remote viewer setup" below)

## 1. One-line start

```bash
./scripts/start.sh
```

That does: `host_setup.sh` (sudo) -> `docker compose up -d sensor_stack` ->
prints first 30 log lines. Stop with `./scripts/stop.sh [--teardown-host]`.

## 2. Environment variables

All settable on the command line, via `.env`, or via shell export before
`docker compose up`.

| Var | Default | Meaning |
|---|---|---|
| `ROS_DOMAIN_ID` | `0` | ROS 2 domain ID — fixed at 0 across the project |
| `HOST_NETBIRD_IP` | autodetect (100.64.0.0/10) | This host's Netbird IPv4 |
| `REMOTE_PEER_IPS` | `100.107.107.160` | Comma-separated remote DDS peers |
| `NETBIRD_IFACE` | autodetect | Optional iface name override |
| `SENSOR_IFACE` | autodetect (169.254.x.x) | Lucid GigE iface |
| `OUSTER_IFACE` | autodetect (192.168.1.x) | Ouster iface |
| `OUSTER_HOST_IP` | `192.168.1.1/24` | Host IP alias on the lidar subnet |
| `LIDAR_HOSTNAME` | `192.168.1.200` | Ouster sensor IP |
| `LIDAR_UDP_DEST` | empty (auto) | Override only on multi-homed hosts |
| `LIDAR_MODE` | `1024x10` | resolution × rate |
| `LIDAR_TIMESTAMP_MODE` | `TIME_FROM_ROS_TIME` | safe default for rosbag |
| `LIDAR_UDP_PROFILE` | `RNG19_RFL8_SIG16_NIR16` | full single return |
| `ENABLE_CAMERA` | `true` | Toggle camera stack |
| `ENABLE_LIDAR` | `true` | Toggle lidar stack |
| `CAMERA_CONFIG` | `…/config/cameras.yaml` | Multi-camera config |
| `RELAY_QUALITY` / `RELAY_WORKERS` | `80` / `4` | JPEG relay tuning |

## 3. Remote viewer setup (over Netbird)

On the remote PC:

1. **Set the WireGuard MTU to 1420** (Netbird default). The DDS profile here
   already caps each UDP datagram below 1420 bytes; both ends must agree or
   you get silent packet loss.
2. Create an analogous FastDDS profile on the remote PC with **the remote's
   Netbird IP** in `<interfaceWhiteList>` + `<defaultUnicastLocatorList>`,
   and the sensor host's Netbird IP in `<initialPeersList>`.
3. Export `FASTRTPS_DEFAULT_PROFILES_FILE=/path/to/remote_profile.xml` +
   `RMW_IMPLEMENTATION=rmw_fastrtps_cpp` + `ROS_DOMAIN_ID=0`.
4. `ros2 topic list` should show `/camera/cam{1,2}/image_raw` and
   `/ouster/*` within ~3 seconds.
5. View: `rqt_image_view` for the camera; `rviz2` with the
   `ouster_ros/config/viz.rviz` config for the lidar pointcloud.

Currently no bridge — pure DDS. If point clouds are sluggish over Netbird,
add `foxglove_bridge` later (placeholder arg `enable_remote_bridge` already
in the launch file).

## 4. Troubleshooting (top 7)

1. **`Build failed` on first `up`.** Drop into the container with
   `docker compose exec sensor_stack bash` and run
   `cd /arena_camera_ros2/ros2_ws && colcon build --symlink-install`. The
   real error is in the log immediately above this line.

2. **`ouster_ros not found` in the launch.** Means the staging step didn't
   run. Inside the container: `ls src/` — should show `arena_camera_node`,
   `ouster_ros`, `ouster_sensor_msgs`. If missing, delete `install/` and
   `build/` and restart the container.

3. **`No Netbird IP found` warning at entrypoint.** Run `ip -4 addr` on the
   host — confirm Netbird is up and has a 100.x.x.x address. If your range
   is non-standard, export `HOST_NETBIRD_IP=…` in `.env`.

4. **Remote `ros2 topic list` shows nothing.** Verify reachability with
   `nc -uvz <sensor-host-netbird-ip> 7400` (FastDDS discovery port). If
   that fails, it's Netbird-level — check both peers are connected and
   not blocked by firewall rules.

5. **Camera publishes but remote drops frames.** Loopback is unlimited;
   Netbird at 1420 MTU caps you. Lower JPEG quality (`RELAY_QUALITY=60`)
   or stay on the lossy compressed topic on the remote side.

6. **LiDAR driver enters `finalized` state.** Means it couldn't reach the
   sensor in time. Test from inside the container:
   `ping $LIDAR_HOSTNAME` then `curl http://$LIDAR_HOSTNAME/api/v1/system/firmware`.
   If ping fails, run `./scripts/host_setup.sh` again — the IP alias may
   have been wiped by NetworkManager.

7. **`AccessException` from the camera node.** GigE Vision heartbeat is
   still held by a prior process. `start_sensor_stack.sh` already retries
   with a 15 s wait. If it keeps failing, run `docker compose down` and
   wait ~30 s before bringing back up.
