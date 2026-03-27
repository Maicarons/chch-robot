"""
工具函数 - 中国象棋相关工具
包括 FEN 转换、坐标转换、走法验证等
"""

import re
from typing import List, Tuple, Optional, Dict


class FENUtils:
    """FEN 串处理工具类"""
    
    # 中国象棋棋子字符映射
    PIECE_CHARS = {
        'r': '车', 'n': '马', 'b': '象', 'a': '士', 
        'k': '将', 'c': '炮', 'p': '卒',
        'R': '车', 'N': '马', 'B': '相', 'A': '仕',
        'K': '帅', 'C': '炮', 'P': '兵'
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
        rows = position.split('/')
        
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
    def to_fen(board: List[List[Optional[str]]], side_to_move: str = 'w') -> str:
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
        position = '/'.join(fen_rows)
        
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
        rows = position.split('/')
        
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
        uci_move = uci_move.replace('+', '')
        
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


class MoveNotationUtils:
    """记谱法转换工具类"""
    
    # 红方棋子名称
    RED_PIECES = {
        'R': '车', 'N': '马', 'B': '相', 'A': '仕',
        'K': '帅', 'C': '炮', 'P': '兵'
    }
    
    # 黑方棋子名称
    BLACK_PIECES = {
        'r': '车', 'n': '马', 'b': '象', 'a': '士',
        'k': '将', 'c': '炮', 'p': '卒'
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
            if piece.lower() in ['n', 'b', 'a']:  # 马、象、士
                target = 9 - to_col
            else:
                target = abs(to_row - from_row)
        else:
            # 后退
            action = "退"
            if piece.lower() in ['n', 'b', 'a']:
                target = 9 - to_col
            else:
                target = abs(from_row - to_row)
        
        return f"{piece_name}{file_num}{action}{target}"


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
            return 'red'
        else:
            return 'black'
    
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
        king = 'K' if color == 'red' else 'k'
        
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
            line = f"{row+1}|"
            for col in range(9):
                piece = board[row][col]
                if piece is None:
                    line += ". "
                else:
                    # 显示棋子中文名称
                    if piece.isupper():
                        chars = {'R': '车', 'N': '马', 'B': '相', 'A': '仕', 
                                'K': '帅', 'C': '炮', 'P': '兵'}
                    else:
                        chars = {'r': '车', 'n': '马', 'b': '象', 'a': '士',
                                'k': '将', 'c': '炮', 'p': '卒'}
                    line += chars.get(piece, '?') + " "
            print(line)
        
        print("  -----------------")
        print()
