# Architecture

CH-RO is a Xiangqi (Chinese chess) human-vs-robot system. A camera watches the
physical board, an ONNX vision pipeline infers the piece layout, a Pikafish UCI
engine decides the AI move, and a five-value command protocol drives an STM32
robot arm over TCP. A Flask backend exposes everything to a browser control
panel.

## Runtime Flow

```text
Camera frame (USB / network MJPEG / RTSP)
        │
        ▼
vision.BoardRecognizer
   ├─ detector  (chessboard corner detection)
   ├─ classifier (per-square piece classification)
   ├─ mapper    (image point  -> board grid)
   └─ stabilizer / dynamic_tracker (move detection)
        │  board_state  (dict of "col,row" -> piece letter)
        ▼
web_simulation (Flask)
   ├─ domain.py      pure board/FEN/turn math
   ├─ robot_cmd.py   UCI move -> five-value command
   ├─ game_logic.py  stateful transitions (AI move, baseline sync)
   └─ routes/*       REST endpoints
        │  UCI move string (e.g. "h2e2")
        ▼
ai.AIEngine (Pikafish UCI subprocess)
   └─ bestmove -> game_logic.apply_ai_best_move
        │
        ▼
robot.protocol.RobotPersistentClient (TCP)
   └─ "startX,startY,endX,endY,signal" -> STM32
```

## Top-Level Modules

| Path | Responsibility |
| --- | --- |
| `main.py` | Interactive CLI orchestration and demo/test entrypoints. |
| `game_manager.py` | Game lifecycle for the CLI path: FEN diff → UCI move extraction, win/loss detection. |
| `config.py` | All tunable runtime settings (camera, board, AI, robot, logging). |
| `utils.py` | `FENUtils`, `CoordinateUtils`, `MoveNotationUtils`, `BoardUtils`. |
| `vision/` | Camera capture, board detection, mapping, stabilization, recognition. |
| `ai/` | Pikafish process wrapper and UCI command handling. |
| `core/` | Low-level ONNX inference helpers. |
| `model/` | ONNX model assets. |
| `robot/` | Board→arm coordinate conversion, TCP protocol, simulation controller. |
| `web_simulation/` | Flask backend + browser UI (control panel). |
| `firmware/stm32-tcp-server/` | Embedded C TCP server and robot-control firmware. |
| `camera_servers/` | Raspberry Pi / Orange Pi network camera servers. |
| `tests/` | Protocol, backend loop, camera, recognizer, and stabilizer tests. |

## Web Backend (`web_simulation`)

The backend was refactored from a single ~2000-line `app.py` into a small
**composition root** plus focused helper modules and Flask Blueprints. This
keeps each file small, decouples game-state logic from HTTP plumbing, and makes
the test surface stable.

| Module | Role |
| --- | --- |
| `app.py` | **Composition root.** Owns the shared `game_state` dict and all runtime globals (recognizer, camera selection, AI engine, robot TCP client). Registers the Blueprints. Re-exports the helper functions so tests can `patch` them in one place. |
| `domain.py` | Pure, side-effect-free helpers: `board_state_to_fen`, `apply_uci_to_board_state`, `serialize/deserialize_board_state`, `points_to_uci`, `parse_*_parameter`, `ROBOT_MODE_*` constants, `STANDARD_INITIAL_BOARD/FEN`. No Flask, no globals. |
| `services.py` | Factories: `get_recognizer` (lazy camera recognizer), `get_ai_engine`, `get_robot_controller`, `get_robot_tcp_client`, camera listing. |
| `robot_cmd.py` | Converts a UCI move into the STM32 five-value command; homing commands; timeout/settle lookup; `RobotSendResult`. |
| `game_logic.py` | Stateful transitions: `apply_ai_best_move`, `current_turn_color`, `is_duplicate_player_move`, `update_current_fen`, dynamic baseline sync. |
| `startup.py` | CLI startup prompts that override grid spacing / robot IP for the current run (parsing delegated to `domain`). |
| `routes/status.py` | `/api/status`, `/api/robot/status`, `/api/cameras`. |
| `routes/camera.py` | MJPEG stream, single frame, capture, network-camera connect/disconnect, camera start/status. |
| `routes/recognition.py` | `/api/recognize`, `/api/recognize/dynamic`, `/api/ai_move`, `/api/ai_status`, `/api/player_move`, `/api/simulate_robot`. |
| `routes/game.py` | `/api/game/start`, `/api/game/reset`. |

