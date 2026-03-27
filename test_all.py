"""
简单测试脚本 - 快速验证各个模块功能
"""

import sys
import logging


def setup_logging():
    """设置日志"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )


def test_utils():
    """测试工具函数"""
    print("\n" + "="*50)
    print("测试工具函数")
    print("="*50)
    
    from utils import FENUtils, CoordinateUtils, MoveNotationUtils, BoardUtils
    
    # 测试 FEN 解析
    print("\n1. FEN 解析测试")
    fen = FENUtils.START_FEN
    print(f"初始 FEN: {fen}")
    
    board = FENUtils.parse_fen(fen)
    print(f"解析为棋盘数组：{len(board)}x{len(board[0])}")
    
    # 打印初始棋盘
    print("\n初始棋盘:")
    BoardUtils.print_board(board)
    
    # 测试坐标转换
    print("\n2. 坐标转换测试")
    uci_square = "e3"
    row, col = CoordinateUtils.uci_to_indices(uci_square)
    print(f"UCI 格子 {uci_square} -> 行列索引 ({row}, {col})")
    
    back_to_uci = CoordinateUtils.indices_to_uci(row, col)
    print(f"行列索引 ({row}, {col}) -> UCI 格子 {back_to_uci}")
    
    # 测试走法解析
    print("\n3. UCI 走法解析测试")
    uci_move = "h3e3"
    (from_row, from_col), (to_row, to_col) = CoordinateUtils.parse_uci_move(uci_move)
    print(f"走法 {uci_move}: ({from_row},{from_col}) -> ({to_row},{to_col})")
    
    # 测试记谱转换
    print("\n4. 记谱法转换测试")
    wxf = MoveNotationUtils.uci_to_wxf(uci_move, fen)
    chinese = MoveNotationUtils.uci_to_chinese(uci_move, fen)
    print(f"UCI: {uci_move}")
    print(f"WXF: {wxf}")
    print(f"中文：{chinese}")
    
    print("\n✓ 工具函数测试完成")


def test_ai_engine():
    """测试 AI 引擎"""
    print("\n" + "="*50)
    print("测试 AI 引擎")
    print("="*50)
    
    from ai_engine import AIEngine
    
    print("\n启动 AI 引擎...")
    with AIEngine() as engine:
        if not engine.is_ready:
            print("✗ 引擎启动失败")
            return
        
        print("✓ 引擎已就绪")
        
        # 测试获取走法
        print("\nAI 思考（深度 8）...")
        move = engine.get_best_move(depth=8)
        
        if move:
            print(f"✓ AI 走法：{move}")
        else:
            print("✗ AI 未能找到走法")
        
        # 测试位置分析
        print("\n分析当前位置...")
        analysis = engine.analyze_position(duration=2000)
        print(f"分析结果：{analysis}")
    
    print("\n✓ AI 引擎测试完成")


def test_board_recognition():
    """测试棋盘识别（需要摄像头）"""
    print("\n" + "="*50)
    print("测试棋盘识别")
    print("="*50)
    
    try:
        import cv2
        from board_recognition import BoardRecognizer
        
        print("\n启动摄像头...")
        with BoardRecognizer() as recognizer:
            print("✓ 摄像头已启动")
            
            print("\n捕获图像...")
            frame = recognizer.capture_frame()
            
            if frame is None:
                print("✗ 无法捕获图像")
                return
            
            print(f"✓ 图像尺寸：{frame.shape}")
            
            # 显示图像
            cv2.imshow('Test', frame)
            print("按任意键继续...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            
            # 检测棋盘
            print("\n检测棋盘网格...")
            corners = recognizer.detect_board_grid(frame)
            
            if corners is not None:
                print(f"✓ 检测到棋盘角点：{corners}")
            else:
                print("✗ 未检测到棋盘")
            
            # 识别棋子
            print("\n识别棋子...")
            board = recognizer.recognize_pieces(frame, corners)
            
            if board is not None:
                print("✓ 棋子识别完成")
                BoardUtils.print_board(board)
            else:
                print("✗ 棋子识别失败")
        
        print("\n✓ 棋盘识别测试完成")
        
    except ImportError:
        print("OpenCV 未安装，跳过此测试")
    except Exception as e:
        print(f"测试失败：{e}")


def test_robot_control():
    """测试机械臂控制"""
    print("\n" + "="*50)
    print("测试机械臂控制")
    print("="*50)
    
    from robot_control import RobotController
    
    print("\n初始化机械臂（仿真模式）...")
    with RobotController("simulation") as controller:
        if not controller.is_initialized:
            print("✗ 初始化失败")
            return
        
        print("✓ 已初始化")
        
        # 测试移动
        print("\n测试移动到多个点...")
        points = [
            (100, 100, 150),
            (150, 100, 150),
            (150, 150, 150),
            (100, 150, 150),
        ]
        
        for point in points:
            success = controller.move_to(*point)
            print(f"移动到 {point}: {'✓' if success else '✗'}")
        
        # 测试夹爪
        print("\n测试夹爪操作...")
        controller.open_gripper()
        controller.close_gripper()
        controller.open_gripper()
        print("✓ 夹爪测试完成")
        
        # 测试 UCI 走法执行
        print("\n测试 UCI 走法执行...")
        success = controller.execute_uci_move(
            "h3e3",
            board_origin=(0, 0, 0),
            square_size_mm=50.0
        )
        print(f"执行 h3e3: {'✓' if success else '✗'}")
    
    print("\n✓ 机械臂测试完成")


def test_game_manager():
    """测试游戏管理器"""
    print("\n" + "="*50)
    print("测试游戏管理器")
    print("="*50)
    
    from game_manager import GameManager
    
    print("\n初始化游戏管理器...")
    with GameManager() as manager:
        print("✓ 已初始化")
        
        # 运行演示
        print("\n运行演示模式...")
        manager.run_demo()
    
    print("\n✓ 游戏管理器测试完成")


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print(" " * 20 + "中国象棋系统完整测试")
    print("="*60)
    
    # 1. 工具函数
    test_utils()
    
    # 2. AI 引擎
    test_ai_engine()
    
    # 3. 棋盘识别（可选）
    # test_board_recognition()
    
    # 4. 机械臂控制
    test_robot_control()
    
    # 5. 游戏管理器
    test_game_manager()
    
    print("\n" + "="*60)
    print(" " * 25 + "所有测试完成!")
    print("="*60)


if __name__ == "__main__":
    setup_logging()
    
    try:
        run_all_tests()
    except KeyboardInterrupt:
        print("\n\n测试被中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n测试出错：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
