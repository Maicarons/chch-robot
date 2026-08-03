"""
主程序入口 - 线下棋盘人机博弈中国象棋。

仅负责：命令行参数解析、可选自定义配置加载、命令分发。
交互式外壳与日志初始化已拆分到 :mod:`cli` 包。
"""

import sys
import argparse
import importlib.util
import logging

import config
from cli.logging_setup import setup_logging
from cli.interactive_shell import InteractiveShell


def load_custom_config(config_path: str):
    """
    动态加载外部配置文件并覆盖 ``config`` 模块中的同名大写常量。

    Args:
        config_path: 配置文件路径（Python 模块）
    """
    print(f"加载配置文件：{config_path}")
    spec = importlib.util.spec_from_file_location("custom_config", config_path)
    if spec and spec.loader:
        custom_config = importlib.util.module_from_spec(spec)
        sys.modules["custom_config"] = custom_config
        spec.loader.exec_module(custom_config)

        # 将自定义配置合并到 config 模块
        for attr in dir(custom_config):
            if not attr.startswith("_") and attr.isupper():
                setattr(config, attr, getattr(custom_config, attr))
                print(f"  - 更新配置：{attr} = {getattr(config, attr)}")
        print("配置加载完成")
    else:
        print(f"警告：无法加载配置文件 {config_path}")


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="中国象棋人机博弈系统")
    parser.add_argument("--demo", action="store_true", help="运行演示模式")
    parser.add_argument("--calibrate", action="store_true", help="校准系统")
    parser.add_argument("--test-camera", action="store_true", help="测试摄像头")
    parser.add_argument("--test-engine", action="store_true", help="测试 AI 引擎")
    parser.add_argument("--test-robot", action="store_true", help="测试机械臂")
    parser.add_argument("--config", type=str, help="配置文件路径")

    args = parser.parse_args()

    # 设置日志
    setup_logging()
    logger = logging.getLogger("main")

    try:
        # 加载自定义配置（如果有）
        if args.config:
            load_custom_config(args.config)

        # 根据参数直接运行对应功能
        if args.demo:
            from game_manager import GameManager
            with GameManager() as manager:
                manager.run_demo()

        elif args.calibrate:
            from game_manager import GameManager
            with GameManager() as manager:
                if manager.initialize() and manager.start_components():
                    manager.calibrate()

        elif args.test_camera:
            from vision import BoardRecognizer
            import cv2
            with BoardRecognizer() as recognizer:
                print("摄像头测试中... 按 ESC 退出")
                while True:
                    frame = recognizer.camera_manager.capture_frame()
                    if frame is not None:
                        cv2.imshow("Camera Test", frame)
                        if cv2.waitKey(1) & 0xFF == 27:
                            break

        elif args.test_engine:
            from ai import AIEngine
            with AIEngine() as engine:
                if engine.is_ready:
                    print("AI 引擎测试:")
                    move = engine.get_best_move(depth=10)
                    print(f"AI 走法：{move}" if move else "AI 未能找到走法")

        elif args.test_robot:
            from robot import RobotController
            with RobotController() as controller:
                if controller.is_initialized:
                    print("机械臂测试:")
                    success = controller.test_sequence()
                    print("✓ 测试通过" if success else "✗ 测试失败")

        else:
            # 默认运行交互式外壳
            shell = InteractiveShell()
            shell.run()

    except KeyboardInterrupt:
        print("\n\n程序中断")
        sys.exit(1)

    except Exception as e:
        logger.error(f"程序异常：{e}", exc_info=True)
        print(f"\n严重错误：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
