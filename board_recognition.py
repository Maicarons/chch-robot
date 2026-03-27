"""
棋盘识别模块 - 使用 OpenCV 进行视觉识别
"""

import cv2
import numpy as np
import logging
from typing import List, Tuple, Optional, Dict
import config

logger = logging.getLogger(__name__)


class BoardRecognizer:
    """中国象棋棋盘识别器"""
    
    def __init__(self, camera_index: int = None):
        """
        初始化棋盘识别器
        
        Args:
            camera_index: 摄像头索引，None 则使用配置值
        """
        self.camera_index = camera_index or config.CAMERA_INDEX
        self.camera: Optional[cv2.VideoCapture] = None
        self.board_origin = (config.BOARD_TOP_LEFT_X, 
                           config.BOARD_TOP_LEFT_Y, 
                           config.BOARD_TOP_LEFT_Z)
        
        # 棋盘网格检测结果缓存
        self.last_board_corners = None
        self.last_frame = None
        
        logger.info(f"棋盘识别器初始化，摄像头：{self.camera_index}")
    
    def start_camera(self) -> bool:
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
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
            self.camera.set(cv2.CAP_PROP_FPS, config.CAMERA_FPS)
            
            logger.info(f"摄像头已启动：{config.CAMERA_WIDTH}x{config.CAMERA_HEIGHT}@{config.CAMERA_FPS}fps")
            return True
            
        except Exception as e:
            logger.error(f"启动摄像头失败：{e}", exc_info=True)
            return False
    
    def stop_camera(self):
        """关闭摄像头"""
        if self.camera:
            self.camera.release()
            self.camera = None
            logger.info("摄像头已关闭")
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """
        捕获一帧图像
        
        Returns:
            图像帧（BGR 格式），失败返回 None
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
    
    def detect_board_grid(self, image: np.ndarray = None) -> Optional[np.ndarray]:
        """
        检测棋盘网格
        
        Args:
            image: 输入图像，None 则使用最新捕获的帧
            
        Returns:
            棋盘角点坐标数组 (4x2)，失败返回 None
        """
        if image is None:
            image = self.capture_frame()
        
        if image is None:
            return None
        
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 高斯模糊
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Canny 边缘检测
        edges = cv2.Canny(
            blurred,
            config.CANNY_THRESHOLD1,
            config.CANNY_THRESHOLD2
        )
        
        # 查找轮廓
        contours, _ = cv2.findContours(
            edges,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        # 寻找最大的四边形轮廓作为棋盘边界
        board_contour = None
        max_area = 0
        
        for contour in contours:
            # 近似轮廓为多边形
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # 只考虑四边形
            if len(approx) == 4:
                area = cv2.contourArea(contour)
                if area > max_area and area > config.MIN_CONTOUR_AREA:
                    max_area = area
                    board_contour = approx
        
        if board_contour is None:
            logger.warning("未检测到棋盘边界")
            return None
        
        # 获取四个角点（按顺序：左上、右上、右下、左下）
        corners = board_contour.reshape(4, 2)
        
        # 排序角点
        corners = self._sort_corners(corners)
        
        self.last_board_corners = corners
        logger.info(f"检测到棋盘角点：{corners}")
        
        return corners
    
    def _sort_corners(self, corners: np.ndarray) -> np.ndarray:
        """
        对角点进行排序（左上、右上、右下、左下）
        
        Args:
            corners: 角点数组
            
        Returns:
            排序后的角点
        """
        # 按 y 坐标排序，找到最上面的两个点
        y_sorted = sorted(corners, key=lambda p: p[1])
        top_two = y_sorted[:2]
        bottom_two = y_sorted[2:]
        
        # 对上面的两个点按 x 坐标排序
        top_left = min(top_two, key=lambda p: p[0])
        top_right = max(top_two, key=lambda p: p[0])
        
        # 对下面的两个点按 x 坐标排序
        bottom_left = min(bottom_two, key=lambda p: p[0])
        bottom_right = max(bottom_two, key=lambda p: p[0])
        
        return np.array([top_left, top_right, bottom_right, bottom_left])
    
    def recognize_pieces(self, image: np.ndarray = None, 
                        board_corners: np.ndarray = None) -> Optional[List[List[Optional[str]]]]:
        """
        识别棋盘上的棋子
        
        Args:
            image: 输入图像
            board_corners: 棋盘角点，None 则尝试检测
            
        Returns:
            10x9 的二维数组，每个元素为棋子代码或 None
        """
        if image is None:
            image = self.capture_frame()
        
        if image is None:
            return None
        
        if board_corners is None:
            board_corners = self.detect_board_grid(image)
        
        if board_corners is None:
            logger.warning("无法获取棋盘网格")
            return None
        
        # 创建 10x9 的棋盘数组
        board = [[None for _ in range(9)] for _ in range(10)]
        
        # 透视变换获取棋盘俯视图
        dst_size = (450, 500)  # 9 列 x50, 10 行 x50
        dst_points = np.float32([[0, 0], [dst_size[0], 0], 
                                [dst_size[0], dst_size[1]], [0, dst_size[1]]])
        
        matrix = cv2.getPerspectiveTransform(board_corners.astype(np.float32), dst_points)
        warped = cv2.warpPerspective(image, matrix, dst_size)
        
        # 转换到 HSV 空间用于颜色识别
        hsv = cv2.cvtColor(warped, cv2.COLOR_BGR2HSV)
        
        # 遍历每个格子
        square_width = dst_size[0] // 9
        square_height = dst_size[1] // 10
        
        for row in range(10):
            for col in range(9):
                # 计算格子 ROI
                x1 = col * square_width
                y1 = row * square_height
                x2 = x1 + square_width
                y2 = y1 + square_height
                
                # 提取格子中心区域（避免边界干扰）
                margin_x = int(square_width * 0.2)
                margin_y = int(square_height * 0.2)
                roi = hsv[y1+margin_y:y2-margin_y, x1+margin_x:x2-margin_x]
                
                if roi.size == 0:
                    continue
                
                # 识别棋子颜色和类型
                piece = self._identify_piece_in_roi(roi, row, col)
                board[row][col] = piece
        
        logger.info("棋子识别完成")
        return board
    
    def _identify_piece_in_roi(self, roi_hsv: np.ndarray, 
                               row: int, col: int) -> Optional[str]:
        """
        在 ROI 区域内识别棋子
        
        Args:
            roi_hsv: HSV 格式的 ROI 图像
            row: 行索引
            col: 列索引
            
        Returns:
            棋子代码或 None
        """
        # 统计颜色分布
        red_mask1 = cv2.inRange(roi_hsv, np.array(config.RED_LOWER1), np.array(config.RED_UPPER1))
        red_mask2 = cv2.inRange(roi_hsv, np.array(config.RED_LOWER2), np.array(config.RED_UPPER2))
        red_mask = cv2.bitwise_or(red_mask1, red_mask2)
        
        black_mask = cv2.inRange(roi_hsv, np.array(config.BLACK_LOWER), np.array(config.BLACK_UPPER))
        
        red_pixels = cv2.countNonZero(red_mask)
        black_pixels = cv2.countNonZero(black_mask)
        total_pixels = roi_hsv.shape[0] * roi_hsv.shape[1]
        
        # 判断是否有棋子
        red_ratio = red_pixels / total_pixels
        black_ratio = black_pixels / total_pixels
        
        if red_ratio < 0.1 and black_ratio < 0.1:
            # 没有棋子
            return None
        
        # 简化处理：根据位置推断棋子类型
        # 实际项目需要更复杂的识别逻辑（如模板匹配、深度学习等）
        piece_type = self._infer_piece_by_position(row, col)
        
        if red_ratio > black_ratio:
            # 红方棋子
            return piece_type.upper()
        else:
            # 黑方棋子
            return piece_type.lower()
    
    def _infer_piece_by_position(self, row: int, col: int) -> str:
        """
        根据位置推断棋子类型（简化版本）
        
        Args:
            row: 行索引
            col: 列索引
            
        Returns:
            棋子基础类型（小写）
        """
        # 初始布局推断
        if row == 0 or row == 9:  # 底线
            if col == 0 or col == 8:
                return 'r'  # 车
            elif col == 1 or col == 7:
                return 'n'  # 马
            elif col == 2 or col == 6:
                return 'b'  # 象/相
            elif col == 3 or col == 5:
                return 'a'  # 士/仕
            elif col == 4:
                return 'k'  # 将/帅
        
        elif row == 2 or row == 7:  # 炮位
            if col == 1 or col == 7:
                return 'c'  # 炮
        
        elif row == 3 or row == 6:  # 卒/兵位
            if col % 2 == 0:
                return 'p'  # 卒/兵
        
        # 默认返回空（未知棋子）
        return 'p'  # 简化处理，假设为卒/兵
    
    def get_fen_from_recognition(self, image: np.ndarray = None) -> Optional[str]:
        """
        从图像识别生成 FEN 串
        
        Args:
            image: 输入图像，None 则自动捕获
            
        Returns:
            FEN 串，失败返回 None
        """
        board = self.recognize_pieces(image)
        
        if board is None:
            return None
        
        # 使用 utils 中的工具转换为 FEN
        from utils import FENUtils
        fen = FENUtils.to_fen(board, side_to_move='w')
        
        logger.info(f"生成 FEN: {fen}")
        return fen
    
    def calibrate_board(self) -> bool:
        """
        校准棋盘位置（手动辅助校准）
        
        Returns:
            是否成功校准
        """
        print("开始棋盘校准...")
        print("请确保棋盘在摄像头视野中，并按回车键捕获图像")
        
        if not self.start_camera():
            return False
        
        while True:
            frame = self.capture_frame()
            
            if frame is None:
                continue
            
            cv2.imshow('Calibration', frame)
            key = cv2.waitKey(1) & 0xFF
            
            if key == 13:  # Enter 键
                # 检测棋盘
                corners = self.detect_board_grid(frame)
                
                if corners is not None:
                    # 绘制检测到的棋盘边界
                    cv2.polylines(frame, [corners], True, (0, 255, 0), 3)
                    cv2.imshow('Calibration', frame)
                    
                    print(f"✓ 校准成功！角点坐标：{corners}")
                    self.board_origin = (corners[0][0], corners[0][1], 0)
                    cv2.waitKey(1000)
                    cv2.destroyAllWindows()
                    return True
                else:
                    print("✗ 未检测到棋盘，请调整摄像头角度后重试")
            
            elif key == 27:  # ESC 键
                print("校准取消")
                cv2.destroyAllWindows()
                return False
        
        return False
    
    def show_detection_result(self, image: np.ndarray = None):
        """
        显示检测结果（用于调试）
        
        Args:
            image: 输入图像
        """
        if image is None:
            image = self.last_frame
        
        if image is None:
            return
        
        display_image = image.copy()
        
        # 绘制棋盘边界
        if self.last_board_corners is not None:
            cv2.polylines(display_image, [self.last_board_corners], True, (0, 255, 0), 2)
        
        cv2.imshow('Board Detection', display_image)
        cv2.waitKey(1)
    
    def __enter__(self):
        """上下文管理器进入"""
        self.start_camera()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.stop_camera()


# 测试函数
def test_recognition():
    """测试棋盘识别功能"""
    print("=" * 50)
    print("棋盘识别测试")
    print("=" * 50)
    
    recognizer = BoardRecognizer()
    
    with recognizer:
        print("\n1. 测试摄像头启动")
        if recognizer.camera is not None:
            print("✓ 摄像头已启动")
        else:
            print("✗ 摄像头启动失败")
            return
        
        print("\n2. 测试图像捕获")
        frame = recognizer.capture_frame()
        if frame is not None:
            print(f"✓ 图像捕获成功，尺寸：{frame.shape}")
        else:
            print("✗ 图像捕获失败")
            return
        
        print("\n3. 测试棋盘网格检测")
        corners = recognizer.detect_board_grid(frame)
        if corners is not None:
            print(f"✓ 检测到棋盘角点：{corners}")
        else:
            print("✗ 未检测到棋盘")
        
        print("\n4. 测试棋子识别")
        board = recognizer.recognize_pieces(frame, corners)
        if board is not None:
            print("✓ 棋子识别完成")
            # 打印棋盘
            from utils import BoardUtils
            BoardUtils.print_board(board)
        else:
            print("✗ 棋子识别失败")
        
        print("\n5. 测试生成 FEN")
        fen = recognizer.get_fen_from_recognition(frame)
        if fen:
            print(f"✓ 生成 FEN: {fen}")
        else:
            print("✗ FEN 生成失败")
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    test_recognition()
