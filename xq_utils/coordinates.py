"""
坐标转换工具。

负责三类坐标之间的互转：

- UCI 棋格（如 ``e3``） <-> 棋盘行列索引 ``(row, col)``
- 棋盘行列索引 <-> 机械臂坐标系下的毫米坐标
"""

from typing import Tuple


class CoordinateUtils:
    """坐标转换工具类"""

    # UCI 坐标文件映射 (a-i 对应 0-8)
    FILES = "abcdefghi"

    @staticmethod
    def uci_to_indices(uci_square: str) -> Tuple[int, int]:
        """
        将 UCI 格式的格子转换为行列索引

        Args:
            uci_square: UCI 格式的格子，如 "e3"

        Returns:
            (row, col) 元组，row: 0-9, col: 0-8
        """
        file_char = uci_square[0].lower()
        rank = int(uci_square[1])

        # 文件转换为列索引 (a=0, b=1, ..., i=8)
        col = CoordinateUtils.FILES.index(file_char)

        # 横线转换为行索引 (1=0, 2=1, ..., 10=9)
        row = rank - 1

        return (row, col)

    @staticmethod
    def indices_to_uci(row: int, col: int) -> str:
        """
        将行列索引转换为 UCI 格式的格子

        Args:
            row: 行索引 (0-9)
            col: 列索引 (0-8)

        Returns:
            UCI 格式的格子，如 "e3"
        """
        file_char = CoordinateUtils.FILES[col]
        rank = row + 1

        return f"{file_char}{rank}"

    @staticmethod
    def parse_uci_move(uci_move: str) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """
        解析 UCI 走法

        Args:
            uci_move: UCI 格式走法，如 "h3e3"

        Returns:
            ((from_row, from_col), (to_row, to_col))
        """
        # 去掉可能的 '+' 符号（升变标记）
        uci_move = uci_move.replace("+", "")

        if len(uci_move) < 4:
            raise ValueError(f"无效的 UCI 走法：{uci_move}")

        from_square = uci_move[0:2]
        to_square = uci_move[2:4]

        from_pos = CoordinateUtils.uci_to_indices(from_square)
        to_pos = CoordinateUtils.uci_to_indices(to_square)

        return (from_pos, to_pos)

    @staticmethod
    def board_to_robot_coords(board_row: int, board_col: int,
                              board_origin: Tuple[float, float, float],
                              square_size_mm: float = 50.0) -> Tuple[float, float, float]:
        """
        将棋盘坐标转换为机械臂坐标

        Args:
            board_row: 棋盘行索引 (0-9)
            board_col: 棋盘列索引 (0-8)
            board_origin: 棋盘原点在机械臂坐标系中的位置 (x, y, z)
            square_size_mm: 格子尺寸（毫米）

        Returns:
            机械臂坐标 (x, y, z)
        """
        origin_x, origin_y, origin_z = board_origin

        # 计算中心位置
        robot_x = origin_x + board_col * square_size_mm + square_size_mm / 2
        robot_y = origin_y + board_row * square_size_mm + square_size_mm / 2
        robot_z = origin_z  # 棋盘平面高度

        return (robot_x, robot_y, robot_z)

    @staticmethod
    def robot_to_board_coords(robot_x: float, robot_y: float,
                              board_origin: Tuple[float, float, float],
                              square_size_mm: float = 50.0) -> Tuple[int, int]:
        """
        将机械臂坐标转换为棋盘坐标

        Args:
            robot_x: 机械臂 X 坐标
            robot_y: 机械臂 Y 坐标
            board_origin: 棋盘原点 (x, y, z)
            square_size_mm: 格子尺寸（毫米）

        Returns:
            (board_row, board_col)
        """
        origin_x, origin_y, _ = board_origin

        # 计算在哪个格子内
        col = int((robot_x - origin_x) / square_size_mm)
        row = int((robot_y - origin_y) / square_size_mm)

        # 边界检查
        col = max(0, min(8, col))
        row = max(0, min(9, row))

        return (row, col)
