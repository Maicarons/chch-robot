# Getting Started

## Requirements

- Python 3.8+
- Windows or Linux host
- USB camera or network MJPEG/RTSP camera
- Pikafish engine binary downloaded into `Pikafish/`
- Optional STM32 robot controller reachable on the LAN

## Install

```bash
pip install -r requirements.txt
```

Download a Pikafish binary from the official release page and place it under `Pikafish/`. Update `ENGINE_PATH` in `config.py` if the binary name differs.

## Run the Web UI

```bash
python web_simulation/app.py
```

Open `http://localhost:5000`. Use simulation mode for software-only testing and hardware mode when the STM32 controller is connected.

## Run the CLI

```bash
python main.py
python main.py --demo
python main.py --test-camera
python main.py --test-engine
```

## Run Tests

```bash
python -m pytest tests/ -v
```

Run targeted tests while editing:

```bash
python -m pytest tests/test_robot_protocol.py -v
python -m pytest tests/test_stabilizer.py -v
```
