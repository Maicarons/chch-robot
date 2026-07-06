# Orange Pi 摄像头实现摘要

## 已实现内容

- Linux 端摄像头服务：`camera_server.py`
- 主机端连接测试：`test_network_camera.py`
- Linux 启动脚本：`start_server.sh`
- Windows 配置辅助脚本：`configure_windows.bat`
- 快速开始、详细使用和项目概览文档

## 核心流程

1. Orange Pi 使用 OpenCV 读取摄像头帧。
2. 服务端将帧编码为 JPEG。
3. 通过 WebSocket 发送到 CH-RO 主机。
4. 主机端解码为图像帧。
5. 图像进入现有视觉识别流程。

## 当前限制

- 默认面向可信局域网，不包含认证和加密。
- 网络质量会直接影响延迟和稳定性。
- 多摄像头和 H.264 编码尚未实现。

## 后续优化方向

- 增加身份认证。
- 增加 H.264 或其他更高效的视频编码。
- 支持多摄像头配置。
- 增加 Web 管理页面。
