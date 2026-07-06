"""
香橙派摄像头服务器 - Linux端
通过WebSocket将摄像头图像传输到Windows主机
"""

import cv2
import asyncio
import websockets
import json
import base64
import logging
import signal
import sys
from typing import Optional
import numpy as np

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("OrangePiCamera")


class CameraServer:
    """摄像头WebSocket服务器"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8765, 
                 camera_index: int = 0, width: int = 1280, 
                 height: int = 720, fps: int = 30, quality: int = 80):
        """
        初始化摄像头服务器
        
        Args:
            host: 监听地址
            port: 监听端口
            camera_index: 摄像头索引
            width: 图像宽度
            height: 图像高度
            fps: 帧率
            quality: JPEG压缩质量 (1-100)
        """
        self.host = host
        self.port = port
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.fps = fps
        self.quality = quality
        
        self.camera: Optional[cv2.VideoCapture] = None
        self.server: Optional[websockets.WebSocketServerProtocol] = None
        self.clients = set()
        self.running = False
        
        logger.info(f"摄像头服务器初始化: {host}:{port}, 摄像头={camera_index}")
    
    def start_camera(self) -> bool:
        """启动摄像头"""
        try:
            self.camera = cv2.VideoCapture(self.camera_index)
            
            if not self.camera.isOpened():
                logger.error(f"无法打开摄像头 {self.camera_index}")
                return False
            
            # 设置摄像头参数
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.camera.set(cv2.CAP_PROP_FPS, self.fps)
            
            logger.info(f"摄像头已启动: {self.width}x{self.height}@{self.fps}fps")
            return True
            
        except Exception as e:
            logger.error(f"启动摄像头失败: {e}", exc_info=True)
            return False
    
    def stop_camera(self):
        """关闭摄像头"""
        if self.camera:
            self.camera.release()
            self.camera = None
            logger.info("摄像头已关闭")
    
    def capture_and_encode(self) -> Optional[str]:
        """
        捕获一帧并编码为Base64
        
        Returns:
            Base64编码的JPEG图像，失败返回None
        """
        if not self.camera or not self.camera.isOpened():
            logger.warning("摄像头未打开")
            return None
        
        ret, frame = self.camera.read()
        
        if not ret:
            logger.warning("捕获图像失败")
            return None
        
        try:
            # JPEG编码
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.quality]
            _, encoded = cv2.imencode('.jpg', frame, encode_param)
            
            # Base64编码
            base64_image = base64.b64encode(encoded).decode('utf-8')
            return base64_image
            
        except Exception as e:
            logger.error(f"图像编码失败: {e}")
            return None
    
    async def handle_client(self, websocket, path):
        """处理客户端连接"""
        client_id = id(websocket)
        self.clients.add(websocket)
        logger.info(f"客户端连接: {client_id}, 当前客户端数: {len(self.clients)}")
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    command = data.get('command')
                    
                    if command == 'get_frame':
                        # 发送单帧
                        frame_data = self.capture_and_encode()
                        if frame_data:
                            response = {
                                'type': 'frame',
                                'image': frame_data,
                                'timestamp': asyncio.get_event_loop().time()
                            }
                            await websocket.send(json.dumps(response))
                    
                    elif command == 'start_stream':
                        # 开始连续推流
                        interval = data.get('interval', 0.1)  # 默认100ms
                        logger.info(f"开始推流: 间隔={interval}s")
                        await self.stream_frames(websocket, interval)
                    
                    elif command == 'stop_stream':
                        logger.info("停止推流")
                        break
                    
                    elif command == 'ping':
                        await websocket.send(json.dumps({'type': 'pong'}))
                    
                    else:
                        logger.warning(f"未知命令: {command}")
                        
                except json.JSONDecodeError:
                    logger.error("无效的JSON消息")
                except Exception as e:
                    logger.error(f"处理消息失败: {e}", exc_info=True)
        
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"客户端断开连接: {client_id}")
        finally:
            self.clients.discard(websocket)
            logger.info(f"客户端清理完成: {client_id}")
    
    async def stream_frames(self, websocket, interval: float = 0.1):
        """
        连续推流
        
        Args:
            websocket: WebSocket连接
            interval: 推送间隔（秒）
        """
        while websocket in self.clients:
            try:
                frame_data = self.capture_and_encode()
                
                if frame_data:
                    response = {
                        'type': 'frame',
                        'image': frame_data,
                        'timestamp': asyncio.get_event_loop().time()
                    }
                    await websocket.send(json.dumps(response))
                
                await asyncio.sleep(interval)
                
            except websockets.exceptions.ConnectionClosed:
                logger.info("推流中断：连接已关闭")
                break
            except Exception as e:
                logger.error(f"推流错误: {e}")
                await asyncio.sleep(1)
    
    async def start_server(self):
        """启动WebSocket服务器"""
        if not self.start_camera():
            logger.error("摄像头启动失败，服务器终止")
            return
        
        self.running = True
        logger.info(f"启动WebSocket服务器: ws://{self.host}:{self.port}")
        
        try:
            async with websockets.serve(self.handle_client, self.host, self.port):
                logger.info("服务器已就绪，等待客户端连接...")
                
                # 保持运行直到被中断
                stop = asyncio.Future()
                
                def signal_handler():
                    logger.info("收到停止信号")
                    if not stop.done():
                        stop.set_result(True)
                
                loop = asyncio.get_event_loop()
                for sig in (signal.SIGINT, signal.SIGTERM):
                    loop.add_signal_handler(sig, signal_handler)
                
                await stop
                
        except Exception as e:
            logger.error(f"服务器错误: {e}", exc_info=True)
        finally:
            self.running = False
            self.stop_camera()
            logger.info("服务器已关闭")
    
    def run(self):
        """运行服务器（阻塞）"""
        try:
            asyncio.run(self.start_server())
        except KeyboardInterrupt:
            logger.info("用户中断")
        finally:
            self.stop_camera()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="香橙派摄像头服务器")
    parser.add_argument('--host', type=str, default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=8765, help='监听端口')
    parser.add_argument('--camera', type=int, default=0, help='摄像头索引')
    parser.add_argument('--width', type=int, default=1280, help='图像宽度')
    parser.add_argument('--height', type=int, default=720, help='图像高度')
    parser.add_argument('--fps', type=int, default=30, help='帧率')
    parser.add_argument('--quality', type=int, default=80, help='JPEG质量(1-100)')
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("香橙派摄像头服务器")
    print("=" * 60)
    print(f"监听地址: ws://{args.host}:{args.port}")
    print(f"摄像头: {args.camera}")
    print(f"分辨率: {args.width}x{args.height}@{args.fps}fps")
    print(f"JPEG质量: {args.quality}")
    print("=" * 60)
    
    server = CameraServer(
        host=args.host,
        port=args.port,
        camera_index=args.camera,
        width=args.width,
        height=args.height,
        fps=args.fps,
        quality=args.quality
    )
    
    server.run()


if __name__ == "__main__":
    main()
