"""
Web仿真环境 - Flask后端应用
提供棋盘识别、AI对弈、机械臂模拟的Web接口
"""

import os
import sys
import logging
import json
import subprocess
from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
import base64
import cv2
import numpy as np
from datetime import datetime
import threading
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision import BoardRecognizer
from vision.camera import normalize_camera_source, is_network_camera_source
from ai import AIEngine
from robot import (
    BoardToArmConfig,
    RobotArmCommand,
    RobotHomingCommand,
    RobotPersistentClient,
    RobotController,
    RobotSendResult,
    uci_to_arm_command,
)
from web_simulation import domain as web_domain
import config

STANDARD_INITIAL_BOARD = {
    "0,0": "r", "1,0": "n", "2,0": "b", "3,0": "a", "4,0": "k", "5,0": "a", "6,0": "b", "7,0": "n", "8,0": "r",
    "1,2": "c", "7,2": "c",
    "0,3": "p", "2,3": "p", "4,3": "p", "6,3": "p", "8,3": "p",
    "0,6": "P", "2,6": "P", "4,6": "P", "6,6": "P", "8,6": "P",
    "1,7": "C", "7,7": "C",
    "0,9": "R", "1,9": "N", "2,9": "B", "3,9": "A", "4,9": "K", "5,9": "A", "6,9": "B", "7,9": "N", "8,9": "R",
}
STANDARD_INITIAL_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"
UCI_FILES = "abcdefghi"
ROBOT_MOVE_PAUSE_SECONDS = getattr(config, "ROBOT_SIMULATED_MOVE_SECONDS", 15.0)
ROBOT_CAPTURE_SETTLE_SECONDS = float(getattr(config, "ROBOT_CAPTURE_SETTLE_SECONDS", 0.0))
ROBOT_NORMAL_SETTLE_SECONDS = float(getattr(config, "ROBOT_NORMAL_SETTLE_SECONDS", 0.0))
ROBOT_POST_BASELINE_GUARD_SECONDS = float(getattr(config, "ROBOT_POST_BASELINE_GUARD_SECONDS", 0.0))
ROBOT_BASELINE_MATCH_REQUIRED = int(getattr(config, "ROBOT_BASELINE_MATCH_REQUIRED", 3))
ROBOT_MODE_HARDWARE = "hardware"
ROBOT_MODE_SIMULATION = "simulation"
ROBOT_MODES = {ROBOT_MODE_HARDWARE, ROBOT_MODE_SIMULATION}

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__, 
            template_folder='templates',
            static_folder='static')
CORS(app)  # 允许跨域请求

# 全局状态
game_state = {
    'initial_fen': 'rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1',  # 初始FEN（只用于AI初始化）
    'current_fen': 'rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1',  # 当前FEN（动态更新）
    'move_history': [],  # UCI走法历史
    'display_history': [],  # 网页显示历史，AI走法用 X0,Y0,X1,Y1,Z
    'is_game_running': False,
    'player_color': 'red',
    'ai_color': 'black',
    'first_player': 'red',
    'ai_thinking': False,
    'ai_analysis': {
        'depth': 0,
        'score': 0,
        'pv': '',
        'nodes': 0,
        'best_move': None,
        'ai_move_token': None,
        'robot_command': None
    },
    'robot_moving': False,
    'pending_ai_move': None,
    'vision_pause_until': 0.0,
    'vision_pause_reason': '',
    'robot_mode': ROBOT_MODE_HARDWARE,
    'board_state': {},  # 当前棋盘状态 {"col,row": "piece_char"}
    'turn_count': 0,  # 回合计数（偶数=红方，奇数=黑方）
}

# 初始化组件（懒加载）
recognizer = None
current_camera_index = config.CAMERA_INDEX
current_camera_source = config.CAMERA_INDEX
current_network_camera_url = getattr(config, "IP_CAMERA_URL", "")
camera_lock = threading.Lock()
recognizer_lock = threading.RLock()
camera_probe_cache = None
active_stream_token = 0
ai_engine = None
robot_controller = None
robot_tcp_client = None
robot_tcp_client_lock = threading.RLock()

game_state.setdefault('last_player_move', None)
game_state.setdefault('last_ai_command_token', None)
game_state.setdefault('awaiting_physical_baseline', False)
game_state.setdefault('post_robot_guard_until', 0.0)
game_state.setdefault('last_robot_move_capture', False)
game_state.setdefault('robot_baseline_match_count', 0)


def resolve_camera_source(camera_index=None, camera_source=None, camera_url=None):
    if camera_url:
        return normalize_camera_source(camera_url)

    if camera_source:
        if camera_source == 'network':
            if not current_network_camera_url:
                raise ValueError('尚未配置网络摄像头URL')
            return normalize_camera_source(current_network_camera_url)
        return normalize_camera_source(camera_source)

    if camera_index is not None:
        return normalize_camera_source(camera_index)

    return normalize_camera_source(current_camera_source)


def camera_source_info(source=None):
    source = normalize_camera_source(current_camera_source if source is None else source)
    return {
        'source_label': str(source),
        'source_type': 'network' if isinstance(source, str) else 'local',
        'camera_index': source if isinstance(source, int) else current_camera_index,
        'network_url': str(source) if isinstance(source, str) else current_network_camera_url,
    }


def get_recognizer(camera_index=None, camera_source=None, camera_url=None):
    """获取棋盘识别器实例"""
    global recognizer, current_camera_index, current_camera_source

    with recognizer_lock:
        source = resolve_camera_source(
            camera_index=camera_index,
            camera_source=camera_source,
            camera_url=camera_url,
        )
        if isinstance(source, int):
            current_camera_index = source
        current_camera_source = source

        if recognizer is None:
            recognizer = BoardRecognizer(camera_index=current_camera_index, camera_source=source)
            if not recognizer.start():
                logger.warning(f"摄像头源 {source} 启动失败，请检查摄像头或URL")
            else:
                logger.info(f"摄像头源 {source} 已启动")
        elif recognizer.camera_manager.camera_source != source:
            logger.info(f"切换摄像头源: {recognizer.camera_manager.source_label} -> {source}")
            recognizer.camera_manager.set_source(source)
            recognizer.stabilizer.clear()
            recognizer.reset_dynamic_tracking()

            if not recognizer.start():
                logger.warning(f"摄像头源 {source} 启动失败，请检查摄像头或URL")
            else:
                logger.info(f"摄像头源 {source} 已启动")

        return recognizer


def get_windows_camera_names():
    """Read friendly camera names from Windows device manager."""
    if os.name != 'nt':
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
            ['powershell', '-NoProfile', '-Command', script],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=5
        )

        if result.returncode != 0 or not result.stdout.strip():
            return []

        raw_devices = json.loads(result.stdout)
        if isinstance(raw_devices, dict):
            raw_devices = [raw_devices]

        names = []
        seen = set()
        for device in raw_devices:
            name = (device.get('Name') or '').strip()
            if not name:
                continue

            dedupe_key = (name, device.get('DeviceID'))
            if dedupe_key in seen:
                continue

            seen.add(dedupe_key)
            names.append(name)

        return names
    except Exception as e:
        logger.warning(f"读取摄像头设备名失败: {e}")
        return []


def list_available_cameras(max_cameras=6):
    """List local camera choices based on OpenCV indexes that can really read frames."""
    global camera_probe_cache

    if camera_probe_cache is not None:
        return camera_probe_cache

    camera_names = get_windows_camera_names()
    cameras = []
    preferred_index = int(config.CAMERA_INDEX)

    for index in range(max_cameras):
        probe = probe_camera_index(index)
        if probe:
            name = camera_names[index] if index < len(camera_names) else None
            label = f'{name or "本地摄像头"}（索引 {index}）'
            if index == preferred_index:
                label = f'USB摄像头（索引 {index}）'
            cameras.append({
                'index': index,
                'name': name,
                'label': label,
                'available': True,
                'width': probe.get('width', 0),
                'height': probe.get('height', 0)
            })

    cameras.sort(key=lambda camera: 0 if camera['index'] == preferred_index else 1)

    if not any(camera['index'] == preferred_index for camera in cameras):
        cameras.insert(0, {
            'index': preferred_index,
            'name': None,
            'label': f'USB摄像头（索引 {preferred_index}）',
            'available': True,
            'width': config.CAMERA_WIDTH,
            'height': config.CAMERA_HEIGHT
        })

    if not cameras:
        cameras.append({
            'index': preferred_index,
            'name': None,
            'label': f'USB摄像头（索引 {preferred_index}）',
            'available': True,
            'width': 0,
            'height': 0
        })

    camera_probe_cache = cameras
    return cameras


