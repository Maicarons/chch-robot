"""Board recognition, AI move, and dynamic tracking endpoints."""

import base64
import threading
import time

import cv2
import numpy as np
from flask import Blueprint, jsonify, request

from web_simulation import app as _app
from web_simulation import domain as web_domain
from web_simulation import game_logic
from web_simulation.routes.camera import camera_request_kwargs
from web_simulation.services import resolve_camera_source

bp = Blueprint("recognition", __name__)


@bp.route("/api/recognize", methods=["POST"])
def recognize_board():
    """Recognize the board state from an uploaded image or the live camera."""
    try:
        data = request.json or {}
        image_data = data.get("image")
        camera_source = resolve_camera_source(**camera_request_kwargs(data))

        recog = _app.get_recognizer(camera_source=camera_source)

        if image_data:
            image_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            with _app.camera_lock:
                image = recog.camera_manager.capture_frame()

        if image is None:
            return jsonify({"success": False, "error": "无法获取图像"})

        # Run the model once; derive the FEN from the result to avoid double inference.
        board_state = recog.recognize_board(image)

        if board_state is None:
            return jsonify({"success": False, "error": "识别失败"})

        board_state_str_keys = web_domain.serialize_board_state(board_state)
        fen = web_domain.board_state_to_fen(board_state_str_keys, _app.current_turn_color())

        if fen:
            _app.game_state["current_fen"] = fen
        _app.game_state["board_state"] = board_state_str_keys

        return jsonify(
            {
                "success": True,
                "board_state": board_state_str_keys,
                "fen": fen,
                "piece_count": len(board_state),
            }
        )
    except Exception as exc:
        _app.logger.error("识别棋盘失败: %s", exc)
        return jsonify({"success": False, "error": str(exc)})


