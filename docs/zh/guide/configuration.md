# 配置

主要运行参数集中在 `config.py`。

## 摄像头

```python
CAMERA_INDEX = 1
USE_IP_CAMERA = True
IP_CAMERA_URL = "http://192.168.0.101:8080/?action=stream"
```

本地 USB 摄像头使用 `CAMERA_INDEX`。局域网 MJPEG 或 RTSP 流使用 `IP_CAMERA_URL`。

## AI 引擎

```python
ENGINE_PATH = "./Pikafish/pikafish-avx2.exe"
ENGINE_DEPTH = 15
THINK_TIME = 5000
```

不要提交下载的引擎二进制文件。优先通过本地配置修改路径，不要在模块中硬编码。

## 机器人网络

```python
ROBOT_NETWORK_HOST = "192.168.0.102"
ROBOT_NETWORK_PORT = 8086
ROBOT_HOMING_TIMEOUT = 30.0
ROBOT_COMMAND_FILE_SPACING_MM = 34
ROBOT_COMMAND_RANK_SPACING_MM = 30
ROBOT_COMMAND_RIVER_SPACING_MM = 32
```

Flask 启动提示可以临时覆盖格距和目标 IP。自动化测试或无人值守启动时设置 `CHRO_SKIP_STARTUP_PROMPT=1`。
