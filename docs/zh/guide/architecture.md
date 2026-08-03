# 系统架构

CH-RO 是一套中国象棋「人机对弈」机器人系统。摄像头观察实体棋盘，ONNX 视觉
流水线推断棋子分布，Pikafish UCI 引擎决定 AI 走法，五值指令协议通过 TCP 驱动
STM32 机械臂。Flask 后端将上述能力统一暴露给浏览器控制台。

## 运行时流程

```text
摄像头帧（USB / 网络 MJPEG / RTSP）
        │
        ▼
vision.BoardRecognizer
   ├─ detector   棋盘角点检测
   ├─ classifier 每格棋子分类
   ├─ mapper     图像坐标 -> 棋盘网格
   └─ stabilizer / dynamic_tracker 走子检测
        │  board_state（"col,row" -> 棋子字母 的字典）
        ▼
web_simulation（Flask）
   ├─ domain.py      纯棋盘 / FEN / 回合计算
   ├─ robot_cmd.py   UCI 走法 -> 五值指令
   ├─ game_logic.py  有状态的状态迁移（AI 走子、基准同步）
   └─ routes/*       REST 接口
        │  UCI 走法字符串（如 "h2e2"）
        ▼
ai.AIEngine（Pikafish UCI 子进程）
   └─ bestmove -> game_logic.apply_ai_best_move
        │
        ▼
robot.protocol.RobotPersistentClient（TCP）
   └─ "startX,startY,endX,endY,signal" -> STM32
```

## 顶层模块

| 路径 | 职责 |
| --- | --- |
| `main.py` | 交互式 CLI 编排，以及 demo / 测试入口。 |
| `game_manager.py` | CLI 模式下的对局生命周期：FEN 差分提取 UCI 走法、胜负判定。 |
| `config.py` | 所有可调运行时配置（摄像头、棋盘、AI、机械臂、日志）。 |
| `utils.py` | `FENUtils`、`CoordinateUtils`、`MoveNotationUtils`、`BoardUtils`。 |
| `vision/` | 摄像头采集、棋盘检测、映射、稳定化、识别。 |
| `ai/` | Pikafish 进程封装与 UCI 指令处理。 |
| `core/` | 底层 ONNX 推理辅助。 |
| `model/` | ONNX 模型资源。 |
| `robot/` | 棋盘→机械臂坐标换算、TCP 协议、仿真控制器。 |
| `web_simulation/` | Flask 后端 + 浏览器控制台 UI。 |
| `firmware/stm32-tcp-server/` | 嵌入式 C 的 TCP 服务端及机械臂控制固件。 |
| `camera_servers/` | 树莓派 / 香橙派网络摄像头服务端。 |
| `tests/` | 协议、后端循环、摄像头、识别、稳定化测试。 |

## Web 后端（`web_simulation`）

后端已从单个近 2000 行的 `app.py` 重构为一个小型**组合根（composition root）**
加若干职责单一的辅助模块与 Flask Blueprint，从而保持每个文件精简、将游戏状态
逻辑与 HTTP  plumbing 解耦，并稳定对外测试接口。

| 模块 | 角色 |
| --- | --- |
| `app.py` | **组合根。** 持有共享的 `game_state` 字典与所有运行时全局变量（识别器、摄像头选择、AI 引擎、机械臂 TCP 客户端），注册各 Blueprint，并重新导出辅助函数，方便测试在统一位置打桩（patch）。 |
| `domain.py` | 纯函数、无副作用：`board_state_to_fen`、`apply_uci_to_board_state`、`serialize/deserialize_board_state`、`points_to_uci`、`parse_*_parameter`、`ROBOT_MODE_*` 常量、`STANDARD_INITIAL_BOARD/FEN`。不依赖 Flask，也不持有全局状态。 |
| `services.py` | 工厂函数：`get_recognizer`（惰性创建摄像头识别器）、`get_ai_engine`、`get_robot_controller`、`get_robot_tcp_client`、摄像头列举。 |
| `robot_cmd.py` | 将 UCI 走法转换为 STM32 五值指令；归位（homing）指令；超时 / 落子稳定时长查询；`RobotSendResult`。 |
| `game_logic.py` | 有状态迁移：`apply_ai_best_move`、`current_turn_color`、`is_duplicate_player_move`、`update_current_fen`、动态基准同步。 |
| `startup.py` | 启动时的命令行提示，用于覆盖本局运行的棋盘间距 / 机械臂 IP（解析逻辑委托给 `domain`）。 |
| `routes/status.py` | `/api/status`、`/api/robot/status`、`/api/cameras`。 |
| `routes/camera.py` | MJPEG 视频流、单帧、抓拍、网络摄像头连接 / 断开、摄像头启动 / 状态。 |
| `routes/recognition.py` | `/api/recognize`、`/api/recognize/dynamic`、`/api/ai_move`、`/api/ai_status`、`/api/player_move`、`/api/simulate_robot`。 |
| `routes/game.py` | `/api/game/start`、`/api/game/reset`。 |