@bp.route("/api/recognize/dynamic", methods=["POST"])
def recognize_dynamic_board():
    """Dynamically recognize the camera feed and emit a move event when stable."""
    try:
        data = request.json or {}
        camera_source = resolve_camera_source(**camera_request_kwargs(data))

        if _app.game_state["is_game_running"]:
            now = time.monotonic()
            pause_until = _app.game_state.get("vision_pause_until", 0.0) or 0.0
            waiting_for_robot_ack = _app.game_state.get("robot_moving") and _app.game_state.get("ai_thinking")
            if (pause_until and now < pause_until) or waiting_for_robot_ack:
                if _app.recognizer is not None and not _app.game_state.get("awaiting_physical_baseline"):
                    game_logic.sync_dynamic_baseline_to_game_state(_app.recognizer)
                remaining = max(0.0, pause_until - now)
                return jsonify(
                    game_logic.dynamic_state_payload(
                        event="paused",
                        stable=False,
                        message=f"AI/robot move pause, resume red recognition in {remaining:.1f}s",
                    )
                )

        recog = _app.get_recognizer(camera_source=camera_source)
        if _app.game_state["is_game_running"]:
            now = time.monotonic()
            pause_until = _app.game_state.get("vision_pause_until", 0.0) or 0.0
            if pause_until and now >= pause_until:
                _app.game_state["vision_pause_until"] = 0.0
                _app.game_state["vision_pause_reason"] = ""
                _app.game_state["robot_moving"] = False
                if not _app.game_state.get("awaiting_physical_baseline"):
                    game_logic.sync_dynamic_baseline_to_game_state(recog)
                _app.logger.info("Robot move pause elapsed; red-side vision recognition resumed")

            if (
                getattr(recog.dynamic_tracker, "saved_board", None) is None
                and not _app.game_state.get("awaiting_physical_baseline")
            ):
                game_logic.sync_dynamic_baseline_to_game_state(recog)

        with _app.camera_lock:
            frame = recog.camera_manager.capture_frame()

        if frame is None:
            return jsonify({"success": False, "error": "无法获取图像"})

        result = recog.recognize_dynamic_frame(frame)

        raw_board_state = result.get("board_state") or {}
        board_state = web_domain.serialize_board_state(raw_board_state)
        response_board_state = (
            dict(_app.game_state.get("board_state") or {})
            if _app.game_state["is_game_running"]
            else board_state
        )
        recognized_fen = (
            web_domain.board_state_to_fen(board_state, _app.current_turn_color()) if board_state else None
        )

        if _app.game_state["is_game_running"] and _app.game_state.get("awaiting_physical_baseline"):
            if result.get("stable") and raw_board_state:
                baseline_ready, baseline_message = game_logic.robot_physical_baseline_status(raw_board_state)
                if baseline_ready:
                    game_logic.sync_dynamic_baseline_to_game_state(recog)
                    _app.game_state["awaiting_physical_baseline"] = False
                    _app.game_state["robot_baseline_match_count"] = 0
                    _app.game_state["post_robot_guard_until"] = (
                        time.monotonic() + _app.ROBOT_POST_BASELINE_GUARD_SECONDS
                    )
                    result["event"] = "robot_board_confirmed"
                    result["stable"] = True
                    result["move"] = None
                    result["message"] = baseline_message
                    _app.logger.info("Robot physical board baseline locked after AI move")
                else:
                    game_logic.reset_dynamic_tracking(recog)
                    result["event"] = "robot_board_waiting"
                    result["stable"] = False
                    result["move"] = None
                    result["message"] = baseline_message
                    _app.logger.info(baseline_message)
            return jsonify(
                {
                    "success": True,
                    "event": result.get("event"),
                    "stable": result.get("stable"),
                    "message": result.get("message"),
                    "move": result.get("move"),
                    "board_state": response_board_state,
                    "fen": _app.game_state["current_fen"],
                    "current_fen": _app.game_state["current_fen"],
                    "piece_count": len(response_board_state),
                    "recognized_piece_count": len(board_state),
                    "move_history": _app.game_state["move_history"],
                    "display_history": _app.game_state["display_history"],
                    "turn_count": _app.game_state["turn_count"],
                    "is_game_running": _app.game_state["is_game_running"],
                    "ai_color": _app.game_state["ai_color"],
                    "player_color": _app.game_state["player_color"],
                    "first_player": _app.game_state["first_player"],
                    "robot_mode": _app.game_state.get("robot_mode", _app.ROBOT_MODE_HARDWARE),
                    "current_turn": _app.current_turn_color(),
                    "vision_paused": not result.get("stable"),
                    "vision_pause_remaining": 0.0,
                }
            )

        guard_until = _app.game_state.get("post_robot_guard_until", 0.0) or 0.0
        if _app.game_state["is_game_running"] and guard_until:
            now = time.monotonic()
            if now < guard_until:
                if result.get("event") == "move":
                    game_logic.sync_dynamic_baseline_to_game_state(recog)
                remaining = max(0.0, guard_until - now)
                return jsonify(
                    {
                        "success": True,
                        "event": "robot_settling",
                        "stable": False,
                        "message": f"机械臂落子保护中，{remaining:.1f}s 后再识别红方走子",
                        "move": None,
                        "board_state": response_board_state,
                        "fen": _app.game_state["current_fen"],
                        "current_fen": _app.game_state["current_fen"],
                        "piece_count": len(response_board_state),
                        "recognized_piece_count": len(board_state),
                        "move_history": _app.game_state["move_history"],
                        "display_history": _app.game_state["display_history"],
                        "turn_count": _app.game_state["turn_count"],
                        "is_game_running": _app.game_state["is_game_running"],
                        "ai_color": _app.game_state["ai_color"],
                        "player_color": _app.game_state["player_color"],
                        "first_player": _app.game_state["first_player"],
                        "robot_mode": _app.game_state.get("robot_mode", _app.ROBOT_MODE_HARDWARE),
                        "current_turn": _app.current_turn_color(),
                        "vision_paused": True,
                        "vision_pause_remaining": round(remaining, 1),
                    }
                )
            _app.game_state["post_robot_guard_until"] = 0.0

        if result.get("stable") and board_state:
            if not _app.game_state["is_game_running"]:
                _app.game_state["board_state"] = board_state
                response_board_state = board_state
                if recognized_fen:
                    _app.game_state["current_fen"] = recognized_fen

            # If this is a move event, sync history and turn on the backend.
            if (
                _app.game_state["is_game_running"]
                and result.get("event") == "move"
                and result.get("move")
            ):
                from_pos = (result["move"]["from"]["col"], result["move"]["from"]["row"])
                to_pos = (result["move"]["to"]["col"], result["move"]["to"]["row"])
                move_code = web_domain.points_to_uci(from_pos, to_pos)
                moved_piece = result["move"].get("piece")
                result["move"]["code"] = move_code
                result["move"]["robot_command"] = _app.uci_to_robot_command(
                    move_code, _app.game_state["board_state"]
                )

                if _app.current_turn_color() != "red":
                    result["move"]["source"] = "ignored_non_player_turn"
                    game_logic.sync_dynamic_baseline_to_game_state(recog)
                    _app.logger.info("Ignored dynamic move outside red turn: %s", move_code)
                elif not web_domain.is_red_piece(moved_piece):
                    result["move"]["source"] = "ignored_non_red_piece"
                    game_logic.sync_dynamic_baseline_to_game_state(recog)
                    _app.logger.info("Ignored non-red dynamic move: %s, piece=%s", move_code, moved_piece)
                elif _app.is_duplicate_player_move(move_code):
                    result["move"]["source"] = "duplicate"
                    game_logic.sync_dynamic_baseline_to_game_state(recog)
                    _app.logger.info("Ignored duplicate player dynamic move: %s", move_code)
                else:
                    result["move"]["source"] = "player"
                    _app.game_state["board_state"] = board_state
                    response_board_state = dict(_app.game_state["board_state"])
                    _app.game_state["move_history"].append(move_code)
                    _app.game_state["display_history"].append(f"红方 {move_code}")
                    _app.game_state["turn_count"] += 1
                    _app.game_state["last_player_move"] = move_code
                    _app.update_current_fen()
                    _app.logger.info(
                        "后端同步走子: %s, 当前回合: %s", move_code, _app.game_state["turn_count"]
                    )
        return jsonify(
            {
                "success": True,
                "event": result.get("event"),
                "stable": result.get("stable"),
                "message": result.get("message"),
                "move": result.get("move"),
                "board_state": response_board_state,
                "fen": recognized_fen if not _app.game_state["is_game_running"] else _app.game_state["current_fen"],
                "current_fen": _app.game_state["current_fen"],
                "piece_count": len(response_board_state),
                "recognized_piece_count": len(board_state),
                "move_history": _app.game_state["move_history"],
                "display_history": _app.game_state["display_history"],
                "turn_count": _app.game_state["turn_count"],
                "is_game_running": _app.game_state["is_game_running"],
                "ai_color": _app.game_state["ai_color"],
                "player_color": _app.game_state["player_color"],
                "first_player": _app.game_state["first_player"],
                "robot_mode": _app.game_state.get("robot_mode", _app.ROBOT_MODE_HARDWARE),
                "current_turn": _app.current_turn_color(),
                "vision_paused": False,
                "vision_pause_remaining": 0.0,
            }
        )
    except Exception as exc:
        _app.logger.error("动态识别失败: %s", exc, exc_info=True)
        return jsonify({"success": False, "error": str(exc)})


