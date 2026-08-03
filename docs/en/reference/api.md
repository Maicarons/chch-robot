# REST API Reference

The Flask backend listens on `http://localhost:5000` (configurable in
`web_simulation/app.py`). All endpoints return JSON unless noted. Most endpoints
accept an optional camera selector via JSON body or query string:

| Field | Source | Meaning |
| --- | --- | --- |
| `camera_source` | body / query | `"usb"`, `"network"`, or a device string. |
| `camera_url` | body / query | Network camera URL (takes precedence over `camera_source`). |
| `camera_index` | body / query | Local USB camera index (e.g. `0`, `1`). |

When omitted, the currently active camera source is used.

## Status

### `GET /api/status`
Return the full live `game_state` dictionary.

```bash
curl http://localhost:5000/api/status
```

Response:

```json
{
  "success": true,
  "state": {
    "initial_fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
    "current_fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
    "board_state": { "0,0": "r", "0,1": "n", "...": "R" },
    "move_history": [],
    "display_history": [],
    "is_game_running": true,
    "player_color": "red",
    "ai_color": "black",
    "first_player": "red",
    "ai_thinking": false,
    "ai_analysis": { "depth": 0, "score": 0, "pv": "", "best_move": null },
    "robot_moving": false,
    "robot_mode": "hardware",
    "turn_count": 0,
    "vision_pause_until": 0.0,
    "vision_pause_reason": "",
    "awaiting_physical_baseline": false,
    "robot_baseline_match_count": 0
  }
}
```

### `GET /api/robot/status`
Robot controller connectivity. Add `?probe=1` to actually attempt a TCP probe.

```bash
curl "http://localhost:5000/api/robot/status?probe=1"
```

Response (probed):

```json
{
  "success": true,
  "connected": true,
  "status": "probed",
  "host": "192.168.0.102",
  "port": 8086,
  "error": ""
}
```

Without `probe`, `connected` is `null` and `status` is `"not_probed"`.

### `GET /api/cameras`
List locally available cameras and the active source.

```bash
curl http://localhost:5000/api/cameras
```

Response:

```json
{
  "success": true,
  "cameras": [{ "index": 0, "name": "Integrated Camera" }, { "index": 1, "name": "USB Camera" }],
  "current_camera_index": 1,
  "is_network": false,
  "source": 1
}
```

## Camera

### `GET /api/camera/stream`
MJPEG live video stream (`multipart/x-mixed-replace`). Open directly in an
`<img>` tag. A new request invalidates any previous stream token.

```html
<img src="http://localhost:5000/api/camera/stream" />
```

### `GET /api/camera/frame`
A single JPEG frame (more robust than MJPEG in some browsers). Returns
`image/jpeg`; HTTP 503 if no frame is available.

```bash
curl http://localhost:5000/api/camera/frame --output frame.jpg
```

### `POST /api/capture`
Capture one frame and return it as a base64 JPEG.

Request body (optional): `{ "camera_source": "usb" }`.

```bash
curl -X POST http://localhost:5000/api/capture \
  -H "Content-Type: application/json" \
  -d '{"camera_source":"usb"}'
```

Response:

```json
{ "success": true, "image": "<base64 jpeg>", "source": 1, "timestamp": "2026-08-01T01:00:00.123456" }
```

### `POST /api/network_camera/connect`
Register and test a LAN network camera URL. On failure the previous source is
restored.

Request body: `{ "url": "http://192.168.0.101:8080/?action=stream" }` (or
`camera_url`). The URL must start with `http://`, `https://`, `rtsp://`, or
`rtmp://`.

```bash
curl -X POST http://localhost:5000/api/network_camera/connect \
  -H "Content-Type: application/json" \
  -d '{"url":"http://192.168.0.101:8080/?action=stream"}'
```

Response (success):

```json
{ "success": true, "message": "网络摄像头连接成功", "width": 640, "height": 480, "is_network": true, "source": "http://192.168.0.101:8080/?action=stream" }
```

### `GET /api/network_camera/status`
Report whether a network camera is configured and opened.

```bash
curl http://localhost:5000/api/network_camera/status
```

### `POST /api/network_camera/disconnect`
Stop the network source and switch back to the local USB camera.

```bash
curl -X POST http://localhost:5000/api/network_camera/disconnect
```

### `GET /api/test/camera`
Test the camera by capturing and returning one base64 frame.

```bash
curl http://localhost:5000/api/test/camera
```

### `POST /api/camera/start`
Start the camera for the selected source. Idempotent if already open.

```bash
curl -X POST http://localhost:5000/api/camera/start -H "Content-Type: application/json" -d '{}'
```

### `GET /api/camera/status`
Report whether the selected camera source is open.

```bash
curl http://localhost:5000/api/camera/status
```

## Recognition & AI

### `POST /api/recognize`
Recognize the board from an uploaded base64 image, or from the live camera when
no image is supplied. Returns the `board_state` dict and derived FEN.

Request body (optional): `{ "image": "<base64 jpeg>" }`.

```bash
curl -X POST http://localhost:5000/api/recognize \
  -H "Content-Type: application/json" \
  -d '{"image":"<base64 jpeg>"}'
```

Response:

```json
{
  "success": true,
  "board_state": { "0,0": "r", "3,0": "p", "...": "R" },
  "fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
  "piece_count": 32
}
```

### `POST /api/recognize/dynamic`
Dynamically recognize the live feed and emit a `move` event once the board is
stable. This is the core loop endpoint the UI polls. It handles pause/guard
windows during robot moves and physical-baseline confirmation in hardware mode.

