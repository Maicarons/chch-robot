# 配置说明

几乎所有运行时配置都集中在 `config.py`。请优先修改其中的值，而不要在模块内部
硬编码路径；同时不要把下载的引擎二进制、日志与生成的抓图提交进 git。

## 摄像头

| 键 | 默认值 | 含义 |
| --- | --- | --- |
| `CAMERA_INDEX` | `1` | 本地 USB 摄像头索引。 |
| `CAMERA_WIDTH` / `CAMERA_HEIGHT` | `640` / `480` | 预览 / 识别帧尺寸。 |
| `CAMERA_FPS` | `30` | 采集帧率。 |
| `USE_IP_CAMERA` | `True` | 是否优先使用下面的网络摄像头 URL。 |
| `IP_CAMERA_URL` | `http://192.168.0.101:8080/?action=stream` | 局域网 MJPEG / RTSP 流地址。 |

本地 USB 摄像头用 `CAMERA_INDEX`；局域网 MJPEG 或 RTSP 流用 `IP_CAMERA_URL`（Pi
摄像头服务端见[硬件与固件](./hardware)）。

## 棋盘识别

| 键 | 默认值 | 含义 |
| --- | --- | --- |
| `BOARD_ROWS` / `BOARD_COLS` | `10` / `9` | 象棋棋盘网格尺寸。 |
| `SQUARE_SIZE_MM` | `50` | 棋子格实际尺寸（毫米）。 |
| `BOARD_MARGIN_MM` | `20` | 棋盘边缘留白（毫米）。 |
| `YOLO_MODEL_PATH` | `./best.pt` | YOLOv8 棋子检测模型。 |
| `YOLO_CONF_THRES` | `0.10` | 检测置信度阈值。 |
| `MIN_PIECE_SIZE` | `70` | 最小棋子像素尺寸（过滤误识）。 |
| `SNAP_DIST_THRES` | `0.45` | 检测框中心吸附到交点的最大容许距离。 |
| `STABLE_WINDOW` / `STABLE_RATIO` | `5` / `0.60` | 稳定化窗口与比例阈值。 |
| `AUTO_STABLE_FRAMES` | `25` | 触发自动识别所需的连续稳定帧数。 |
| `CANNY_THRESHOLD1/2` | `50` / `150` | Canny 边缘检测阈值。 |
| `MIN_CONTOUR_AREA` / `MAX_CONTOUR_AREA` | `500` / `5000` | 棋子轮廓面积上下限。 |
| `RED_LOWER1/2`、`RED_UPPER1/2`、`BLACK_LOWER`、`BLACK_UPPER` | — | 红 / 黑棋子的 HSV 颜色范围。 |

## AI 引擎

| 键 | 默认值 | 含义 |
| --- | --- | --- |
| `ENGINE_PATH` | `./Pikafish/pikafish-avx2.exe` | Pikafish 二进制路径。 |
| `ENGINE_DEPTH` | `15` | 默认搜索深度。 |
| `THINK_TIME` | `5000` | 思考时间预算（毫秒）。 |
| `USE_HASH_TABLE` | `True` | 启用引擎哈希表。 |
| `HASH_SIZE_MB` | `128` | 哈希表大小（MB）。 |

下载 Pikafish 二进制放入 `Pikafish/`，文件名不同则修改 `ENGINE_PATH`。Web 后端
可通过 `/api/ai_move` 的 `depth` 请求字段按次覆盖搜索深度。

## 机械臂网络与运动