### 共享状态设计

Flask 路由是无状态函数，但对局需要持久化的棋盘状态。`app.py` 将这些状态保存在
模块级全局变量与 `game_state` 字典中。辅助模块通过
`from web_simulation import app as _app` 访问这些全局变量，并调用
`_app.get_recognizer()` / `_app.send_robot_command_to_controller()` 这类经由
`_app` 对象的封装函数，而非直接 import 辅助函数。这样测试契约保持稳定：测试
执行 `patch.object(web_app, "send_robot_command_to_controller")` 时，路由实际
使用的正是被打桩的对象。

当以脚本方式运行（`python web_simulation/app.py`）时，会写入
`sys.modules["web_simulation.app"] = sys.modules["__main__"]` 别名，确保子模块
与 `__main__` 模块共享同一个状态对象。

## 机械臂传输（`robot`）

| 模块 | 状态 | 角色 |
| --- | --- | --- |
| `protocol.py` | **在用** | `RobotPersistentClient` —— 持久 TCP 连接，发送五值指令 `startX,startY,endX,endY,signal`。被 Web 后端与 `services.py` 使用。 |
| `controller.py` | 在用 | `RobotController` 抽象；仿真路径下的 `execute_uci_move`。 |
| `legacy_tcp_client.py` | **遗留 / 未导出** | 旧版基于 JSON 的 `RobotTCPClient`。仅作历史参考保留，运行系统不引用。 |

五值协议与归位握手详见 `firmware/stm32-f103-angle-plan/README.md`（见
[硬件与固件](./hardware)）；旧的 JSON 固件与 `legacy_tcp_client.py` 客户端见
`firmware/stm32-tcp-server/PROTOCOL.md`。

## 视觉流水线（`vision`）

`BoardRecognizer.recognize_board(image)` 依次执行检测 → 分类 → 映射 → 稳定化，
返回以 `"col,row"` 为键的 `board_state` 字典（如 `"0,3": "P"`）。
`recognize_dynamic_frame(frame)` 在其上叠加走子检测：当棋盘稳定且仅有单子移动
时，发出包含 `from`/`to` 网格坐标与棋子字母的 `move` 事件。后端将其转换为 UCI
字符串与机械臂指令。

## AI 引擎（`ai`）

`AIEngine` 以子进程方式启动 Pikafish 二进制，使用 UCI 协议通信
（`uci`、`isready`、`position fen ... moves ...`、`go depth N`、`bestmove`）。
引擎路径与搜索深度来自 `config.py`（`ENGINE_PATH`、`ENGINE_DEPTH`）。后端在后台
线程中执行搜索，UI 可通过 `/api/ai_status` 轮询结果。

## 领域模型

- **`board_state`** —— `dict[str, str]`，键为 `"col,row"`（列 0-8，行 0-9），
  值为棋子字母（`R` 红车、`r` 黑车、`P`/`p` 兵、`N`/`n` 马、`B`/`b` 士、
  `C`/`c` 炮、`K`/`k` 将/帅、`A`/`a` 仕）。空格不写入字典。
- **FEN** —— 标准象棋 FEN。`domain.board_state_to_fen` 负责构建，
  `xq_utils.FENUtils` 负责解析与互转。
- **`game_state`** —— 后端的实时字典：`current_fen`、`board_state`、
  `move_history`、`display_history`、`is_game_running`、`player_color`、
  `ai_color`、`first_player`、`ai_thinking`、`robot_moving`、`robot_mode`、
  `vision_pause_until`、`awaiting_physical_baseline`、`robot_baseline_match_count`
  等。由 `/api/status` 整体返回。

## 延伸阅读

- [配置说明](./configuration) —— `config.py` 中的全部可调项。
- [REST API](/zh/reference/api) —— 完整接口参考。
- [硬件与固件](./hardware) —— 摄像头选项与 STM32 协议。
