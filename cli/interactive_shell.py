"""
交互式命令行外壳与欢迎横幅。

``InteractiveShell`` 负责在 ``python main.py`` 不带参数时与用户交互，
各子命令（demo / start / calibrate / test_* / status / help / quit）在此分发。
"""

import logging

logger = logging.getLogger(__name__)


def print_banner():
    """打印欢迎横幅"""
    print("\n" + "=" * 60)
    print(" " * 15 + "中国象棋人机博弈系统")
    print(" " * 20 + "线下棋盘 + AI + 机械臂")
    print("=" * 60)
    print()


def show_help():
    """显示帮助信息"""
    help_text = """
可用命令:
  start       - 开始游戏
  calibrate   - 校准系统（棋盘和机械臂）
  demo        - 运行演示模式
  test_camera - 测试摄像头
  test_engine - 测试 AI 引擎
  test_robot  - 测试机械臂
  status      - 显示当前状态
  help        - 显示此帮助信息
  quit/exit   - 退出程序

游戏流程:
  1. 运行 'calibrate' 校准系统（首次使用必须）
  2. 运行 'start' 开始游戏
  3. 系统会自动识别初始棋盘
  4. AI 会思考并走棋（通过机械臂执行）
  5. 玩家走棋后，系统会自动检测
  6. 重复步骤 4-5 直到游戏结束

注意事项:
  - 确保棋盘在摄像头视野内
  - 保持光照条件稳定
  - 机械臂工作时请注意安全
  - 玩家走棋后等待系统检测
"""
    print(help_text)


class InteractiveShell:
    """交互式命令行外壳"""

    def __init__(self):
        self.game_manager = None
        self.is_running = True
        self.is_initialized = False

    def run(self):
        """运行交互式外壳"""
        print_banner()
        show_help()

        while self.is_running:
            try:
                command = input("\n>>> ").strip().lower()

                if not command:
                    continue

                self.process_command(command)

            except KeyboardInterrupt:
                print("\n\n程序中断")
                break

            except Exception as e:
                print(f"\n错误：{e}")

        # 清理
        self.cleanup()

    def process_command(self, command: str):
        """处理用户命令"""

        if command in ["quit", "exit", "q"]:
            self.is_running = False
            print("再见！")

        elif command == "help":
            show_help()

        elif command == "demo":
            self.run_demo()

        elif command == "start":
            self.start_game()

        elif command == "calibrate":
            self.calibrate_system()

        elif command == "test_camera":
            self.test_camera()

        elif command == "test_engine":
            self.test_ai_engine()

        elif command == "test_robot":
            self.test_robot()

        elif command == "status":
            self.show_status()

        else:
            print(f"未知命令：{command}")
            print("输入 'help' 查看帮助")

    def run_demo(self):
        """运行演示"""
        print("\n=== 运行演示模式 ===\n")

        try:
            from game_manager import GameManager

            with GameManager() as manager:
                manager.run_demo()

            print("\n演示完成")

        except Exception as e:
            print(f"\n演示失败：{e}")

    def start_game(self):
        """开始游戏"""
        print("\n=== 开始游戏 ===\n")

        if not self.is_initialized:
            print("正在初始化系统...")
            if not self.initialize_system():
                print("初始化失败，无法开始游戏")
                return

        try:
            from game_manager import GameManager

            self.game_manager = GameManager()

            if not self.game_manager.initialize():
                print("游戏管理器初始化失败")
                return

            if not self.game_manager.start_components():
                print("组件启动失败")
                return

            # 识别初始棋盘
            print("\n正在识别初始棋盘...")
            if not self.game_manager.recognize_initial_board():
                print("棋盘识别失败，请调整摄像头后重试")
                return

            print("\n✓ 准备就绪，游戏开始！\n")

            # 开始游戏循环
            self.game_manager.play_game()

        except Exception as e:
            print(f"\n游戏出错：{e}")

        finally:
            if self.game_manager:
                self.game_manager.shutdown()
                self.game_manager = None

    def calibrate_system(self):
        """校准系统"""
        print("\n=== 系统校准 ===\n")

        try:
            from game_manager import GameManager

            with GameManager() as manager:
                if not manager.initialize():
                    print("初始化失败")
                    return

                if not manager.start_components():
                    print("组件启动失败")
                    return

                if manager.calibrate():
                    print("\n✓ 系统校准成功！")
                else:
                    print("\n✗ 系统校准失败")

        except Exception as e:
            print(f"\n校准失败：{e}")

    def test_camera(self):
        """测试摄像头"""
        print("\n=== 摄像头测试 ===\n")

        try:
            from vision import BoardRecognizer
            import cv2

            with BoardRecognizer() as recognizer:
                print("摄像头已启动")
                print("按任意键捕获图像，ESC 退出")

                while True:
                    frame = recognizer.camera_manager.capture_frame()

                    if frame is not None:
                        cv2.imshow("Camera Test", frame)

                        key = cv2.waitKey(1) & 0xFF
                        if key == 27:  # ESC
                            break

                print("\n测试完成")

        except ImportError:
            print("OpenCV 未安装，请先安装：pip install opencv-python")
        except Exception as e:
            print(f"测试失败：{e}")

    def test_ai_engine(self):
        """测试 AI 引擎"""
        print("\n=== AI 引擎测试 ===\n")

        try:
            from ai import AIEngine

            with AIEngine() as engine:
                if not engine.is_ready:
                    print("引擎启动失败")
                    return

                print("引擎已启动")

                # 测试思考
                print("\nAI 正在思考（深度 10）...")
                move = engine.get_best_move(depth=10)

                if move:
                    print(f"AI 走法：{move}")
                else:
                    print("AI 未能找到走法")

                print("\n测试完成")

        except Exception as e:
            print(f"测试失败：{e}")

    def test_robot(self):
        """测试机械臂"""
        print("\n=== 机械臂测试 ===\n")

        try:
            from robot import RobotController

            with RobotController() as controller:
                if not controller.is_initialized:
                    print("机械臂初始化失败")
                    return

                print("机械臂已初始化")

                # 执行测试序列
                print("\n执行测试序列...")
                if controller.test_sequence():
                    print("✓ 测试通过")
                else:
                    print("✗ 测试失败")

                print("\n测试完成")

        except Exception as e:
            print(f"测试失败：{e}")

    def show_status(self):
        """显示当前状态"""
        print("\n=== 系统状态 ===")
        print(f"初始化状态：{'是' if self.is_initialized else '否'}")
        print(f"游戏运行中：{'是' if self.game_manager and self.game_manager.is_game_running else '否'}")

        if self.game_manager:
            self.game_manager.print_game_status()

    def initialize_system(self) -> bool:
        """初始化系统"""
        try:
            # 这里可以进行一些全局初始化
            self.is_initialized = True
            print("✓ 系统初始化成功")
            return True

        except Exception as e:
            print(f"✗ 系统初始化失败：{e}")
            return False

    def cleanup(self):
        """清理资源"""
        print("\n正在清理...")

        if self.game_manager:
            self.game_manager.shutdown()

        print("清理完成")
