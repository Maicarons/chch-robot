# REST API 参考

Flask 后端监听 `http://localhost:5000`（可在 `web_simulation/app.py` 中修改）。
除特别说明外，所有接口均返回 JSON。多数接口可通过 JSON 请求体或查询字符串传入
可选的摄像头选择器：

| 字段 | 来源 | 含义 |
| --- | --- | --- |
| `camera_source` | body / query | `"usb"`、`"network"` 或设备字符串。 |
| `camera_url` | body / query | 网络摄像头 URL（优先级高于 `camera_source`）。 |
| `camera_index` | body / query | 本地 USB 摄像头索引（如 `0`、`1`）。 |

未提供时使用当前激活的摄像头源。

## 状态

### `GET /api/status`
返回完整的实时 `game_state` 字典。

```bash
curl http://localhost:5000/api/status
```

响应：

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
机械臂控制器连接状态。附加 `?probe=1` 才会实际尝试 TCP 探测。

```bash
curl "http://localhost:5000/api/robot/status?probe=1"
```

响应（已探测）：

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

未带 `probe` 时，`connected` 为 `null`，`status` 为 `"not_probed"`。

### `GET /api/cameras`
列举本地可用摄像头及当前激活的源。

```bash
curl http://localhost:5000/api/cameras
```

响应：

```json
{
  "success": true,
  "cameras": [{ "index": 0, "name": "Integrated Camera" }, { "index": 1, "name": "USB Camera" }],
  "current_camera_index": 1,
  "is_network": false,
  "source": 1
}
```

## 摄像头

### `GET /api/camera/stream`
MJPEG 实时视频流（`multipart/x-mixed-replace`）。可直接放入 `<img>` 标签。
新请求会使之前的流令牌失效。

```html
<img src="http://localhost:5000/api/camera/stream" />
```

### `GET /api/camera/frame`
返回单张 JPEG 帧（在部分浏览器中比 MJPEG 更稳）。返回 `image/jpeg`；无画面时
返回 HTTP 503。

```bash
curl http://localhost:5000/api/camera/frame --output frame.jpg
```

### `POST /api/capture`
抓取一帧并以 base64 JPEG 返回。

请求体（可选）：`{ "camera_source": "usb" }`。

```bash
curl -X POST http://localhost:5000/api/capture \
  -H "Content-Type: application/json" \
  -d '{"camera_source":"usb"}'
```

响应：

```json
{ "success": true, "image": "<base64 jpeg>", "source": 1, "timestamp": "2026-08-01T01:00:00.123456" }
```

### `POST /api/network_camera/connect`
注册并测试局域网网络摄像头 URL。失败时回滚到之前的源。

请求体：`{ "url": "http://192.168.0.101:8080/?action=stream" }`（或
`camera_url`）。URL 必须以 `http://`、`https://`、`rtsp://` 或 `rtmp://` 开头。

```bash
curl -X POST http://localhost:5000/api/network_camera/connect \
  -H "Content-Type: application/json" \
  -d '{"url":"http://192.168.0.101:8080/?action=stream"}'
```

响应（成功）：

```json
{ "success": true, "message": "网络摄像头连接成功", "width": 640, "height": 480, "is_network": true, "source": "http://192.168.0.101:8080/?action=stream" }
```

### `GET /api/network_camera/status`
回报网络摄像头是否已配置并打开。

```bash
curl http://localhost:5000/api/network_camera/status
```

### `POST /api/network_camera/disconnect`
停止网络源，切回本地 USB 摄像头。

```bash
curl -X POST http://localhost:5000/api/network_camera/disconnect
```

### `GET /api/test/camera`
测试摄像头：抓取并返回一帧 base64 图像。

```bash
curl http://localhost:5000/api/test/camera
```

### `POST /api/camera/start`
启动所选源的摄像头。已打开时幂等。

```bash
curl -X POST http://localhost:5000/api/camera/start -H "Content-Type: application/json" -d '{}'
```

### `GET /api/camera/status`
回报所选摄像头源是否已打开。

```bash
curl http://localhost:5000/api/camera/status
```

## 识别与 AI

