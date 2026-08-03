# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chinese Chess (Xiangqi) human-machine robot system. Integrates ONNX-based vision recognition, Pikafish AI engine (UCI protocol), STM32 robot arm control (TCP), and a Flask web management interface.

## Architecture

```
main.py (CLI)  ──►  game_manager.py (orchestrates game flow)
                          │
    ┌─────────────────────┼─────────────────────┐
    ▼                     ▼                     ▼
vision/                ai/                   robot/
├── camera.py          └── engine.py         ├── controller.py
├── detector.py        (Pikafish UCI)        ├── protocol.py (active: RobotPersistentClient)
├── mapper.py                                 └── legacy_tcp_client.py (legacy JSON transport, not exported)
├── stabilizer.py                             └── (STM32 firmware)
├── network_camera.py
└── recognizer.py

core/                  web_simulation/ (Flask, port 5000)
├── chessboard_detector.py   ├── app.py        (composition root / shared state)
├── keypoint_helper.py       ├── domain.py     (pure board/turn helpers)
└── runonnx/                 ├── services.py   (camera + robot client factories)
                               ├── robot_cmd.py  (five-value command layer)
                               ├── game_logic.py (stateful game transitions)
                               ├── startup.py    (CLI startup overrides)
                               └── routes/       (Blueprints: status, camera, recognition, game)
```

Data flow: Camera → RTMPose ONNX → Piece Classifier ONNX → Stabilization → FEN → Pikafish → UCI move → Robot arm coordinates → TCP to STM32

## Key Commands

```bash
# Web interface (primary)
python web_simulation/app.py

# CLI
python main.py                    # interactive shell
python main.py --demo             # demo mode
python main.py --test-camera
python main.py --test-engine

# Install
pip install -r requirements.txt

# Tests
python -m pytest tests/ -v
python -m pytest tests/test_stabilizer.py -v
```

## Configuration

All config in `config.py` at project root. Key sections:

- **Camera**: `CAMERA_INDEX`, `CAMERA_WIDTH/HEIGHT`, `USE_IP_CAMERA`, `IP_CAMERA_URL`
- **AI Engine**: `ENGINE_PATH` (Pikafish binary), `ENGINE_DEPTH`, `THINK_TIME`
- **Robot Arm**: `ROBOT_NETWORK_HOST/PORT`, `ROBOT_COMMAND_FILE_SPACING_MM` (34), `ROBOT_COMMAND_RANK_SPACING_MM` (30), `ROBOT_COMMAND_RIVER_SPACING_MM` (32)
- **Game**: `PLAYER_COLOR`, `FEN_START_POSITION`

Pikafish binary not in git — download from [Pikafish releases](https://github.com/official-pikafish/Pikafish/releases) to `./Pikafish/`.

## Key Technical Details

### Robot Arm Protocol
- Five-value command: `startX,startY,endX,endY,signal` (signal: 0=normal, 1=capture)
- Homing command: `m1_angle,m2_angle,0,0,99`
- STM32 acknowledges with `STATE:5,RESULT:1`
- `RobotPersistentClient` maintains persistent TCP connection
- `BoardToArmConfig` maps UCI squares to arm coordinates (origin at top-right, file spacing 34mm, rank spacing 30mm, river 32mm)

### Vision Pipeline
- Pose model: `model/pose/4_v6-0301.onnx`
- Classifier: `model/layout_recognition/nano_v3-0319.onnx`
- `DynamicBoardTracker` infers moves from occupancy diff with noise tolerance
- `infer_one_move_from_occupancy()` handles normal moves, captures, and noisy detections
- `_is_legal_xiangqi_move()` validates moves against Xiangqi rules
- Network cameras: HTTP MJPEG via `HttpSnapshotCapture`, RTSP via OpenCV

### Web App (web_simulation/)
- `app.py` is the **composition root**: it owns the shared `game_state` dict and the module-level globals (recognizer, robot clients, camera selection) and registers the route Blueprints onto the Flask app.
- Pure helpers live in `domain.py` (board/FEN/turn math). `services.py` provides the camera and robot-TCP client factories. `robot_cmd.py` wraps the five-value command protocol. `game_logic.py` owns the stateful transitions (AI move application, dynamic baseline sync). `startup.py` handles CLI parameter overrides.
- Routes are split by responsibility into Blueprints: `routes/status.py` (status/probe), `routes/camera.py` (camera/MJPEG), `routes/recognition.py` (recognition/AI move/dynamic tracking), `routes/game.py` (start/reset).
- Flask + CORS, threaded mode
- Two robot modes: `hardware` (real STM32) and `simulation`
- Dynamic recognition endpoint `/api/recognize/dynamic` returns events: `move`, `unchanged`, `initial_locked`, `paused`, `robot_board_confirmed`, `robot_board_waiting`, `robot_settling`
- Vision pauses during robot moves; physical baseline confirmation required in hardware mode
- `ai_command_token` prevents duplicate AI moves
- Startup prompt allows overriding grid spacing and robot IP (skip with `CHRO_SKIP_STARTUP_PROMPT=1`)

### Board State Convention
- Board keys: `"col,row"` strings (col 0-8, row 0-9, row 0 = black home rank)
- Piece chars: uppercase = Red, lowercase = Black
- UCI files: `abcdefghi`, rank 0-9

## Code Conventions

- Python 3.8+ with type annotations
- Google-style docstrings
- Per-module loggers: `logging.getLogger(__name__)`
- Log file: `./chchess.log`
- Each module has `__init__.py` with explicit `__all__` exports