def probe_camera_index(index):
    """Probe one OpenCV camera index in a child process so bad devices cannot hang Flask."""
    backend_expr = 'cv2.CAP_DSHOW' if os.name == 'nt' else 'cv2.CAP_ANY'
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
            [sys.executable, '-c', code],
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=4
        )

        if result.returncode != 0:
            return None

        probe = json.loads(result.stdout.strip().splitlines()[-1])
        return probe if probe.get('ok') else None
    except Exception as e:
        logger.info(f"摄像头索引 {index} 探测失败或超时: {e}")
        return None


def get_ai_engine():
    """获取AI引擎实例"""
    global ai_engine
    if ai_engine is None:
        ai_engine = AIEngine()
        ai_engine.start()
    return ai_engine


def get_robot_controller():
    """获取机械臂控制器实例"""
    global robot_controller
    if robot_controller is None:
        robot_controller = RobotController(robot_type='simulation')
        robot_controller.initialize()
    return robot_controller


def normalize_robot_mode(value=None):
    return web_domain.normalize_robot_mode(value)


def current_robot_mode():
    try:
        return normalize_robot_mode(game_state.get('robot_mode'))
    except ValueError:
        game_state['robot_mode'] = ROBOT_MODE_HARDWARE
        return ROBOT_MODE_HARDWARE


def color_to_turn_char(color):
    return web_domain.color_to_turn_char(color)


def turn_char_to_color(turn_char):
    return web_domain.turn_char_to_color(turn_char)


def opposite_color(color):
    return web_domain.opposite_color(color)


def apply_turn_to_fen(fen, turn_color):
    return web_domain.apply_turn_to_fen(fen, turn_color)


def current_turn_color():
    first_player = game_state.get('first_player', 'red')
    if len(game_state['move_history']) % 2 == 0:
        return first_player
    return opposite_color(first_player)


def is_duplicate_player_move(move_code):
    if not move_code:
        return False
    if game_state.get('last_player_move') == move_code:
        return True
    return bool(game_state['move_history'] and game_state['move_history'][-1] == move_code)


def ai_command_token(best_move):
    return f"{len(game_state['move_history'])}:{best_move}"


