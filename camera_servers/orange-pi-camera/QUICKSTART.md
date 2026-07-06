# Orange Pi 摄像头快速开始

## 1. 在 Orange Pi 上启动服务

```bash
cd camera_servers/orange-pi-camera
pip install -r requirements.txt
python camera_server.py --host 0.0.0.0 --port 8765
```

查看设备 IP：

```bash
hostname -I
```

## 2. 在主机端测试连接

把下面命令中的 IP 换成 Orange Pi 的实际 IP：

```bash
python camera_servers/orange-pi-camera/test_network_camera.py --url ws://192.168.1.100:8765
```

## 3. 接入 CH-RO

在 `config.py` 中启用网络摄像头，并填写服务地址：

```python
USE_IP_CAMERA = True
IP_CAMERA_URL = "ws://192.168.1.100:8765"
```

然后启动 Web 界面：

```bash
python web_simulation/app.py
```

## 建议参数

- 分辨率：`640x480` 或 `1280x720`
- 帧率：`10-25 fps`
- JPEG 质量：`70-85`

如果延迟较高，优先降低分辨率和 JPEG 质量。
