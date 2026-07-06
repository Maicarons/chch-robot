# Orange Pi 摄像头项目概览

本模块用于把 Orange Pi 上的摄像头画面传输到 CH-RO 主机，解决主机与棋盘距离较远或需要独立摄像头节点的问题。

## 目录结构

```text
camera_servers/orange-pi-camera/
├── camera_server.py
├── test_network_camera.py
├── start_server.sh
├── configure_windows.bat
├── requirements.txt
├── README.md
├── QUICKSTART.md
└── USAGE.md
```

## 数据流

```text
摄像头采集
  -> OpenCV 读取帧
  -> JPEG 编码
  -> WebSocket 发送
  -> 主机端接收
  -> 视觉识别
```

## 适用场景

- 摄像头需要固定在棋盘上方。
- 主机不方便直接连接 USB 摄像头。
- 需要把摄像头节点和 AI/控制主机分开部署。

## 运行建议

- 优先使用有线网络。
- 初始调试使用 `640x480` 和 `10 fps`。
- 识别稳定后再提升分辨率。
- 不要在公网环境直接暴露摄像头服务。
