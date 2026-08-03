"""
FEN 串处理工具。

提供中国象棋 FEN（Forsyth–Edwards Notation）的解析、生成、校验，
以及从连续两帧 FEN 的差异中推断走法（UCI 格式）。
"""

import logging
from typing import List, Optional, Tuple

from .coordinates import CoordinateUtils

logger = logging.getLogger(__name__)


class FENUtils:
    """FEN 串处理工具类"""

    # 中国象棋棋子字符映射
    PIECE_CHARS = {
        "r": "车", "n": "马", "b": "象", "a": "士",
        "k": "将", "c": "炮", "p": "卒",
        "R": "车", "N": "马", "B": "相", "A": "仕",
        "K": "帅", "C": "炮", "P": "兵",
    }

    # 初始棋盘 FEN
    START_FEN = "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1"

    @staticmethod
    def parse_fen(fen: str) -> List[List[Optional[str]]]:
        """
        解析 FEN 串为二维数组

        Args:
            fen: FEN 串

        Returns:
            10x9 的二维数组，每个元素为棋子代码或 None
        """
        board = [[None for _ in range(9)] for _ in range(10)]

        parts = fen.strip().split()
        if not parts:
            return board

        position = parts[0]
        rows = position.split("/")

        # 从第 10 行（黑方底线）到第 1 行（红方底线）
        row_idx = 9
        for row_str in rows:
            col_idx = 0
            for char in row_str:
                if char.isdigit():
                    # 数字表示空位数量
                    col_idx += int(char)
                else:
                    # 字符表示棋子
                    if col_idx < 9:
                        board[row_idx][col_idx] = char
                        col_idx += 1
            row_idx -= 1

        return board

    @staticmethod
    def to_fen(board: List[List[Optional[str]]], side_to_move: str = "w") -> str:
        """
        将二维数组转换为 FEN 串

        Args:
            board: 10x9 的二维数组
            side_to_move: 轮到哪方走棋 ('w' 或 'b')

        Returns:
            FEN 串
        """
        fen_rows = []

        # 从第 10 行到第 1 行
        for row_idx in range(9, -1, -1):
            row_str = ""
            empty_count = 0

            for col_idx in range(9):
                piece = board[row_idx][col_idx]
                if piece is None:
                    empty_count += 1
                else:
                    if empty_count > 0:
                        row_str += str(empty_count)
                        empty_count = 0
                    row_str += piece

            if empty_count > 0:
                row_str += str(empty_count)

            fen_rows.append(row_str)

        # 用 '/' 连接所有行
        position = "/".join(fen_rows)

        # 完整的 FEN 包含 6 个部分
        return f"{position} {side_to_move} - - 0 1"

    @staticmethod
    def get_start_fen() -> str:
        """获取中国象棋初始 FEN"""
        return FENUtils.START_FEN

    @staticmethod
    def validate_fen(fen: str) -> bool:
        """
        简单验证 FEN 格式是否正确

        Args:
            fen: FEN 串

        Returns:
            是否有效
        """
        # 基本格式检查
        parts = fen.split()
        if len(parts) < 2:
            return False

        position = parts[0]
        rows = position.split("/")

        if len(rows) != 10:
            return False

        for row in rows:
            total_cols = 0
            for char in row:
                if char.isdigit():
                    total_cols += int(char)
                else:
                    total_cols += 1

            if total_cols != 9:
                return False

        return True

    @staticmethod
    def extract_move_from_fen_change(old_fen: str, new_fen: str) -> Optional[str]:
        """
        从 FEN 变化中提取走法（UCI 格式）。

        比较新旧 FEN 对应棋盘上的差异，推断出起点与终点。

        Args:
            old_fen: 走棋前的 FEN
            new_fen: 走棋后的 FEN

        Returns:
            UCI 格式走法，无法提取时返回 None
        """
        old_board = FENUtils.parse_fen(old_fen)
        new_board = FENUtils.parse_fen(new_fen)

        # 查找变化的位置
        changed_positions = []

        for row in range(10):
            for col in range(9):
                old_piece = old_board[row][col]
                new_piece = new_board[row][col]

                if old_piece != new_piece:
                    changed_positions.append({
                        "row": row,
                        "col": col,
                        "old_piece": old_piece,
                        "new_piece": new_piece,
                    })

        logger.debug(f"发现 {len(changed_positions)} 个变化的位置")

        # 正常走法应该有 2-3 个变化位置（起点、终点，可能还有被吃掉的棋子）
        if len(changed_positions) < 2:
            logger.warning(f"变化位置数量异常：{len(changed_positions)}")
            return None

        from_pos = None
        to_pos = None

        # 旧棋盘上有棋子而新棋盘上没有的位置 -> 起点
        # 新棋盘上有棋子而旧棋盘上没有的位置 -> 终点
        pieces_that_moved = []    # (row, col, piece)
        pieces_that_arrived = []  # (row, col, piece)

        for change in changed_positions:
            row, col = change["row"], change["col"]
            old_piece = change["old_piece"]
            new_piece = change["new_piece"]

            if old_piece and not new_piece:
                pieces_that_moved.append((row, col, old_piece))

            if new_piece and not old_piece:
                pieces_that_arrived.append((row, col, new_piece))
            elif old_piece and new_piece and old_piece != new_piece:
                # 吃子：新位置的棋子视为移动过来的棋子
                pieces_that_arrived.append((row, col, new_piece))

        if len(pieces_that_moved) >= 1 and len(pieces_that_arrived) >= 1:
            from_pos = (pieces_that_moved[0][0], pieces_that_moved[0][1])
            to_pos = (pieces_that_arrived[0][0], pieces_that_arrived[0][1])

            move = CoordinateUtils.indices_to_uci(*from_pos) + CoordinateUtils.indices_to_uci(*to_pos)
            logger.info(f"提取走法：{move}")
            return move

        # 退化处理：取前两个变化点
        if len(changed_positions) >= 2:
            from_pos = (changed_positions[0]["row"], changed_positions[0]["col"])
            to_pos = (changed_positions[1]["row"], changed_positions[1]["col"])

            move = CoordinateUtils.indices_to_uci(*from_pos) + CoordinateUtils.indices_to_uci(*to_pos)
            logger.warning(f"简化提取走法：{move}")
            return move

        logger.error("无法提取走法")
        return None
