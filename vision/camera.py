"""
摄像头管理器 - 负责图像捕获和摄像头控制
支持本地摄像头和网络摄像头（香橙派）
"""

import cv2
import logging
from typing import Optional
import numpy as np
import asyncio
import threading

logger = logging.getLogger(__name__)


class CameraManager:
    """摄像头管理器 - 封装OpenCV摄像头操作和网络摄像头"""
    
    def __init__(self, camera_index: int = 0, width: int = 1280, 
                 height: int = 720, fps: int = 30,
                 use_network: bool = False, network_url: str = "ws://192.168.1.100:8765"):
        """
        初始化摄像头管理器
        
        Args:
            camera_index: 摄像头索引
            width: 图像宽度
            height: 图像高度
            fps: 帧率
            use_network: 是否使用网络摄像头
            network_url: 网络摄像头WebSocket地址
        """
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        self.use_network = use_network
        self.network_url = network_url
        
        self.camera: Optional[cv2.VideoCapture] = None
        self.network_client = None
        self.last_frame: Optional[np.ndarray] = None
        self._network_loop = None
        self._network_thread = None
        
        if use_network:
            logger.info(f"网络摄像头管理器初始化: {network_url}")
        else:
            logger.info(f"本地摄像头管理器初始化: index={camera_index}, {width}x{height}@{fps}fps")
    
    def start(self) -> bool:
        """
        启动摄像头
        
        Returns:
            是否成功启动
        """
        try:
            if self.use_network:
                return self._start_network_camera()
            else:
                return self._start_local_camera()
        except Exception as e:
            logger.error(f"启动摄像头失败: {e}", exc_info=True)
            return False
    
    def _start_local_camera(self) -> bool:
        """启动本地摄像头"""
        try:
            self.camera = cv2.VideoCapture(self.camera_index)
            
            if not self.camera.isOpened():
                logger.error(f"无法打开摄像头 {self.camera_index}")
                return False
            
            # 设置摄像头参数
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.camera.set(cv2.CAP_PROP_FPS, self.fps)
            
            logger.info("本地摄像头已启动")
            return True
            
        except Exception as e:
            logger.error(f"启动本地摄像头失败: {e}", exc_info=True)
            return False
    
    def _start_network_camera(self) -> bool:
        """启动网络摄像头"""
        try:
            from .network_camera import NetworkCameraClient
            
            # 创建客户端
            self.network_client = NetworkCameraClient(server_url=self.network_url)
            
            # 在后台线程中运行异步连接
            def connect_async():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    success = loop.run_until_complete(self.network_client.connect())
                    if success:
                        logger.info("网络摄像头已连接")
                    else:
                        logger.error("网络摄像头连接失败")
                finally:
                    loop.close()
            
            self._network_thread = threading.Thread(target=connect_async, daemon=True)
            self._network_thread.start()
            self._network_thread.join(timeout=10)  # 等待最多10秒
            
            return self.network_client.is_connected()
            
        except Exception as e:
            logger.error(f"启动网络摄像头失败: {e}", exc_info=True)
            return False
    
    def stop(self):
        """关闭摄像头"""
        if self.use_network:
            self._stop_network_camera()
        else:
            self._stop_local_camera()
    
    def _stop_local_camera(self):
        """关闭本地摄像头"""
        if self.camera:
            self.camera.release()
            self.camera = None
            logger.info("本地摄像头已关闭")
    
    def _stop_network_camera(self):
        """关闭网络摄像头"""
        if self.network_client:
            try:
                self.network_client.stop()
                if self._network_loop:
                    self._network_loop.run_until_complete(self.network_client.disconnect())
                self.network_client = None
                logger.info("网络摄像头已断开")
            except Exception as e:
                logger.error(f"关闭网络摄像头失败: {e}")
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """
        捕获一帧图像
        
        Returns:
            BGR格式图像，失败返回None
        """
        if self.use_network:
            return self._capture_network_frame()
        else:
            return self._capture_local_frame()
    
    def _capture_local_frame(self) -> Optional[np.ndarray]:
        """捕获本地摄像头帧"""
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
    
    def _capture_network_frame(self) -> Optional[np.ndarray]:
        """捕获网络摄像头帧"""
        if not self.network_client or not self.network_client.is_connected():
            logger.warning("网络摄像头未连接")
            return None
        
        try:
            # 在新的事件循环中获取帧
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                frame = loop.run_until_complete(self.network_client.get_frame())
                if frame is not None:
                    self.last_frame = frame.copy()
                return frame
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"捕获网络帧失败: {e}")
            return None
    
    def is_opened(self) -> bool:
        """检查摄像头是否打开"""
        if self.use_network:
            return self.network_client is not None and self.network_client.is_connected()
        else:
            return self.camera is not None and self.camera.isOpened()
    
    def __enter__(self):
        """上下文管理器进入"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.stop()
