"""
摄像头管理器 - 负责图像捕获和摄像头控制
"""

import cv2
import logging
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


class CameraManager:
    """摄像头管理器 - 封装OpenCV摄像头操作"""
    
    def __init__(self, camera_index: int = 0, width: int = 1280, 
                 height: int = 720, fps: int = 30):
        """
        初始化摄像头管理器
        
        Args:
            camera_index: 摄像头索引
            width: 图像宽度
            height: 图像高度
            fps: 帧率
        """
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        self.camera: Optional[cv2.VideoCapture] = None
        self.last_frame: Optional[np.ndarray] = None
        
        logger.info(f"摄像头管理器初始化: index={camera_index}, {width}x{height}@{fps}fps")
    
    def start(self) -> bool:
        """
        启动摄像头
        
        Returns:
            是否成功启动
        """
        try:
            self.camera = cv2.VideoCapture(self.camera_index)
            
            if not self.camera.isOpened():
                logger.error(f"无法打开摄像头 {self.camera_index}")
                return False
            
            # 设置摄像头参数
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.camera.set(cv2.CAP_PROP_FPS, self.fps)
            
            logger.info("摄像头已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动摄像头失败: {e}", exc_info=True)
            return False
    
    def stop(self):
        """关闭摄像头"""
        if self.camera:
            self.camera.release()
            self.camera = None
            logger.info("摄像头已关闭")
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """
        捕获一帧图像
        
        Returns:
            BGR格式图像，失败返回None
        """
        if not self.camera or not self.camera.isOpened():
            logger.warning("摄像头未打开")
            return None
        
        ret, frame = self.camera.read()
        
        if ret:
            self.last_frame = frame.copy()
            return frame
        else:
            logger.warning("捕获图像失败")
            return None
    
    def is_opened(self) -> bool:
        """检查摄像头是否打开"""
        return self.camera is not None and self.camera.isOpened()
    
    def __enter__(self):
        """上下文管理器进入"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.stop()