| 键 | 默认值 | 含义 |
| --- | --- | --- |
| `ROBOT_NETWORK_HOST` | `192.168.0.102` | STM32 控制器 IP。 |
| `ROBOT_NETWORK_PORT` | `8086` | STM32 控制器 TCP 端口。 |
| `ROBOT_NETWORK_TIMEOUT` | `1.0` | Socket 连接 / IO 超时（秒）。 |
| `ROBOT_HOMING_TIMEOUT` | `30.0` | 归位握手超时（秒）。 |
| `ROBOT_COMMAND_TIMEOUT` | `60.0` | 默认指令超时（秒）。 |
| `ROBOT_NORMAL_COMMAND_TIMEOUT` | `60.0` | 普通走子指令超时（秒）。 |
| `ROBOT_CAPTURE_COMMAND_TIMEOUT` | `120.0` | 吃子指令超时（秒）。 |
| `ROBOT_CAPTURE_SETTLE_SECONDS` | `0.0` | 吃子后的落子稳定等待（秒）。 |
| `ROBOT_NORMAL_SETTLE_SECONDS` | `0.0` | 普通走子后的落子稳定等待（秒）。 |
| `ROBOT_POST_BASELINE_GUARD_SECONDS` | `0.0` | AI 走子后的保护窗口（秒）。 |
| `ROBOT_HOMING_M1_ANGLE_DEG` / `ROBOT_HOMING_M2_ANGLE_DEG` | `-17.18` / `-55.63` | 归位关节角度（度）。 |
| `ROBOT_COMMAND_ORIGIN_X` / `ROBOT_COMMAND_ORIGIN_Y` | `0` / `0` | 棋盘原点在机械臂坐标系中的位置（毫米）。 |
| `ROBOT_COMMAND_FILE_SPACING_MM` | `34` | 纵线（列）间距（毫米）。 |
| `ROBOT_COMMAND_RANK_SPACING_MM` | `30` | 横线（行）间距（毫米）。 |
| `ROBOT_COMMAND_RIVER_SPACING_MM` | `32` | 河道额外间隙（毫米）。 |
| `ROBOT_SIMULATED_MOVE_SECONDS` | `15.0` | 仿真走子时长（秒）。 |
| `HOME_POSITION_X/Y/Z` | `100/100/150` | 机械臂 home 点（毫米）。 |
| `GRIPPER_PICK_HEIGHT` / `GRIPPER_GRASP_HEIGHT` / `GRIPPER_MOVE_HEIGHT` | `80/10/50` | 夹爪各阶段高度（毫米）。 |
| `ROBOT_SPEED_FAST` / `ROBOT_SPEED_SLOW` | `100` / `30` | 运动速度（毫米/秒）。 |
| `ROBOT_TYPE` | `"simulation"` | `"simulation"`、`"dobot"` 或 `"elephant_robotics"`。 |

棋盘间距与目标 IP 可在启动时通过 Flask 的启动提示覆盖本局运行。自动化测试或
无人值守启动时，设置 `CHRO_SKIP_STARTUP_PROMPT=1` 可跳过提示。

## 对局

| 键 | 默认值 | 含义 |
| --- | --- | --- |
| `PLAYER_COLOR` | `"red"` | 人类玩家执子颜色。 |
| `AI_AUTO_PLAY` | `False` | 让 AI 连续自动走子（测试用）。 |
| `WAIT_PLAYER_MOVE_TIMEOUT` | `120` | 等待玩家走子的超时（秒）。 |

## 显示与日志

| 键 | 默认值 | 含义 |
| --- | --- | --- |
| `SHOW_CAMERA_PREVIEW` | `True` | 显示摄像头预览窗口。 |
| `SHOW_DETECTION_RESULT` | `True` | 叠加检测结果。 |
| `DEBUG_MODE` | `False` | 详细调试叠加。 |
| `LOG_LEVEL` | `"INFO"` | `DEBUG` / `INFO` / `WARNING` / `ERROR`。 |
| `LOG_FILE` | `./chchess.log` | 日志文件路径。 |
| `SAVE_LOG_TO_FILE` | `True` | 是否将日志写入文件。 |

## 坐标校准

| 键 | 默认值 | 含义 |
| --- | --- | --- |
| `BOARD_TOP_LEFT_X/Y/Z` | `0/0/0` | 棋盘左上角在机械臂坐标系中的位置（毫米）。 |
| `BOARD_ROTATION_ANGLE` | `0` | 棋盘旋转角度（度）。 |

## 参考

`FEN_START_POSITION` 保存了作为默认基准的标准象棋开局 FEN。棋盘 / FEN 计算辅助
函数位于 `web_simulation/domain.py` 与 `xq_utils.FENUtils`。
