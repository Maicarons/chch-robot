"""
棋盘状态工具。

提供棋盘范围校验、棋子颜色判定、棋子计数、将/帅定位，以及调试用棋盘打印。
"""

from typing import Dict, List, Optional, Tuple


class BoardUtils:
    """棋盘状态工具类"""

    @staticmethod
    def is_valid_position(row: int, col: int) -> bool:
        """
        检查位置是否在棋盘范围内

        Args:
            row: 行索引
            col: 列索引

        Returns:
            是否有效
        """
        return 0 <= row < 10 and 0 <= col < 9

    @staticmethod
    def get_piece_color(piece: Optional[str]) -> Optional[str]:
        """
        获取棋子颜色

        Args:
            piece: 棋子代码

        Returns:
            'red', 'black', 或 None
        """
        if piece is None:
            return None

        if piece.isupper():
            return "red"
        else:
            return "black"

    @staticmethod
    def count_pieces(board: List[List[Optional[str]]]) -> Dict[str, int]:
        """
        统计棋盘上各类棋子数量

        Args:
            board: 棋盘状态

        Returns:
            字典，键为棋子代码，值为数量
        """
        counts = {}

        for row in range(10):
            for col in range(9):
                piece = board[row][col]
                if piece is not None:
                    counts[piece] = counts.get(piece, 0) + 1

        return counts

    @staticmethod
    def find_king_position(board: List[List[Optional[str]]], color: str) -> Optional[Tuple[int, int]]:
        """
        查找将/帅的位置

        Args:
            board: 棋盘状态
            color: 颜色 ('red' 或 'black')

        Returns:
            (row, col) 或 None
        """
        king = "K" if color == "red" else "k"

        for row in range(10):
            for col in range(9):
                if board[row][col] == king:
                    return (row, col)

        return None

    @staticmethod
    def print_board(board: List[List[Optional[str]]]):
        """
        打印棋盘到控制台（用于调试）

        Args:
            board: 棋盘状态
        """
        print("\n  a b c d e f g h i")
        print("  -----------------")

        for row in range(9, -1, -1):
            line = f"{row + 1}|"
            for col in range(9):
                piece = board[row][col]
                if piece is None:
                    line += ". "
                else:
                    # 显示棋子中文名称
                    if piece.isupper():
                        chars = {"R": "车", "N": "马", "B": "相", "A": "仕",
                                 "K": "帅", "C": "炮", "P": "兵"}
                    else:
                        chars = {"r": "车", "n": "马", "b": "象", "a": "士",
                                 "k": "将", "c": "炮", "p": "卒"}
                    line += chars.get(piece, "?") + " "
            print(line)

        print("  -----------------")
        print()
