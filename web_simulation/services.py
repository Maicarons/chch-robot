"""
Lazy service accessors and camera discovery.

The long-lived component instances (recognizer, AI engine, robot controller,
and the STM32 TCP client) are owned by the app module so they survive across
requests and only one instance of each exists. This module exposes getters that
mutate ``web_simulation.app`` attributes directly, which keeps them patchable
from the test-suite and consistent with the original module-level globals.
"""

import os
import sys
import json
import logging
import subprocess
import threading
import time

import config
from vision.camera import normalize_camera_source, is_network_camera_source

logger = logging.getLogger(__name__)


def _app_module():
    from web_simulation import app as _app

    return _app


def resolve_camera_source(camera_index=None, camera_source=None, camera_url=None):
    _app = _app_module()
    if camera_url:
        return normalize_camera_source(camera_url)

    if camera_source:
        if camera_source == "network":
            if not _app.current_network_camera_url:
                raise ValueError("尚未配置网络摄像头URL")
            return normalize_camera_source(_app.current_network_camera_url)
        return normalize_camera_source(camera_source)

    if camera_index is not None:
        return normalize_camera_source(camera_index)

    return normalize_camera_source(_app.current_camera_source)


def camera_source_info(source=None):
    _app = _app_module()
    source = normalize_camera_source(
        _app.current_camera_source if source is None else source
    )
    return {
        "source_label": str(source),
        "source_type": "network" if isinstance(source, str) else "local",
        "camera_index": source if isinstance(source, int) else _app.current_camera_index,
        "network_url": str(source) if isinstance(source, str) else _app.current_network_camera_url,
    }


def get_recognizer(camera_index=None, camera_source=None, camera_url=None):
    """Return the shared board recognizer, creating/restarting it if needed."""
    _app = _app_module()

    with _app.recognizer_lock:
        source = resolve_camera_source(
            camera_index=camera_index,
            camera_source=camera_source,
            camera_url=camera_url,
        )
        if isinstance(source, int):
            _app.current_camera_index = source
        _app.current_camera_source = source

        if _app.recognizer is None:
            _app.recognizer = _app.BoardRecognizer(
                camera_index=_app.current_camera_index, camera_source=source
            )
            if not _app.recognizer.start():
                logger.warning("摄像头源 %s 启动失败，请检查摄像头或URL", source)
            else:
                logger.info("摄像头源 %s 已启动", source)
        elif _app.recognizer.camera_manager.camera_source != source:
            logger.info(
                "切换摄像头源: %s -> %s",
                _app.recognizer.camera_manager.source_label,
                source,
            )
            _app.recognizer.camera_manager.set_source(source)
            _app.recognizer.stabilizer.clear()
            _app.recognizer.reset_dynamic_tracking()

            if not _app.recognizer.start():
                logger.warning("摄像头源 %s 启动失败，请检查摄像头或URL", source)
            else:
                logger.info("摄像头源 %s 已启动", source)

        return _app.recognizer


def get_ai_engine():
    """Return the shared AI engine, starting it on first use."""
    _app = _app_module()
    if _app.ai_engine is None:
        from ai import AIEngine

        _app.ai_engine = AIEngine()
        _app.ai_engine.start()
    return _app.ai_engine


def get_robot_controller():
    """Return the shared simulation robot controller."""
    _app = _app_module()
    if _app.robot_controller is None:
        from robot import RobotController

        _app.robot_controller = RobotController(robot_type="simulation")
        _app.robot_controller.initialize()
    return _app.robot_controller


def get_robot_tcp_client():
    """Return the reusable STM32 TCP client for the configured target."""
    _app = _app_module()
    from robot import RobotPersistentClient

    host, port = _app.robot_network_target()
    with _app.robot_tcp_client_lock:
        client = _app.robot_tcp_client
        if client is None or client.host != host or client.port != port:
            if client is not None:
                client.close()
            _app.robot_tcp_client = RobotPersistentClient(
                host, port, timeout=_app.robot_network_timeout()
            )
        return _app.robot_tcp_client


