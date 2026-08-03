"""Camera, stream, capture, and network-camera endpoints."""

import base64
import threading
import time

import cv2
import numpy as np
from datetime import datetime
from flask import Blueprint, jsonify, request, Response

from web_simulation import app as _app
from web_simulation.services import (
    camera_source_info,
    get_recognizer,
    resolve_camera_source,
)
from vision.camera import normalize_camera_source

bp = Blueprint("camera", __name__)


def camera_request_kwargs(data=None):
    """Extract an optional camera selector from JSON body or query string."""
    data = data or {}
    camera_source = data.get("camera_source") or request.args.get("camera_source")
    camera_url = data.get("camera_url") or request.args.get("camera_url")

    if camera_url:
        return {"camera_url": camera_url}
    if camera_source:
        return {"camera_source": camera_source}
    if "camera_index" in data:
        return {"camera_index": data.get("camera_index")}
    if "camera_index" in request.args:
        return {"camera_index": request.args.get("camera_index")}
    return {}


def create_stream_unavailable_frame(message="Camera stream unavailable"):
    """Create a small JPEG placeholder for stream startup failures."""
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    frame[:] = (245, 245, 245)
    cv2.putText(frame, message, (40, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (60, 60, 60), 2)
    ok, buffer = cv2.imencode(".jpg", frame)
    return buffer.tobytes() if ok else b""


def generate_camera_stream(camera_source, stream_token):
    """Yield MJPEG frames from the selected local or network camera."""
    frame_delay = 1.0 / 30.0
    source_label = str(camera_source)
    while True:
        if stream_token != _app.active_stream_token:
            break

        try:
            with _app.camera_lock:
                if stream_token != _app.active_stream_token:
                    break
                recog = get_recognizer(camera_source=camera_source)
                frame = recog.camera_manager.capture_frame()

            if frame is None:
                placeholder = create_stream_unavailable_frame(f"Camera {source_label} has no frame")
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + placeholder + b"\r\n"
                )
                time.sleep(0.15)
                continue

            ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            if not ok:
                time.sleep(0.02)
                continue

            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
            )
            time.sleep(frame_delay)
        except GeneratorExit:
            break
        except Exception as exc:
            _app.logger.error("视频流读取失败: %s", exc)
            time.sleep(0.5)


@bp.route("/api/network_camera/connect", methods=["POST"])
def connect_network_camera():
    """Register and test a LAN network camera URL."""
    previous_url = None
    previous_source = None
    try:
        data = request.json or {}
        url = (data.get("url") or data.get("camera_url") or "").strip()
        try:
            source = normalize_camera_source(url)
        except ValueError:
            return jsonify(
                {"success": False, "error": "网络摄像头URL必须以 http://、https://、rtsp:// 或 rtmp:// 开头"}
            )
        if not isinstance(source, str):
            return jsonify(
                {"success": False, "error": "网络摄像头URL必须以 http://、https://、rtsp:// 或 rtmp:// 开头"}
            )

        previous_url = _app.current_network_camera_url
        previous_source = _app.current_camera_source
        with _app.camera_lock:
            _app.current_network_camera_url = source
            _app.current_camera_source = source
            recog = get_recognizer(camera_source="network")
            frame = recog.camera_manager.capture_frame()

        if frame is None:
            last_camera_error = getattr(recog.camera_manager, "last_error", "") or "no frame returned"
            _app.current_network_camera_url = previous_url
            _app.current_camera_source = previous_source
            if _app.recognizer is not None:
                _app.recognizer.camera_manager.set_source(previous_source)
            return jsonify(
                {
                    "success": False,
                    "error": "网络摄像头已配置，但未能读取到画面；请检查树莓派URL、同一局域网、防火墙和流格式",
                    "detail": last_camera_error,
                    **camera_source_info(source),
                }
            )

        return jsonify(
            {
                "success": True,
                "message": "网络摄像头连接成功",
                "width": int(frame.shape[1]),
                "height": int(frame.shape[0]),
                **camera_source_info(source),
            }
        )
    except Exception as exc:
        if previous_url is not None:
            _app.current_network_camera_url = previous_url
            _app.current_camera_source = previous_source
        _app.logger.error("连接网络摄像头失败: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": str(exc)})


@bp.route("/api/network_camera/status")
def network_camera_status():
    try:
        is_current_network = isinstance(_app.current_camera_source, str)
        is_opened = (
            _app.recognizer is not None
            and _app.recognizer.camera_manager.is_network_source
            and _app.recognizer.camera_manager.is_opened()
        )
        return jsonify(
            {
                "success": True,
                "configured": bool(_app.current_network_camera_url),
                "active": is_current_network,
                "camera_opened": is_opened,
                **camera_source_info(),
            }
        )
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)})


@bp.route("/api/network_camera/disconnect", methods=["POST"])
def disconnect_network_camera():
    try:
        with _app.camera_lock:
            if _app.recognizer is not None and _app.recognizer.camera_manager.is_network_source:
                _app.recognizer.camera_manager.stop()
            _app.current_camera_source = _app.current_camera_index

        return jsonify(
            {
                "success": True,
                "message": "已切回本地摄像头",
                **camera_source_info(_app.current_camera_index),
            }
        )
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)})


