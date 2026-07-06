# Configuration

Most runtime configuration is in `config.py`.

## Camera

```python
CAMERA_INDEX = 1
USE_IP_CAMERA = True
IP_CAMERA_URL = "http://192.168.0.101:8080/?action=stream"
```

Use `CAMERA_INDEX` for a local USB camera. Use `IP_CAMERA_URL` for a LAN MJPEG or RTSP stream.

## AI Engine

```python
ENGINE_PATH = "./Pikafish/pikafish-avx2.exe"
ENGINE_DEPTH = 15
THINK_TIME = 5000
```

Keep downloaded engine binaries out of git. Prefer editing local config values instead of hard-coding paths in modules.

## Robot Network

```python
ROBOT_NETWORK_HOST = "192.168.0.102"
ROBOT_NETWORK_PORT = 8086
ROBOT_HOMING_TIMEOUT = 30.0
ROBOT_COMMAND_FILE_SPACING_MM = 34
ROBOT_COMMAND_RANK_SPACING_MM = 30
ROBOT_COMMAND_RIVER_SPACING_MM = 32
```

The Flask startup prompt can override spacing and target IP for the current run. Set `CHRO_SKIP_STARTUP_PROMPT=1` for automated tests or unattended startup.
