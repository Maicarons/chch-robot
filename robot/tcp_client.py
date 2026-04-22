"""
机械臂TCP通信客户端 - Windows主机端
通过TCP向STM32机械臂发送走棋指令
"""

import socket
import json
import logging
import time
from typing import Optional, Dict, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class RobotCommandType(Enum):
    """机械臂指令类型"""
    MOVE_PIECE = "MOVE"      # 移动棋子
    TEST = "TEST"            # 测试指令
    HOME = "HOME"            # 回home点
    EMERGENCY_STOP = "STOP"  # 急停


class RobotResponseCode(Enum):
    """机械臂响应码"""
    SUCCESS = 0        # 成功
    ERROR_PARAM = 1    # 参数错误
    ERROR_EXECUTE = 2  # 执行错误
    ERROR_TIMEOUT = 3  # 超时
    BUSY = 4           # 忙碌


class RobotTCPClient:
    """机械臂TCP客户端"""
    
    def __init__(self, host: str = "192.168.1.200", port: int = 5000, 
                 timeout: float = 10.0, reconnect_interval: float = 5.0):
        """
        初始化TCP客户端
        
        Args:
            host: STM32服务器IP地址
            port: TCP端口
            timeout: 通信超时时间（秒）
            reconnect_interval: 重连间隔（秒）
        """
        self.host = host
        self.port = port
        self.timeout = timeout
        self.reconnect_interval = reconnect_interval
        
        self.socket: Optional[socket.socket] = None
        self.connected = False
        self.last_error: Optional[str] = None
        
        logger.info(f"机械臂TCP客户端初始化: {host}:{port}")
    
    def connect(self) -> bool:
        """
        连接到STM32服务器
        
        Returns:
            是否连接成功
        """
        try:
            logger.info(f"正在连接到机械臂 {self.host}:{self.port}...")
            
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))
            
            self.connected = True
            self.last_error = None
            
            logger.info("✓ 机械臂连接成功")
            return True
            
        except socket.timeout:
            self.last_error = f"连接超时: {self.host}:{self.port}"
            logger.error(self.last_error)
            self.connected = False
            return False
            
        except ConnectionRefusedError:
            self.last_error = f"连接被拒绝，请检查STM32是否启动: {self.host}:{self.port}"
            logger.error(self.last_error)
            self.connected = False
            return False
            
        except Exception as e:
            self.last_error = f"连接失败: {e}"
            logger.error(self.last_error, exc_info=True)
            self.connected = False
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.socket:
            try:
                self.socket.close()
                logger.info("已断开机械臂连接")
            except Exception as e:
                logger.error(f"断开连接错误: {e}")
            finally:
                self.socket = None
                self.connected = False
    
    def send_command(self, command_type: RobotCommandType, 
                    params: Dict) -> Tuple[bool, str]:
        """
        发送指令到机械臂
        
        Args:
            command_type: 指令类型
            params: 参数字典
            
        Returns:
            (是否成功, 响应消息)
        """
        if not self.connected or not self.socket:
            self.last_error = "未连接到机械臂"
            logger.warning(self.last_error)
            return False, self.last_error
        
        try:
            # 构建JSON消息
            message = {
                "cmd": command_type.value,
                "params": params,
                "timestamp": time.time()
            }
            
            # 序列化并添加结束符
            json_str = json.dumps(message, ensure_ascii=False) + "\n"
            data = json_str.encode('utf-8')
            
            logger.info(f"发送指令: {json_str.strip()}")
            
            # 发送数据
            self.socket.sendall(data)
            
            # 接收响应
            response_data = b""
            while True:
                chunk = self.socket.recv(4096)
                if not chunk:
                    break
                response_data += chunk
                if b"\n" in chunk:
                    break
            
            if not response_data:
                self.last_error = "未收到响应"
                logger.error(self.last_error)
                return False, self.last_error
            
            # 解析响应
            response_str = response_data.decode('utf-8').strip()
            response = json.loads(response_str)
            
            logger.info(f"收到响应: {response_str}")
            
            # 检查响应码
            code = response.get("code", -1)
            message = response.get("message", "")
            
            if code == RobotResponseCode.SUCCESS.value:
                self.last_error = None
                return True, message
            else:
                self.last_error = f"机械臂错误 [{code}]: {message}"
                logger.error(self.last_error)
                return False, self.last_error
                
        except socket.timeout:
            self.last_error = "等待响应超时"
            logger.error(self.last_error)
            return False, self.last_error
            
        except json.JSONDecodeError:
            self.last_error = f"无效的JSON响应: {response_data}"
            logger.error(self.last_error)
            return False, self.last_error
            
        except Exception as e:
            self.last_error = f"通信错误: {e}"
            logger.error(self.last_error, exc_info=True)
            self.connected = False
            return False, self.last_error
    
    def move_piece(self, piece_char: str, from_x: float, from_y: float,
                  to_x: float, to_y: float, is_capture: bool = False,
                  z_height: float = 0.0) -> Tuple[bool, str]:
        """
        移动棋子
        
        Args:
            piece_char: 棋子字符 (R/N/B/A/K/C/P 或 r/n/b/a/k/c/p)
            from_x: 起始X坐标（毫米）
            from_y: 起始Y坐标（毫米）
            to_x: 目标X坐标（毫米）
            to_y: 目标Y坐标（毫米）
            is_capture: 是否吃子
            z_height: Z轴高度（毫米），可选
            
        Returns:
            (是否成功, 响应消息)
        """
        params = {
            "piece": piece_char,
            "from_x": round(from_x, 2),
            "from_y": round(from_y, 2),
            "to_x": round(to_x, 2),
            "to_y": round(to_y, 2),
            "is_capture": is_capture,
            "z_height": round(z_height, 2) if z_height != 0.0 else None
        }
        
        logger.info(f"移动棋子: {piece_char} ({from_x:.1f},{from_y:.1f}) -> ({to_x:.1f},{to_y:.1f}), 吃子={is_capture}")
        
        success, message = self.send_command(RobotCommandType.MOVE_PIECE, params)
        
        if success:
            logger.info(f"✓ 棋子移动成功: {message}")
        else:
            logger.error(f"✗ 棋子移动失败: {message}")
        
        return success, message
    
    def test_sequence(self) -> Tuple[bool, str]:
        """执行测试序列"""
        logger.info("执行机械臂测试序列")
        return self.send_command(RobotCommandType.TEST, {})
    
    def go_home(self) -> Tuple[bool, str]:
        """回到home点"""
        logger.info("机械臂回home点")
        return self.send_command(RobotCommandType.HOME, {})
    
    def emergency_stop(self) -> Tuple[bool, str]:
        """急停"""
        logger.warning("!!! 机械臂急停 !!!")
        return self.send_command(RobotCommandType.EMERGENCY_STOP, {})
    
    def ping(self) -> bool:
        """心跳检测"""
        if not self.connected:
            return False
        
        try:
            # 发送简单的ping
            message = json.dumps({"cmd": "PING"}) + "\n"
            self.socket.sendall(message.encode('utf-8'))
            
            response = self.socket.recv(1024)
            return len(response) > 0
            
        except Exception:
            return False
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        return self.connected
    
    def get_last_error(self) -> Optional[str]:
        """获取最后错误信息"""
        return self.last_error
    
    def reconnect(self) -> bool:
        """重新连接"""
        logger.info(f"{self.reconnect_interval}秒后尝试重连...")
        time.sleep(self.reconnect_interval)
        return self.connect()
    
    def __enter__(self):
        """上下文管理器进入"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器退出"""
        self.disconnect()


