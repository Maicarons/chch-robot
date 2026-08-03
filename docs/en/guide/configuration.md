# Configuration

Almost all runtime configuration lives in `config.py`. Edit values there rather
than hard-coding paths inside modules, and keep downloaded engine binaries, logs,
and generated captures out of git.

## Camera

| Key | Default | Meaning |
| --- | --- | --- |
| `CAMERA_INDEX` | `1` | Local USB camera index. |
| `CAMERA_WIDTH` / `CAMERA_HEIGHT` | `640` / `480` | Preview / recognition frame size. |
| `CAMERA_FPS` | `30` | Capture frame rate. |
| `USE_IP_CAMERA` | `True` | Prefer the network camera URL below. |
| `IP_CAMERA_URL` | `http://192.168.0.101:8080/?action=stream` | LAN MJPEG / RTSP stream. |

Use `CAMERA_INDEX` for a local USB camera. Use `IP_CAMERA_URL` for a LAN MJPEG or
RTSP stream (see [Hardware](./hardware) for the Pi camera servers).

## Board Recognition

| Key | Default | Meaning |
| --- | --- | --- |
| `BOARD_ROWS` / `BOARD_COLS` | `10` / `9` | Xiangqi grid size. |
| `SQUARE_SIZE_MM` | `50` | Physical square size (mm). |
| `BOARD_MARGIN_MM` | `20` | Board edge margin (mm). |
| `YOLO_MODEL_PATH` | `./best.pt` | YOLOv8 piece-detection model. |
| `YOLO_CONF_THRES` | `0.10` | Detection confidence threshold. |
| `MIN_PIECE_SIZE` | `70` | Min piece pixel size (filter false hits). |
| `SNAP_DIST_THRES` | `0.45` | Max snap distance of a box center to an intersection. |
| `STABLE_WINDOW` / `STABLE_RATIO` | `5` / `0.60` | Stabilization window and ratio. |
| `AUTO_STABLE_FRAMES` | `25` | Consecutive stable frames to trigger auto-recognition. |
| `CANNY_THRESHOLD1/2` | `50` / `150` | Edge-detection thresholds. |
| `MIN_CONTOUR_AREA` / `MAX_CONTOUR_AREA` | `500` / `5000` | Piece contour area bounds. |
| `RED_LOWER1/2`, `RED_UPPER1/2`, `BLACK_LOWER`, `BLACK_UPPER` | — | HSV color ranges for red/black piece detection. |

## AI Engine

| Key | Default | Meaning |
| --- | --- | --- |
| `ENGINE_PATH` | `./Pikafish/pikafish-avx2.exe` | Pikafish binary path. |
| `ENGINE_DEPTH` | `15` | Default search depth. |
| `THINK_TIME` | `5000` | Thinking time budget (ms). |
| `USE_HASH_TABLE` | `True` | Enable the engine hash table. |
| `HASH_SIZE_MB` | `128` | Hash table size (MB). |

Download a Pikafish binary and place it under `Pikafish/`. Update `ENGINE_PATH`
if the file name differs. The web backend overrides depth per request via
`/api/ai_move` (`depth` body field).

## Robot Network & Motion

| Key | Default | Meaning |
| --- | --- | --- |
| `ROBOT_NETWORK_HOST` | `192.168.0.102` | STM32 controller IP. |
| `ROBOT_NETWORK_PORT` | `8086` | STM32 controller TCP port. |
| `ROBOT_NETWORK_TIMEOUT` | `1.0` | Socket connect/IO timeout (s). |
| `ROBOT_HOMING_TIMEOUT` | `30.0` | Homing handshake timeout (s). |
| `ROBOT_COMMAND_TIMEOUT` | `60.0` | Default command timeout (s). |
| `ROBOT_NORMAL_COMMAND_TIMEOUT` | `60.0` | Normal-move command timeout (s). |
| `ROBOT_CAPTURE_COMMAND_TIMEOUT` | `120.0` | Capture-move command timeout (s). |
| `ROBOT_CAPTURE_SETTLE_SECONDS` | `0.0` | Settle wait after a capture (s). |
| `ROBOT_NORMAL_SETTLE_SECONDS` | `0.0` | Settle wait after a normal move (s). |
| `ROBOT_POST_BASELINE_GUARD_SECONDS` | `0.0` | Guard window after an AI move (s). |
| `ROBOT_HOMING_M1_ANGLE_DEG` / `ROBOT_HOMING_M2_ANGLE_DEG` | `-17.18` / `-55.63` | Homing joint angles (deg). |
| `ROBOT_COMMAND_ORIGIN_X` / `ROBOT_COMMAND_ORIGIN_Y` | `0` / `0` | Board origin in robot coordinates (mm). |
| `ROBOT_COMMAND_FILE_SPACING_MM` | `34` | File (column) spacing (mm). |
| `ROBOT_COMMAND_RANK_SPACING_MM` | `30` | Rank (row) spacing (mm). |
| `ROBOT_COMMAND_RIVER_SPACING_MM` | `32` | Extra river gap (mm). |
| `ROBOT_SIMULATED_MOVE_SECONDS` | `15.0` | Simulated move duration (s). |
| `HOME_POSITION_X/Y/Z` | `100/100/150` | Robot home point (mm). |
| `GRIPPER_PICK_HEIGHT` / `GRIPPER_GRASP_HEIGHT` / `GRIPPER_MOVE_HEIGHT` | `80/10/50` | Gripper heights (mm). |
| `ROBOT_SPEED_FAST` / `ROBOT_SPEED_SLOW` | `100` / `30` | Motion speeds (mm/s). |
| `ROBOT_TYPE` | `"simulation"` | `"simulation"`, `"dobot"`, or `"elephant_robotics"`. |

The grid spacing and target IP can be overridden for the current run via the
Flask startup prompt. Set `CHRO_SKIP_STARTUP_PROMPT=1` for automated tests or
unattended startup to skip the prompt.

## Game

| Key | Default | Meaning |
| --- | --- | --- |
| `PLAYER_COLOR` | `"red"` | Human player color. |
| `AI_AUTO_PLAY` | `False` | Let the AI auto-play continuously (testing). |
| `WAIT_PLAYER_MOVE_TIMEOUT` | `120` | Wait-for-player timeout (s). |

## Display & Logging

| Key | Default | Meaning |
| --- | --- | --- |
| `SHOW_CAMERA_PREVIEW` | `True` | Show the camera preview window. |
| `SHOW_DETECTION_RESULT` | `True` | Overlay detection results. |
| `DEBUG_MODE` | `False` | Verbose debug overlays. |
| `LOG_LEVEL` | `"INFO"` | `DEBUG` / `INFO` / `WARNING` / `ERROR`. |
| `LOG_FILE` | `./chchess.log` | Log file path. |
| `SAVE_LOG_TO_FILE` | `True` | Persist logs to file. |

## Coordinate Calibration

| Key | Default | Meaning |
| --- | --- | --- |
| `BOARD_TOP_LEFT_X/Y/Z` | `0/0/0` | Board top-left corner in robot coordinates (mm). |
| `BOARD_ROTATION_ANGLE` | `0` | Board rotation (deg). |

## Reference

`FEN_START_POSITION` holds the standard Xiangqi opening FEN used as the default
baseline. Board/FEN math helpers live in `web_simulation/domain.py` and
`xq_utils.FENUtils`.
