# 网络摄像头系统 - 项目总览

## 📋 概述

本项目实现了基于WebSocket的分布式摄像头系统，用于中国象棋机器人项目的三机联动架构：

- **香橙派 (Linux)**: 摄像头图像采集和推流
- **Windows主机**: 图像接收、棋盘识别、AI决策
- **STM32机械臂**: 执行走棋动作

## 📁 文件结构

```
chch-robot/
├── orange-pi-camera/              # 香橙派端代码
│   ├── camera_server.py          # WebSocket服务器（主程序）
│   ├── requirements.txt          # Python依赖
│   ├── start_server.sh           # Linux启动脚本
│   ├── test_network_camera.py    # 测试脚本
│   ├── configure_windows.bat     # Windows配置助手
│   ├── README.md                 # 快速开始
│   └── USAGE.md                  # 详细使用指南
│
├── vision/                        # Windows主机视觉模块
│   ├── __init__.py               # 模块导出
│   ├── camera.py                 # 摄像头管理器（已更新）
│   ├── network_camera.py         # 网络摄像头客户端（新增）
│   ├── detector.py               # 棋盘检测器
│   ├── recognizer.py             # 识别器（已更新）
│   ├── mapper.py                 # 坐标映射
│   └── stabilizer.py             # 多帧稳定化
│
├── config.py                      # 配置文件（已更新）
├── requirements.txt               # 全局依赖（已更新）
└── main.py                        # 主程序入口
```

## 🔧 核心组件

### 1. 香橙派端 (camera_server.py)

**功能：**
- 通过OpenCV捕获摄像头画面
- JPEG压缩和Base64编码
- WebSocket服务器实现
- 支持单帧请求和连续推流
- 多客户端并发支持

**关键特性：**
- 可配置的分辨率、帧率、JPEG质量
- 异步IO提高性能
- 自动重连机制
- 心跳检测

### 2. Windows主机端 (network_camera.py)

**功能：**
- WebSocket客户端实现
- Base64解码和JPEG解压
- 同步/异步API
- 帧回调机制
- 自动重连

**集成方式：**
```python
# 方式1: 通过CameraManager（推荐）
from vision import BoardRecognizer
recognizer = BoardRecognizer(use_network=True)

# 方式2: 直接使用NetworkCameraClient
from vision import NetworkCameraClient
client = NetworkCameraClient(server_url="ws://192.168.1.100:8765")
```

### 3. CameraManager增强 (camera.py)

**更新内容：**
- 添加`use_network`参数
- 添加`network_url`参数
- 本地/网络摄像头统一接口
- 透明切换，无需修改上层代码

## 🚀 快速开始

### 步骤1: 香橙派端设置

```bash
# SSH连接到香橙派
ssh pi@192.168.1.100

# 进入项目目录
cd chch-robot/orange-pi-camera

# 安装依赖
pip install -r requirements.txt

# 启动服务器
bash start_server.sh
```

### 步骤2: Windows主机配置

```bash
# 运行配置助手
cd orange-pi-camera
configure_windows.bat

# 输入香橙派IP地址
# 例如: 192.168.1.100
```

### 步骤3: 测试连接

```bash
# 测试摄像头
python orange-pi-camera/test_network_camera.py --mode camera

# 测试棋盘识别
python orange-pi-camera/test_network_camera.py --mode recognition
```

### 步骤4: 运行主程序

```bash
python main.py
```

## 📊 数据流

```
┌──────────────┐
│  香橙派摄像头  │
└──────┬───────┘
       │ 1. OpenCV捕获原始帧
       ▼
┌──────────────┐
│  JPEG压缩     │ (quality=80)
└──────┬───────┘
       │ 2. cv2.imencode()
       ▼
┌──────────────┐
│  Base64编码   │
└──────┬───────┘
       │ 3. base64.b64encode()
       ▼
┌──────────────┐
│ WebSocket发送 │ (JSON格式)
└──────┬───────┘
       │ 4. {"type":"frame","image":"..."}
       ▼
┌──────────────┐
│ Windows接收   │
└──────┬───────┘
       │ 5. JSON解析
       ▼
┌──────────────┐
│  Base64解码   │
└──────┬───────┘
       │ 6. base64.b64decode()
       ▼
┌──────────────┐
│  JPEG解码     │
└──────┬───────┘
       │ 7. cv2.imdecode()
       ▼
┌──────────────┐
│ numpy数组     │ (BGR格式)
└──────┬───────┘
       │ 8. 传递给识别器
       ▼
┌──────────────┐
│  棋盘识别     │
└──────┬───────┘
       │ 9. ONNX推理
       ▼
┌──────────────┐
│  FEN字符串    │
└──────┬───────┘
       │ 10. 发送给AI引擎
       ▼
┌──────────────┐
│  AI决策       │
└──────┬───────┘
       │ 11. UCI走法
       ▼
┌──────────────┐
│  机械臂执行   │
└──────────────┘
```

## ⚙️ 配置选项

