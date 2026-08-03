"""Game lifecycle endpoints: start and reset."""

from flask import Blueprint, jsonify, request

from web_simulation import app as _app
from web_simulation import domain as web_domain

bp = Blueprint("game", __name__)


@bp.route("/api/game/start", methods=["POST"])
def start_game():
    """Start a new game, optionally homing the physical robot first."""
    try:
        data = request.json or {}
        try:
            robot_mode = web_domain.normalize_robot_mode(data.get("mode", _app.ROBOT_MODE_HARDWARE))
        except ValueError as exc:
            return jsonify({"success": False, "error": str(exc)}), 400

        use_recognized_board = data.get("use_recognized_board", False)
        board_state = data.get("board_state", {})
        ai_color = "black"
        first_player = "red"

        _app.game_state["is_game_running"] = False
        _app.game_state["robot_mode"] = robot_mode
        _app.game_state["robot_moving"] = robot_mode == _app.ROBOT_MODE_HARDWARE
        _app.game_state["vision_pause_until"] = 0.0
        _app.game_state["vision_pause_reason"] = "homing" if robot_mode == _app.ROBOT_MODE_HARDWARE else ""
        _app.game_state["awaiting_physical_baseline"] = False
        _app.game_state["post_robot_guard_until"] = 0.0
        _app.game_state["last_robot_move_capture"] = False
        _app.game_state["robot_baseline_match_count"] = 0

        homing_result = None
        if robot_mode == _app.ROBOT_MODE_HARDWARE:
            homing_result = _app.send_homing_command_to_controller()
            if not homing_result.success or not homing_result.homing_acknowledged:
                _app.game_state["robot_moving"] = False
                _app.game_state["vision_pause_reason"] = ""
                return jsonify(
                    {
                        "success": False,
                        "error": homing_result.error or "STM32 homing acknowledgement missing",
                        "homing_command": homing_result.command_text,
                        "homing_response": homing_result.response,
                        "homing_acknowledged": False,
                        "robot_mode": robot_mode,
                    }
                ), 503

        _app.game_state["move_history"] = []
        _app.game_state["display_history"] = []
        _app.game_state["pending_ai_move"] = None
        _app.game_state["last_player_move"] = None
        _app.game_state["last_ai_command_token"] = None
        _app.game_state["awaiting_physical_baseline"] = False
        _app.game_state["post_robot_guard_until"] = 0.0
        _app.game_state["last_robot_move_capture"] = False
        _app.game_state["robot_baseline_match_count"] = 0
        _app.game_state["robot_moving"] = False
        _app.game_state["vision_pause_until"] = 0.0
        _app.game_state["vision_pause_reason"] = ""
        _app.game_state["is_game_running"] = True
        _app.game_state["turn_count"] = 0
        _app.game_state["ai_color"] = ai_color
        _app.game_state["player_color"] = web_domain.opposite_color(ai_color)
        _app.game_state["first_player"] = first_player

        engine = _app.get_ai_engine()
        engine.reset_game()

        _app.logger.info("使用标准初始布局作为识别基准")
        _app.game_state["initial_fen"] = web_domain.apply_turn_to_fen(_app.STANDARD_INITIAL_FEN, first_player)
        _app.game_state["current_fen"] = _app.game_state["initial_fen"]
        _app.game_state["board_state"] = dict(_app.STANDARD_INITIAL_BOARD)

        if _app.recognizer is not None:
            _app.recognizer.sync_dynamic_baseline(
                web_domain.deserialize_board_state(_app.game_state["board_state"])
            )

        _app.logger.info("游戏已开始")

        return jsonify(
            {
                "success": True,
                "message": "游戏已开始",
                "fen": _app.game_state["initial_fen"],
                "current_fen": _app.game_state["current_fen"],
                "use_recognized_board": True,
                "board_state": _app.game_state["board_state"],
                "ai_color": _app.game_state["ai_color"],
                "player_color": _app.game_state["player_color"],
                "first_player": _app.game_state["first_player"],
                "current_turn": _app.current_turn_color(),
                "robot_mode": _app.game_state["robot_mode"],
                "homing_command": homing_result.command_text if homing_result else "",
                "homing_response": homing_result.response if homing_result else "",
                "homing_acknowledged": bool(homing_result.homing_acknowledged) if homing_result else False,
            }
        )
    except Exception as exc:
        _app.logger.error("开始游戏失败: %s", exc)
        return jsonify({"success": False, "error": str(exc)})


@bp.route("/api/game/reset", methods=["POST"])
def reset_game():
    """Reset the game to its initial (idle) state."""
    try:
        _app.game_state["current_fen"] = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
        _app.game_state["move_history"] = []
        _app.game_state["display_history"] = []
        _app.game_state["pending_ai_move"] = None
        _app.game_state["robot_moving"] = False
        _app.game_state["vision_pause_until"] = 0.0
        _app.game_state["vision_pause_reason"] = ""
        _app.game_state["is_game_running"] = False
        _app.game_state["board_state"] = {}
        _app.game_state["ai_color"] = "black"
        _app.game_state["player_color"] = "red"
        _app.game_state["first_player"] = "red"
        _app.game_state["robot_mode"] = _app.ROBOT_MODE_HARDWARE
        _app.game_state["turn_count"] = 0
        _app.game_state["last_player_move"] = None
        _app.game_state["last_ai_command_token"] = None
        _app.game_state["awaiting_physical_baseline"] = False
        _app.game_state["post_robot_guard_until"] = 0.0
        _app.game_state["last_robot_move_capture"] = False
        _app.game_state["robot_baseline_match_count"] = 0

        if _app.recognizer is not None:
            _app.reset_dynamic_tracking(_app.recognizer)

        return jsonify({"success": True, "message": "游戏已重置"})
    except Exception as exc:
        _app.logger.error("重置游戏失败: %s", exc)
        return jsonify({"success": False, "error": str(exc)})