@bp.route("/api/ai_move", methods=["POST"])
def get_ai_move():
    """Start the (async) AI thinking task."""
    try:
        if _app.game_state["ai_thinking"]:
            return jsonify({"success": False, "error": "AI已经在思考中"})

        ai_color = "black"
        _app.game_state["ai_color"] = ai_color
        _app.game_state["player_color"] = web_domain.opposite_color(ai_color)

        fen_parts = _app.game_state["current_fen"].split()
        current_turn_char = fen_parts[1] if len(fen_parts) > 1 else "w"
        ai_color_char = web_domain.color_to_turn_char(ai_color)

        if current_turn_char != ai_color_char:
            turn_name = "红方" if current_turn_char == "w" else "黑方"
            ai_name = "红方" if ai_color_char == "w" else "黑方"
            return jsonify(
                {
                    "success": False,
                    "error": f"当前是 {turn_name} 回合，AI 执 {ai_name}，尚未到 AI 走棋",
                }
            )

        depth = request.json.get("depth", 8) if request.is_json else 8

        _app.game_state["ai_thinking"] = True
        _app.game_state["ai_analysis"] = {
            "depth": 0,
            "score": 0,
            "pv": "",
            "best_move": None,
            "ai_move_token": None,
            "robot_command": None,
            "robot_mode": _app.current_robot_mode(),
            "robot_send_success": None,
            "ai_move_applied": False,
        }

        def think_task(depth_to_use):
            try:
                engine = _app.get_ai_engine()
                if not engine.is_ready or engine.process is None:
                    _app.logger.error("AI引擎尚未就绪或未成功启动（请检查Pikafish文件是否存在）。")
                    return

                engine.set_position(_app.game_state["initial_fen"], _app.game_state["move_history"])
                depth = depth_to_use
                engine._send_command(f"go depth {depth}")

                start_time = time.time()
                while time.time() - start_time < 30:
                    line = engine.process.stdout.readline().strip()
                    if not line:
                        continue

                    if line.startswith("info"):
                        parts = line.split()
                        if "depth" in parts:
                            _app.game_state["ai_analysis"]["depth"] = int(parts[parts.index("depth") + 1])
                        if "cp" in parts:
                            _app.game_state["ai_analysis"]["score"] = int(parts[parts.index("cp") + 1])
                        if "pv" in parts:
                            pv_idx = line.find(" pv ")
                            _app.game_state["ai_analysis"]["pv"] = line[pv_idx + 4 :].strip()
                        if "nodes" in parts:
                            _app.game_state["ai_analysis"]["nodes"] = int(parts[parts.index("nodes") + 1])

                    if line.startswith("bestmove"):
                        best_move = line.split()[1]
                        _app.game_state["ai_analysis"]["best_move"] = best_move
                        if best_move != "(none)":
                            _app.apply_ai_best_move(best_move)
                        break
            except Exception as exc:
                _app.logger.error("后台思考线程出错: %s", exc)
            finally:
                _app.game_state["ai_thinking"] = False

        thread = threading.Thread(target=think_task, args=(depth,))
        thread.start()

        return jsonify({"success": True, "message": "AI思考已启动"})
    except Exception as exc:
        _app.logger.error("启动AI思考失败: %s", exc)
        _app.game_state["ai_thinking"] = False
        return jsonify({"success": False, "error": str(exc)})


