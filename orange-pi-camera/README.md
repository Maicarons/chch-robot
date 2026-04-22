# 香橙派摄像头服务器

通过WebSocket将摄像头图像传输到Windows主机。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 使用方法

### 基本启动

```bash
python camera_server.py
```

### 自定义参数

```bash
python camera_server.py --host 0.0.0.0 --port 8765 --camera 0 --width 1280 --height 720 --fps 30 --quality 80
```

### 参数说明

- `--host`: 监听地址（默认: 0.0.0.0）
- `--port`: 监听端口（默认: 8765）
- `--camera`: 摄像头索引（默认: 0）
- `--width`: 图像宽度（默认: 1280）
- `--height`: 图像高度（默认: 720）
- `--fps`: 帧率（默认: 30）
- `--quality`: JPEG压缩质量 1-100（默认: 80）

## WebSocket协议

### 客户端发送命令

```json
{"command": "get_frame"}           // 获取单帧
{"command": "start_stream", "interval": 0.1}  // 开始推流
{"command": "stop_stream"}         // 停止推流
{"command": "ping"}                // 心跳检测
```

### 服务器响应

```json
{
    "type": "frame",
    "image": "base64_encoded_jpeg_data",
    "timestamp": 1234567890.123
}
```

## 连接示例

Windows主机连接地址：`ws://<香橙派IP>:8765`
