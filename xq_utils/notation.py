"""
记谱法转换工具。

将 UCI 走法转换为中国象棋的 WXF 记谱法（简化）与中文记谱（如「炮二平五」）。
"""

from typing import Tuple

from .coordinates import CoordinateUtils
from .fen import FENUtils


class MoveNotationUtils:
    """记谱法转换工具类"""

    # 红方棋子名称
    RED_PIECES = {
        "R": "车", "N": "马", "B": "相", "A": "仕",
        "K": "帅", "C": "炮", "P": "兵",
    }

    # 黑方棋子名称
    BLACK_PIECES = {
        "r": "车", "n": "马", "b": "象", "a": "士",
        "k": "将", "c": "炮", "p": "卒",
    }

    @staticmethod
    def uci_to_wxf(uci_move: str, fen: str) -> str:
        """
        将 UCI 走法转换为 WXF 记谱法（简化版）

        Args:
            uci_move: UCI 格式走法
            fen: 当前 FEN

        Returns:
            WXF 格式走法，如 "C2=5"
        """
        # 解析走法
        (from_row, from_col), (to_row, to_col) = CoordinateUtils.parse_uci_move(uci_move)

        # 获取棋盘状态
        board = FENUtils.parse_fen(fen)

        # 获取移动的棋子
        piece = board[from_row][from_col]
        if piece is None:
            return "?"

        # 判断红方还是黑方
        is_red = piece.isupper()

        # 获取棋子中文名称
        piece_name = MoveNotationUtils.RED_PIECES.get(piece) if is_red \
                    else MoveNotationUtils.BLACK_PIECES.get(piece)

        if piece_name is None:
            return "?"

        # 计算纵线编号（从右往左 1-9）
        file_num = 9 - from_col

        # 判断移动类型
        if from_row == to_row:
            # 平移
            direction = "="
            target = 9 - to_col
        elif (is_red and to_row > from_row) or (not is_red and to_row < from_row):
            # 前进
            direction = "+"
            target = abs(to_col - from_col)
        else:
            # 后退
            direction = "-"
            target = abs(to_col - from_col)

        return f"{piece_name}{file_num}{direction}{target}"

    @staticmethod
    def uci_to_chinese(uci_move: str, fen: str) -> str:
        """
        将 UCI 走法转换为中文记谱（简化版）

        Args:
            uci_move: UCI 格式走法
            fen: 当前 FEN

        Returns:
            中文记谱，如 "炮二平五"
        """
        # 解析走法
        (from_row, from_col), (to_row, to_col) = CoordinateUtils.parse_uci_move(uci_move)

        # 获取棋盘状态
        board = FENUtils.parse_fen(fen)

        # 获取移动的棋子
        piece = board[from_row][from_col]
        if piece is None:
            return "?"

        # 判断红方还是黑方
        is_red = piece.isupper()

        # 获取棋子中文名称
        piece_name = MoveNotationUtils.RED_PIECES.get(piece) if is_red \
                    else MoveNotationUtils.BLACK_PIECES.get(piece)

        if piece_name is None:
            return "?"

        # 计算纵线编号（从右往左 1-9）
        file_num = 9 - from_col

        # 判断移动类型
        if from_row == to_row:
            # 平移
            action = "平"
            target = 9 - to_col
        elif (is_red and to_row > from_row) or (not is_red and to_row < from_row):
            # 前进
            action = "进"
            # 计算前进的步数或目标位置
            if piece.lower() in ["n", "b", "a"]:  # 马、象、士
                target = 9 - to_col
            else:
                target = abs(to_row - from_row)
        else:
            # 后退
            action = "退"
            if piece.lower() in ["n", "b", "a"]:
                target = 9 - to_col
            else:
                target = abs(from_row - to_row)

        return f"{piece_name}{file_num}{action}{target}"
