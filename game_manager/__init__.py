"""
游戏管理器包。

- :mod:`game_manager.manager` —— :class:`GameManager` 协调整个对局流程
- :mod:`game_manager.recorder` —— 棋谱（对局记录）持久化
"""

from .manager import GameManager

__all__ = ["GameManager"]