Request body (optional): `{ "camera_source": "usb" }`.

```bash
curl -X POST http://localhost:5000/api/recognize/dynamic -H "Content-Type: application/json" -d '{}'
```

Events (`event` field):

| Event | Meaning |
| --- | --- |
| `move` | A single piece moved; `move` contains `from`, `to`, `piece`, `code` (UCI), `robot_command` (five-value string), `source` (`player` / `duplicate` / `ignored_*`). |
| `unchanged` | Board stable, no move detected. |
| `initial_locked` | Baseline board locked at game start. |
| `paused` | Vision paused during AI/robot move. |
| `robot_board_confirmed` / `robot_board_waiting` | Physical baseline confirmation after an AI move (hardware mode). |
| `robot_settling` | Short guard window after a robot move. |

Response (move event):

```json
{
  "success": true,
  "event": "move",
  "stable": true,
  "move": {
    "from": { "col": 7, "row": 2 },
    "to": { "col": 4, "row": 2 },
    "piece": "P",
    "code": "h2e2",
    "robot_command": "289,70,189,70,0",
    "source": "player"
  },
  "board_state": { "...": "..." },
  "current_fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
  "move_history": ["h2e2"],
  "display_history": ["红方 h2e2"],
  "turn_count": 1,
  "is_game_running": true,
  "ai_color": "black",
  "player_color": "red",
  "first_player": "red",
  "robot_mode": "hardware",
  "current_turn": "black",
  "vision_paused": false,
  "vision_pause_remaining": 0.0
}
```

### `POST /api/ai_move`
Start the (async) AI search in a background thread. The UI then polls
`/api/ai_status`.

Request body (optional): `{ "depth": 8 }`. Defaults to `8`. Errors if it is not
the AI's turn or the AI is already thinking.

```bash
curl -X POST http://localhost:5000/api/ai_move -H "Content-Type: application/json" -d '{"depth":10}'
```

Response:

```json
{ "success": true, "message": "AI思考已启动" }
```

### `GET /api/ai_status`
AI thinking state and latest analysis.

```bash
curl http://localhost:5000/api/ai_status
```

Response:

```json
{
  "success": true,
  "ai_thinking": false,
  "analysis": {
    "depth": 10,
    "score": 36,
    "pv": "h2e2 h9g7 ...",
    "best_move": "h2e2",
    "robot_command": "289,70,189,70,0",
    "robot_mode": "hardware",
    "robot_send_success": true,
    "ai_move_applied": true
  },
  "move_history": ["h2e2"],
  "display_history": ["红方 h2e2"],
  "turn_count": 1,
  "current_fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
  "board_state": { "...": "..." },
  "piece_count": 32,
  "robot_mode": "hardware",
  "vision_paused": false,
  "vision_pause_remaining": 0.0
}
```

### `POST /api/player_move`
Record a player-submitted move (used when the UI drives moves directly rather
than via vision). Errors if it is not the player's turn.

Request body: `{ "move": "h2e2" }` (UCI string).

```bash
curl -X POST http://localhost:5000/api/player_move \
  -H "Content-Type: application/json" \
  -d '{"move":"h2e2"}'
```

Response:

```json
{ "success": true, "move": "h2e2", "fen": "...", "display_history": ["红方 h2e2"], "is_player_turn": false, "turn_count": 1 }
```

### `POST /api/simulate_robot`
Drive the simulation robot controller to execute an AI move (simulation mode).

Request body: `{ "move": "h2e2" }`.

```bash
curl -X POST http://localhost:5000/api/simulate_robot \
  -H "Content-Type: application/json" \
  -d '{"move":"h2e2"}'
```

Response:

```json
{ "success": true, "move": "h2e2", "message": "机械臂已执行AI走法", "board_state": { "...": "..." } }
```

## Game Lifecycle

### `POST /api/game/start`
Start a new game. In `hardware` mode the STM32 is first sent a homing command;
if the homing acknowledgement is missing the call returns HTTP 503.

Request body:

```json
{
  "mode": "hardware",            // "hardware" | "simulation"
  "use_recognized_board": false, // reserved
  "board_state": {}              // reserved
}
```

`mode` defaults to `hardware`; any value other than `hardware`/`simulation`
returns HTTP 400.

```bash
curl -X POST http://localhost:5000/api/game/start \
  -H "Content-Type: application/json" \
  -d '{"mode":"simulation"}'
```

Response (success):

```json
{
  "success": true,
  "message": "游戏已开始",
  "fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
  "current_fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
  "use_recognized_board": true,
  "board_state": { "...": "..." },
  "ai_color": "black",
  "player_color": "red",
  "first_player": "red",
  "current_turn": "red",
  "robot_mode": "simulation",
  "homing_command": "",
  "homing_response": "",
  "homing_acknowledged": false
}
```

Response (homing failed, hardware mode, HTTP 503):

```json
{
  "success": false,
  "error": "STM32 homing acknowledgement missing",
  "homing_command": "m1_angle,m2_angle,0,0,99",
  "homing_response": "",
  "homing_acknowledged": false,
  "robot_mode": "hardware"
}
```

### `POST /api/game/reset`
Reset the game to its initial idle state and clear dynamic tracking.

```bash
curl -X POST http://localhost:5000/api/game/reset
```

Response:

```json
{ "success": true, "message": "游戏已重置" }
```
