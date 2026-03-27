"""
AI 引擎模块 - 与 Pikafish 通信（基于 UCI 协议）
Pikafish 是中国象棋引擎，不需要设置变体
"""

import subprocess
import logging
from typing import Optional, List, Tuple
import config

logger = logging.getLogger(__name__)


class AIEngine:
    """中国象棋 AI 引擎（UCI 协议 - Pikafish）"""
    
    def __init__(self, engine_path: str = None):
        """
        初始化 AI 引擎
        
        Args:
            engine_path: 引擎路径
        """
        self.engine_path = engine_path or config.ENGINE_PATH
        self.process: Optional[subprocess.Popen] = None
        self.is_ready = False
        self.current_fen = config.FEN_START_POSITION
        self.move_history: List[str] = []
        
        logger.info(f"AI 引擎初始化，路径：{self.engine_path}")
    
    def start(self) -> bool:
        """
        启动 Pikafish 引擎进程
        
        Returns:
            是否成功启动
        """
        try:
            # 启动引擎进程
            self.process = subprocess.Popen(
                self.engine_path,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            logger.info("引擎进程已启动")
            
            # 发送 uci 命令初始化
            self._send_command("uci")
            
            # 等待 uciok 响应
            if self._wait_for_response("uciok", timeout=10.0):
                logger.info("引擎 UCI 模式已就绪")
                
                # 设置难度参数
                self._send_command(f"setoption name Skill Level value {config.ENGINE_DEPTH}")
                
                # 设置哈希表大小
                if config.USE_HASH_TABLE:
                    self._send_command(f"setoption name Hash value {config.HASH_SIZE_MB}")
                
                # 新游戏
                self._send_command("ucinewgame")
                
                self.is_ready = True
                return True
            else:
                logger.error("引擎未返回 uciok")
                return False
                
        except Exception as e:
            logger.error(f"启动引擎失败：{e}", exc_info=True)
            return False
    
    def stop(self):
        """停止引擎进程"""
        if self.process:
            try:
                self._send_command("quit")
                self.process.wait(timeout=2)
                self.process = None
                self.is_ready = False
                logger.info("引擎已停止")
            except Exception as e:
                logger.error(f"停止引擎时出错：{e}")
                if self.process:
                    self.process.kill()
                    self.process = None
    
    def _send_command(self, command: str):
        """
        发送命令到引擎
        
        Args:
            command: UCI 命令
        """
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.write(command + "\n")
                self.process.stdin.flush()
                logger.debug(f"发送命令：{command}")
            except Exception as e:
                logger.error(f"发送命令失败：{e}")
        else:
            logger.warning("引擎进程未运行，无法发送命令")
    
    def _wait_for_response(self, expected: str, timeout: float = 5.0) -> bool:
        """
        等待引擎响应
        
        Args:
            expected: 期望的响应字符串
            timeout: 超时时间（秒）
            
        Returns:
            是否在超时前收到期望响应
        """
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.process and self.process.poll() is not None:
                # 进程已终止
                return False
            
            try:
                line = self.process.stdout.readline().strip()
                if line:
                    logger.debug(f"收到响应：{line}")
                    
                    if expected in line:
                        return True
                        
            except Exception as e:
                logger.error(f"读取响应失败：{e}")
                return False
        
        logger.warning(f"等待响应超时：{expected}")
        return False
    
    def set_position(self, fen: str = None, moves: List[str] = None):
        """
        设置棋盘位置
        
        Args:
            fen: FEN 串，None 则使用当前 FEN
            moves: 走法历史列表
        """
        if not self.is_ready:
            logger.warning("引擎未就绪，无法设置位置")
            return
        
        fen_to_use = fen or self.current_fen
        moves_to_use = moves or self.move_history
        
        if moves_to_use:
            moves_str = " ".join(moves_to_use)
            self._send_command(f"position fen {fen_to_use} moves {moves_str}")
        else:
            self._send_command(f"position fen {fen_to_use}")
        
        logger.debug(f"设置位置：FEN={fen_to_use}, moves={moves_to_use}")
    
    def get_best_move(self, depth: int = None, think_time: int = None) -> Optional[str]:
        """
        获取 AI 最佳走法
        
        Args:
            depth: 搜索深度，None 则使用配置值
            think_time: 思考时间（毫秒），None 则使用配置值
            
        Returns:
            最佳走法（UCI 格式），失败返回 None
        """
        if not self.is_ready:
            logger.warning("引擎未就绪，无法获取走法")
            return None
        
        depth_to_use = depth or config.ENGINE_DEPTH
        time_to_use = think_time or config.THINK_TIME
        
        # 设置当前位置
        self.set_position()
        
        # 发送思考命令
        self._send_command(f"go depth {depth_to_use}")
        
        logger.info(f"AI 正在思考，深度：{depth_to_use}")
        
        # 等待 bestmove 响应
        best_move = self._parse_bestmove(timeout=time_to_use / 1000.0 + 5.0)
        
        if best_move:
            logger.info(f"AI 选择走法：{best_move}")
            self.move_history.append(best_move)
        else:
            logger.warning("AI 未能找到最佳走法")
        
        return best_move
    
    def get_current_fen_after_moves(self, start_fen: str, moves: List[str]) -> str:
        """
        根据起始 FEN 和走法历史获取当前 FEN
        通过设置 position 并使用 d 命令来获取当前 FEN
        
        Args:
            start_fen: 起始 FEN
            moves: 走法历史列表
            
        Returns:
            当前 FEN 串
        """
        if not self.is_ready:
            return start_fen
        
        try:
            # 设置位置
            if moves:
                moves_str = " ".join(moves)
                self._send_command(f"position fen {start_fen} moves {moves_str}")
            else:
                self._send_command(f"position fen {start_fen}")
            
            # 发送 d 命令（display）获取当前局面
            self._send_command("d")
            
            # 读取输出直到找到 FEN
            import time
            time.sleep(0.1)
            
            fen = None
            start_time = time.time()
            timeout = 1.0
            
            while time.time() - start_time < timeout:
                line = self.process.stdout.readline().strip()
                if line:
                    logger.debug(f"d 命令输出：{line}")
                    
                    # FEN 通常在 "Fen: " 或 "fent: " 后面
                    if "Fen:" in line or "fent:" in line:
                        # 提取 FEN
                        parts = line.split(":")
                        if len(parts) >= 2:
                            fen = parts[1].strip()
                            logger.info(f"获取到 FEN: {fen}")
                            return fen
                
                # 检查是否读到空行（表示输出结束）
                if not line:
                    time.sleep(0.05)
                    continue
            
            logger.warning("未能从 d 命令获取 FEN")
            return None
            
        except Exception as e:
            logger.error(f"获取 FEN 失败：{e}")
            return None
    
    def _parse_bestmove(self, timeout: float = 10.0) -> Optional[str]:
        """
        解析 bestmove 响应
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            最佳走法或 None
        """
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.process and self.process.poll() is not None:
                return None
            
            try:
                line = self.process.stdout.readline().strip()
                if line:
                    logger.debug(f"思考输出：{line}")
                    
                    if line.startswith("bestmove"):
                        parts = line.split()
                        if len(parts) >= 2:
                            return parts[1]
                            
            except Exception as e:
                logger.error(f"解析 bestmove 失败：{e}")
                return None
        
        logger.warning("等待 bestmove 超时")
        return None
    
    def analyze_position(self, duration: int = 3000) -> dict:
        """
        分析当前位置
        
        Args:
            duration: 分析时长（毫秒）
            
        Returns:
            分析结果字典
        """
        if not self.is_ready:
            return {}
        
        # 设置位置
        self.set_position()
        
        # 开始分析
        self._send_command(f"go movetime {duration}")
        
        result = {
            'best_move': None,
            'score': None,
            'depth': None,
            'nodes': None
        }
        
        import time
        start_time = time.time()
        
        while time.time() - start_time < (duration / 1000.0 + 2.0):
            if self.process and self.process.poll() is not None:
                break
            
            try:
                line = self.process.stdout.readline().strip()
                if line:
                    # 解析分数
                    if line.startswith("info") and "score cp" in line:
                        try:
                            parts = line.split()
                            score_idx = parts.index("cp")
                            if score_idx + 1 < len(parts):
                                result['score'] = int(parts[score_idx + 1])
                        except:
                            pass
                    
                    # 解析深度
                    if line.startswith("info") and "depth" in line:
                        try:
                            parts = line.split()
                            depth_idx = parts.index("depth")
                            if depth_idx + 1 < len(parts):
                                result['depth'] = int(parts[depth_idx + 1])
                        except:
                            pass
                    
                    # 解析最佳走法
                    if line.startswith("bestmove"):
                        parts = line.split()
                        if len(parts) >= 2:
                            result['best_move'] = parts[1]
                        break
                        
            except Exception as e:
                logger.error(f"分析位置失败：{e}")
        
        return result
    
    def reset_game(self):
        """重置游戏状态"""
        self.current_fen = config.FEN_START_POSITION
        self.move_history = []
        self._send_command("ucinewgame")
        logger.info("游戏已重置")
    
    def is_valid_move(self, move: str) -> bool:
        """
        检查走法是否合法（通过尝试执行来验证）
        
        Args:
            move: UCI 格式走法
            
        Returns:
            是否合法
        """
        # 简单验证格式
        if len(move) < 4:
            return False
        
        # 更精确的验证需要查询引擎
        # 这里简化处理
        return True
    
    def get_game_result(self) -> Optional[str]:
        """
        获取游戏结果（如果已结束）
        
        Returns:
            结果："1-0" (红胜), "0-1" (黑胜), "1/2" (和棋), 或 None (未结束)
        """
        # 通过分析位置来判断
        analysis = self.analyze_position(duration=1000)
        
        if analysis.get('best_move') == '(none)':
            # 无合法走法，游戏结束
            score = analysis.get('score', 0)
            if abs(score) > 1000:  # 将死
                return "0-1" if score < 0 else "1-0"
            else:
                return "1/2"  # 困毙或其他和棋
        
        return None
    
    def __enter__(self):
        """上下文管理器进入"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.stop()


# 测试函数
def test_engine():
    """测试 AI 引擎功能"""
    print("=" * 50)
    print("AI 引擎测试")
    print("=" * 50)
    
    with AIEngine() as engine:
        print("\n1. 测试引擎启动")
        if engine.is_ready:
            print("✓ 引擎启动成功")
        else:
            print("✗ 引擎启动失败")
            return
        
        print("\n2. 测试获取初始 FEN")
        print(f"初始 FEN: {engine.current_fen}")
        
        print("\n3. 测试 AI 思考（深度 10）")
        best_move = engine.get_best_move(depth=10)
        if best_move:
            print(f"✓ AI 走法：{best_move}")
        else:
            print("✗ AI 未能找到走法")
        
        print("\n4. 测试位置分析")
        analysis = engine.analyze_position(duration=2000)
        print(f"分析结果：{analysis}")
        
        print("\n5. 测试重置游戏")
        engine.reset_game()
        print("✓ 游戏已重置")
    
    print("\n" + "=" * 50)
    print("测试完成")
    print("=" * 50)


if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    test_engine()