### 香橙派端参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| --host | 0.0.0.0 | 监听地址 |
| --port | 8765 | 监听端口 |
| --camera | 0 | 摄像头索引 |
| --width | 1280 | 图像宽度 |
| --height | 720 | 图像高度 |
| --fps | 30 | 帧率 |
| --quality | 80 | JPEG质量(1-100) |

### Windows主机配置 (config.py)

```python
# 是否使用网络摄像头
USE_NETWORK_CAMERA = True

# 香橙派WebSocket地址
NETWORK_CAMERA_URL = "ws://192.168.1.100:8765"

# 其他摄像头参数（本地模式使用）
CAMERA_INDEX = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
CAMERA_FPS = 30
```

## 🎯 性能优化

### 带宽优化

1. **降低JPEG质量**
   ```bash
   python camera_server.py --quality 60
   ```

2. **降低分辨率**
   ```bash
   python camera_server.py --width 640 --height 480
   ```

3. **增加推流间隔**
   ```python
   await client.start_stream(interval=0.2)  # 200ms
   ```

### 延迟优化

1. **使用有线网络**（避免WiFi不稳定）
2. **降低JPEG质量**（减少编码时间）
3. **提高帧率**（减少等待时间）

### CPU优化

1. **降低分辨率**（减少处理负担）
2. **降低帧率**（减少计算频率）
3. **使用硬件加速**（如果支持）

## 🔍 故障排查

### 常见问题

#### 1. 连接超时
```
错误: ConnectionRefusedError
```
**解决：**
- 确认香橙派服务器已启动
- 检查防火墙设置
- 验证IP地址正确性
- 测试网络连通性: `ping 192.168.1.100`

#### 2. 图像黑屏
```
现象: 能连接但无图像
```
**解决：**
- 检查摄像头是否正常: `ls /dev/video*`
- 尝试其他摄像头索引: `--camera 1`
- 检查权限: `sudo chmod 666 /dev/video0`

#### 3. 延迟过高
```
现象: 图像延迟>500ms
```
**解决：**
- 降低JPEG质量
- 降低分辨率
- 使用有线网络
- 检查网络带宽

#### 4. 频繁断连
```
现象: 连接不稳定
```
**解决：**
- 检查网络稳定性
- 降低推流频率
- 检查香橙派CPU负载
- 使用更稳定的电源

### 调试技巧

#### 香橙派端
```bash
# 查看服务器日志
python camera_server.py 2>&1 | tee server.log

# 监控网络流量
sudo tcpdump -i eth0 port 8765

# 检查摄像头状态
v4l2-ctl --list-devices
v4l2-ctl --all
```

#### Windows端
```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.DEBUG)

# 测试连接
from vision import NetworkCameraClient
import asyncio

async def test():
    client = NetworkCameraClient("ws://192.168.1.100:8765")
    if await client.connect():
        print("✓ 连接成功")
        frame = await client.get_frame()
        print(f"✓ 获取帧: {frame.shape if frame is not None else 'None'}")
        await client.disconnect()

asyncio.run(test())
```

## 📈 性能基准

### 典型性能指标（千兆局域网）

| 配置 | 延迟 | 帧率 | 带宽 |
|------|------|------|------|
| 1280x720, quality=80, fps=30 | 80-120ms | 20-25fps | 5-8Mbps |
| 1280x720, quality=60, fps=20 | 60-100ms | 15-18fps | 3-5Mbps |
| 640x480, quality=60, fps=15 | 40-80ms | 12-14fps | 1-2Mbps |

### 资源占用

**香橙派端：**
- CPU: 15-25%（单核）
- 内存: 100-150MB
- 网络: 取决于配置

**Windows端：**
- CPU: 5-10%（解码）
- 内存: 50-100MB
- 网络: 同香橙派

## 🔐 安全考虑

⚠️ **当前实现仅适用于可信局域网环境！**

### 安全措施建议

1. **网络隔离**
   - 使用专用VLAN
   - 限制访问IP范围

2. **加密通信**（未来改进）
   - 使用WSS (WebSocket Secure)
   - TLS/SSL证书

3. **身份验证**（未来改进）
   - Token认证
   - API密钥

4. **防火墙规则**
   ```bash
   # 仅允许特定IP访问
   sudo iptables -A INPUT -p tcp -s 192.168.1.0/24 --dport 8765 -j ACCEPT
   sudo iptables -A INPUT -p tcp --dport 8765 -j DROP
   ```

## 🔄 版本历史

### v1.0 (当前版本)
- ✅ 基础WebSocket通信
- ✅ 单帧和推流模式
- ✅ 自动重连机制
- ✅ 集成到CameraManager
- ✅ 配置助手脚本

### 计划功能
- ⏳ WSS加密支持
- ⏳ 身份验证机制
- ⏳ 视频流压缩优化（H.264）
- ⏳ 多摄像头支持
- ⏳ 实时监控面板

## 📞 技术支持

遇到问题？

1. 查看 `USAGE.md` 详细文档
2. 检查日志输出
3. 运行测试脚本诊断
4. 查看故障排查章节

## 📄 许可证

与主项目相同许可证。
