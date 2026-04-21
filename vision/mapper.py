"""
棋盘坐标映射器 - 处理透视变换和网格吸附
"""

import numpy as np
import cv2
import logging
from typing import Tuple, Optional, Dict

logger = logging.getLogger(__name__)


class BoardMapper:
    """
    棋盘坐标映射器
    
    功能:
    - 图像坐标与棋盘坐标的透视变换
    - 棋子位置网格吸附
    - 可视化绘制
    """
    
    def __init__(self, corners: np.ndarray):
        """
        初始化映射器
        
        Args:
            corners: 棋盘四个角点 (左上、右上、右下、左下)
        """
        # 定义目标棋盘坐标系 (9列 x 10行)
        board_pts = np.array([[0, 9], [8, 9], [8, 0], [0, 0]], dtype=np.float32)
        
        # 计算透视变换矩阵
        self.H_img_to_board = cv2.getPerspectiveTransform(corners, board_pts)
        self.H_board_to_img = cv2.getPerspectiveTransform(board_pts, corners)
        
        logger.info("棋盘映射器初始化成功")
    
    def board_to_image(self, pt: Tuple[float, float]) -> np.ndarray:
        """棋盘坐标转图像坐标"""
        return cv2.perspectiveTransform(
            np.array([pt], dtype=np.float32).reshape(-1, 1, 2),
            self.H_board_to_img
        ).reshape(-1, 2)[0]
    
    def image_to_board(self, pt: Tuple[float, float]) -> np.ndarray:
        """图像坐标转棋盘坐标"""
        return cv2.perspectiveTransform(
            np.array([pt], dtype=np.float32).reshape(-1, 1, 2),
            self.H_img_to_board
        ).reshape(-1, 2)[0]
    
    def snap_to_grid(self, pt: Tuple[float, float], 
                    threshold: float = 0.45) -> Optional[Tuple[int, int]]:
        """
        将图像坐标吸附到最近的棋盘交点
        
        Args:
            pt: 图像坐标 (x, y)
            threshold: 吸附阈值
            
        Returns:
            棋盘交点 (col, row) 或 None
        """
        bx, by = self.image_to_board(pt)
        c, r = int(round(bx)), int(round(by))
        
        # 检查是否在棋盘范围内且距离足够近
        if (0 <= c <= 8 and 0 <= r <= 9 and 
            ((bx - c)**2 + (by - r)**2)**0.5 < threshold):
            return (c, r)
        
        return None
    
    def draw_state(self, frame: np.ndarray, 
                  board_state: Dict[Tuple[int, int], str]):
        """
        在图像上绘制棋盘状态
        
        Args:
            frame: 输入图像
            board_state: 棋盘状态字典 {(col, row): 'red'/'black'}
        """
        for (c, r), side in board_state.items():
            cx, cy = map(int, self.board_to_image((c, r)))
            
            if side == "red":
                edge_color = (0, 0, 255)
                fill_color = (220, 220, 255)
                label = "R"
                text_color = (40, 40, 180)
            else:
                edge_color = (0, 0, 0)
                fill_color = (210, 210, 210)
                label = "B"
                text_color = (255, 255, 255)
            
            # 绘制棋子圆圈
            cv2.circle(frame, (cx, cy), 18, fill_color, -1, cv2.LINE_AA)
            cv2.circle(frame, (cx, cy), 18, edge_color, 2, cv2.LINE_AA)
            cv2.putText(frame, label, (cx - 8, cy + 7),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2, cv2.LINE_AA)
