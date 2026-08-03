"""
游戏管理器自测入口：``python -m game_manager``。
"""

import logging

from .manager import GameManager


def test_game_manager():
    """测试游戏管理器"""
    print("=" * 50)
    print("游戏管理器测试")
    print("=" * 50)

    manager = GameManager()

    with manager:
        # 运行演示
        manager.run_demo()


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    test_game_manager()
