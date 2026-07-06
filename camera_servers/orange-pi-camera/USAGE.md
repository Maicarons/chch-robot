# Orange Pi 摄像头使用说明

## 架构

```text
Orange Pi 摄像头
  -> camera_server.py
  -> WebSocket / JPEG
  -> CH-RO 主机
  -> 视觉识别与 AI 流程
```

## 服务端命令

```bash
python camera_server.py \
  --host 0.0.0.0 \
  --port 8765 \
  --camera 0 \
  --width 1280 \
  --height 720 \
  --fps 20 \
  --quality 80
```

常用参数：

| 参数 | 说明 |
| --- | --- |
| `--host` | 监听地址，通常为 `0.0.0.0` |
| `--port` | WebSocket 端口 |
| `--camera` | 摄像头索引 |
| `--width` / `--height` | 输出分辨率 |
| `--fps` | 目标帧率 |
| `--quality` | JPEG 压缩质量 |

## 主机端测试

```bash
python camera_servers/orange-pi-camera/test_network_camera.py --url ws://192.168.1.100:8765
```

## 故障排查

如果无法连接：

- 确认 Orange Pi 和主机在同一局域网。
- 确认端口未被防火墙阻止。
- 确认服务端日志显示正在监听。
- 确认摄像头能被 OpenCV 打开。

如果延迟过高：

- 降低分辨率。
- 降低 JPEG 质量。
- 使用有线网络。
- 降低帧率。

## 安全提示

当前服务面向可信局域网使用，未内置身份认证和加密。不要直接暴露到公网。
