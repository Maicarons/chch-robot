"""
棋盘识别器 - 整合检测、映射、稳定化等功能的主类
提供高层API用于棋盘识别和FEN生成
"""

import os
import time
import logging
import numpy as np
import cv2
from typing import Optional, Dict, Tuple, List

from .camera import CameraManager
from .detector import ChessboardDetector
from .stabilizer import StableBoardBuffer
from config import CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS, SNAP_DIST_THRES, STABLE_WINDOW, STABLE_RATIO, USE_NETWORK_CAMERA, NETWORK_CAMERA_URL

logger = logging.getLogger(__name__)


class BoardRecognizer:
    """
    棋盘识别器 - 高层API
    
    整合了:
    - 摄像头管理
    - 棋盘检测
    - 棋子分类
    - 多帧稳定化
    - FEN生成
    """
    
    def __init__(self, camera_index: int = 0, 
                 detect_interval: float = 3.0,
                 pose_model_path: str = None,
                 classifier_model_path: str = None,
                 width: int = None,
                 height: int = None,
                 fps: int = None,
                 use_network: bool = None,
                 network_url: str = None):
        """
        初始化识别器
        
        Args:
            camera_index: 摄像头索引
            detect_interval: 自动检测间隔（秒）
            pose_model_path: 姿态模型路径
            classifier_model_path: 分类模型路径
            width: 图像宽度
            height: 图像高度
            fps: 帧率
            use_network: 是否使用网络摄像头
            network_url: 网络摄像头WebSocket地址
        """
        # 获取项目根目录（vision/的父目录）
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 默认模型路径（使用绝对路径）
        if pose_model_path is None:
            pose_model_path = os.path.join(project_root, "model", "pose", "4_v6-0301.onnx")
        if classifier_model_path is None:
            classifier_model_path = os.path.join(project_root, "model", "layout_recognition", "nano_v3-0319.onnx")
        
        # 使用配置或默认值
        width = width or CAMERA_WIDTH
        height = height or CAMERA_HEIGHT
        fps = fps or CAMERA_FPS
        use_network = use_network if use_network is not None else USE_NETWORK_CAMERA
        network_url = network_url or NETWORK_CAMERA_URL
        
        self.camera_manager = CameraManager(
            camera_index=camera_index,
            width=width,
            height=height,
            fps=fps,
            use_network=use_network,
            network_url=network_url
        )
        self.detector = ChessboardDetector(
            pose_model_path=pose_model_path,
            classifier_model_path=classifier_model_path
        )
        self.stabilizer = StableBoardBuffer(maxlen=STABLE_WINDOW, ratio=STABLE_RATIO)
        
        self.detect_interval = detect_interval
        self.last_board_state = None
        self.current_fen = None
        
        mode = "网络" if use_network else "本地"
        logger.info(f"棋盘识别器初始化完成 (detect_interval={detect_interval}s, {mode}摄像头)")
    
    def start(self) -> bool:
        """启动摄像头"""
        return self.camera_manager.start()
    
    def stop(self):
        """关闭摄像头"""
        self.camera_manager.stop()
    
    def recognize_board(self, image: np.ndarray = None) -> Optional[Dict[Tuple[int, int], str]]:
        """
        识别棋盘状态
        
        Args:
            image: 输入图像，None则自动捕获
            
        Returns:
            棋盘状态字典 {(col, row): piece_char}  # piece_char: 'R'/'r'等棋子字符
        """
        # 捕获图像
        if image is None:
            image = self.camera_manager.capture_frame()
        
        if image is None:
            logger.warning("无法获取图像")
            return None
        
        try:
            # 转换为RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # 如果图片太小，放大到合适尺寸（至少800像素宽）
            height, width = image_rgb.shape[:2]
            if width < 800:
                scale = 800.0 / width
                new_width = int(width * scale)
                new_height = int(height * scale)
                image_rgb = cv2.resize(image_rgb, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
                logger.info(f"图片尺寸过小 ({width}x{height})，已放大到 {new_width}x{new_height}")
            
            # 检测并分类
            original_with_kpts, transformed, layout_str, scores, time_info = self.detector.detect_and_classify(image_rgb)
            
            if layout_str is None:
                logger.warning("棋盘检测失败")
                return None
            
            # 保存拉伸后的棋盘图像用于调试
            if transformed is not None:
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                debug_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), f"debug_board_{timestamp}.jpg")
                transformed_bgr = cv2.cvtColor(transformed, cv2.COLOR_RGB2BGR)
                cv2.imwrite(debug_path, transformed_bgr)
                logger.info(f"已保存拉伸棋盘到: {debug_path}")
            
            # 打印置信度信息
            if scores:
                avg_confidence = np.mean([conf for row in scores for conf in row if conf > 0])
                min_confidence = np.min([conf for row in scores for conf in row if conf > 0])
                logger.info(f"平均置信度: {avg_confidence:.3f}, 最低置信度: {min_confidence:.3f}")
                logger.info(f"布局字符串:\n{layout_str}")
            
            logger.info(time_info)
            
            # 解析布局字符串
            board_state = self.detector.parse_layout_string(layout_str)
            
            # 添加到稳定化缓冲区
            self.stabilizer.add(board_state)
            
            # 获取稳定结果
            stable_state = self.stabilizer.get_stable()
            
            logger.info(f"检测到 {len(stable_state)} 个稳定棋子")
            return stable_state
            
        except Exception as e:
            logger.error(f"识别失败: {e}", exc_info=True)
            return None
    
    def get_fen(self, image: np.ndarray = None) -> Optional[str]:
        """
        获取当前棋局的FEN串
        
        Args:
            image: 输入图像，None则自动捕获
            
        Returns:
            FEN串
        """
        if image is None:
            image = self.camera_manager.capture_frame()
        
        if image is None:
            return None
        
        try:
            # 转换为RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # 检测并分类
            _, _, layout_str, _, _ = self.detector.detect_and_classify(image_rgb)
            
            if layout_str is None:
                logger.warning("FEN生成: 棋盘检测失败")
                return None
            
            logger.info(f"FEN生成 - 布局字符串:\n{layout_str}")
            
            # 将布局字符串转换为二维数组
            board_2d = [[None for _ in range(9)] for _ in range(10)]
            rows = layout_str.strip().split('\n')
            
            for row_idx, row_str in enumerate(rows):
                if row_idx >= 10:
                    break
                if len(row_str) != 9:
                    continue
                
                for col_idx, char in enumerate(row_str):
                    if col_idx >= 9:
                        break
                    if char == '.' or char == 'x':
                        continue
                    board_2d[row_idx][col_idx] = char
            
            # 转换为FEN (需要反转行顺序)
            import sys
            sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            from utils import FENUtils
            fen = FENUtils.to_fen(board_2d, side_to_move='w')
            
            self.current_fen = fen
            logger.info(f"生成FEN: {fen}")
            return fen
            
        except Exception as e:
            logger.error(f"FEN生成失败: {e}", exc_info=True)
            return None
    
    def show_result(self, image: np.ndarray = None):
        """显示检测结果（调试用）"""
        if image is None:
            image = self.camera_manager.last_frame
        
        if image is None:
            return
        
        try:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            original_with_kpts, transformed, _, _, _ = \
                self.detector.detect_and_classify(image_rgb)
            
            if original_with_kpts is not None:
                display_image = cv2.cvtColor(original_with_kpts, cv2.COLOR_RGB2BGR)
                cv2.imshow('Board Detection - Keypoints', display_image)
            
            if transformed is not None:
                display_transformed = cv2.cvtColor(transformed, cv2.COLOR_RGB2BGR)
                cv2.imshow('Transformed Board', display_transformed)
            
            cv2.waitKey(1)
            
        except Exception as e:
            logger.error(f"显示结果失败: {e}")
    
    def __enter__(self):
        """上下文管理器"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.stop()