def close_robot_tcp_client():
    _app = _app_module()
    with _app.robot_tcp_client_lock:
        if _app.robot_tcp_client is not None:
            _app.robot_tcp_client.close()
            _app.robot_tcp_client = None


def get_windows_camera_names():
    """Read friendly camera names from Windows device manager."""
    if os.name != "nt":
        return []

    script = r"""
$items = Get-CimInstance Win32_PnPEntity |
  Where-Object {
    $_.PNPClass -in @('Camera','Image','MEDIA') -and
    $_.Name -match 'camera|webcam|video|capture|摄像|相机'
  } |
  Select-Object Name,PNPClass,DeviceID
$items | ConvertTo-Json -Compress
"""

    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=5,
        )

        if result.returncode != 0 or not result.stdout.strip():
            return []

        raw_devices = json.loads(result.stdout)
        if isinstance(raw_devices, dict):
            raw_devices = [raw_devices]

        names = []
        seen = set()
        for device in raw_devices:
            name = (device.get("Name") or "").strip()
            if not name:
                continue

            dedupe_key = (name, device.get("DeviceID"))
            if dedupe_key in seen:
                continue

            seen.add(dedupe_key)
            names.append(name)

        return names
    except Exception as exc:  # pragma: no cover - environment dependent
        logger.warning("读取摄像头设备名失败: %s", exc)
        return []


def list_available_cameras(max_cameras=6):
    """List local camera choices based on OpenCV indexes that can really read frames."""
    _app = _app_module()

    if _app.camera_probe_cache is not None:
        return _app.camera_probe_cache

    camera_names = get_windows_camera_names()
    cameras = []
    preferred_index = int(config.CAMERA_INDEX)

    for index in range(max_cameras):
        probe = probe_camera_index(index)
        if probe:
            name = camera_names[index] if index < len(camera_names) else None
            label = f"{name or '本地摄像头'}（索引 {index}）"
            if index == preferred_index:
                label = f"USB摄像头（索引 {index}）"
            cameras.append(
                {
                    "index": index,
                    "name": name,
                    "label": label,
                    "available": True,
                    "width": probe.get("width", 0),
                    "height": probe.get("height", 0),
                }
            )

    cameras.sort(key=lambda camera: 0 if camera["index"] == preferred_index else 1)

    if not any(camera["index"] == preferred_index for camera in cameras):
        cameras.insert(
            0,
            {
                "index": preferred_index,
                "name": None,
                "label": f"USB摄像头（索引 {preferred_index}）",
                "available": True,
                "width": config.CAMERA_WIDTH,
                "height": config.CAMERA_HEIGHT,
            },
        )

    if not cameras:
        cameras.append(
            {
                "index": preferred_index,
                "name": None,
                "label": f"USB摄像头（索引 {preferred_index}）",
                "available": True,
                "width": 0,
                "height": 0,
            }
        )

    _app.camera_probe_cache = cameras
    return cameras


def probe_camera_index(index):
    """Probe one OpenCV camera index in a child process so bad devices cannot hang Flask."""
    backend_expr = "cv2.CAP_DSHOW" if os.name == "nt" else "cv2.CAP_ANY"
    code = f"""
import cv2, json, time
index = {index}
cap = cv2.VideoCapture(index, {backend_expr})
result = {{'ok': False, 'width': 0, 'height': 0}}
try:
    if cap.isOpened():
        good = 0
        frame_shape = None
        for _ in range(10):
            ret, frame = cap.read()
            if ret and frame is not None:
                good += 1
                frame_shape = frame.shape
            time.sleep(0.02)
        if good >= 3 and frame_shape is not None:
            result = {{'ok': True, 'width': int(frame_shape[1]), 'height': int(frame_shape[0])}}
finally:
    cap.release()
print(json.dumps(result))
"""

    try:
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=4,
        )

        if result.returncode != 0:
            return None

        probe = json.loads(result.stdout.strip().splitlines()[-1])
        return probe if probe.get("ok") else None
    except Exception as exc:  # pragma: no cover - environment dependent
        logger.info("摄像头索引 %d 探测失败或超时: %s", index, exc)
        return None
