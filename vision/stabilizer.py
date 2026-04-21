"""
稳定化缓冲区 - 通过多帧投票消除检测抖动
"""

import numpy as np
from collections import deque
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class StableBoardBuffer:
    """
    稳定化棋盘缓冲区
    
    原理:
    - 维护最近N帧的检测结果
    - 对每个位置进行投票
    - 只有超过阈值的棋子才被认定为稳定
    """
    
    def __init__(self, maxlen: int = 5, ratio: float = 0.6):
        """
        初始化缓冲区
        
        Args:
            maxlen: 缓冲队列最大长度
            ratio: 稳定判定比例阈值 (0-1)
        """
        self.buf = deque(maxlen=maxlen)
        self.ratio = ratio
        logger.info(f"稳定化缓冲区初始化: maxlen={maxlen}, ratio={ratio}")
    
    def add(self, state: Dict[Tuple[int, int], str]):
        """
        添加一帧检测结果
        
        Args:
            state: 当前帧的棋盘状态
        """
        self.buf.append(dict(state))
    
    def get_stable(self) -> Dict[Tuple[int, int], str]:
        """
        获取稳定的棋盘状态（通过多帧投票）
        
        Returns:
            稳定的棋盘状态 {(col, row): piece_char}
        """
        if not self.buf:
            return {}
        
        stable = {}
        need = max(1, int(np.ceil(len(self.buf) * self.ratio)))
        
        # 收集所有出现过的棋子位置
        all_positions = set()
        for board in self.buf:
            all_positions.update(board.keys())
        
        # 对每个位置进行投票
        for pos in all_positions:
            # 统计每个棋子字符的出现次数
            piece_votes = {}
            
            for board in self.buf:
                piece = board.get(pos)
                if piece and piece != '.' and piece != 'x':
                    piece_votes[piece] = piece_votes.get(piece, 0) + 1
            
            # 找出得票最多的棋子
            if piece_votes:
                best_piece = max(piece_votes, key=piece_votes.get)
                best_count = piece_votes[best_piece]
                
                # 如果得票数超过阈值，认定为稳定
                if best_count >= need:
                    stable[pos] = best_piece
        
        return stable
    
    def clear(self):
        """清空缓冲区"""
        self.buf.clear()
        logger.info("稳定化缓冲区已清空")
