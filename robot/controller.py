"""
机械臂控制模块 - 模拟和真实机械臂控制
整合自原 robot_control.py
"""

import time
import logging
from typing import Tuple, Optional, List
import config

logger = logging.getLogger(__name__)


class RobotController:
    """机械臂控制器（支持仿真和真实硬件）"""
    
    def __init__(self, robot_type: str = None):
        """
        初始化机械臂控制器
        
        Args:
            robot_type: 机械臂类型："simulation", "dobot", "elephant_robotics"
        """
        self.robot_type = robot_type or config.ROBOT_TYPE
        self.is_initialized = False
        self.current_position = (config.HOME_POSITION_X, 
                                config.HOME_POSITION_Y, 
                                config.HOME_POSITION_Z)
        self.gripper_open = True
        
        # 真实机械臂对象（根据类型加载不同库）
        self.robot_device = None
        
        logger.info(f"机械臂控制器初始化，类型：{self.robot_type}")
    
    def initialize(self) -> bool:
        """
        初始化机械臂
        
        Returns:
            是否成功初始化
        """
        try:
            if self.robot_type == "simulation":
                logger.info("使用仿真模式")
                self.is_initialized = True
                return True
            
            elif self.robot_type == "dobot":
                # TODO: 集成 Dobot 机械臂 SDK
                logger.warning("Dobot 机械臂集成待实现")
                self.is_initialized = False
                return False
            
            elif self.robot_type == "elephant_robotics":
                # TODO: 集成大象机器人 SDK
                logger.warning("大象机器人集成待实现")
                self.is_initialized = False
                return False
            
            else:
                logger.error(f"未知的机械臂类型：{self.robot_type}")
                return False
                
        except Exception as e:
            logger.error(f"初始化机械臂失败：{e}", exc_info=True)
            return False
    
    def shutdown(self):
        """关闭机械臂"""
        try:
            if self.robot_type == "simulation":
                logger.info("仿真机械臂已关闭")
            
            elif self.robot_device is not None:
                # 断开真实机械臂连接
                if hasattr(self.robot_device, 'disconnect'):
                    self.robot_device.disconnect()
            
            self.is_initialized = False
            logger.info("机械臂已关闭")
            
        except Exception as e:
            logger.error(f"关闭机械臂失败：{e}")
    
    def move_to(self, x: float, y: float, z: float, 
                speed: float = None) -> bool:
        """
        移动到目标位置
        
        Args:
            x: X 坐标（毫米）
            y: Y 坐标（毫米）
            z: Z 坐标（毫米）
            speed: 移动速度（毫米/秒），None 则使用默认值
            
        Returns:
            是否成功移动
        """
        if not self.is_initialized:
            logger.warning("机械臂未初始化")
            return False
        
        speed_to_use = speed or config.ROBOT_SPEED_FAST
        
        try:
            if self.robot_type == "simulation":
                # 仿真模式：打印移动信息
                logger.info(f"[仿真] 移动到 ({x:.1f}, {y:.1f}, {z:.1f}), 速度：{speed_to_use}mm/s")
                
                # 模拟移动时间
                distance = self._calculate_distance(self.current_position, (x, y, z))
                move_time = distance / speed_to_use
                time.sleep(move_time * 0.1)  # 加速仿真
                
                self.current_position = (x, y, z)
                return True
            
            elif self.robot_device is not None:
                # 真实机械臂：调用 SDK
                # TODO: 实现真实移动逻辑
                logger.warning("真实机械臂移动待实现")
                return False
            
            return False
            
        except Exception as e:
            logger.error(f"移动到目标位置失败：{e}", exc_info=True)
            return False
    
    def _calculate_distance(self, pos1: Tuple[float, float, float], 
                           pos2: Tuple[float, float, float]) -> float:
        """计算两点间距离"""
        return sum((a - b) ** 2 for a, b in zip(pos1, pos2)) ** 0.5
    
    def pick_piece(self, x: float, y: float, z: float = None) -> bool:
        """
        抓取棋子
        
        Args:
            x: X 坐标
            y: Y 坐标
            z: Z 坐标（棋盘平面高度），None 则自动计算
            
        Returns:
            是否成功抓取
        """
        if not self.is_initialized:
            return False
        
        z_height = z or config.GRIPPER_PICK_HEIGHT
        
        logger.info(f"开始抓取棋子，位置：({x}, {y}, {z_height})")
        
        # 步骤 1: 移动到抓取点上方
        safe_z = z_height + config.GRIPPER_MOVE_HEIGHT
        if not self.move_to(x, y, safe_z, config.ROBOT_SPEED_FAST):
            return False
        
        # 步骤 2: 下降到抓取位置
        if not self.move_to(x, y, z_height - config.GRIPPER_GRASP_HEIGHT, 
                          config.ROBOT_SPEED_SLOW):
            return False
        
        # 步骤 3: 闭合夹爪
        if not self.close_gripper():
            return False
        
        # 步骤 4: 抬起
        if not self.move_to(x, y, safe_z, config.ROBOT_SPEED_FAST):
            return False
        
        logger.info("抓取棋子完成")
        return True
    
    def place_piece(self, x: float, y: float, z: float = None) -> bool:
        """
        放置棋子
        
        Args:
            x: X 坐标
            y: Y 坐标
            z: Z 坐标，None 则自动计算
            
        Returns:
            是否成功放置
        """
        if not self.is_initialized:
            return False
        
        z_height = z or config.GRIPPER_PICK_HEIGHT
        
        logger.info(f"开始放置棋子，位置：({x}, {y}, {z_height})")
        
        # 步骤 1: 移动到放置点上方
        safe_z = z_height + config.GRIPPER_MOVE_HEIGHT
        if not self.move_to(x, y, safe_z, config.ROBOT_SPEED_FAST):
            return False
        
        # 步骤 2: 下降到放置位置
        if not self.move_to(x, y, z_height - config.GRIPPER_GRASP_HEIGHT, 
                          config.ROBOT_SPEED_SLOW):
            return False
        
        # 步骤 3: 打开夹爪
        if not self.open_gripper():
            return False
        
        # 步骤 4: 抬起
        if not self.move_to(x, y, safe_z, config.ROBOT_SPEED_FAST):
            return False
        
        logger.info("放置棋子完成")
        return True
    
    def close_gripper(self) -> bool:
        """
        闭合夹爪
        
        Returns:
            是否成功
        """
        if not self.is_initialized:
            return False
        
        if self.robot_type == "simulation":
            logger.info("[仿真] 夹爪闭合")
            self.gripper_open = False
            return True
        
        # TODO: 真实机械臂夹爪控制
        logger.warning("真实夹爪闭合控制待实现")
        return False
    
    def open_gripper(self) -> bool:
        """
        打开夹爪
        
        Returns:
            是否成功
        """
        if not self.is_initialized:
            return False
        
        if self.robot_type == "simulation":
            logger.info("[仿真] 夹爪打开")
            self.gripper_open = True
            return True
        
        # TODO: 真实机械臂夹爪控制
        logger.warning("真实夹爪打开控制待实现")
        return False
    
    def move_piece(self, from_x: float, from_y: float, 
                  to_x: float, to_y: float,
                  z: float = None) -> bool:
        """
        移动棋子从一个位置到另一个位置
        
        Args:
            from_x: 起始 X 坐标
            from_y: 起始 Y 坐标
            to_x: 目标 X 坐标
            to_y: 目标 Y 坐标
            z: Z 坐标，None 则自动计算
            
        Returns:
            是否成功移动
        """
        logger.info(f"移动棋子：({from_x}, {from_y}) -> ({to_x}, {to_y})")
        
        # 步骤 1: 移动到起始位置上方
        safe_z = (z or config.GRIPPER_PICK_HEIGHT) + config.GRIPPER_MOVE_HEIGHT
        if not self.move_to(from_x, from_y, safe_z):
            return False
        
        # 步骤 2: 抓取棋子
        if not self.pick_piece(from_x, from_y, z):
            return False
        
        # 步骤 3: 移动到目标位置上方
        if not self.move_to(to_x, to_y, safe_z):
            return False
        
        # 步骤 4: 放置棋子
        if not self.place_piece(to_x, to_y, z):
            return False
        
        logger.info("棋子移动完成")
        return True
    
    def go_home(self) -> bool:
        """
        回到 home 点
        
        Returns:
            是否成功
        """
        home_pos = (config.HOME_POSITION_X, 
                   config.HOME_POSITION_Y, 
                   config.HOME_POSITION_Z)
        
        logger.info("正在返回 home 点")
        return self.move_to(*home_pos)
    
    def execute_uci_move(self, uci_move: str, board_origin: Tuple[float, float, float],
                        square_size_mm: float = 50.0) -> bool:
        """
        执行 UCI 格式的走法
        
        Args:
            uci_move: UCI 格式走法，如 "h3e3"
            board_origin: 棋盘原点在机械臂坐标系中的位置
            square_size_mm: 格子尺寸（毫米）
            
        Returns:
            是否成功执行
        """
        import sys
        import os
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from utils import CoordinateUtils
        
        try:
            # 解析 UCI 走法
            (from_row, from_col), (to_row, to_col) = CoordinateUtils.parse_uci_move(uci_move)
            
            logger.info(f"执行 UCI 走法：{uci_move}")
            logger.info(f"棋盘坐标：({from_row}, {from_col}) -> ({to_row}, {to_col})")
            
            # 转换为机械臂坐标
            from_robot = CoordinateUtils.board_to_robot_coords(
                from_row, from_col, board_origin, square_size_mm
            )
            to_robot = CoordinateUtils.board_to_robot_coords(
                to_row, to_col, board_origin, square_size_mm
            )
            
            logger.info(f"机械臂坐标：{from_robot} -> {to_robot}")
            
            # 执行移动
            success = self.move_piece(
                from_robot[0], from_robot[1],
                to_robot[0], to_robot[1],
                board_origin[2]
            )
            
            if success:
                logger.info(f"UCI 走法执行成功：{uci_move}")
            else:
                logger.error(f"UCI 走法执行失败：{uci_move}")
            
            return success
            
        except Exception as e:
            logger.error(f"执行 UCI 走法失败：{e}", exc_info=True)
            return False
    
    def test_sequence(self) -> bool:
        """
        执行测试序列（用于调试）
        
        Returns:
            是否成功完成
        """
        logger.info("开始执行测试序列")
        
        # 测试 1: 移动到几个关键点
        points = [
            (100, 100, 150),
            (150, 100, 150),
            (150, 150, 150),
            (100, 150, 150),
        ]
        
        for i, point in enumerate(points):
            logger.info(f"测试点 {i+1}: {point}")
            if not self.move_to(*point):
                return False
            time.sleep(0.5)
        
        # 测试 2: 夹爪开合
        if not self.open_gripper():
            return False
        time.sleep(0.5)
        
        if not self.close_gripper():
            return False
        time.sleep(0.5)
        
        if not self.open_gripper():
            return False
        
        # 测试 3: 返回 home 点
        if not self.go_home():
            return False
        
        logger.info("测试序列完成")
        return True
    
    def __enter__(self):
        """上下文管理器进入"""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.shutdown()
