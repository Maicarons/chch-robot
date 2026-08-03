"""
Web simulation backend - Flask application composition root.

This module is intentionally small. It:

* owns the shared, mutable runtime state (``game_state`` and the long-lived
  component instances: recognizer, AI engine, robot controller, STM32 client);
* declares the configuration constants and the Flask ``app``;
* re-exports the helper functions that the REST blueprints and the test-suite
  rely on (they live in ``services``, ``robot_cmd``, ``game_logic``,
  ``startup`` and ``domain`` so each concern stays in its own file);

The route handlers themselves are split across :mod:`web_simulation.routes`.
Helper modules reach the shared state through ``web_simulation.app`` (this
module) so test patches on ``web_app.<name>`` take effect.
"""

import logging
import os
import sys

# Make the project root importable when launched as `python web_simulation/app.py`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    # Register this module as `web_simulation.app` so submodules share the same
    # state object instead of importing a second copy of the module.
    import web_simulation  # noqa: F401

    sys.modules.setdefault("web_simulation.app", sys.modules["__main__"])

import config
from flask import Flask, render_template
from flask_cors import CORS

from vision import BoardRecognizer
from web_simulation import domain as web_domain

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #
STANDARD_INITIAL_BOARD = web_domain.STANDARD_INITIAL_BOARD
STANDARD_INITIAL_FEN = web_domain.STANDARD_INITIAL_FEN
UCI_FILES = web_domain.UCI_FILES
ROBOT_MODE_HARDWARE = web_domain.ROBOT_MODE_HARDWARE
ROBOT_MODE_SIMULATION = web_domain.ROBOT_MODE_SIMULATION
ROBOT_MODES = web_domain.ROBOT_MODES

ROBOT_MOVE_PAUSE_SECONDS = float(getattr(config, "ROBOT_SIMULATED_MOVE_SECONDS", 15.0))
ROBOT_CAPTURE_SETTLE_SECONDS = float(getattr(config, "ROBOT_CAPTURE_SETTLE_SECONDS", 0.0))
ROBOT_NORMAL_SETTLE_SECONDS = float(getattr(config, "ROBOT_NORMAL_SETTLE_SECONDS", 0.0))
ROBOT_POST_BASELINE_GUARD_SECONDS = float(getattr(config, "ROBOT_POST_BASELINE_GUARD_SECONDS", 0.0))
ROBOT_BASELINE_MATCH_REQUIRED = int(getattr(config, "ROBOT_BASELINE_MATCH_REQUIRED", 3))
ROBOT_NETWORK_HOST = getattr(config, "ROBOT_NETWORK_HOST", "192.168.0.102")
ROBOT_NETWORK_PORT = int(getattr(config, "ROBOT_NETWORK_PORT", 8086))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------- #
# Flask application
# --------------------------------------------------------------------------- #
app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)  # 允许跨域请求

# --------------------------------------------------------------------------- #
# Shared mutable state
# --------------------------------------------------------------------------- #
game_state = {
    "initial_fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
    "current_fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
    "move_history": [],
    "display_history": [],
    "is_game_running": False,
    "player_color": "red",
    "ai_color": "black",
    "first_player": "red",
    "ai_thinking": False,
    "ai_analysis": {
        "depth": 0,
        "score": 0,
        "pv": "",
        "nodes": 0,
        "best_move": None,
        "ai_move_token": None,
        "robot_command": None,
    },
    "robot_moving": False,
    "pending_ai_move": None,
    "vision_pause_until": 0.0,
    "vision_pause_reason": "",
    "robot_mode": ROBOT_MODE_HARDWARE,
    "board_state": {},
    "turn_count": 0,
}
game_state.setdefault("last_player_move", None)
game_state.setdefault("last_ai_command_token", None)
game_state.setdefault("awaiting_physical_baseline", False)
game_state.setdefault("post_robot_guard_until", 0.0)
game_state.setdefault("last_robot_move_capture", False)
game_state.setdefault("robot_baseline_match_count", 0)

# Long-lived component instances (lazy-initialised by the service getters).
recognizer = None
current_camera_index = config.CAMERA_INDEX
current_camera_source = config.CAMERA_INDEX
current_network_camera_url = getattr(config, "IP_CAMERA_URL", "")
camera_lock = __import__("threading").Lock()
recognizer_lock = __import__("threading").RLock()
camera_probe_cache = None
active_stream_token = 0
ai_engine = None
robot_controller = None
robot_tcp_client = None
robot_tcp_client_lock = __import__("threading").RLock()


# --------------------------------------------------------------------------- #
# Page route
# --------------------------------------------------------------------------- #
@app.route("/")
def index():
    """Serve the main web UI."""
    return render_template("index.html")


# --------------------------------------------------------------------------- #
# Re-exported helpers (single source of truth lives in the focused modules)
# --------------------------------------------------------------------------- #
# Pure domain helpers.
normalize_robot_mode = web_domain.normalize_robot_mode
color_to_turn_char = web_domain.color_to_turn_char
turn_char_to_color = web_domain.turn_char_to_color
opposite_color = web_domain.opposite_color
apply_turn_to_fen = web_domain.apply_turn_to_fen
board_state_to_fen = web_domain.board_state_to_fen
serialize_board_state = web_domain.serialize_board_state
deserialize_board_state = web_domain.deserialize_board_state
is_red_piece = web_domain.is_red_piece
apply_uci_to_board_state = web_domain.apply_uci_to_board_state
board_pos_to_uci = web_domain.board_pos_to_uci
points_to_uci = web_domain.points_to_uci

# Service layer: camera discovery + lazy component getters.
from web_simulation.services import (  # noqa: E402
    resolve_camera_source,
    camera_source_info,
    get_recognizer,
    get_ai_engine,
    get_robot_controller,
    get_robot_tcp_client,
    close_robot_tcp_client,
    list_available_cameras,
    probe_camera_index,
    get_windows_camera_names,
)

# Robot command translation + transport wrappers.
from web_simulation.robot_cmd import (  # noqa: E402
    get_robot_board_config,
    robot_network_target,
    robot_network_timeout,
    robot_command_timeout_for_command,
    uci_to_robot_command,
    send_robot_command_to_controller,
    probe_robot_controller,
    send_homing_command_to_controller,
    build_robot_log_messages,
    format_robot_command,
    robot_command_is_capture,
    robot_settle_seconds_for_command,
)

# Core game-state transitions.
from web_simulation.game_logic import (  # noqa: E402
    current_robot_mode,
    current_turn_color,
    is_duplicate_player_move,
    ai_command_token,
    update_current_fen,
    sync_dynamic_baseline_to_game_state,
    reset_dynamic_tracking,
    apply_ai_best_move,
    dynamic_state_payload,
    robot_physical_baseline_status,
)

# Interactive startup parameter prompts.
from web_simulation.startup import (  # noqa: E402
    parse_positive_int_parameter,
    parse_robot_ip_parameter,
    prompt_positive_int_parameter,
    prompt_robot_ip_parameter,
    prompt_startup_parameter_overrides,
)


# --------------------------------------------------------------------------- #
# Blueprint registration
# --------------------------------------------------------------------------- #
from web_simulation.routes import register_routes  # noqa: E402

register_routes(app)


if __name__ == "__main__":
    prompt_startup_parameter_overrides()
    print("=" * 60)
    print("Web仿真环境启动")
    print("=" * 60)
    print("访问地址: http://localhost:5000")
    print("=" * 60)

    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
