#!/usr/bin/env python3
import os
import re

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import yaml


def _camera_defaults():
    return {
        "width": int(os.environ.get("CAMERA_WIDTH", "0")),
        "height": int(os.environ.get("CAMERA_HEIGHT", "0")),
        "pixelformat": os.environ.get("CAMERA_PIXELFORMAT", "rgb8"),
        "gain": float(os.environ.get("CAMERA_GAIN", "0.0")),
        "exposure_time": float(os.environ.get("CAMERA_EXPOSURE_TIME", "10000.0")),
        "frame_rate": float(os.environ.get("CAMERA_FRAME_RATE", "0.0")),
        "qos_reliability": os.environ.get("CAMERA_QOS_RELIABILITY", "reliable"),
        "trigger_mode": os.environ.get("CAMERA_TRIGGER_MODE", "false").lower() == "true",
    }


def _csv_env(name):
    return [s.strip() for s in os.environ.get(name, "").split(",") if s.strip()]


def _bool_env(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _sanitize_ros_name(value, fallback):
    name = re.sub(r"[^A-Za-z0-9_]+", "_", str(value).strip()).strip("_")
    if not name:
        name = fallback
    if not re.match(r"^[A-Za-z_]", name):
        name = f"camera_{name}"
    return name


def _discover_camera_serials():
    try:
        from arena_api.system import system
    except Exception as exc:
        print(f"[multi_camera] Arena API indisponível para autodetect: {exc}")
        return []

    try:
        system.DEVICE_INFOS_TIMEOUT_MILLISEC = int(
            os.environ.get("CAMERA_DISCOVERY_TIMEOUT_MS", "5000")
        )
    except ValueError:
        system.DEVICE_INFOS_TIMEOUT_MILLISEC = 5000

    try:
        device_infos = system.device_infos
    except Exception as exc:
        print(f"[multi_camera] Autodetect de câmeras falhou: {exc}")
        return []

    serials = []
    for info in device_infos:
        serial = str(info.get("serial", "")).strip()
        if serial:
            serials.append(serial)
    print(f"[multi_camera] Autodetect serials: {','.join(serials) or '<none>'}")
    return serials


def _serial_as_int(serial, camera_name):
    try:
        return int(serial)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"Invalid serial for {camera_name}: {serial!r}") from exc


def _start_delay(index):
    try:
        delay = float(os.environ.get("CAMERA_START_DELAY_SEC", "3.0"))
    except ValueError:
        delay = 3.0
    return max(0.0, delay) * (index - 1)


def _make_node(cam):
    d = _camera_defaults()
    params = {
        "topic": cam.get("topic", "/arena_camera_node/images"),
        "width": cam.get("width", d["width"]),
        "height": cam.get("height", d["height"]),
        "pixelformat": cam.get("pixelformat", d["pixelformat"]),
        "gain": cam.get("gain", d["gain"]),
        "exposure_time": cam.get("exposure_time", d["exposure_time"]),
        "frame_rate": cam.get("frame_rate", d["frame_rate"]),
        "qos_reliability": cam.get("qos_reliability", d["qos_reliability"]),
        "trigger_mode": cam.get("trigger_mode", d["trigger_mode"]),
    }
    camera_name = cam.get("name", f"camera_{cam.get('serial', 'unknown')}")
    serial = str(cam.get("serial", "")).strip()
    if serial:
        params["serial"] = _serial_as_int(serial, camera_name)

    return Node(
        package="arena_camera_node",
        executable="start",
        name=camera_name,
        parameters=[params],
        output="screen",
        respawn=True,
        respawn_delay=5.0,
    )


def _camera_count(serials, names, topics):
    try:
        requested = int(os.environ.get("CAMERA_COUNT", "0") or "0")
    except ValueError:
        requested = 0
    return max(requested, len(serials), len(names), len(topics))


def _cameras_from_env():
    serials = _csv_env("CAMERA_SERIALS")
    names = _csv_env("CAMERA_NAMES")
    topics = _csv_env("CAMERA_TOPICS")
    count = _camera_count(serials, names, topics)
    require_serials = _bool_env("CAMERA_REQUIRE_SERIALS", False)

    if count == 0:
        if require_serials:
            raise RuntimeError("CAMERA_SERIALS is empty and CAMERA_REQUIRE_SERIALS=true")
        return []

    if len(serials) < count:
        if require_serials:
            raise RuntimeError(
                f"CAMERA_SERIALS has {len(serials)} serial(s), but {count} camera(s) are configured"
            )
        detected = [s for s in _discover_camera_serials() if s not in serials]
        while len(serials) < count and detected:
            serials.append(detected.pop(0))

    if len(serials) < count:
        raise RuntimeError(
            f"Only {len(serials)} serial(s) available for {count} configured camera(s)"
        )

    cameras = []
    for i in range(1, count + 1):
        name = _sanitize_ros_name(
            names[i - 1] if i <= len(names) else f"camera_{i}",
            f"camera_{i}",
        )
        topic = topics[i - 1] if i <= len(topics) else f"/camera/{name}/image_raw"
        cameras.append(
            {
                "name": name,
                "serial": serials[i - 1],
                "topic": topic,
            }
        )
    return cameras


def generate_camera_nodes(context):
    config_file = LaunchConfiguration("config_file").perform(context)
    if not config_file:
        config_file = os.environ.get("CAMERA_CONFIG_FILE", "")

    if config_file and os.path.exists(config_file):
        with open(config_file, "r") as f:
            config = yaml.safe_load(f) or {}
        cameras = config.get("cameras", [])
    else:
        cameras = _cameras_from_env()

    if not cameras:
        cameras = [{"name": "arena_camera_node", "topic": "/arena_camera_node/images"}]

    nodes = []
    for index, cam in enumerate(cameras, start=1):
        node = _make_node(cam)
        delay = _start_delay(index)
        nodes.append(node if delay == 0.0 else TimerAction(period=delay, actions=[node]))
    return nodes


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "config_file",
                default_value="",
                description="YAML de câmeras (opcional; tem prioridade sobre CAMERA_SERIALS)",
            ),
            OpaqueFunction(function=generate_camera_nodes),
        ]
    )
