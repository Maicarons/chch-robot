# CH-RO Xiangqi Robot

CH-RO is a Chinese Chess (Xiangqi) human-machine robot system. It combines camera-based board recognition, Pikafish AI search, robot-arm command conversion, STM32 TCP control, and a Flask web interface.

Chinese README: [README_zh.md](README_zh.md).

## Features

- USB camera and network camera support.
- ONNX-based pose and piece classification pipeline.
- Board stabilization and dynamic move detection.
- Pikafish UCI engine integration for Xiangqi.
- Simulation and hardware robot modes.
- STM32 five-value motion protocol with homing handshake.
- Flask web interface for camera preview, recognition, AI moves, and robot status.

## Project Layout

```text
ai/                 Pikafish engine wrapper
core/               ONNX inference helpers
vision/             Camera, detector, mapper, stabilizer, recognizer
robot/              Robot protocol, TCP client, controller, firmware assets
web_simulation/     Flask backend and browser UI
model/              ONNX model files
tests/              Python tests and sample images
docs/               VitePress documentation source
firmware/stm32-tcp-server/        STM32 TCP server firmware
camera_servers/orange-pi-camera/   Orange Pi camera server
camera_servers/raspberry-pi-zero2w-usb-camera/  Raspberry Pi camera server
```

## Quick Start

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Download Pikafish and place the binary in `Pikafish/`. Update `ENGINE_PATH` in `config.py` if needed.

Run the web interface:

```bash
python web_simulation/app.py
```

Open `http://localhost:5000`.

Run the CLI:

```bash
python main.py
python main.py --demo
python main.py --test-camera
python main.py --test-engine
```

## Tests

```bash
python -m pytest tests/ -v
```

## Documentation

The documentation is managed with VitePress and includes English and Chinese pages.

```bash
npm install
npm run docs:dev
npm run docs:build
```

Docs start at `docs/index.md`.

## Configuration

Edit `config.py` for camera source, model paths, Pikafish path, robot network target, command spacing, and runtime timeouts. Set `CHRO_SKIP_STARTUP_PROMPT=1` for non-interactive Flask startup.

## Hardware Notes

The STM32 controller expects:

```text
startX,startY,endX,endY,signal
```

Homing uses:

```text
m1_angle,m2_angle,0,0,99
```

Completion acknowledgement is `STATE:5,RESULT:1`.
