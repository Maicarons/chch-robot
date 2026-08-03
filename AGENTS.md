# Repository Guidelines

## Project Structure & Module Organization

This repository implements a Xiangqi robot system with Python services, web UI, AI integration, vision models, and STM32 firmware.

- `main.py` (CLI entry), `game_manager/` (orchestration), `config.py` (configuration), and `xq_utils/` (shared Xiangqi utilities: FEN, coordinates, notation, board helpers) are the top-level modules.
- `vision/` contains camera capture, board detection, mapping, stabilization, and recognition code.
- `ai/` wraps the Pikafish UCI engine. Keep platform-specific engine paths configurable in `config.py`.
- `robot/` contains robot-arm command conversion, TCP protocol code, and controller abstractions. The active transport is `protocol.py` (`RobotPersistentClient`, five-value command protocol); `legacy_tcp_client.py` is a deprecated JSON transport kept only for reference and is not exported from the package.
- `core/` contains lower-level ONNX inference helpers; `model/` stores ONNX assets.
- `web_simulation/` is the Flask app (port 5000), decomposed into a composition root plus helper modules and route Blueprints:
  - `app.py` — composition root: owns the shared `game_state` dict and module-level globals, registers the Blueprints.
  - `domain.py` — pure board/FEN/turn helpers (single source of truth for web board math).
  - `services.py` — camera and robot-TCP client factories.
  - `robot_cmd.py` — five-value command layer (build/send robot commands).
  - `game_logic.py` — stateful game transitions (AI move application, dynamic baseline sync).
  - `startup.py` — CLI parameter overrides.
  - `routes/` — Blueprints split by responsibility: `status.py`, `camera.py`, `recognition.py`, `game.py`.
  - `templates/`, `static/` — HTML/CSS/JS frontend.
- `tests/` contains pytest/unittest tests and sample images; `camera_debug/` stores captured debug frames.
- `firmware/stm32-tcp-server/`, `firmware/stm32-f103-angle-plan/`, and `firmware/stm32-f103-keil-robot/` contain embedded C firmware and Keil artifacts.

## Build, Test, and Development Commands

```bash
pip install -r requirements.txt
python web_simulation/app.py
python main.py
python main.py --demo
python main.py --test-camera
python main.py --test-engine
python -m pytest tests/ -v
python -m pytest tests/test_stabilizer.py -v
```

Use `python web_simulation/app.py` for the Flask interface at `http://localhost:5000`. Use `python main.py` for the interactive CLI. For firmware work, run `make` from `firmware/stm32-tcp-server/` when ARM GCC and STM32 support files are installed.

## Coding Style & Naming Conventions

Use Python 3.8+ style with 4-space indentation, type annotations for public or non-trivial functions, and module loggers via `logging.getLogger(__name__)`. Prefer explicit imports and intentional `__init__.py` exports. Test names should describe behavior, for example `test_homing_sender_requires_command_specific_completion_ack`.

For C firmware, keep headers paired with implementation files, use clear protocol-oriented names such as `robot_tcp_server.c`, and compile with warning flags already present in `firmware/stm32-tcp-server/Makefile`.

## Testing Guidelines

Run the full suite with `python -m pytest tests/ -v` before changing protocol, vision, game-flow, or web API behavior. Add focused tests under `tests/test_<area>.py`; existing tests use both pytest discovery and `unittest.TestCase`. Prefer loopback sockets or simulation paths over real hardware in automated tests.

## Commit & Pull Request Guidelines

Recent history uses concise Conventional Commit-style subjects such as `feat(vision): ...`, `feat(ai): ...`, `refactor(core): ...`, and `docs: ...`. Follow that pattern when practical.

Pull requests should include a behavior summary, tests run, configuration changes, and hardware impact. Include screenshots or API examples for web UI changes, and note required Pikafish, ONNX, camera, or STM32 setup.

## Security & Configuration Tips

Do not commit local IPs, generated logs, virtual environments, or downloaded engine binaries. Keep robot host, camera URL, grid spacing, and engine path in `config.py` or environment-specific overrides.
