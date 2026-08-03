"""
中国象棋（Xiangqi）纯工具函数集合。

将原先散落在 ``utils.py`` 中的四个互不相关的工具类拆分为独立的子模块，
统一收纳在 ``xq_utils`` 包下，便于按需导入与解耦：

- :class:`FENUtils`        —— FEN 串解析 / 生成 / 校验 / 走法差异提取
- :class:`CoordinateUtils` —— UCI 坐标与棋盘/机械臂坐标互转
- :class:`MoveNotationUtils` —— UCI 与 WXF / 中文记谱法互转
- :class:`BoardUtils`      —— 棋盘状态查询与统计
"""

from .board import BoardUtils
from .coordinates import CoordinateUtils
from .fen import FENUtils
from .notation import MoveNotationUtils

__all__ = [
    "FENUtils",
    "CoordinateUtils",
    "MoveNotationUtils",
    "BoardUtils",
]
