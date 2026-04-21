"""
Web仿真环境 - Flask后端应用
提供棋盘识别、AI对弈、机械臂模拟的Web接口
"""

import os
import sys
import logging
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
from ai import AIEngine
from robot import RobotController

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
    'is_game_running': False,
    'player_color': 'red',  # 玩家执红先行
    'ai_color': 'black',    # AI执黑后手
    'ai_thinking': False,
    'robot_moving': False,
    'board_state': {},  # 当前棋盘状态 {"col,row": "piece_char"}
    'turn_count': 0,  # 回合计数（偶数=红方，奇数=黑方）
}

# 初始化组件（懒加载）
recognizer = None
ai_engine = None
robot_controller = None


def get_recognizer():
    """获取棋盘识别器实例"""
    global recognizer
    if recognizer is None:
        recognizer = BoardRecognizer()
        # 自动启动摄像头
        if not recognizer.start():
            logger.warning("摄像头启动失败，请检查摄像头是否可用")
        else:
            logger.info("摄像头已启动")
    return recognizer


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


def update_current_fen():
    """根据走法历史更新当前FEN"""
    moves = game_state['move_history']
    
    # 解析初始FEN
    fen_parts = game_state['initial_fen'].split()
    
    if len(fen_parts) >= 6:
        # 根据走法数量切换回合
        if len(moves) % 2 == 0:
            fen_parts[1] = 'w'  # 红方
        else:
            fen_parts[1] = 'b'  # 黑方
        
        # 更新步数计数器（每两步增加1）
        move_number = int(fen_parts[5])
        fen_parts[5] = str(move_number + len(moves) // 2)
        
        game_state['current_fen'] = ' '.join(fen_parts)
        logger.info(f"更新FEN: {game_state['current_fen']}")


def board_state_to_fen(board_state):
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
    fen = f"{fen_board} w - - 0 1"  # 默认红方先手
    
    return fen


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


@app.route('/api/capture', methods=['POST'])
def capture_image():
    """捕获摄像头图像"""
    try:
        data = request.json
        camera_index = data.get('camera_index', 0)
        
        recog = get_recognizer()
        frame = recog.camera_manager.capture_frame()
        
        if frame is None:
            return jsonify({'success': False, 'error': '无法捕获图像'})
        
        # 转换为base64
        _, buffer = cv2.imencode('.jpg', frame)
        image_base64 = base64.b64encode(buffer).decode('utf-8')
        
        return jsonify({
            'success': True,
            'image': image_base64,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"捕获图像失败: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/recognize', methods=['POST'])
def recognize_board():
    """识别棋盘状态"""
    try:
        data = request.json
        image_data = data.get('image')
        
        recog = get_recognizer()
        
        if image_data:
            # 从base64解码图像
            image_bytes = base64.b64decode(image_data)
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        else:
            # 直接从摄像头捕获
            image = recog.camera_manager.capture_frame()
        
        if image is None:
            return jsonify({'success': False, 'error': '无法获取图像'})
        
        # 识别棋盘
        board_state = recog.recognize_board(image)
        fen = recog.get_fen(image)
        
        if board_state is None:
            return jsonify({'success': False, 'error': '识别失败'})
        
        # 转换board_state的key为字符串（JSON不支持元组）
        # value保留棋子字符（大写=红方，小写=黑方）
        board_state_str_keys = {f"{k[0]},{k[1]}": v for k, v in board_state.items()}
        
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


@app.route('/api/ai_move', methods=['POST'])
def get_ai_move():
    """获取AI走法（黑方后手）"""
    try:
        # 检查是否轮到AI（奇数回合=黑方）
        if game_state['turn_count'] % 2 == 0:
            return jsonify({
                'success': False,
                'error': '当前是红方回合，请玩家先走棋'
            })
        
        logger.info(f"AI思考中 (回合 {game_state['turn_count']})")
        logger.info(f"走法历史: {game_state['move_history']}")
        game_state['ai_thinking'] = True
        
        engine = get_ai_engine()
        
        # 同步走法历史到AI引擎内部
        engine.move_history = list(game_state['move_history'])
        logger.info(f"已同步走法历史到引擎: {engine.move_history}")
        
        # 同步current_fen（重要！）
        engine.current_fen = game_state['initial_fen']
        logger.info(f"已设置引擎current_fen: {engine.current_fen}")
        
        # 设置位置（使用初始FEN + 走法历史）
        # 注意：走法历史的数量决定了当前轮到哪一方
        # 偶数个走法 = 轮到红方，奇数个走法 = 轮到黑方
        engine.set_position(
            game_state['initial_fen'],
            game_state['move_history']
        )
        logger.info(f"已设置位置: FEN={game_state['initial_fen']}, moves={game_state['move_history']}")
        logger.info(f"走法数量: {len(game_state['move_history'])}, 应该轮到: {'红方' if len(game_state['move_history']) % 2 == 0 else '黑方'}")
        
        # 获取最佳走法
        best_move = engine.get_best_move(depth=15)
        
        game_state['ai_thinking'] = False
        
        if best_move:
            logger.info(f"AI走法: {best_move}")
            
            # 添加到历史
            game_state['move_history'].append(best_move)
            game_state['turn_count'] += 1  # 回合+1
            
            # 更新当前FEN
            update_current_fen()
            
            # 分析局面（使用当前FEN和走法历史）
            analysis = engine.analyze_position(
                game_state['current_fen'], 
                think_time=1.0,
                moves=list(game_state['move_history'])
            )
            
            return jsonify({
                'success': True,
                'move': best_move,
                'analysis': analysis,
                'fen': game_state['current_fen'],  # 返回当前FEN
                'is_player_turn': True,  # AI走完轮到玩家
                'turn_count': game_state['turn_count']
            })
        else:
            return jsonify({
                'success': False,
                'error': 'AI未能找到走法'
            })
        
    except Exception as e:
        logger.error(f"获取AI走法失败: {e}")
        game_state['ai_thinking'] = False
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/player_move', methods=['POST'])
def player_move():
    """处理玩家走法（红方）"""
    try:
        data = request.json
        uci_move = data.get('move')
        
        if not uci_move:
            return jsonify({'success': False, 'error': '缺少走法参数'})
        
        # 检查是否轮到玩家（偶数回合=红方）
        if game_state['turn_count'] % 2 == 1:
            return jsonify({
                'success': False,
                'error': '当前是黑方回合，请等待AI走棋'
            })
        
        logger.info(f"玩家走法: {uci_move} (回合 {game_state['turn_count']})")
        
        # 添加到走法历史
        game_state['move_history'].append(uci_move)
        game_state['turn_count'] += 1  # 回合+1
        
        # 更新当前FEN
        update_current_fen()
        
        return jsonify({
            'success': True,
            'move': uci_move,
            'fen': game_state['current_fen'],  # 返回当前FEN
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
        use_recognized_board = data.get('use_recognized_board', False)
        board_state = data.get('board_state', {})
        
        game_state['move_history'] = []
        game_state['is_game_running'] = True
        game_state['turn_count'] = 0  # 重置回合计数
        
        # 重置AI引擎
        engine = get_ai_engine()
        engine.reset_game()
        
        # 如果有识别的棋盘，生成对应的FEN
        if use_recognized_board and board_state:
            logger.info(f"使用识别的棋盘布局，棋子数量: {len(board_state)}")
            # 将board_state转换为FEN
            initial_fen = board_state_to_fen(board_state)
            game_state['initial_fen'] = initial_fen
            game_state['current_fen'] = initial_fen
            logger.info(f"生成的FEN: {initial_fen}")
        else:
            logger.info("使用标准初始布局")
            game_state['initial_fen'] = 'rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1'
            game_state['current_fen'] = game_state['initial_fen']
        
        logger.info("游戏已开始")
        
        return jsonify({
            'success': True,
            'message': '游戏已开始 - 玩家执红先行，AI执黑后手',
            'fen': game_state['initial_fen'],
            'use_recognized_board': use_recognized_board,
            'board_state': board_state if use_recognized_board else None
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
        game_state['is_game_running'] = False
        
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
        recog = get_recognizer()
        
        if recog.camera_manager.is_opened():
            return jsonify({
                'success': True,
                'message': '摄像头已经打开'
            })
        
        if recog.start():
            logger.info("摄像头启动成功")
            return jsonify({
                'success': True,
                'message': '摄像头已启动'
            })
        else:
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
        recog = get_recognizer()
        is_opened = recog.camera_manager.is_opened()
        
        return jsonify({
            'success': True,
            'camera_opened': is_opened,
            'message': '摄像头已打开' if is_opened else '摄像头未打开'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


if __name__ == '__main__':
    print("=" * 60)
    print("Web仿真环境启动")
    print("=" * 60)
    print("访问地址: http://localhost:5000")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
