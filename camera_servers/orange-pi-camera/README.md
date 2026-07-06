# Orange Pi 网络摄像头服务

该目录提供一个运行在 Orange Pi 或其他 Linux 主机上的摄像头服务，用于把摄像头画面通过网络发送给 CH-RO 主机。

## 文件说明

- `camera_server.py`：摄像头服务主程序。
- `requirements.txt`：服务端 Python 依赖。
- `start_server.sh`：Linux 启动脚本。
- `test_network_camera.py`：Windows/主机端连接测试脚本。
- `configure_windows.bat`：Windows 配置辅助脚本。
- `QUICKSTART.md`：快速部署说明。
- `USAGE.md`：详细使用说明。

## 安装依赖

```bash
pip install -r requirements.txt
```

## 启动服务

```bash
cd camera_servers/orange-pi-camera
python camera_server.py --host 0.0.0.0 --port 8765
```

或使用脚本：

```bash
bash start_server.sh
```

## 在 CH-RO 中使用

在主机端配置网络摄像头地址，例如：

```text
ws://192.168.1.100:8765
```

建议在同一局域网内使用，并优先使用有线网络。