@bp.route("/api/camera/stream")
def camera_stream():
    """Local or network camera live MJPEG stream."""
    camera_source = resolve_camera_source(**camera_request_kwargs())
    _app.active_stream_token += 1
    stream_token = _app.active_stream_token

    try:
        with _app.camera_lock:
            recog = get_recognizer(camera_source=camera_source)
            camera_opened = recog.camera_manager.is_opened()
            if not camera_opened:
                recog.camera_manager.start()
                camera_opened = True

        if not camera_opened:
            raise RuntimeError(f"摄像头源 {camera_source} 无法打开")
    except Exception as exc:
        _app.logger.error("启动视频流失败: %s", exc)
        placeholder = create_stream_unavailable_frame()

        def unavailable_stream():
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + placeholder + b"\r\n"
            )

        return Response(unavailable_stream(), mimetype="multipart/x-mixed-replace; boundary=frame")

    return Response(
        generate_camera_stream(camera_source, stream_token),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )


@bp.route("/api/camera/frame")
def camera_frame():
    """Return one JPEG frame. More robust than MJPEG in some browsers."""
    camera_source = resolve_camera_source(**camera_request_kwargs())
    try:
        with _app.camera_lock:
            recog = get_recognizer(camera_source=camera_source)
            frame = recog.camera_manager.capture_frame()

        if frame is None:
            frame_bytes = create_stream_unavailable_frame(f"Camera {camera_source} has no frame")
            return Response(frame_bytes, mimetype="image/jpeg", status=503)

        ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ok:
            frame_bytes = create_stream_unavailable_frame("JPEG encode failed")
            return Response(frame_bytes, mimetype="image/jpeg", status=500)

        response = Response(buffer.tobytes(), mimetype="image/jpeg")
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        return response
    except Exception as exc:
        _app.logger.error("读取单帧失败: %s", exc, exc_info=True)
        frame_bytes = create_stream_unavailable_frame(str(exc)[:60])
        return Response(frame_bytes, mimetype="image/jpeg", status=500)


@bp.route("/api/capture", methods=["POST"])
def capture_image():
    """Capture a single camera frame and return it as base64."""
    try:
        data = request.json or {}
        camera_source = resolve_camera_source(**camera_request_kwargs(data))

        with _app.camera_lock:
            recog = get_recognizer(camera_source=camera_source)
            frame = recog.camera_manager.capture_frame()

        if frame is None:
            return jsonify({"success": False, "error": "无法捕获图像"})

        _, buffer = cv2.imencode(".jpg", frame)
        image_base64 = base64.b64encode(buffer).decode("utf-8")

        return jsonify(
            {
                "success": True,
                "image": image_base64,
                **camera_source_info(camera_source),
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception as exc:
        _app.logger.error("捕获图像失败: %s", exc)
        return jsonify({"success": False, "error": str(exc)})


@bp.route("/api/test/camera")
def test_camera():
    """Test the camera by returning one captured frame."""
    try:
        recog = get_recognizer()

        if not recog.camera_manager.is_opened():
            _app.logger.info("摄像头未打开，尝试重新启动...")
            if not recog.start():
                return jsonify({"success": False, "error": "摄像头启动失败"})

        frame = recog.camera_manager.capture_frame()

        if frame is None:
            return jsonify({"success": False, "error": "无法捕获图像"})

        _, buffer = cv2.imencode(".jpg", frame)
        image_base64 = base64.b64encode(buffer).decode("utf-8")

        return jsonify({"success": True, "image": image_base64})
    except Exception as exc:
        _app.logger.error("测试摄像头失败: %s", exc)
        return jsonify({"success": False, "error": str(exc)})


@bp.route("/api/camera/start", methods=["POST"])
def start_camera():
    """Start the camera for the selected source."""
    try:
        data = request.json or {}
        camera_source = resolve_camera_source(**camera_request_kwargs(data))
        with _app.camera_lock:
            recog = get_recognizer(camera_source=camera_source)

            if recog.camera_manager.is_opened():
                return jsonify(
                    {
                        "success": True,
                        **camera_source_info(camera_source),
                        "message": "摄像头已经打开",
                    }
                )

            started = recog.start()

        if started:
            _app.logger.info("摄像头启动成功")
            return jsonify(
                {
                    "success": True,
                    **camera_source_info(camera_source),
                    "message": "摄像头已启动",
                }
            )

        return jsonify({"success": False, "error": "摄像头启动失败，请检查设备"})
    except Exception as exc:
        _app.logger.error("启动摄像头失败: %s", exc)
        return jsonify({"success": False, "error": str(exc)})


@bp.route("/api/camera/status")
def camera_status():
    """Report whether the camera for the selected source is open."""
    try:
        camera_source = resolve_camera_source(**camera_request_kwargs())
        is_opened = (
            _app.recognizer is not None
            and _app.recognizer.camera_manager.camera_source == camera_source
            and _app.recognizer.camera_manager.is_opened()
        )

        return jsonify(
            {
                "success": True,
                "camera_opened": is_opened,
                **camera_source_info(camera_source),
                "message": "摄像头已打开" if is_opened else "摄像头未打开",
            }
        )
    except Exception as exc:
        return jsonify({"success": False, "error": str(exc)})
