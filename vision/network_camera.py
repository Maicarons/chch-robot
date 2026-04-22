"""
网络摄像头客户端 - Windows主机端
从香橙派WebSocket服务器接收图像数据
"""

import asyncio
import websockets
import json
import base64
import logging
import numpy as np
import cv2
from typing import Optional, Callable
import time

logger = logging.getLogger(__name__)


class NetworkCameraClient:
    """网络摄像头WebSocket客户端"""
    
    def __init__(self, server_url: str = "ws://192.168.1.100:8765", 
                 reconnect_interval: float = 5.0):
        """
        初始化网络摄像头客户端
        
        Args:
            server_url: WebSocket服务器地址
            reconnect_interval: 重连间隔（秒）
        """
        self.server_url = server_url
        self.reconnect_interval = reconnect_interval
        
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.connected = False
        self.running = False
        self.last_frame: Optional[np.ndarray] = None
        self.frame_callback: Optional[Callable] = None
        
        logger.info(f"网络摄像头客户端初始化: {server_url}")
    
    async def connect(self) -> bool:
        """
        连接到服务器
        
        Returns:
            是否连接成功
        """
        try:
            logger.info(f"正在连接到 {self.server_url}...")
            self.websocket = await websockets.connect(self.server_url)
            self.connected = True
            logger.info("连接成功")
            return True
            
        except Exception as e:
            logger.error(f"连接失败: {e}")
            self.connected = False
            return False
    
    async def disconnect(self):
        """断开连接"""
        if self.websocket:
            try:
                await self.websocket.close()
                logger.info("已断开连接")
            except Exception as e:
                logger.error(f"断开连接错误: {e}")
            finally:
                self.websocket = None
                self.connected = False
    
    async def get_frame(self) -> Optional[np.ndarray]:
        """
        获取单帧图像
        
        Returns:
            BGR格式图像，失败返回None
        """
        if not self.connected or not self.websocket:
            logger.warning("未连接")
            return None
        
        try:
            # 发送请求
            request = json.dumps({"command": "get_frame"})
            await self.websocket.send(request)
            
            # 接收响应
            response = await self.websocket.recv()
            data = json.loads(response)
            
            if data.get('type') == 'frame':
                # 解码Base64图像
                image_data = base64.b64decode(data['image'])
                nparr = np.frombuffer(image_data, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                self.last_frame = frame
                return frame
            else:
                logger.warning(f"意外的响应类型: {data.get('type')}")
                return None
                
        except Exception as e:
            logger.error(f"获取帧失败: {e}")
            self.connected = False
            return None
    
    async def start_stream(self, interval: float = 0.1):
        """
        开始连续推流
        
        Args:
            interval: 推送间隔（秒）
        """
        if not self.connected or not self.websocket:
            logger.warning("未连接")
            return
        
        try:
            request = json.dumps({
                "command": "start_stream",
                "interval": interval
            })
            await self.websocket.send(request)
            logger.info(f"已开始推流: 间隔={interval}s")
            
            # 持续接收帧
            while self.connected and self.running:
                try:
                    response = await asyncio.wait_for(
                        self.websocket.recv(), 
                        timeout=5.0
                    )
                    data = json.loads(response)
                    
                    if data.get('type') == 'frame':
                        # 解码图像
                        image_data = base64.b64decode(data['image'])
                        nparr = np.frombuffer(image_data, np.uint8)
                        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                        
                        self.last_frame = frame
                        
                        # 调用回调函数
                        if self.frame_callback:
                            self.frame_callback(frame)
                    
                    elif data.get('type') == 'pong':
                        continue
                    
                except asyncio.TimeoutError:
                    logger.warning("接收帧超时")
                    break
                except websockets.exceptions.ConnectionClosed:
                    logger.info("推流中断：连接已关闭")
                    self.connected = False
                    break
                    
        except Exception as e:
            logger.error(f"推流错误: {e}")
            self.connected = False
    
    async def stop_stream(self):
        """停止推流"""
        if self.connected and self.websocket:
            try:
                request = json.dumps({"command": "stop_stream"})
                await self.websocket.send(request)
                logger.info("已停止推流")
            except Exception as e:
                logger.error(f"停止推流失败: {e}")
    
    async def ping(self) -> bool:
        """心跳检测"""
        if not self.connected or not self.websocket:
            return False
        
        try:
            request = json.dumps({"command": "ping"})
            await self.websocket.send(request)
            
            response = await asyncio.wait_for(self.websocket.recv(), timeout=3.0)
            data = json.loads(response)
            
            return data.get('type') == 'pong'
            
        except Exception as e:
            logger.error(f"Ping失败: {e}")
            return False
    
    def set_frame_callback(self, callback: Callable):
        """
        设置帧回调函数
        
        Args:
            callback: 回调函数 callback(frame: np.ndarray)
        """
        self.frame_callback = callback
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self.connected
    
    def get_last_frame(self) -> Optional[np.ndarray]:
        """获取最后一帧"""
        return self.last_frame
    
    async def run_with_reconnect(self, stream_mode: bool = False, interval: float = 0.1):
        """
        运行客户端（带自动重连）
        
        Args:
            stream_mode: 是否使用推流模式
            interval: 推流间隔
        """
        self.running = True
        
        while self.running:
            # 尝试连接
            if not self.connected:
                success = await self.connect()
                if not success:
                    logger.info(f"{self.reconnect_interval}秒后重试...")
                    await asyncio.sleep(self.reconnect_interval)
                    continue
            
            # 执行任务
            if stream_mode:
                await self.start_stream(interval)
            else:
                # 单次获取模式
                frame = await self.get_frame()
                if frame is not None and self.frame_callback:
                    self.frame_callback(frame)
                await asyncio.sleep(0.1)
            
            # 如果断开连接，等待重连
            if not self.connected:
                logger.info(f"连接断开，{self.reconnect_interval}秒后重连...")
                await asyncio.sleep(self.reconnect_interval)
    
    def stop(self):
        """停止客户端"""
        self.running = False
        logger.info("客户端已停止")
    
    async def __aenter__(self):
        """异步上下文管理器进入"""
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出"""
        await self.disconnect()


def main():
    """测试主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="网络摄像头客户端测试")
    parser.add_argument('--url', type=str, default='ws://192.168.1.100:8765', 
                       help='WebSocket服务器地址')
    parser.add_argument('--stream', action='store_true', help='使用推流模式')
    parser.add_argument('--interval', type=float, default=0.1, help='推流间隔（秒）')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("网络摄像头客户端测试")
    print("=" * 60)
    print(f"服务器地址: {args.url}")
    print(f"模式: {'推流' if args.stream else '单帧'}")
    if args.stream:
        print(f"推流间隔: {args.interval}s")
    print("=" * 60)
    
    client = NetworkCameraClient(server_url=args.url)
    
    def on_frame(frame):
        """帧回调函数"""
        cv2.imshow('Network Camera', frame)
        if cv2.waitKey(1) & 0xFF == 27:  # ESC键退出
            client.stop()
    
    client.set_frame_callback(on_frame)
    
    try:
        asyncio.run(client.run_with_reconnect(
            stream_mode=args.stream, 
            interval=args.interval
        ))
    except KeyboardInterrupt:
        print("\n用户中断")
    finally:
        client.stop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
