"""
视觉识别模块 - 棋盘检测和棋子识别

提供:
- CameraManager: 摄像头管理
- ChessboardDetector: ONNX检测器
- BoardMapper: 坐标映射
- StableBoardBuffer: 多帧稳定化
- BoardRecognizer: 识别器主类
"""

from .camera import CameraManager
from .detector import ChessboardDetector
from .mapper import BoardMapper
from .stabilizer import StableBoardBuffer
from .recognizer import BoardRecognizer

__all__ = [
    'CameraManager',
    'ChessboardDetector', 
    'BoardMapper',
    'StableBoardBuffer',
    'BoardRecognizer'
]