### `POST /api/recognize`
从上传的 base64 图像、或（未提供图像时）从实时摄像头识别棋盘，返回 `board_state`
字典与推导出的 FEN。

请求体（可选）：`{ "image": "<base64 jpeg>" }`。

```bash
curl -X POST http://localhost:5000/api/recognize \
  -H "Content-Type: application/json" \
  -d '{"image":"<base64 jpeg>"}'
```

响应：

```json
{
  "success": true,
  "board_state": { "0,0": "r", "3,0": "p", "...": "R" },
  "fen": "rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1",
  "piece_count": 32
}
```

### `POST /api/recognize/dynamic`
动态识别实时画面，棋盘稳定后发出 `move` 事件。这是 UI 轮询的核心循环接口，会处理
机械臂走子期间的视觉暂停 / 保护窗口，以及硬件模式下的实体棋盘基准确认。

请求体（可选）：`{ "camera_source": "usb" }`。

```bash
curl -X POST http://localhost:5000/api/recognize/dynamic -H "Content-Type: application/json" -d '{}'
```

事件（`event` 字段）：

| 事件 | 含义 |
| --- | --- |
| `move` | 单子移动；`move` 含 `from`、`to`、`piece`、`code`（UCI）、`robot_command`（五值字符串）、`source`（`player` / `duplicate` / `ignored_*`）。 |
| `unchanged` | 棋盘稳定，未检测到走子。 |
| `initial_locked` | 开局时锁定基准棋盘。 |
| `paused` | AI / 机械臂走子期间视觉暂停。 |
| `robot_board_confirmed` / `robot_board_waiting` | AI 走子后的实体基准确认（硬件模式）。 |
| `robot_settling` | 机械臂落子后的短暂保护窗口。 |

响应（走子事件）：

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
在后台线程中启动（异步）AI 搜索。随后 UI 轮询 `/api/ai_status`。

请求体（可选）：`{ "depth": 8 }`，默认 `8`。若未轮到 AI 或 AI 正在思考则报错。

```bash
curl -X POST http://localhost:5000/api/ai_move -H "Content-Type: application/json" -d '{"depth":10}'
```

响应：

```json
{ "success": true, "message": "AI思考已启动" }
```

### `GET /api/ai_status`
AI 思考状态与最新分析。

```bash
curl http://localhost:5000/api/ai_status
```

响应：

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
记录玩家提交的走法（UI 直接驱动走子、而非经由视觉时使用）。未轮到玩家则报错。

请求体：`{ "move": "h2e2" }`（UCI 字符串）。

```bash
curl -X POST http://localhost:5000/api/player_move \
  -H "Content-Type: application/json" \
  -d '{"move":"h2e2"}'
```

响应：

```json
{ "success": true, "move": "h2e2", "fen": "...", "display_history": ["红方 h2e2"], "is_player_turn": false, "turn_count": 1 }
```

### `POST /api/simulate_robot`
驱动仿真机械臂控制器执行 AI 走法（仿真模式）。

请求体：`{ "move": "h2e2" }`。

```bash
curl -X POST http://localhost:5000/api/simulate_robot \
  -H "Content-Type: application/json" \
  -d '{"move":"h2e2"}'
```

响应：

```json
{ "success": true, "move": "h2e2", "message": "机械臂已执行AI走法", "board_state": { "...": "..." } }
```

## 对局生命周期

### `POST /api/game/start`
开始新对局。在 `hardware` 模式下，会先向 STM32 发送归位指令；若缺少归位确认，
则返回 HTTP 503。

请求体：

```json
{
  "mode": "hardware",            // "hardware" | "simulation"
  "use_recognized_board": false, // 预留
  "board_state": {}              // 预留
}
```

`mode` 默认为 `hardware`；除 `hardware`/`simulation` 之外的值返回 HTTP 400。

```bash
curl -X POST http://localhost:5000/api/game/start \
  -H "Content-Type: application/json" \
  -d '{"mode":"simulation"}'
```

响应（成功）：

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

响应（硬件模式归位失败，HTTP 503）：

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
将对局重置为初始空闲状态，并清除动态追踪。

```bash
curl -X POST http://localhost:5000/api/game/reset
```

响应：

```json
{ "success": true, "message": "游戏已重置" }
```
