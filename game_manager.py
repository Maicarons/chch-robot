"""
游戏管理器 - 协调整个游戏流程
"""

import time
import logging
from typing import Optional, List, Tuple
import config

logger = logging.getLogger(__name__)


class GameManager:
    """中国象棋人机对弈游戏管理器"""
    
    def __init__(self):
        """初始化游戏管理器"""
        self.board_recognizer = None
        self.ai_engine = None
        self.robot_controller = None
        
        self.current_fen = config.FEN_START_POSITION
        self.move_history: List[str] = []
        self.player_color = config.PLAYER_COLOR
        self.ai_color = "black" if self.player_color == "red" else "red"
        
        self.is_game_running = False
        self.is_player_turn = True
        
        logger.info("游戏管理器初始化")
    
    def initialize(self) -> bool:
        """
        初始化所有组件
        
        Returns:
            是否成功初始化
        """
        try:
            logger.info("开始初始化各组件...")
            
            # 1. 初始化棋盘识别器
            from board_recognition import BoardRecognizer
            self.board_recognizer = BoardRecognizer()
            logger.info("✓ 棋盘识别器已初始化")
            
            # 2. 初始化 AI 引擎
            from ai_engine import AIEngine
            self.ai_engine = AIEngine()
            logger.info("✓ AI 引擎已初始化")
            
            # 3. 初始化机械臂控制器
            from robot_control import RobotController
            self.robot_controller = RobotController()
            logger.info("✓ 机械臂控制器已初始化")
            
            return True
            
        except Exception as e:
            logger.error(f"初始化组件失败：{e}", exc_info=True)
            return False
    
    def start_components(self) -> bool:
        """
        启动所有组件
        
        Returns:
            是否成功启动
        """
        try:
            # 1. 启动摄像头
            if not self.board_recognizer.start_camera():
                logger.error("无法启动摄像头")
                return False
            logger.info("✓ 摄像头已启动")
            
            # 2. 启动 AI 引擎
            if not self.ai_engine.start():
                logger.error("无法启动 AI 引擎")
                return False
            logger.info("✓ AI 引擎已启动")
            
            # 3. 初始化机械臂
            if not self.robot_controller.initialize():
                logger.error("无法初始化机械臂")
                return False
            logger.info("✓ 机械臂已初始化")
            
            return True
            
        except Exception as e:
            logger.error(f"启动组件失败：{e}", exc_info=True)
            return False
    
    def shutdown(self):
        """关闭所有组件"""
        logger.info("正在关闭所有组件...")
        
        try:
            # 1. 关闭机械臂
            if self.robot_controller:
                self.robot_controller.shutdown()
            logger.info("✓ 机械臂已关闭")
            
            # 2. 关闭 AI 引擎
            if self.ai_engine:
                self.ai_engine.stop()
            logger.info("✓ AI 引擎已关闭")
            
            # 3. 关闭摄像头
            if self.board_recognizer:
                self.board_recognizer.stop_camera()
            logger.info("✓ 摄像头已关闭")
            
            logger.info("所有组件已关闭")
            
        except Exception as e:
            logger.error(f"关闭组件失败：{e}")
    
    def calibrate(self) -> bool:
        """
        校准系统（棋盘和机械臂）
        
        Returns:
            是否成功校准
        """
        logger.info("开始系统校准...")
        
        # 校准棋盘位置
        print("\n=== 棋盘校准 ===")
        if not self.board_recognizer.calibrate_board():
            logger.error("棋盘校准失败")
            return False
        
        # 测试机械臂
        print("\n=== 机械臂测试 ===")
        if not self.robot_controller.test_sequence():
            logger.error("机械臂测试失败")
            return False
        
        logger.info("系统校准完成")
        return True
    
    def recognize_initial_board(self) -> bool:
        """
        识别初始棋盘
        
        Returns:
            是否成功识别
        """
        logger.info("识别初始棋盘...")
        
        # 捕获图像并识别
        frame = self.board_recognizer.capture_frame()
        
        if frame is None:
            logger.error("无法捕获图像")
            return False
        
        # 生成 FEN
        fen = self.board_recognizer.get_fen_from_recognition(frame)
        
        if fen is None:
            logger.error("无法识别棋盘")
            return False
        
        self.current_fen = fen
        logger.info(f"初始棋盘 FEN: {fen}")
        
        # 显示检测结果
        if config.SHOW_DETECTION_RESULT:
            self.board_recognizer.show_detection_result(frame)
        
        return True
    
    def get_ai_move(self) -> Optional[str]:
        """
        获取 AI 走法
        
        Returns:
            AI 走法（UCI 格式），失败返回 None
        """
        logger.info("AI 正在思考...")
        
        # 设置 AI 难度
        depth = config.ENGINE_DEPTH
        think_time = config.THINK_TIME
        
        # 获取最佳走法
        best_move = self.ai_engine.get_best_move(depth=depth, think_time=think_time)
        
        if best_move:
            logger.info(f"AI 选择走法：{best_move}")
        else:
            logger.error("AI 未能找到走法")
        
        return best_move
    
    def execute_ai_move(self, uci_move: str) -> bool:
        """
        执行 AI 走法
        
        Args:
            uci_move: UCI 格式走法
            
        Returns:
            是否成功执行
        """
        logger.info(f"执行 AI 走法：{uci_move}")
        
        # 使用机械臂执行走法
        success = self.robot_controller.execute_uci_move(
            uci_move,
            board_origin=self.board_recognizer.board_origin,
            square_size_mm=config.SQUARE_SIZE_MM
        )
        
        if success:
            # 更新走法历史
            self.move_history.append(uci_move)
            logger.info(f"AI 走法执行成功，历史记录：{self.move_history}")
        else:
            logger.error(f"AI 走法执行失败：{uci_move}")
        
        return success
    
    def wait_for_player_move(self, timeout: int = None) -> bool:
        """
        等待玩家走棋
        
        Args:
            timeout: 超时时间（秒），None 则使用配置值
            
        Returns:
            玩家是否走了棋
        """
        timeout_to_use = timeout or config.WAIT_PLAYER_MOVE_TIMEOUT
        
        logger.info(f"等待玩家走棋（超时：{timeout_to_use}秒）...")
        
        start_time = time.time()
        last_fen = self.current_fen
        
        while time.time() - start_time < timeout_to_use:
            # 定期检测棋盘变化
            time.sleep(2)
            
            new_fen = self.board_recognizer.get_fen_from_recognition()
            
            if new_fen and new_fen != last_fen:
                logger.info("检测到棋盘变化")
                
                # 验证走法合法性
                if self._validate_player_move(last_fen, new_fen):
                    self.current_fen = new_fen
                    logger.info("玩家走法有效")
                    return True
                else:
                    logger.warning("玩家走法无效，请重新走棋")
                    last_fen = new_fen  # 更新为当前状态继续监控
        
        logger.warning("等待玩家走棋超时")
        return False
    
    def _validate_player_move(self, old_fen: str, new_fen: str) -> bool:
        """
        验证玩家走法是否合法
        
        Args:
            old_fen: 走棋前的 FEN
            new_fen: 走棋后的 FEN
            
        Returns:
            是否合法
        """
        logger.debug(f"验证走法：{old_fen} -> {new_fen}")
        
        if not self.ai_engine or not self.ai_engine.is_ready:
            logger.warning("AI 引擎未就绪，无法验证走法")
            return True  # 引擎不可用时暂时认为合法
        
        try:
            # 使用 Pikafish 验证走法
            # 设置当前位置
            self.ai_engine.set_position(old_fen, [])
            
            # 获取所有合法走法
            from ai_engine import AIEngine
            # 通过 go 命令获取 bestmove，如果有返回则说明位置合法
            test_move = self.ai_engine.get_best_move(depth=1)
            
            if test_move is None:
                # 没有合法走法，可能是将死或无子可动
                logger.info("当前局面没有合法走法")
                return False
            
            # 比较新旧 FEN，提取可能的走法
            move = self._extract_move_from_fen_change(old_fen, new_fen)
            
            if move is None:
                logger.warning("无法从 FEN 变化中提取走法")
                return False
            
            # 检查走法格式是否正确
            if len(move) != 4:
                logger.warning(f"走法格式错误：{move}")
                return False
            
            logger.info(f"验证通过，走法：{move}")
            return True
            
        except Exception as e:
            logger.error(f"验证走法时出错：{e}")
            return True  # 出错时暂时认为合法
    
    def detect_player_move(self) -> Optional[str]:
        """
        检测玩家的走法
        
        Returns:
            玩家走法（UCI 格式），未检测到返回 None
        """
        logger.info("检测玩家走法...")
        
        # 连续检测棋盘直到发现变化
        attempts = 0
        max_attempts = 30  # 最多尝试 30 次（约 60 秒）
        
        previous_fen = self.current_fen
        
        while attempts < max_attempts:
            time.sleep(2)
            
            current_fen = self.board_recognizer.get_fen_from_recognition()
            
            if current_fen and current_fen != previous_fen:
                logger.info(f"检测到棋盘变化：{previous_fen} -> {current_fen}")
                
                # 提取走法（比较两个 FEN 的差异）
                move = self._extract_move_from_fen_change(previous_fen, current_fen)
                
                if move:
                    logger.info(f"检测到玩家走法：{move}")
                    self.current_fen = current_fen
                    self.move_history.append(move)
                    return move
            
            attempts += 1
        
        logger.warning("未检测到玩家走法")
        return None
    
    def _extract_move_from_fen_change(self, old_fen: str, new_fen: str) -> Optional[str]:
        """
        从 FEN 变化中提取走法
        
        Args:
            old_fen: 旧 FEN
            new_fen: 新 FEN
            
        Returns:
            UCI 格式走法
        """
        from utils import FENUtils, CoordinateUtils
        
        old_board = FENUtils.parse_fen(old_fen)
        new_board = FENUtils.parse_fen(new_fen)
        
        # 查找变化的位置
        changed_positions = []
        
        for row in range(10):
            for col in range(9):
                old_piece = old_board[row][col]
                new_piece = new_board[row][col]
                
                # 如果这个位置有变化
                if old_piece != new_piece:
                    changed_positions.append({
                        'row': row,
                        'col': col,
                        'old_piece': old_piece,
                        'new_piece': new_piece
                    })
        
        logger.debug(f"发现 {len(changed_positions)} 个变化的位置")
        
        # 正常走法应该有 2-3 个变化位置
        # - 起点（棋子离开）
        # - 终点（棋子到达）
        # - 可能还有被吃掉的棋子
        
        if len(changed_positions) < 2:
            logger.warning(f"变化位置数量异常：{len(changed_positions)}")
            return None
        
        # 找出起点和终点
        from_pos = None
        to_pos = None
        
        # 策略：找到旧棋盘上有棋子而新棋盘上没有的位置（起点）
        # 和新棋盘上有棋子而旧棋盘上没有的位置（终点）
        pieces_that_moved = []  # (from_pos, piece)
        pieces_that_arrived = []  # (to_pos, piece)
        
        for change in changed_positions:
            row, col = change['row'], change['col']
            old_piece = change['old_piece']
            new_piece = change['new_piece']
            
            # 如果旧位置有棋子，新位置没有 -> 可能是起点
            if old_piece and not new_piece:
                pieces_that_moved.append((row, col, old_piece))
            
            # 如果新位置有棋子，旧位置没有 -> 可能是终点
            if new_piece and not old_piece:
                pieces_that_arrived.append((row, col, new_piece))
            
            # 如果是吃子，旧位置和新位置都有棋子，但不同
            elif old_piece and new_piece and old_piece != new_piece:
                # 这种情况需要判断哪个是移动过来的棋子
                # 简单处理：认为是吃子，新位置的棋子是移动过来的
                pieces_that_arrived.append((row, col, new_piece))
        
        # 正常情况下应该能找到起点和终点
        if len(pieces_that_moved) >= 1 and len(pieces_that_arrived) >= 1:
            from_pos = (pieces_that_moved[0][0], pieces_that_moved[0][1])
            to_pos = (pieces_that_arrived[0][0], pieces_that_arrived[0][1])
            
            # 转换为 UCI 格式
            from_uci = CoordinateUtils.indices_to_uci(*from_pos)
            to_uci = CoordinateUtils.indices_to_uci(*to_pos)
            
            move = from_uci + to_uci
            logger.info(f"提取走法：{move}")
            return move
        
        # 如果找不到，尝试最简单的方法：取前两个变化点
        if len(changed_positions) >= 2:
            from_pos = (changed_positions[0]['row'], changed_positions[0]['col'])
            to_pos = (changed_positions[1]['row'], changed_positions[1]['col'])
            
            from_uci = CoordinateUtils.indices_to_uci(*from_pos)
            to_uci = CoordinateUtils.indices_to_uci(*to_pos)
            
            move = from_uci + to_uci
            logger.warning(f"简化提取走法：{move}")
            return move
        
        logger.error("无法提取走法")
        return None
    
    def check_game_over(self) -> Tuple[bool, Optional[str]]:
        """
        检查游戏是否结束
        
        Returns:
            (是否结束，结果："1-0", "0-1", "1/2", 或 None)
        """
        if self.ai_engine:
            result = self.ai_engine.get_game_result()
            if result:
                return (True, result)
        
        return (False, None)
    
    def update_fen_after_move(self, move: str):
        """
        根据走法更新 FEN
        
        Args:
            move: UCI 格式走法
        """
        if self.ai_engine and self.ai_engine.is_ready:
            # 使用 AI 引擎计算新 FEN
            new_fen = self.ai_engine.get_current_fen_after_moves(
                config.FEN_START_POSITION, 
                self.move_history
            )
            
            if new_fen:
                self.current_fen = new_fen
                logger.info(f"FEN 已更新：{new_fen[:50]}...")
            else:
                logger.warning("无法获取新 FEN，保持原 FEN")
        else:
            logger.warning("AI 引擎未就绪，无法更新 FEN")
    
    def print_game_status(self):
        """打印游戏状态"""
        print("\n" + "=" * 50)
        print("游戏状态")
        print("=" * 50)
        print(f"当前 FEN: {self.current_fen}")
        print(f"走法数量：{len(self.move_history)}")
        print(f"走法历史：{' '.join(self.move_history[-5:])}")
        print(f"玩家颜色：{self.player_color}")
        print(f"当前回合：{'玩家' if self.is_player_turn else 'AI'}")
        print("=" * 50 + "\n")
    
    def play_game(self):
        """主游戏循环"""
        logger.info("开始游戏循环")
        self.is_game_running = True
        
        try:
            # 游戏主循环
            while self.is_game_running:
                # 1. 检查游戏是否结束
                game_over, result = self.check_game_over()
                if game_over:
                    self._handle_game_end(result)
                    break
                
                # 2. 打印状态
                self.print_game_status()
                
                if self.is_player_turn:
                    # === 玩家回合 ===
                    print("\n>>> 轮到你了，请走棋...")
                    
                    # 等待并检测玩家走棋
                    player_moved = self.wait_for_player_move()
                    
                    if not player_moved:
                        print("超时未走棋，游戏结束")
                        break
                    
                    # 切换回合
                    self.is_player_turn = False
                    
                else:
                    # === AI 回合 ===
                    print("\n>>> AI 正在思考...")
                    
                    # 获取 AI 走法
                    ai_move = self.get_ai_move()
                    
                    if ai_move:
                        # 执行 AI 走法
                        print(f"\nAI 走法：{ai_move}")
                        print("机械臂正在移动棋子...")
                        
                        success = self.execute_ai_move(ai_move)
                        
                        if not success:
                            print("机械臂执行失败，请人工协助")
                            # 可以选择暂停或继续
                    else:
                        print("AI 无法找到合法走法，游戏可能已结束")
                        break
                    
                    # 切换回合
                    self.is_player_turn = True
            
            logger.info("游戏循环结束")
            
        except KeyboardInterrupt:
            logger.info("用户中断游戏")
            print("\n游戏被用户中断")
        
        except Exception as e:
            logger.error(f"游戏过程中出错：{e}", exc_info=True)
            print(f"\n错误：{e}")
        
        finally:
            self.is_game_running = False
    
    def _handle_game_end(self, result: str):
        """
        处理游戏结束
        
        Args:
            result: 游戏结果
        """
        print("\n" + "=" * 50)
        print("游戏结束！")
        print("=" * 50)
        
        if result == "1-0":
            if self.player_color == "red":
                print("恭喜你赢了！")
            else:
                print("AI 赢了！")
        elif result == "0-1":
            if self.player_color == "black":
                print("恭喜你赢了！")
            else:
                print("AI 赢了！")
        elif result == "1/2":
            print("和棋！")
        
        print("=" * 50)
        
        # 保存棋谱
        self._save_game_record()
    
    def _save_game_record(self):
        """保存游戏记录（棋谱）"""
        import datetime
        
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"game_record_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("中国象棋人机对弈记录\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"时间：{datetime.datetime.now()}\n")
                f.write(f"玩家颜色：{self.player_color}\n")
                f.write(f"初始 FEN: {config.FEN_START_POSITION}\n\n")
                f.write("走法记录:\n")
                
                for i, move in enumerate(self.move_history):
                    if i % 2 == 0:
                        f.write(f"{i//2 + 1}. ")
                    f.write(f"{move} ")
                    
                    if i % 2 == 1:
                        f.write("\n")
                
                f.write(f"\n最终 FEN: {self.current_fen}\n")
            
            logger.info(f"游戏记录已保存到：{filename}")
            print(f"\n游戏记录已保存到：{filename}")
            
        except Exception as e:
            logger.error(f"保存游戏记录失败：{e}")
    
    def run_demo(self):
        """运行演示（不需要真实硬件）"""
        logger.info("运行演示模式")
        
        print("\n" + "=" * 50)
        print("中国象棋人机博弈系统 - 演示模式")
        print("=" * 50)
        
        # 演示步骤
        print("\n步骤 1: 初始化系统")
        if not self.initialize():
            print("✗ 系统初始化失败")
            return
        print("✓ 系统初始化成功")
        
        print("\n步骤 2: 启动组件")
        if not self.start_components():
            print("✗ 组件启动失败")
            return
        print("✓ 组件启动成功")
        
        print("\n步骤 3: 识别初始棋盘")
        print(f"初始 FEN: {self.current_fen}")
        
        print("\n步骤 4: AI 思考示例")
        ai_move = self.get_ai_move()
        if ai_move:
            print(f"AI 走法：{ai_move}")
        else:
            print("AI 未能找到走法")
        
        print("\n步骤 5: 演示结束")
        print("实际游戏中，机械臂会执行 AI 走法，然后等待玩家操作")
        
        # 关闭
        self.shutdown()
        
        print("\n" + "=" * 50)
        print("演示完成")
        print("=" * 50)
    
    def __enter__(self):
        """上下文管理器进入"""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.shutdown()


# 测试函数
def test_game_manager():
    """测试游戏管理器"""
    print("=" * 50)
    print("游戏管理器测试")
    print("=" * 50)
    
    manager = GameManager()
    
    with manager:
        # 运行演示
        manager.run_demo()


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    test_game_manager()