### Shared-state design

Flask routes are stateless functions, but the game needs a persistent board
state. `app.py` holds that state in module-level globals and a `game_state`
dict. Helper modules reach those globals through `from web_simulation import app
as _app` and call patched functions like `_app.get_recognizer()` /
`_app.send_robot_command_to_controller()` rather than importing helpers
directly. This keeps the test contract stable: tests do
`patch.object(web_app, "send_robot_command_to_controller")` and the routes
actually use the patched object.

When the package is run as a script (`python web_simulation/app.py`), a
`sys.modules["web_simulation.app"] = sys.modules["__main__"]` alias guarantees
submodules and the `__main__` module share the same state object.

## Robot Transport (`robot`)

| Module | Status | Role |
| --- | --- | --- |
| `protocol.py` | **Active** | `RobotPersistentClient` — persistent TCP connection sending five-value commands `startX,startY,endX,endY,signal`. Used by the web backend and `services.py`. |
| `controller.py` | Active | `RobotController` abstraction; `execute_uci_move` for the simulation path. |
| `legacy_tcp_client.py` | **Legacy / not exported** | Old JSON-based `RobotTCPClient`. Kept for reference only; not imported by the running system. |

The five-value protocol and homing handshake are documented in
`firmware/stm32-f103-angle-plan/README.md` (see [Hardware](./hardware)); the
legacy JSON firmware and its `legacy_tcp_client.py` client are documented in
`firmware/stm32-tcp-server/PROTOCOL.md`.

## Vision Pipeline (`vision`)

`BoardRecognizer.recognize_board(image)` runs detection → classification →
mapping → stabilization and returns a `board_state` dict keyed by
`"col,row"` (e.g. `"0,3": "P"`). `recognize_dynamic_frame(frame)` adds move
detection on top: when the board is stable and a single piece moved, it emits a
`move` event with `from`/`to` grid points and the piece letter. The backend
converts that to a UCI string and a robot command.

## AI Engine (`ai`)

`AIEngine` launches the Pikafish binary as a subprocess and speaks the UCI
protocol (`uci`, `isready`, `position fen ... moves ...`, `go depth N`,
`bestmove`). The engine path and depth come from `config.py` (`ENGINE_PATH`,
`ENGINE_DEPTH`). The web backend runs the search in a background thread so the
UI can poll `/api/ai_status`.

## Domain Model

- **`board_state`** — `dict[str, str]`, keys `"col,row"` (0-8 columns, 0-9
  rows), values are piece letters (`R` red rook, `r` black rook, `P`/`p` pawn,
  `N`/`n` knight, `B`/`b` bishop/cannon-adjacent, `C`/`c` cannon, `K`/`k` king,
  `A`/`a` advisor). Empty squares are omitted.
- **FEN** — standard Xiangqi FEN. `domain.board_state_to_fen` builds it;
  `xq_utils.FENUtils` parses/round-trips it.
- **`game_state`** — the backend's live dict: `current_fen`, `board_state`,
  `move_history`, `display_history`, `is_game_running`, `player_color`,
  `ai_color`, `first_player`, `ai_thinking`, `robot_moving`, `robot_mode`,
  `vision_pause_until`, `awaiting_physical_baseline`, `robot_baseline_match_count`,
  and more. It is returned wholesale by `/api/status`.

## Next Reads

- [Configuration](./configuration) — every tunable in `config.py`.
- [REST API](/en/reference/api) — full endpoint reference.
- [Hardware](./hardware) — camera options and STM32 protocol.
