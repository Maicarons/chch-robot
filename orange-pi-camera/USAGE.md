# 网络摄像头使用指南

## 系统架构

```
香橙派(Linux)                    Windows主机
┌─────────────┐                 ┌──────────────┐
│ 摄像头       │   WebSocket     │ BoardRecognizer│
│ CameraServer │◄══════════════►│ CameraManager │
│ ws://0.0.0.0│   Base64 JPEG   │ + AI引擎      │
│   :8765     │                 └──────────────┘
└─────────────┘                        │
                                       ▼
                                ┌──────────────┐
                                │ 机械臂控制器  │
                                └──────────────┘
```

## 一、香橙派端配置（Linux）

### 1. 安装依赖

```bash
cd orange-pi-camera
pip install -r requirements.txt
```

### 2. 启动摄像头服务器

```bash
# 基本启动（默认参数）
python camera_server.py

# 自定义参数
python camera_server.py \
    --host 0.0.0.0 \
    --port 8765 \
    --camera 0 \
    --width 1280 \
    --height 720 \
    --fps 30 \
    --quality 80
```

### 3. 查看香橙派IP地址

```bash
ifconfig
# 或
ip addr show
```

记下IP地址，例如：`192.168.1.100`

## 二、Windows主机配置

### 1. 安装依赖

```bash
pip install websockets>=12.0
# 或更新所有依赖
pip install -r requirements.txt
```

### 2. 修改配置文件

编辑 `config.py`：

```python
# 启用网络摄像头
USE_NETWORK_CAMERA = True

# 设置香橙派地址（替换为实际IP）
NETWORK_CAMERA_URL = "ws://192.168.1.100:8765"
```

### 3. 测试连接

```bash
# 仅测试摄像头
python orange-pi-camera/test_network_camera.py --mode camera

# 测试棋盘识别
python orange-pi-camera/test_network_camera.py --mode recognition
```

### 4. 运行主程序

```bash
python main.py
```

系统会自动使用网络摄像头进行图像采集。

## 三、独立使用NetworkCameraClient

如果需要在其他场景下使用网络摄像头：

```python
import asyncio
from vision import NetworkCameraClient
import cv2

async def main():
    # 创建客户端
    client = NetworkCameraClient(
        server_url="ws://192.168.1.100:8765"
    )
    
    # 连接
    if await client.connect():
        print("连接成功")
        
        # 获取单帧
        frame = await client.get_frame()
        if frame is not None:
            cv2.imshow('Frame', frame)
            cv2.waitKey(0)
        
        # 或者开始推流
        def on_frame(frame):
            cv2.imshow('Stream', frame)
            if cv2.waitKey(1) & 0xFF == 27:
                client.stop()
        
        client.set_frame_callback(on_frame)
        await client.start_stream(interval=0.1)
        
        await client.disconnect()

asyncio.run(main())
```

## 四、性能优化建议

### 1. 调整JPEG质量

- 高质量（90-100）：清晰但带宽占用大
- 中等质量（70-80）：平衡选择（推荐）
- 低质量（50-60）：带宽优先

```bash
python camera_server.py --quality 75
```

### 2. 调整分辨率和帧率

根据网络状况调整：

```bash
# 高速网络
python camera_server.py --width 1920 --height 1080 --fps 30

# 普通网络
python camera_server.py --width 1280 --height 720 --fps 20

# 低速网络
python camera_server.py --width 640 --height 480 --fps 15
```

### 3. 调整推流间隔

在客户端控制接收频率：

```python
# 快速响应（100ms间隔）
await client.start_stream(interval=0.1)

# 节省资源（200ms间隔）
await client.start_stream(interval=0.2)
```

## 五、故障排查

### 问题1：连接失败

**检查清单：**
1. 确认香橙派服务器已启动
2. 确认IP地址正确
3. 确认防火墙允许8765端口
4. 测试网络连通性：`ping 192.168.1.100`

**解决方案：**
```bash
# 香橙派端检查服务器状态
netstat -tuln | grep 8765

# Windows端测试端口连通性
telnet 192.168.1.100 8765
```

### 问题2：图像延迟高

**可能原因：**
- 网络带宽不足
- JPEG质量过高
- 分辨率过高

**解决方案：**
1. 降低JPEG质量：`--quality 60`
2. 降低分辨率：`--width 640 --height 480`
3. 增加推流间隔：`interval=0.2`

### 问题3：频繁断连

**可能原因：**
- 网络不稳定
- 香橙派性能不足

**解决方案：**
1. 使用有线网络连接
2. 降低帧率和分辨率
3. 检查香橙派CPU使用率

## 六、高级用法

### 1. 多客户端支持

服务器同时支持多个客户端连接：

```python
# 可以同时在多个设备上查看摄像头画面
# 设备1
python test_network_camera.py --mode camera

# 设备2（另一台电脑）
python test_network_camera.py --mode camera
```

### 2. 心跳检测

检测连接状态：

```python
is_alive = await client.ping()
if not is_alive:
    print("连接已断开")
```

### 3. 自动重连

客户端内置自动重连机制：

```python
# 断连后每5秒自动重连
await client.run_with_reconnect(stream_mode=True, interval=0.1)
```

## 七、安全注意事项

⚠️ **警告：** 当前实现未加密，仅适用于局域网环境！

如需公网部署，请考虑：
1. 使用WSS（WebSocket Secure）
2. 添加身份验证
3. 使用VPN隧道
4. 限制访问IP范围

## 八、技术细节

### WebSocket消息格式

**请求：**
```json
{"command": "get_frame"}
{"command": "start_stream", "interval": 0.1}
{"command": "stop_stream"}
{"command": "ping"}
```

**响应：**
```json
{
    "type": "frame",
    "image": "base64_encoded_jpeg_data",
    "timestamp": 1234567890.123
}
```

### 数据流

1. 香橙派捕获摄像头帧
2. OpenCV编码为JPEG（可调整质量）
3. Base64编码
4. 通过WebSocket发送JSON
5. Windows主机解码Base64
6. OpenCV解码JPEG为numpy数组
7. 传递给识别器处理

### 性能指标

典型性能（千兆局域网）：
- 延迟：50-150ms
- 帧率：10-30fps（取决于设置）
- 带宽：2-10Mbps（取决于质量和分辨率）