def main():
    """测试主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="机械臂TCP客户端测试")
    parser.add_argument('--host', type=str, default='192.168.1.200', help='STM32 IP地址')
    parser.add_argument('--port', type=int, default=5000, help='TCP端口')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("机械臂TCP客户端测试")
    print("=" * 60)
    print(f"目标地址: {args.host}:{args.port}")
    print("=" * 60)
    
    client = RobotTCPClient(host=args.host, port=args.port)
    
    try:
        # 连接
        if not client.connect():
            print("❌ 连接失败")
            return
        
        print("\n✅ 连接成功\n")
        
        # 测试1: Ping
        print("测试1: Ping...")
        if client.ping():
            print("✓ Ping成功\n")
        else:
            print("✗ Ping失败\n")
        
        # 测试2: 回home点
        print("测试2: 回home点...")
        success, msg = client.go_home()
        print(f"{'✓' if success else '✗'} {msg}\n")
        
        # 测试3: 移动棋子（示例）
        print("测试3: 移动棋子...")
        success, msg = client.move_piece(
            piece_char='R',
            from_x=100.0,
            from_y=100.0,
            to_x=150.0,
            to_y=100.0,
            is_capture=False
        )
        print(f"{'✓' if success else '✗'} {msg}\n")
        
        # 测试4: 测试序列
        print("测试4: 测试序列...")
        success, msg = client.test_sequence()
        print(f"{'✓' if success else '✗'} {msg}\n")
        
    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        client.disconnect()
        print("\n测试完成")


if __name__ == "__main__":
    main()
