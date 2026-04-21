"""
AI引擎模块 - 与Pikafish通信
"""

import subprocess
import logging
import os
from typing import Optional, List
import config

logger = logging.getLogger(__name__)


class AIEngine:
    """中国象棋AI引擎(UCI协议)"""
    
    def __init__(self, engine_path: str = None):
        # 如果路径不存在，尝试从项目根目录解析
        if engine_path is None:
            engine_path = config.ENGINE_PATH
        
        # 确保使用绝对路径
        if not os.path.isabs(engine_path):
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            engine_path = os.path.join(project_root, engine_path.lstrip('./\\'))
        
        self.engine_path = engine_path
        self.process: Optional[subprocess.Popen] = None
        self.is_ready = False
        self.current_fen = config.FEN_START_POSITION
        self.move_history: List[str] = []
        
        logger.info(f"AI引擎初始化: {self.engine_path}")
    
    def start(self) -> bool:
        """启动引擎"""
        try:
            self.process = subprocess.Popen(
                self.engine_path,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                bufsize=1
            )
            
            self._send_command("uci")
            
            if self._wait_for_response("uciok", timeout=10.0):
                # 设置为中国象棋变体
                self._send_command("setoption name UCI_Variant value xiangqi")
                self._send_command(f"setoption name Skill Level value {config.ENGINE_DEPTH}")
                
                if config.USE_HASH_TABLE:
                    self._send_command(f"setoption name Hash value {config.HASH_SIZE_MB}")
                
                self._send_command("ucinewgame")
                self.is_ready = True
                logger.info("引擎就绪（中国象棋模式）")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"启动失败: {e}", exc_info=True)
            return False
    
    def stop(self):
        """停止引擎"""
        if self.process:
            try:
                self._send_command("quit")
                self.process.wait(timeout=2)
            except:
                self.process.kill()
            finally:
                self.process = None
                self.is_ready = False
    
    def get_best_move(self, depth: int = None, think_time: int = None) -> Optional[str]:
        """获取最佳走法"""
        if not self.is_ready:
            return None
        
        depth = depth or config.ENGINE_DEPTH
        time_ms = think_time or config.THINK_TIME
        
        self.set_position()
        self._send_command(f"go depth {depth}")
        
        logger.info(f"AI思考中(深度{depth})...")
        
        best_move = self._parse_bestmove(timeout=time_ms / 1000.0 + 5.0)
        
        if best_move:
            logger.info(f"AI走法: {best_move}")
            self.move_history.append(best_move)
        
        return best_move
    
    def set_position(self, fen: str = None, moves: List[str] = None):
        """设置棋盘位置"""
        if not self.is_ready:
            return
        
        fen = fen or self.current_fen
        moves = moves or self.move_history
        
        logger.info(f"set_position调用: fen={fen}, moves={moves}")
        
        if moves:
            moves_str = " ".join(moves)
            cmd = f"position fen {fen} moves {moves_str}"
            logger.info(f"发送命令: {cmd}")
            self._send_command(cmd)
        else:
            cmd = f"position fen {fen}"
            logger.info(f"发送命令: {cmd}")
            self._send_command(cmd)
    
    def _send_command(self, command: str):
        """发送命令到引擎"""
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.write(command + "\n")
                self.process.stdin.flush()
            except Exception as e:
                logger.error(f"发送命令失败: {e}")
    
    def _wait_for_response(self, expected: str, timeout: float = 5.0) -> bool:
        """等待响应"""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.process and self.process.poll() is not None:
                return False
            
            try:
                line = self.process.stdout.readline().strip()
                if line and expected in line:
                    return True
            except:
                return False
        
        return False
    
    def _parse_bestmove(self, timeout: float = 10.0) -> Optional[str]:
        """解析bestmove响应"""
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.process and self.process.poll() is not None:
                return None
            
            try:
                line = self.process.stdout.readline().strip()
                if line and line.startswith("bestmove"):
                    parts = line.split()
                    if len(parts) >= 2:
                        return parts[1]
            except:
                return None
        
        return None
    
    def get_current_fen_after_moves(self, start_fen: str, moves: List[str]) -> Optional[str]:
        """
        根据起始FEN和走法历史获取当前FEN
        
        Args:
            start_fen: 起始FEN
            moves: 走法历史列表
            
        Returns:
            当前FEN串
        """
        if not self.is_ready:
            logger.warning("引擎未就绪，返回起始FEN")
            return start_fen
        
        try:
            # 设置位置
            if moves:
                moves_str = " ".join(moves)
                logger.info(f"设置位置: {start_fen} moves {moves_str}")
                self._send_command(f"position fen {start_fen} moves {moves_str}")
            else:
                logger.info(f"设置位置: {start_fen}")
                self._send_command(f"position fen {start_fen}")
            
            # 发送d命令(display)获取当前局面
            self._send_command("d")
            logger.info("已发送d命令，等待响应...")
            
            # 读取输出直到找到FEN
            import time
            time.sleep(0.5)  # 增加等待时间
            
            fen = None
            start_time = time.time()
            timeout = 5.0  # 增加超时时间
            all_output = []  # 记录所有输出用于调试
            
            while time.time() - start_time < timeout:
                line = self.process.stdout.readline().strip()
                if line:
                    all_output.append(line)
                    logger.debug(f"d命令输出：{line}")
                    
                    # Pikafish的d命令输出格式可能是 "Fen: xxx" 或 "fen: xxx"
                    # 尝试多种匹配方式
                    if "Fen:" in line or "fen:" in line or "FEN:" in line:
                        # 按冒号分割
                        parts = line.split(":", 1)
                        if len(parts) >= 2:
                            fen_candidate = parts[1].strip()
                            logger.info(f"找到包含Fen的行: {line}")
                            logger.info(f"提取的FEN候选: {fen_candidate}")
                            
                            # 验证FEN格式（应该包含6个部分）
                            fen_parts = fen_candidate.split()
                            if len(fen_parts) == 6:
                                logger.info(f"✅ 获取到有效FEN: {fen_candidate}")
                                return fen_candidate
                            else:
                                logger.warning(f"⚠️ FEN格式错误，部分数: {len(fen_parts)}")
                
                if not line:
                    time.sleep(0.1)
                    continue
            
            logger.warning(f"❌ 未能从d命令获取FEN")
            logger.warning(f"d命令的所有输出 ({len(all_output)}行):")
            for i, out_line in enumerate(all_output[:20]):  # 显示前20行
                logger.warning(f"  [{i}] {out_line}")
            if len(all_output) > 20:
                logger.warning(f"  ... 还有 {len(all_output) - 20} 行")
            
            # 如果d命令失败，尝试手动构建FEN
            logger.warning("尝试手动构建FEN...")
            return self._build_fen_from_position(start_fen, moves)
            
        except Exception as e:
            logger.error(f"获取FEN失败：{e}，返回起始FEN", exc_info=True)
            return start_fen
    
    def _build_fen_from_position(self, start_fen: str, moves: List[str]) -> str:
        """
        当d命令失败时，尝试通过设置位置后查询引擎来获取FEN
        """
        try:
            # 重新设置位置
            if moves:
                moves_str = " ".join(moves)
                self._send_command(f"position fen {start_fen} moves {moves_str}")
            else:
                self._send_command(f"position fen {start_fen}")
            
            # 尝试使用eval命令或其他方法
            # 对于中国象棋引擎，可能需要不同的方法
            # 这里先返回一个合理的FEN
            logger.warning("无法从引擎获取FEN，使用后备方案")
            
            # 简单的后备：返回初始FEN但更新回合数
            fen_parts = start_fen.split()
            if len(fen_parts) >= 2:
                # 根据走法数量切换回合
                if len(moves) % 2 == 0:
                    fen_parts[1] = 'w'  # 白方/红方
                else:
                    fen_parts[1] = 'b'  # 黑方
                
                # 更新步数计数器
                if len(fen_parts) >= 6:
                    move_number = int(fen_parts[5])
                    fen_parts[5] = str(move_number + len(moves) // 2)
                
                return ' '.join(fen_parts)
            
            return start_fen
            
        except Exception as e:
            logger.error(f"构建FEN失败: {e}")
            return start_fen
    
    def analyze_position(self, fen: str = None, think_time: float = 3.0, moves: List[str] = None) -> dict:
        """
        分析指定位置
        
        Args:
            fen: FEN串，None则使用当前FEN
            think_time: 思考时间（秒）
            moves: 走法历史列表，None则使用self.move_history
            
        Returns:
            分析结果字典 {'best_move', 'score', 'depth', 'pv'}
        """
        if not self.is_ready:
            logger.warning("引擎未就绪")
            return {}
        
        # 设置位置
        fen_to_use = fen or self.current_fen
        moves_to_use = moves if moves is not None else self.move_history
        logger.info(f"analyze_position: fen={fen_to_use}, moves={moves_to_use}")
        self.set_position(fen_to_use, moves_to_use)
        
        # 开始分析
        think_time_ms = int(think_time * 1000)
        self._send_command(f"go movetime {think_time_ms}")
        
        result = {
            'best_move': None,
            'score': None,
            'depth': None,
            'pv': None,
            'nodes': None
        }
        
        import time
        start_time = time.time()
        timeout = think_time + 2.0
        
        while time.time() - start_time < timeout:
            if self.process and self.process.poll() is not None:
                break
            
            try:
                line = self.process.stdout.readline().strip()
                if line:
                    logger.debug(f"分析输出：{line}")
                    
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
                    
                    # 解析PV线
                    if line.startswith("info") and " pv " in line:
                        try:
                            parts = line.split(" pv ")
                            if len(parts) >= 2:
                                result['pv'] = parts[1].strip()
                        except:
                            pass
                    
                    # 解析最佳走法
                    if line.startswith("bestmove"):
                        parts = line.split()
                        if len(parts) >= 2:
                            result['best_move'] = parts[1]
                        logger.info(f"分析完成，最佳走法: {result['best_move']}")
                        break
                        
            except Exception as e:
                logger.error(f"分析位置失败：{e}")
                break
        
        return result
    
    def get_game_result(self) -> Optional[str]:
        """
        获取游戏结果（如果已结束）
        
        Returns:
            结果："1-0" (红胜), "0-1" (黑胜), "1/2" (和棋), 或 None (未结束)
        """
        # 通过分析位置来判断
        analysis = self.analyze_position(think_time=1.0)
        
        if analysis.get('best_move') == '(none)':
            # 无合法走法，游戏结束
            score = analysis.get('score', 0)
            if abs(score) > 1000:  # 将死
                return "0-1" if score < 0 else "1-0"
            else:
                return "1/2"  # 困毙或其他和棋
        
        return None
    
    def reset_game(self):
        """重置游戏"""
        self.current_fen = config.FEN_START_POSITION
        self.move_history = []
        self._send_command("ucinewgame")
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
