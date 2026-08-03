"""Status, robot status, and camera-listing endpoints."""

import logging

from flask import Blueprint, jsonify, request

import config
from web_simulation import app as _app
from web_simulation.services import camera_source_info, list_available_cameras

logger = logging.getLogger(__name__)

bp = Blueprint("status", __name__)


@bp.route("/api/status")
def get_status():
    """Return the full game state."""
    return jsonify({"success": True, "state": _app.game_state})


@bp.route("/api/robot/status")
def get_robot_status():
    should_probe = request.args.get("probe") in {"1", "true", "yes"}
    if not should_probe:
        return jsonify(
            {
                "success": True,
                "connected": None,
                "status": "not_probed",
                "host": getattr(config, "ROBOT_NETWORK_HOST", "192.168.0.102"),
                "port": getattr(config, "ROBOT_NETWORK_PORT", 8086),
                "error": "",
            }
        )

    result = _app.probe_robot_controller()
    return jsonify(
        {
            "success": True,
            "connected": result.success,
            "status": "probed",
            "host": getattr(config, "ROBOT_NETWORK_HOST", "192.168.0.102"),
            "port": getattr(config, "ROBOT_NETWORK_PORT", 8086),
            "error": result.error,
        }
    )


@bp.route("/api/cameras")
def get_cameras():
    """List the locally available cameras."""
    try:
        cameras = list_available_cameras()
        return jsonify(
            {
                "success": True,
                "cameras": cameras,
                "current_camera_index": _app.current_camera_index,
                **camera_source_info(),
            }
        )
    except Exception as exc:
        logger.error("获取摄像头列表失败: %s", exc)
        return jsonify({"success": False, "error": str(exc)})