def update_current_fen():
    """根据走法历史和棋盘状态更新当前FEN"""
    moves = game_state['move_history']
    
    if game_state.get('board_state'):
        # 基于最新的棋盘状态生成基础FEN
        fen = board_state_to_fen(game_state['board_state'], current_turn_color())
        fen_parts = fen.split()
        
        # 从初始FEN获取初始步数并加上已走回合数
        initial_parts = game_state['initial_fen'].split()
        initial_move_number = int(initial_parts[5]) if len(initial_parts) >= 6 else 1
        current_move_number = initial_move_number + len(moves) // 2
        
        if len(fen_parts) >= 6:
            fen_parts[5] = str(current_move_number)
            game_state['current_fen'] = ' '.join(fen_parts)
            logger.info(f"更新FEN: {game_state['current_fen']}")
            return
            
    # 解析初始FEN (回退)
    fen_parts = game_state['initial_fen'].split()
    
    if len(fen_parts) >= 6:
        # 根据先手方和走法数量切换回合
        fen_parts[1] = color_to_turn_char(current_turn_color())
        
        # 更新步数计数器（每两步增加1）
        move_number = int(fen_parts[5])
        fen_parts[5] = str(move_number + len(moves) // 2)
        
        game_state['current_fen'] = ' '.join(fen_parts)
        logger.info(f"更新FEN(回退): {game_state['current_fen']}")


def board_pos_to_uci(pos):
    return web_domain.board_pos_to_uci(pos)


def points_to_uci(from_pos, to_pos):
    return web_domain.points_to_uci(from_pos, to_pos)


def get_robot_board_config():
    return BoardToArmConfig(
        origin_x=getattr(config, "ROBOT_COMMAND_ORIGIN_X", 0),
        origin_y=getattr(config, "ROBOT_COMMAND_ORIGIN_Y", 0),
        file_spacing_mm=getattr(config, "ROBOT_COMMAND_FILE_SPACING_MM", 34),
        rank_spacing_mm=getattr(config, "ROBOT_COMMAND_RANK_SPACING_MM", 30),
        river_spacing_mm=getattr(config, "ROBOT_COMMAND_RIVER_SPACING_MM", 32),
    )


def robot_network_target():
    return (
        getattr(config, "ROBOT_NETWORK_HOST", "192.168.0.102"),
        int(getattr(config, "ROBOT_NETWORK_PORT", 8086)),
    )


def robot_network_timeout():
    return getattr(config, "ROBOT_NETWORK_TIMEOUT", 1.0)


def parse_positive_int_parameter(raw_value, current_value, label):
    value = str(raw_value).strip()
    if not value:
        return int(current_value)
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{label} 必须是正整数") from exc
    if parsed <= 0:
        raise ValueError(f"{label} 必须大于 0")
    return parsed


def parse_robot_ip_parameter(raw_value, current_host):
    value = str(raw_value).strip()
    if not value:
        return str(current_host)

    if value.isdigit():
        octet = int(value)
        if 0 <= octet <= 255:
            return f"192.168.0.{octet}"
        raise ValueError("下位机 IP 最后一段必须在 0-255 之间")

    parts = value.split(".")
    if len(parts) != 4:
        raise ValueError("下位机 IP 格式应类似 192.168.0.102，或只输入 102")
    octets = []
    for part in parts:
        if not part.isdigit():
            raise ValueError("下位机 IP 只能包含数字和点号")
        octet = int(part)
        if not 0 <= octet <= 255:
            raise ValueError("下位机 IP 每一段必须在 0-255 之间")
        octets.append(str(octet))
    return ".".join(octets)


def prompt_positive_int_parameter(label, current_value):
    while True:
        raw_value = input(f"{label} [{current_value}]: ")
        try:
            return parse_positive_int_parameter(raw_value, current_value, label)
        except ValueError as exc:
            print(f"  输入无效: {exc}")


def prompt_robot_ip_parameter(current_host):
    while True:
        raw_value = input(f"下位机 IP，输入完整地址或最后一段 [{current_host}]: ")
        try:
            return parse_robot_ip_parameter(raw_value, current_host)
        except ValueError as exc:
            print(f"  输入无效: {exc}")


def prompt_startup_parameter_overrides():
    if os.environ.get("CHRO_SKIP_STARTUP_PROMPT", "").lower() in {"1", "true", "yes", "y"}:
        return
    if not getattr(sys, "stdin", None) or not sys.stdin.isatty():
        return

    print()
    print("=" * 60)
    print("启动参数")
    print("=" * 60)
    print(f"棋盘横向格距: {getattr(config, 'ROBOT_COMMAND_FILE_SPACING_MM', 34)} mm")
    print(f"棋盘纵向格距: {getattr(config, 'ROBOT_COMMAND_RANK_SPACING_MM', 30)} mm")
    print(f"楚河汉界纵向长: {getattr(config, 'ROBOT_COMMAND_RIVER_SPACING_MM', 32)} mm")
    print(f"下位机 IP: {getattr(config, 'ROBOT_NETWORK_HOST', '192.168.0.102')}")
    print("=" * 60)

    try:
        choice = input("启动前是否更改这些参数？[y/N]: ").strip().lower()
    except EOFError:
        return
    if choice not in {"y", "yes", "是"}:
        print("沿用当前启动参数。")
        return

    try:
        config.ROBOT_COMMAND_FILE_SPACING_MM = prompt_positive_int_parameter(
            "棋盘横向格距 mm",
            getattr(config, "ROBOT_COMMAND_FILE_SPACING_MM", 34),
        )
        config.ROBOT_COMMAND_RANK_SPACING_MM = prompt_positive_int_parameter(
            "棋盘纵向格距 mm",
            getattr(config, "ROBOT_COMMAND_RANK_SPACING_MM", 30),
        )
        config.ROBOT_COMMAND_RIVER_SPACING_MM = prompt_positive_int_parameter(
            "楚河汉界纵向长 mm",
            getattr(config, "ROBOT_COMMAND_RIVER_SPACING_MM", 32),
        )
        config.ROBOT_NETWORK_HOST = prompt_robot_ip_parameter(
            getattr(config, "ROBOT_NETWORK_HOST", "192.168.0.102")
        )
    except KeyboardInterrupt:
        print()
        print("已取消参数修改，沿用当前值。")
        return

    close_robot_tcp_client()
    print("=" * 60)
    print("本次运行参数:")
    print(f"棋盘尺寸: 横向={config.ROBOT_COMMAND_FILE_SPACING_MM} mm, "
          f"纵向={config.ROBOT_COMMAND_RANK_SPACING_MM} mm, "
          f"楚河汉界={config.ROBOT_COMMAND_RIVER_SPACING_MM} mm")
    print(f"下位机目标: {config.ROBOT_NETWORK_HOST}:{getattr(config, 'ROBOT_NETWORK_PORT', 8086)}")
    print("=" * 60)


def robot_command_timeout_for_command(command):
    if robot_command_is_capture(command):
        return float(getattr(
            config,
            "ROBOT_CAPTURE_COMMAND_TIMEOUT",
            max(getattr(config, "ROBOT_COMMAND_TIMEOUT", 60.0), 120.0),
        ))
    return float(getattr(
        config,
        "ROBOT_NORMAL_COMMAND_TIMEOUT",
        getattr(config, "ROBOT_COMMAND_TIMEOUT", max(robot_network_timeout(), ROBOT_MOVE_PAUSE_SECONDS + 5.0)),
    ))


def get_robot_tcp_client():
    """Return the reusable STM32 TCP client for the configured target."""

    global robot_tcp_client
    host, port = robot_network_target()
    with robot_tcp_client_lock:
        if (
            robot_tcp_client is None
            or robot_tcp_client.host != host
            or robot_tcp_client.port != port
        ):
            if robot_tcp_client is not None:
                robot_tcp_client.close()
            robot_tcp_client = RobotPersistentClient(host, port, timeout=robot_network_timeout())
        return robot_tcp_client


def close_robot_tcp_client():
    global robot_tcp_client
    with robot_tcp_client_lock:
        if robot_tcp_client is not None:
            robot_tcp_client.close()
            robot_tcp_client = None


def uci_to_robot_command(uci_move, board_state=None):
    """Convert UCI to the STM32 five-value command [startX,startY,endX,endY,signal]."""
    try:
        return uci_to_arm_command(
            uci_move,
            board_state=board_state,
            config=get_robot_board_config(),
        ).to_tuple()
    except ValueError as exc:
        logger.warning(f"Invalid UCI move for robot command: {uci_move}, error={exc}")
        return None


def send_robot_command_to_controller(command):
    if not command:
        return RobotSendResult(success=False, command_text="", error="empty robot command")

    try:
        arm_command = command if isinstance(command, RobotArmCommand) else RobotArmCommand.from_sequence(command)
    except (TypeError, ValueError) as exc:
        return RobotSendResult(
            success=False,
            command_text=format_robot_command(command),
            error=str(exc),
        )

    command_timeout = robot_command_timeout_for_command(arm_command)
    result = get_robot_tcp_client().send_robot_command(
        arm_command,
        timeout=command_timeout,
    )

    if result.success:
        logger.info(
            "Robot five-value command sent to %s:%s: %s%s, timeout=%.1fs",
            getattr(config, "ROBOT_NETWORK_HOST", "127.0.0.1"),
            getattr(config, "ROBOT_NETWORK_PORT", 8086),
            result.command_text,
            f", response={result.response}" if result.response else "",
            command_timeout,
        )
    else:
        logger.warning(
            "Robot five-value command send failed in hardware mode: %s, timeout=%.1fs, error=%s",
            result.command_text,
            command_timeout,
            result.error,
        )

    return result


def probe_robot_controller():
    try:
        get_robot_tcp_client().connect(timeout=robot_network_timeout())
        return RobotSendResult(success=True, command_text="", response="persistent connection ready")
    except OSError as exc:
        return RobotSendResult(success=False, command_text="", error=str(exc))


def send_homing_command_to_controller():
    command = RobotHomingCommand(
        m1_angle_deg=getattr(config, "ROBOT_HOMING_M1_ANGLE_DEG", -17.1848),
        m2_angle_deg=getattr(config, "ROBOT_HOMING_M2_ANGLE_DEG", -55.6304),
    )
    result = get_robot_tcp_client().send_homing_command(
        command,
        timeout=getattr(config, "ROBOT_HOMING_TIMEOUT", 30.0),
    )

    if result.success:
        logger.info(
            "STM32 homing completed: command=%s, response=%s",
            result.command_text,
            result.response,
        )
    else:
        logger.warning(
            "STM32 homing failed: command=%s, response=%s, error=%s",
            result.command_text,
            result.response,
            result.error,
        )
    return result


def build_robot_log_messages(robot_command_text, send_result, robot_command=None):
    target = f"{getattr(config, 'ROBOT_NETWORK_HOST', '127.0.0.1')}:{getattr(config, 'ROBOT_NETWORK_PORT', 8086)}"
    messages = [
        f"STM32 target: {target}",
        f"five-value command: {robot_command_text or 'none'}",
        f"sent payload: {send_result.command_text or robot_command_text or 'none'}",
    ]
    if robot_command is not None:
        messages.append(f"command timeout: {robot_command_timeout_for_command(robot_command):.1f}s")

    if send_result.success:
        if send_result.response:
            messages.append(f"controller response: {send_result.response}")
        else:
            messages.append("send result: sent")
    else:
        messages.append(f"send result: failed, {send_result.error}")

    return messages


def format_robot_command(command):
    if hasattr(command, "to_wire"):
        return command.to_wire()
    return ",".join(str(v) for v in command) if command else ""


def robot_command_is_capture(command):
    try:
        if isinstance(command, RobotArmCommand):
            return command.signal == 1
        return len(command or []) >= 5 and int(command[4]) == 1
    except (TypeError, ValueError):
        return False


def robot_settle_seconds_for_command(command):
    return ROBOT_CAPTURE_SETTLE_SECONDS if robot_command_is_capture(command) else ROBOT_NORMAL_SETTLE_SECONDS


def apply_uci_to_board_state(board_state, uci_move):
    return web_domain.apply_uci_to_board_state(board_state, uci_move)


def apply_ai_best_move(best_move):
    robot_command = uci_to_robot_command(best_move, game_state.get('board_state'))
    robot_command_text = format_robot_command(robot_command)
    mode = current_robot_mode()
    command_token = ai_command_token(best_move)

    game_state['ai_analysis']['robot_command'] = robot_command
    game_state['ai_analysis']['robot_command_text'] = robot_command_text
    game_state['ai_analysis']['robot_send_success'] = None
    game_state['ai_analysis']['robot_send_acknowledged'] = False
    game_state['ai_analysis']['robot_send_response'] = None
    game_state['ai_analysis']['robot_send_error'] = None
    game_state['ai_analysis']['robot_mode'] = mode
    game_state['ai_analysis']['ai_move_token'] = command_token
    game_state['ai_analysis']['robot_netassist_target'] = (
        f"{getattr(config, 'ROBOT_NETWORK_HOST', '127.0.0.1')}:"
        f"{getattr(config, 'ROBOT_NETWORK_PORT', 8086)}"
    )
    game_state['ai_analysis']['robot_log_messages'] = []
    game_state['ai_analysis']['ai_move_applied'] = False

    if game_state['move_history'] and game_state['move_history'][-1] == best_move:
        duplicate_result = RobotSendResult(
            success=True,
            command_text=robot_command_text,
            response="DUPLICATE_AI_MOVE_IGNORED",
        )
        game_state['pending_ai_move'] = None
        game_state['robot_moving'] = False
        game_state['vision_pause_until'] = 0.0
        game_state['vision_pause_reason'] = ''
        game_state['ai_analysis']['robot_send_success'] = True
        game_state['ai_analysis']['robot_send_acknowledged'] = True
        game_state['ai_analysis']['robot_send_response'] = duplicate_result.response
        game_state['ai_analysis']['robot_send_error'] = ''
        game_state['ai_analysis']['ai_move_applied'] = True
        game_state['ai_analysis']['robot_log_messages'] = [
            f"duplicate AI move ignored: {best_move}"
        ]
        logger.warning("Ignored duplicate AI move already at history tail: %s", best_move)
        return duplicate_result

    if game_state.get('last_ai_command_token') == command_token:
        duplicate_result = RobotSendResult(
            success=True,
            command_text=robot_command_text,
            response="DUPLICATE_AI_COMMAND_IGNORED",
        )
        game_state['ai_analysis']['robot_send_success'] = True
        game_state['ai_analysis']['robot_send_acknowledged'] = True
        game_state['ai_analysis']['robot_send_response'] = duplicate_result.response
        game_state['ai_analysis']['robot_send_error'] = ''
        game_state['ai_analysis']['ai_move_applied'] = True
        game_state['ai_analysis']['robot_log_messages'] = [
            f"duplicate AI command token ignored: {command_token}"
        ]
        logger.warning("Ignored duplicate AI command token: %s", command_token)
        return duplicate_result

    if not game_state['move_history'] or game_state['move_history'][-1] != best_move:
        game_state['move_history'].append(best_move)
        game_state['display_history'].append(robot_command_text)
        game_state['turn_count'] += 1
        apply_uci_to_board_state(game_state['board_state'], best_move)
        game_state['last_ai_command_token'] = command_token

    update_current_fen()
    game_state['pending_ai_move'] = None
    game_state['robot_moving'] = True
    game_state['vision_pause_until'] = time.monotonic() + ROBOT_MOVE_PAUSE_SECONDS
    game_state['vision_pause_reason'] = (
        'simulation_move' if mode == ROBOT_MODE_SIMULATION else 'robot_move'
    )
    game_state['ai_analysis']['ai_move_applied'] = True

    if recognizer is not None:
        sync_dynamic_baseline_to_game_state(recognizer)

    logger.info(
        "AI move %s pre-applied in %s mode; vision pauses for %.0fs before controller ack",
        best_move,
        mode,
        ROBOT_MOVE_PAUSE_SECONDS,
    )

    if mode == ROBOT_MODE_SIMULATION:
        robot_send_result = RobotSendResult(
            success=True,
            command_text=robot_command_text,
            response="RESULT:1,MODE:simulation",
        )
    else:
        robot_send_result = send_robot_command_to_controller(robot_command)

    robot_acknowledged = (
        robot_send_result.success
        if mode == ROBOT_MODE_SIMULATION
        else robot_send_result.motion_acknowledged
    )
    game_state['ai_analysis']['robot_send_success'] = robot_send_result.success
    game_state['ai_analysis']['robot_send_acknowledged'] = robot_acknowledged
    game_state['ai_analysis']['robot_send_response'] = robot_send_result.response
    game_state['ai_analysis']['robot_send_error'] = robot_send_result.error
    game_state['ai_analysis']['robot_log_messages'] = build_robot_log_messages(
        robot_command_text,
        robot_send_result,
        robot_command,
    )

    if not robot_send_result.success:
        logger.error(
            "AI move %s is already pre-displayed, but robot send failed in %s mode: %s",
            best_move,
            mode,
            robot_send_result.error,
        )
        return robot_send_result

    if mode == ROBOT_MODE_HARDWARE:
        game_state['robot_moving'] = False
        game_state['vision_pause_until'] = 0.0
        game_state['vision_pause_reason'] = ''
        game_state['awaiting_physical_baseline'] = False
        game_state['last_robot_move_capture'] = robot_command_is_capture(robot_command)
        game_state['post_robot_guard_until'] = 0.0
        game_state['robot_baseline_match_count'] = 0
        if recognizer is not None:
            reset_dynamic_tracking(recognizer)
            sync_dynamic_baseline_to_game_state(recognizer)
        logger.info(
            "Robot controller confirmed STATE:5,RESULT:1 for %s; red-side vision recognition resumes immediately",
            best_move,
        )

    if mode == ROBOT_MODE_SIMULATION:
        logger.info(
            "AI move applied in simulation mode; vision resumes in %.0fs",
            ROBOT_MOVE_PAUSE_SECONDS,
        )
    else:
        logger.info("AI move applied in hardware mode; vision resumes immediately after controller ACK")
    return robot_send_result


def board_state_to_fen(board_state, turn_color='red'):
    """
    将board_state转换为FEN字符串
    board_state格式: {"col,row": "piece_char"}
    """
    # 初始化10x9的棋盘
    board = [['.' for _ in range(9)] for _ in range(10)]
    
    # 填充棋子
    for pos_key, piece in board_state.items():
        col, row = map(int, pos_key.split(','))
        if 0 <= col < 9 and 0 <= row < 10:
            board[row][col] = piece
    
    # 转换为FEN格式（从黑方底线row=0到红方底线row=9）
    fen_rows = []
    for row in range(10):
        fen_row = ''
        empty_count = 0
        for col in range(9):
            if board[row][col] == '.':
                empty_count += 1
            else:
                if empty_count > 0:
                    fen_row += str(empty_count)
                    empty_count = 0
                fen_row += board[row][col]
        if empty_count > 0:
            fen_row += str(empty_count)
        fen_rows.append(fen_row)
    
    # 组合FEN
    fen_board = '/'.join(fen_rows)
    fen = f"{fen_board} {color_to_turn_char(turn_color)} - - 0 1"
    
    return fen


def serialize_board_state(board_state):
    """Convert tuple-key board states to JSON-safe string-key states."""
    return {f"{k[0]},{k[1]}": v for k, v in (board_state or {}).items()}


def deserialize_board_state(board_state):
    """Convert JSON string-key board states to tuple-key states."""
    converted = {}
    for pos_key, piece in (board_state or {}).items():
        col, row = map(int, pos_key.split(','))
        converted[(col, row)] = piece
    return converted


def is_red_piece(piece):
    """Chinese-chess piece chars use uppercase for red and lowercase for black."""
    return isinstance(piece, str) and piece.isupper()


def sync_dynamic_baseline_to_game_state(recog):
    if recog is not None:
        recog.sync_dynamic_baseline(deserialize_board_state(game_state.get('board_state') or {}))


def reset_dynamic_tracking(recog):
    if recog is not None and hasattr(recog, "reset_dynamic_tracking"):
        recog.reset_dynamic_tracking()


def robot_physical_baseline_status(observed_board):
    expected_board = deserialize_board_state(game_state.get('board_state') or {})
    observed_board = dict(observed_board or {})
    expected_positions = set(expected_board.keys())
    observed_positions = set(observed_board.keys())
    missing = expected_positions - observed_positions
    extra = observed_positions - expected_positions

    if missing or extra:
        game_state['robot_baseline_match_count'] = 0
        return False, (
            "等待机械臂落子后棋盘稳定: "
            f"当前识别{len(observed_positions)}/期望{len(expected_positions)}，"
            f"缺失{len(missing)}，多出{len(extra)}"
        )

    match_count = game_state.get('robot_baseline_match_count', 0) + 1
    game_state['robot_baseline_match_count'] = match_count
    if match_count < ROBOT_BASELINE_MATCH_REQUIRED:
        return False, (
            "等待机械臂落子后棋盘连续稳定: "
            f"{match_count}/{ROBOT_BASELINE_MATCH_REQUIRED}"
        )

    return True, "机械臂落子后的真实棋盘基线已锁定，等待红方走子"


def dynamic_state_payload(event='paused', stable=False, message='', move=None):
    board_state = dict(game_state.get('board_state') or {})
    pause_until = game_state.get('vision_pause_until', 0.0) or 0.0
    pause_remaining = max(0.0, pause_until - time.monotonic())

    return {
        'success': True,
        'event': event,
        'stable': stable,
        'message': message,
        'move': move,
        'board_state': board_state,
        'fen': game_state.get('current_fen'),
        'current_fen': game_state.get('current_fen'),
        'piece_count': len(board_state),
        'move_history': game_state['move_history'],
        'display_history': game_state['display_history'],
        'turn_count': game_state['turn_count'],
        'is_game_running': game_state['is_game_running'],
        'ai_color': game_state['ai_color'],
        'player_color': game_state['player_color'],
        'first_player': game_state['first_player'],
        'robot_mode': game_state.get('robot_mode', ROBOT_MODE_HARDWARE),
        'current_turn': current_turn_color(),
        'vision_paused': pause_remaining > 0,
        'vision_pause_remaining': round(pause_remaining, 1)
    }


@app.route('/')
def index():
    """主页"""
    return render_template('index.html')


@app.route('/api/status')
def get_status():
    """获取游戏状态"""
    return jsonify({
        'success': True,
        'state': game_state
    })


@app.route('/api/robot/status')
def get_robot_status():
    should_probe = request.args.get('probe') in {'1', 'true', 'yes'}
    if not should_probe:
        return jsonify({
            'success': True,
            'connected': None,
            'status': 'not_probed',
            'host': getattr(config, "ROBOT_NETWORK_HOST", "192.168.0.102"),
            'port': getattr(config, "ROBOT_NETWORK_PORT", 8086),
            'error': '',
        })

    result = probe_robot_controller()
    return jsonify({
        'success': True,
        'connected': result.success,
        'status': 'probed',
        'host': getattr(config, "ROBOT_NETWORK_HOST", "192.168.0.102"),
        'port': getattr(config, "ROBOT_NETWORK_PORT", 8086),
        'error': result.error,
    })


@app.route('/api/cameras')
def get_cameras():
    """获取可用的本地摄像头列表"""
    try:
        cameras = list_available_cameras()

        return jsonify({
            'success': True,
            'cameras': cameras,
            'current_camera_index': current_camera_index,
            **camera_source_info()
        })
    except Exception as e:
        logger.error(f"获取摄像头列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


def camera_request_kwargs(data=None):
    data = data or {}
    camera_source = data.get('camera_source') or request.args.get('camera_source')
    camera_url = data.get('camera_url') or request.args.get('camera_url')

    if camera_url:
        return {'camera_url': camera_url}
    if camera_source:
        return {'camera_source': camera_source}
    if 'camera_index' in data:
        return {'camera_index': data.get('camera_index')}
    if 'camera_index' in request.args:
        return {'camera_index': request.args.get('camera_index')}
    return {}


@app.route('/api/network_camera/connect', methods=['POST'])
def connect_network_camera():
    """Register and test a LAN network camera URL."""
    global current_network_camera_url, current_camera_source

    try:
        data = request.json or {}
        url = (data.get('url') or data.get('camera_url') or '').strip()
        try:
            source = normalize_camera_source(url)
        except ValueError:
            return jsonify({'success': False, 'error': '网络摄像头URL必须以 http://、https://、rtsp:// 或 rtmp:// 开头'})
        if not isinstance(source, str):
            return jsonify({'success': False, 'error': '网络摄像头URL必须以 http://、https://、rtsp:// 或 rtmp:// 开头'})

        previous_url = current_network_camera_url
        previous_source = current_camera_source
        with camera_lock:
            current_network_camera_url = source
            current_camera_source = source
            recog = get_recognizer(camera_source='network')
            frame = recog.camera_manager.capture_frame()

        if frame is None:
            last_camera_error = getattr(recog.camera_manager, 'last_error', '') or 'no frame returned'
            current_network_camera_url = previous_url
            current_camera_source = previous_source
            if recognizer is not None:
                recognizer.camera_manager.set_source(previous_source)
            return jsonify({
                'success': False,
                'error': '网络摄像头已配置，但未能读取到画面；请检查树莓派URL、同一局域网、防火墙和流格式',
                'detail': last_camera_error,
                **camera_source_info(source)
            })

        return jsonify({
            'success': True,
            'message': '网络摄像头连接成功',
            'width': int(frame.shape[1]),
            'height': int(frame.shape[0]),
            **camera_source_info(source)
        })
    except Exception as e:
        if 'previous_url' in locals():
            current_network_camera_url = previous_url
            current_camera_source = previous_source
        logger.error(f"连接网络摄像头失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/network_camera/status')
def network_camera_status():
    try:
        is_current_network = isinstance(current_camera_source, str)
        is_opened = (
            recognizer is not None and
            recognizer.camera_manager.is_network_source and
            recognizer.camera_manager.is_opened()
        )
        return jsonify({
            'success': True,
            'configured': bool(current_network_camera_url),
            'active': is_current_network,
            'camera_opened': is_opened,
            **camera_source_info()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/network_camera/disconnect', methods=['POST'])
def disconnect_network_camera():
    global current_camera_source

    try:
        with camera_lock:
            if recognizer is not None and recognizer.camera_manager.is_network_source:
                recognizer.camera_manager.stop()
            current_camera_source = current_camera_index

        return jsonify({
            'success': True,
            'message': '已切回本地摄像头',
            **camera_source_info(current_camera_index)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


def generate_camera_stream(camera_source, stream_token):
    """Yield MJPEG frames from the selected local or network camera."""
    frame_delay = 1.0 / 30.0
    source_label = str(camera_source)
    while True:
        if stream_token != active_stream_token:
            break

        try:
            with camera_lock:
                if stream_token != active_stream_token:
                    break
                recog = get_recognizer(camera_source=camera_source)
                frame = recog.camera_manager.capture_frame()

            if frame is None:
                placeholder = create_stream_unavailable_frame(f'Camera {source_label} has no frame')
                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' +
                    placeholder +
                    b'\r\n'
                )
                time.sleep(0.15)
                continue

            ok, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
            if not ok:
                time.sleep(0.02)
                continue

            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' +
                buffer.tobytes() +
                b'\r\n'
            )
            time.sleep(frame_delay)
        except GeneratorExit:
            break
        except Exception as e:
            logger.error(f"视频流读取失败: {e}")
            time.sleep(0.5)


def create_stream_unavailable_frame(message='Camera stream unavailable'):
    """Create a small JPEG placeholder for stream startup failures."""
    frame = np.zeros((360, 640, 3), dtype=np.uint8)
    frame[:] = (245, 245, 245)
    cv2.putText(frame, message, (40, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (60, 60, 60), 2)
    ok, buffer = cv2.imencode('.jpg', frame)
    return buffer.tobytes() if ok else b''


@app.route('/api/camera/stream')
def camera_stream():
    """本地或网络摄像头实时视频流"""
    global active_stream_token

    camera_source = resolve_camera_source(**camera_request_kwargs())
    active_stream_token += 1
    stream_token = active_stream_token

    try:
        with camera_lock:
            recog = get_recognizer(camera_source=camera_source)
            camera_opened = recog.camera_manager.is_opened()
            if not camera_opened:
                recog.camera_manager.start()
                camera_opened = True

        if not camera_opened:
            raise RuntimeError(f"摄像头源 {camera_source} 无法打开")
    except Exception as e:
        logger.error(f"启动视频流失败: {e}")
        placeholder = create_stream_unavailable_frame()

        def unavailable_stream():
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' +
                placeholder +
                b'\r\n'
            )

        return Response(
            unavailable_stream(),
            mimetype='multipart/x-mixed-replace; boundary=frame'
        )

    return Response(
        generate_camera_stream(camera_source, stream_token),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/api/camera/frame')
def camera_frame():
    """Return one JPEG frame. This is more robust than MJPEG in some browsers."""
    camera_source = resolve_camera_source(**camera_request_kwargs())
    try:
        with camera_lock:
            recog = get_recognizer(camera_source=camera_source)
            frame = recog.camera_manager.capture_frame()

        if frame is None:
            frame_bytes = create_stream_unavailable_frame(f'Camera {camera_source} has no frame')
            return Response(frame_bytes, mimetype='image/jpeg', status=503)

        ok, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ok:
            frame_bytes = create_stream_unavailable_frame('JPEG encode failed')
            return Response(frame_bytes, mimetype='image/jpeg', status=500)

        response = Response(buffer.tobytes(), mimetype='image/jpeg')
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response
    except Exception as e:
        logger.error(f"读取单帧失败: {e}", exc_info=True)
        frame_bytes = create_stream_unavailable_frame(str(e)[:60])
        return Response(frame_bytes, mimetype='image/jpeg', status=500)


@app.route('/api/capture', methods=['POST'])
def capture_image():
    """捕获摄像头图像"""
    try:
        data = request.json or {}
        camera_source = resolve_camera_source(**camera_request_kwargs(data))
        
        with camera_lock:
            recog = get_recognizer(camera_source=camera_source)
            frame = recog.camera_manager.capture_frame()
        
        if frame is None:
            return jsonify({'success': False, 'error': '无法捕获图像'})
        
        # 转换为base64
        _, buffer = cv2.imencode('.jpg', frame)
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            'success': True,
            'image': image_base64,
            **camera_source_info(camera_source),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"捕获图像失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/recognize', methods=['POST'])
def recognize_board():
    """识别棋盘状态"""
    try:
        data = request.json or {}
        image_data = data.get('image')
        camera_source = resolve_camera_source(**camera_request_kwargs(data))
        
        recog = get_recognizer(camera_source=camera_source)
        
        if image_data:
            # 从base64解码图像
            image_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            # 直接从摄像头捕获
            with camera_lock:
                image = recog.camera_manager.capture_frame()
        
        if image is None:
            return jsonify({'success': False, 'error': '无法获取图像'})
        
        # 识别棋盘。这里只跑一次模型，再由识别结果生成 FEN，避免重复推理造成卡顿。
        board_state = recog.recognize_board(image)
        
        if board_state is None:
            return jsonify({'success': False, 'error': '识别失败'})
        
        # 转换board_state的key为字符串（JSON不支持元组）
        # value保留棋子字符（大写=红方，小写=黑方）
        board_state_str_keys = {f"{k[0]},{k[1]}": v for k, v in board_state.items()}
        fen = board_state_to_fen(board_state_str_keys, current_turn_color())
        
        # 更新游戏状态
        if fen:
            game_state['current_fen'] = fen
        game_state['board_state'] = board_state_str_keys
        
        return jsonify({
            'success': True,
            'board_state': board_state_str_keys,
            'fen': fen,
            'piece_count': len(board_state)
        })
        
    except Exception as e:
        logger.error(f"识别棋盘失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/recognize/dynamic', methods=['POST'])
def recognize_dynamic_board():
    """动态识别摄像头画面，并在画面稳定后返回识别事件。"""
    try:
        data = request.json or {}
        camera_source = resolve_camera_source(**camera_request_kwargs(data))

        if game_state['is_game_running']:
            now = time.monotonic()
            pause_until = game_state.get('vision_pause_until', 0.0) or 0.0
            waiting_for_robot_ack = game_state.get('robot_moving') and game_state.get('ai_thinking')
            if (pause_until and now < pause_until) or waiting_for_robot_ack:
                if recognizer is not None and not game_state.get('awaiting_physical_baseline'):
                    sync_dynamic_baseline_to_game_state(recognizer)
                remaining = max(0.0, pause_until - now)
                return jsonify(dynamic_state_payload(
                    event='paused',
                    stable=False,
                    message=f'AI/robot move pause, resume red recognition in {remaining:.1f}s'
                ))

        recog = get_recognizer(camera_source=camera_source)
        if game_state['is_game_running']:
            now = time.monotonic()
            pause_until = game_state.get('vision_pause_until', 0.0) or 0.0
            if pause_until and now >= pause_until:
                game_state['vision_pause_until'] = 0.0
                game_state['vision_pause_reason'] = ''
                game_state['robot_moving'] = False
                if not game_state.get('awaiting_physical_baseline'):
                    sync_dynamic_baseline_to_game_state(recog)
                logger.info("Robot move pause elapsed; red-side vision recognition resumed")

            if (
                getattr(recog.dynamic_tracker, 'saved_board', None) is None
                and not game_state.get('awaiting_physical_baseline')
            ):
                sync_dynamic_baseline_to_game_state(recog)

        with camera_lock:
            frame = recog.camera_manager.capture_frame()

        if frame is None:
            return jsonify({'success': False, 'error': '无法获取图像'})

        result = recog.recognize_dynamic_frame(frame)

        raw_board_state = result.get('board_state') or {}
        board_state = serialize_board_state(raw_board_state)
        response_board_state = dict(game_state.get('board_state') or {}) if game_state['is_game_running'] else board_state
        recognized_fen = board_state_to_fen(board_state, current_turn_color()) if board_state else None

        if game_state['is_game_running'] and game_state.get('awaiting_physical_baseline'):
            if result.get('stable') and raw_board_state:
                baseline_ready, baseline_message = robot_physical_baseline_status(raw_board_state)
                if baseline_ready:
                    sync_dynamic_baseline_to_game_state(recog)
                    game_state['awaiting_physical_baseline'] = False
                    game_state['robot_baseline_match_count'] = 0
                    game_state['post_robot_guard_until'] = time.monotonic() + ROBOT_POST_BASELINE_GUARD_SECONDS
                    result['event'] = 'robot_board_confirmed'
                    result['stable'] = True
                    result['move'] = None
                    result['message'] = baseline_message
                    logger.info("Robot physical board baseline locked after AI move")
                else:
                    reset_dynamic_tracking(recog)
                    result['event'] = 'robot_board_waiting'
                    result['stable'] = False
                    result['move'] = None
                    result['message'] = baseline_message
                    logger.info(baseline_message)
            return jsonify({
                'success': True,
                'event': result.get('event'),
                'stable': result.get('stable'),
                'message': result.get('message'),
                'move': result.get('move'),
                'board_state': response_board_state,
                'fen': game_state['current_fen'],
                'current_fen': game_state['current_fen'],
                'piece_count': len(response_board_state),
                'recognized_piece_count': len(board_state),
                'move_history': game_state['move_history'],
                'display_history': game_state['display_history'],
                'turn_count': game_state['turn_count'],
                'is_game_running': game_state['is_game_running'],
                'ai_color': game_state['ai_color'],
                'player_color': game_state['player_color'],
                'first_player': game_state['first_player'],
                'robot_mode': game_state.get('robot_mode', ROBOT_MODE_HARDWARE),
                'current_turn': current_turn_color(),
                'vision_paused': not result.get('stable'),
                'vision_pause_remaining': 0.0
            })

        guard_until = game_state.get('post_robot_guard_until', 0.0) or 0.0
        if game_state['is_game_running'] and guard_until:
            now = time.monotonic()
            if now < guard_until:
                if result.get('event') == 'move':
                    sync_dynamic_baseline_to_game_state(recog)
                remaining = max(0.0, guard_until - now)
                return jsonify({
                    'success': True,
                    'event': 'robot_settling',
                    'stable': False,
                    'message': f'机械臂落子保护中，{remaining:.1f}s 后再识别红方走子',
                    'move': None,
                    'board_state': response_board_state,
                    'fen': game_state['current_fen'],
                    'current_fen': game_state['current_fen'],
                    'piece_count': len(response_board_state),
                    'recognized_piece_count': len(board_state),
                    'move_history': game_state['move_history'],
                    'display_history': game_state['display_history'],
                    'turn_count': game_state['turn_count'],
                    'is_game_running': game_state['is_game_running'],
                    'ai_color': game_state['ai_color'],
                    'player_color': game_state['player_color'],
                    'first_player': game_state['first_player'],
                    'robot_mode': game_state.get('robot_mode', ROBOT_MODE_HARDWARE),
                    'current_turn': current_turn_color(),
                    'vision_paused': True,
                    'vision_pause_remaining': round(remaining, 1)
                })
            game_state['post_robot_guard_until'] = 0.0

        if result.get('stable') and board_state:
            if not game_state['is_game_running']:
                game_state['board_state'] = board_state
                response_board_state = board_state
                if recognized_fen:
                    game_state['current_fen'] = recognized_fen
            
            # 如果是走子事件，在后端同步更新历史和回合
            if game_state['is_game_running'] and result.get('event') == 'move' and result.get('move'):
                from_pos = (result['move']['from']['col'], result['move']['from']['row'])
                to_pos = (result['move']['to']['col'], result['move']['to']['row'])
                move_code = points_to_uci(from_pos, to_pos)
                moved_piece = result['move'].get('piece')
                result['move']['code'] = move_code
                result['move']['robot_command'] = uci_to_robot_command(move_code, game_state['board_state'])

                if current_turn_color() != 'red':
                    result['move']['source'] = 'ignored_non_player_turn'
                    sync_dynamic_baseline_to_game_state(recog)
                    logger.info(f"Ignored dynamic move outside red turn: {move_code}")
                elif not is_red_piece(moved_piece):
                    result['move']['source'] = 'ignored_non_red_piece'
                    sync_dynamic_baseline_to_game_state(recog)
                    logger.info(f"Ignored non-red dynamic move: {move_code}, piece={moved_piece}")
                elif is_duplicate_player_move(move_code):
                    result['move']['source'] = 'duplicate'
                    sync_dynamic_baseline_to_game_state(recog)
                    logger.info(f"Ignored duplicate player dynamic move: {move_code}")
                else:
                    result['move']['source'] = 'player'
                    game_state['board_state'] = board_state
                    response_board_state = dict(game_state['board_state'])
                    game_state['move_history'].append(move_code)
                    game_state['display_history'].append(f"红方 {move_code}")
                    game_state['turn_count'] += 1
                    game_state['last_player_move'] = move_code
                    update_current_fen()
                    logger.info(f"后端同步走子: {move_code}, 当前回合: {game_state['turn_count']}")
        return jsonify({
            'success': True,
            'event': result.get('event'),
            'stable': result.get('stable'),
            'message': result.get('message'),
            'move': result.get('move'),
            'board_state': response_board_state,
            'fen': recognized_fen if not game_state['is_game_running'] else game_state['current_fen'],
            'current_fen': game_state['current_fen'],
            'piece_count': len(response_board_state),
            'recognized_piece_count': len(board_state),
            'move_history': game_state['move_history'],
            'display_history': game_state['display_history'],
            'turn_count': game_state['turn_count'],
            'is_game_running': game_state['is_game_running'],
            'ai_color': game_state['ai_color'],
            'player_color': game_state['player_color'],
            'first_player': game_state['first_player'],
            'robot_mode': game_state.get('robot_mode', ROBOT_MODE_HARDWARE),
            'current_turn': current_turn_color(),
            'vision_paused': False,
            'vision_pause_remaining': 0.0
        })

    except Exception as e:
        logger.error(f"动态识别失败: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/ai_move', methods=['POST'])
def get_ai_move():
    """开始AI思考任务（异步）"""
    try:
        if game_state['ai_thinking']:
            return jsonify({'success': False, 'error': 'AI已经在思考中'})

        # 获取请求中的AI颜色设置（如果没有，使用全局默认）
        ai_color = 'black'
        game_state['ai_color'] = ai_color
        game_state['player_color'] = opposite_color(ai_color)
        
        # 判断当前是谁的回合（从 FEN 码判断：'w'=红方，'b'=黑方）
        fen_parts = game_state['current_fen'].split()
        current_turn_char = fen_parts[1] if len(fen_parts) > 1 else 'w'
        
        # 将 'red'/'black' 映射到 'w'/'b'
        ai_color_char = color_to_turn_char(ai_color)
        
        if current_turn_char != ai_color_char:
            turn_name = "红方" if current_turn_char == 'w' else "黑方"
            ai_name = "红方" if ai_color_char == 'w' else "黑方"
            return jsonify({
                'success': False,
                'error': f"当前是 {turn_name} 回合，AI 执 {ai_name}，尚未到 AI 走棋"
            })
        
        # 获取请求参数
        depth = request.json.get('depth', 8) if request.is_json else 8
        
        game_state['ai_thinking'] = True
        game_state['ai_analysis'] = {
            'depth': 0,
            'score': 0,
            'pv': '',
            'best_move': None,
            'ai_move_token': None,
            'robot_command': None,
            'robot_mode': current_robot_mode(),
            'robot_send_success': None,
            'ai_move_applied': False,
        }
        
        # 在后台线程启动思考
        def think_task(depth_to_use):
            try:
                engine = get_ai_engine()
                if not engine.is_ready or engine.process is None:
                    logger.error("AI引擎尚未就绪或未成功启动（请检查Pikafish文件是否存在）。")
                    return
                    
                # 同步位置
                engine.set_position(game_state['initial_fen'], game_state['move_history'])
                
                # 启动分析（使用内部循环获取实时输出）
                depth = depth_to_use
                
                # 重新实现一个能更新状态的分析过程
                engine._send_command(f"go depth {depth}")
                
                start_time = time.time()
                while time.time() - start_time < 30: # 最多等待30秒
                    line = engine.process.stdout.readline().strip()
                    if not line:
                        continue
                    
                    if line.startswith("info"):
                        # 解析 info 行更新分析状态
                        parts = line.split()
                        if "depth" in parts:
                            game_state['ai_analysis']['depth'] = int(parts[parts.index("depth")+1])
                        if "cp" in parts:
                            game_state['ai_analysis']['score'] = int(parts[parts.index("cp")+1])
                        if "pv" in parts:
                            pv_idx = line.find(" pv ")
                            game_state['ai_analysis']['pv'] = line[pv_idx+4:].strip()
                        if "nodes" in parts:
                            game_state['ai_analysis']['nodes'] = int(parts[parts.index("nodes")+1])
                            
                    if line.startswith("bestmove"):
                        best_move = line.split()[1]
                        game_state['ai_analysis']['best_move'] = best_move
                        if best_move != "(none)":
                            apply_ai_best_move(best_move)
                        break
            except Exception as e:
                logger.error(f"后台思考线程出错: {e}")
            finally:
                game_state['ai_thinking'] = False

        thread = threading.Thread(target=think_task, args=(depth,))
        thread.start()
        
        return jsonify({
            'success': True,
            'message': 'AI思考已启动'
        })
        
    except Exception as e:
        logger.error(f"启动AI思考失败: {e}")
        game_state['ai_thinking'] = False
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/ai_status')
def get_ai_status():
    """获取AI思考状态和分析结果"""
    return jsonify({
        'success': True,
        'ai_thinking': game_state['ai_thinking'],
        'analysis': game_state['ai_analysis'],
        'move_history': game_state['move_history'],
        'display_history': game_state['display_history'],
        'turn_count': game_state['turn_count'],
        'current_fen': game_state['current_fen'],
        'board_state': game_state['board_state'],
        'piece_count': len(game_state['board_state']),
        'robot_mode': game_state.get('robot_mode', ROBOT_MODE_HARDWARE),
        'vision_paused': (game_state.get('vision_pause_until', 0.0) or 0.0) > time.monotonic(),
        'vision_pause_remaining': round(max(0.0, (game_state.get('vision_pause_until', 0.0) or 0.0) - time.monotonic()), 1)
    })


@app.route('/api/player_move', methods=['POST'])
def player_move():
    """处理玩家走法"""
    try:
        data = request.json
        uci_move = data.get('move')
        
        if not uci_move:
            return jsonify({'success': False, 'error': '缺少走法参数'})
        
        if current_turn_color() != game_state.get('player_color', 'red'):
            turn_name = "红方" if current_turn_color() == 'red' else "黑方"
            return jsonify({
                'success': False,
                'error': f'当前是{turn_name}回合，尚未轮到玩家走棋'
            })
        
        logger.info(f"玩家走法: {uci_move} (回合 {game_state['turn_count']})")
        
        # 添加到走法历史
        game_state['move_history'].append(uci_move)
        game_state['display_history'].append(f"红方 {uci_move}")
        game_state['turn_count'] += 1  # 回合+1
        game_state['last_player_move'] = uci_move
        
        # 更新当前FEN
        update_current_fen()
        
        return jsonify({
            'success': True,
            'move': uci_move,
            'fen': game_state['current_fen'],  # 返回当前FEN
            'display_history': game_state['display_history'],
            'is_player_turn': False,  # 玩家走完轮到AI
            'turn_count': game_state['turn_count']
        })
        
    except Exception as e:
        logger.error(f"处理玩家走法失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/simulate_robot', methods=['POST'])
def simulate_robot_move():
    """模拟机械臂移动（执行AI走法）"""
    try:
        data = request.json
        uci_move = data.get('move')
        
        if not uci_move:
            return jsonify({'success': False, 'error': '缺少走法参数'})
        
        game_state['robot_moving'] = True
        logger.info(f"机械臂开始执行AI走法: {uci_move}")
        
        robot = get_robot_controller()
        
        # 模拟执行UCI走法
        board_origin = (0, 0, 0)
        square_size_mm = 50.0
        
        success = robot.execute_uci_move(uci_move, board_origin, square_size_mm)
        
        game_state['robot_moving'] = False
        
        if success:
            logger.info(f"机械臂完成AI走法: {uci_move}")
            return jsonify({
                'success': True,
                'move': uci_move,
                'message': '机械臂已执行AI走法',
                'board_state': game_state['board_state']
            })
        else:
            return jsonify({
                'success': False,
                'error': '机械臂移动失败'
            })
        
    except Exception as e:
        logger.error(f"模拟机械臂失败: {e}")
        game_state['robot_moving'] = False
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/game/start', methods=['POST'])
def start_game():
    """开始新游戏"""
    try:
        data = request.json or {}
        try:
            robot_mode = normalize_robot_mode(data.get('mode', ROBOT_MODE_HARDWARE))
        except ValueError as exc:
            return jsonify({'success': False, 'error': str(exc)}), 400
        use_recognized_board = data.get('use_recognized_board', False)
        board_state = data.get('board_state', {})
        ai_color = 'black'
        first_player = 'red'

        game_state['is_game_running'] = False
        game_state['robot_mode'] = robot_mode
        game_state['robot_moving'] = robot_mode == ROBOT_MODE_HARDWARE
        game_state['vision_pause_until'] = 0.0
        game_state['vision_pause_reason'] = 'homing' if robot_mode == ROBOT_MODE_HARDWARE else ''
        game_state['awaiting_physical_baseline'] = False
        game_state['post_robot_guard_until'] = 0.0
        game_state['last_robot_move_capture'] = False
        game_state['robot_baseline_match_count'] = 0

        homing_result = None
        if robot_mode == ROBOT_MODE_HARDWARE:
            homing_result = send_homing_command_to_controller()
            if not homing_result.success or not homing_result.homing_acknowledged:
                game_state['robot_moving'] = False
                game_state['vision_pause_reason'] = ''
                return jsonify({
                    'success': False,
                    'error': homing_result.error or 'STM32 homing acknowledgement missing',
                    'homing_command': homing_result.command_text,
                    'homing_response': homing_result.response,
                    'homing_acknowledged': False,
                    'robot_mode': robot_mode,
                }), 503
        
        game_state['move_history'] = []
        game_state['display_history'] = []
        game_state['pending_ai_move'] = None
        game_state['last_player_move'] = None
        game_state['last_ai_command_token'] = None
        game_state['awaiting_physical_baseline'] = False
        game_state['post_robot_guard_until'] = 0.0
        game_state['last_robot_move_capture'] = False
        game_state['robot_baseline_match_count'] = 0
        game_state['robot_moving'] = False
        game_state['vision_pause_until'] = 0.0
        game_state['vision_pause_reason'] = ''
        game_state['is_game_running'] = True
        game_state['turn_count'] = 0  # 重置回合计数
        game_state['ai_color'] = ai_color
        game_state['player_color'] = opposite_color(ai_color)
        game_state['first_player'] = first_player
        
        # 重置AI引擎
        engine = get_ai_engine()
        engine.reset_game()
        
        logger.info("使用标准初始布局作为识别基准")
        game_state['initial_fen'] = apply_turn_to_fen(STANDARD_INITIAL_FEN, first_player)
        game_state['current_fen'] = game_state['initial_fen']
        game_state['board_state'] = dict(STANDARD_INITIAL_BOARD)

        if recognizer is not None:
            recognizer.sync_dynamic_baseline(deserialize_board_state(game_state['board_state']))
        
        logger.info("游戏已开始")
        
        return jsonify({
            'success': True,
            'message': '游戏已开始',
            'fen': game_state['initial_fen'],
            'current_fen': game_state['current_fen'],
            'use_recognized_board': True,
            'board_state': game_state['board_state'],
            'ai_color': game_state['ai_color'],
            'player_color': game_state['player_color'],
            'first_player': game_state['first_player'],
            'current_turn': current_turn_color(),
            'robot_mode': game_state['robot_mode'],
            'homing_command': homing_result.command_text if homing_result else '',
            'homing_response': homing_result.response if homing_result else '',
            'homing_acknowledged': bool(homing_result.homing_acknowledged) if homing_result else False,
        })
        
    except Exception as e:
        logger.error(f"开始游戏失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/game/reset', methods=['POST'])
def reset_game():
    """重置游戏"""
    try:
        game_state['current_fen'] = 'rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1'
        game_state['move_history'] = []
        game_state['display_history'] = []
        game_state['pending_ai_move'] = None
        game_state['robot_moving'] = False
        game_state['vision_pause_until'] = 0.0
        game_state['vision_pause_reason'] = ''
        game_state['is_game_running'] = False
        game_state['board_state'] = {}
        game_state['ai_color'] = 'black'
        game_state['player_color'] = 'red'
        game_state['first_player'] = 'red'
        game_state['robot_mode'] = ROBOT_MODE_HARDWARE
        game_state['turn_count'] = 0
        game_state['last_player_move'] = None
        game_state['last_ai_command_token'] = None
        game_state['awaiting_physical_baseline'] = False
        game_state['post_robot_guard_until'] = 0.0
        game_state['last_robot_move_capture'] = False
        game_state['robot_baseline_match_count'] = 0

        if recognizer is not None:
            recognizer.reset_dynamic_tracking()
        
        return jsonify({
            'success': True,
            'message': '游戏已重置'
        })
        
    except Exception as e:
        logger.error(f"重置游戏失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/test/camera')
def test_camera():
    """测试摄像头"""
    try:
        recog = get_recognizer()
        
        # 如果摄像头未打开，尝试重新启动
        if not recog.camera_manager.is_opened():
            logger.info("摄像头未打开，尝试重新启动...")
            if not recog.start():
                return jsonify({'success': False, 'error': '摄像头启动失败'})
        
        frame = recog.camera_manager.capture_frame()
        
        if frame is None:
            return jsonify({'success': False, 'error': '无法捕获图像'})
        
        _, buffer = cv2.imencode('.jpg', frame)
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            'success': True,
            'image': image_base64
        })
        
    except Exception as e:
        logger.error(f"测试摄像头失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/camera/start', methods=['POST'])
def start_camera():
    """启动摄像头"""
    try:
        data = request.json or {}
        camera_source = resolve_camera_source(**camera_request_kwargs(data))
        with camera_lock:
            recog = get_recognizer(camera_source=camera_source)
        
            if recog.camera_manager.is_opened():
                return jsonify({
                    'success': True,
                    **camera_source_info(camera_source),
                    'message': '摄像头已经打开'
                })

            started = recog.start()

        if started:
            logger.info("摄像头启动成功")
            return jsonify({
                'success': True,
                **camera_source_info(camera_source),
                'message': '摄像头已启动'
            })

        return jsonify({
            'success': False,
            'error': '摄像头启动失败，请检查设备'
        })
    except Exception as e:
        logger.error(f"启动摄像头失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/camera/status')
def camera_status():
    """获取摄像头状态"""
    try:
        camera_source = resolve_camera_source(**camera_request_kwargs())
        is_opened = (
            recognizer is not None and
            recognizer.camera_manager.camera_source == camera_source and
            recognizer.camera_manager.is_opened()
        )
        
        return jsonify({
            'success': True,
            'camera_opened': is_opened,
            **camera_source_info(camera_source),
            'message': '摄像头已打开' if is_opened else '摄像头未打开'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    prompt_startup_parameter_overrides()
    print("=" * 60)
    print("Web仿真环境启动")
    print("=" * 60)
    print("访问地址: http://localhost:5000")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
