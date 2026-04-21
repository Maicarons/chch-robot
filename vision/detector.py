"""
棋盘检测器 - 基于ONNX模型的关键点检测和棋子分类
"""

import os
import time
import logging
import numpy as np
import cv2
from typing import Tuple, Optional, Union

logger = logging.getLogger(__name__)


class ChessboardDetector:
    """
    棋盘检测器 - 使用ONNX模型进行关键点检测和棋子分类
    
    工作流程:
    1. 检测棋盘关键点 (RTMPose模型)
    2. 透视变换拉伸棋盘
    3. 棋子分类 (Full Classifier模型)
    """
    
    def __init__(self, pose_model_path: str, classifier_model_path: str):
        """
        初始化检测器
        
        Args:
            pose_model_path: 姿态估计模型路径
            classifier_model_path: 棋子分类模型路径
        """
        self.pose_model_path = pose_model_path
        self.classifier_model_path = classifier_model_path
        
        # 延迟加载模型
        self._pose_model = None
        self._classifier_model = None
        
        logger.info(f"棋盘检测器初始化")
        logger.info(f"  姿态模型: {pose_model_path}")
        logger.info(f"  分类模型: {classifier_model_path}")
    
    def _load_models(self):
        """懒加载ONNX模型"""
        if self._pose_model is None or self._classifier_model is None:
            try:
                from core.chessboard_detector import ChessboardDetector as CoreDetector
                
                self._core_detector = CoreDetector(
                    pose_model_path=self.pose_model_path,
                    full_classifier_model_path=self.classifier_model_path
                )
                logger.info("ONNX模型加载成功")
                
            except Exception as e:
                logger.error(f"加载ONNX模型失败: {e}", exc_info=True)
                raise RuntimeError(f"无法加载ONNX模型: {e}")
    
    def detect_and_classify(self, image_rgb: np.ndarray) -> Tuple[
        Optional[np.ndarray],  # 带关键点的原图
        Optional[np.ndarray],  # 拉伸后的棋盘
        Optional[str],         # 棋子布局字符串
        Optional[list],        # 置信度分数
        str                    # 时间信息
    ]:
        """
        检测棋盘并分类棋子
        
        Args:
            image_rgb: RGB格式输入图像
            
        Returns:
            (原图关键点, 拉伸棋盘, 布局字符串, 置信度, 时间信息)
        """
        self._load_models()
        
        if image_rgb is None:
            return None, None, None, None, ""
        
        try:
            # 调用核心检测器
            result = self._core_detector.pred_detect_board_and_classifier(image_rgb)
            return result
            
        except Exception as e:
            logger.error(f"检测失败: {e}", exc_info=True)
            return None, None, None, None, f"错误: {e}"
    
    def parse_layout_string(self, layout_str: str) -> dict:
        """
        解析布局字符串为棋盘状态字典
        
        Args:
            layout_str: 布局字符串 (如 "rnbakabnr\n.........\n...")
            
        Returns:
            棋盘状态字典 {(col, row): piece_char}  # 返回棋子字符，不是'red'/'black'
        """
        if not layout_str:
            return {}
        
        board_state = {}
        rows = layout_str.strip().split('\n')
        
        for row_idx, row_str in enumerate(rows):
            if len(row_str) != 9:
                continue
            
            for col_idx, char in enumerate(row_str):
                if char == '.' or char == 'x':
                    continue
                
                # 直接返回棋子字符（大写=红方，小写=黑方）
                board_state[(col_idx, row_idx)] = char
        
        return board_state