@bp.route("/api/ai_status")
def get_ai_status():
    """Return the AI thinking state and analysis result."""
    return jsonify(
        {
            "success": True,
            "ai_thinking": _app.game_state["ai_thinking"],
            "analysis": _app.game_state["ai_analysis"],
            "move_history": _app.game_state["move_history"],
            "display_history": _app.game_state["display_history"],
            "turn_count": _app.game_state["turn_count"],
            "current_fen": _app.game_state["current_fen"],
            "board_state": _app.game_state["board_state"],
            "piece_count": len(_app.game_state["board_state"]),
            "robot_mode": _app.game_state.get("robot_mode", _app.ROBOT_MODE_HARDWARE),
            "vision_paused": (_app.game_state.get("vision_pause_until", 0.0) or 0.0) > time.monotonic(),
            "vision_pause_remaining": round(
                max(0.0, (_app.game_state.get("vision_pause_until", 0.0) or 0.0) - time.monotonic()), 1
            ),
        }
    )


@bp.route("/api/player_move", methods=["POST"])
def player_move():
    """Handle a player-submitted move."""
    try:
        data = request.json or {}
        uci_move = data.get("move")

        if not uci_move:
            return jsonify({"success": False, "error": "缺少走法参数"})

        if _app.current_turn_color() != _app.game_state.get("player_color", "red"):
            turn_name = "红方" if _app.current_turn_color() == "red" else "黑方"
            return jsonify(
                {
                    "success": False,
                    "error": f"当前是{turn_name}回合，尚未轮到玩家走棋",
                }
            )

        _app.logger.info("玩家走法: %s (回合 %s)", uci_move, _app.game_state["turn_count"])

        _app.game_state["move_history"].append(uci_move)
        _app.game_state["display_history"].append(f"红方 {uci_move}")
        _app.game_state["turn_count"] += 1
        _app.game_state["last_player_move"] = uci_move
        _app.update_current_fen()

        return jsonify(
            {
                "success": True,
                "move": uci_move,
                "fen": _app.game_state["current_fen"],
                "display_history": _app.game_state["display_history"],
                "is_player_turn": False,
                "turn_count": _app.game_state["turn_count"],
            }
        )
    except Exception as exc:
        _app.logger.error("处理玩家走法失败: %s", exc)
        return jsonify({"success": False, "error": str(exc)})


@bp.route("/api/simulate_robot", methods=["POST"])
def simulate_robot_move():
    """Drive the simulation robot controller to execute an AI move."""
    try:
        data = request.json or {}
        uci_move = data.get("move")

        if not uci_move:
            return jsonify({"success": False, "error": "缺少走法参数"})

        _app.game_state["robot_moving"] = True
        _app.logger.info("机械臂开始执行AI走法: %s", uci_move)

        robot = _app.get_robot_controller()

        board_origin = (0, 0, 0)
        square_size_mm = 50.0
        success = robot.execute_uci_move(uci_move, board_origin, square_size_mm)

        _app.game_state["robot_moving"] = False

        if success:
            _app.logger.info("机械臂完成AI走法: %s", uci_move)
            return jsonify(
                {
                    "success": True,
                    "move": uci_move,
                    "message": "机械臂已执行AI走法",
                    "board_state": _app.game_state["board_state"],
                }
            )
        return jsonify({"success": False, "error": "机械臂移动失败"})
    except Exception as exc:
        _app.logger.error("模拟机械臂失败: %s", exc)
        _app.game_state["robot_moving"] = False
        return jsonify({"success": False, "error": str(exc)})
