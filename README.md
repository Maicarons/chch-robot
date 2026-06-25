# 中国象棋人机博弈机器人系统

一套完整的线下中国象棋人机对弈系统，集成视觉识别、AI 引擎、机械臂控制和 Web 管理界面。

## 系统架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Web 管理界面 (Flask)                          │
│                   http://localhost:5000                              │
└──────────┬──────────────────┬──────────────────┬────────────────────┘
           │                  │                  │
     ┌─────▼─────┐    ┌──────▼──────┐    ┌──────▼──────┐
     │  视觉识别  │    │   AI 引擎   │    │  机械臂控制  │
     │  vision/   │    │    ai/      │    │   robot/    │
     └─────┬─────┘    └──────┬──────┘    └──────┬──────┘
           │                  │                  │
     ┌─────▼─────┐    ┌──────▼──────┐    ┌──────▼──────┐
     │ ONNX 模型  │    │  Pikafish   │    │   STM32     │
     │ RTMPose +  │    │  UCI 引擎   │    │  下位机     │
     │ 分类器     │    │             │    │  (TCP)      │
     └───────────┘    └─────────────┘    └─────────────┘
```

### 数据流

```
摄像头画面 (USB / 网络摄像头)
    ↓
棋盘关键点检测 (RTMPose ONNX)
    ↓
棋子分类识别 (Full Classifier ONNX)
    ↓
多帧稳定化 + 动态追踪
    ↓
棋盘状态 → FEN 生成
    ↓
Pikafish AI 引擎思考 (UCI 协议)
    ↓
UCI 走法 → 机械臂坐标转换
    ↓
TCP 发送至 STM32 下位机执行
```

## 功能特性

- **实时棋盘识别**: ONNX 模型推理，支持 USB 摄像头和网络摄像头（MJPEG/RTSP 流）
- **动态走子检测**: `DynamicBoardTracker` 基于占用差异自动推断走法，内置容错和中国象棋规则合法性校验
- **多帧稳定化**: `StableBoardBuffer` 通过投票机制消除检测抖动
- **AI 对弈**: 集成 Pikafish（皮卡鱼）引擎，UCI 协议通信，支持深度/时间控制
- **机械臂控制**: 支持仿真模式和真实 STM32 机械臂（TCP 五值指令协议）
- **Web 管理界面**: Flask 后端 + 前端页面，提供摄像头预览、棋盘识别、AI 对弈、机械臂状态监控
- **硬件/仿真双模式**: 启动时可选择 `hardware`（真实机械臂）或 `simulation`（纯软件模拟）
- **Homing 握手**: 硬件模式启动时自动发送归位指令，等待 STM32 确认后才开始对弈

## 硬件需求

| 组件 | 要求 | 说明 |
|------|------|------|
| **摄像头** | USB 摄像头 720p+ 或网络摄像头 | 用于拍摄棋盘画面 |
| **机械臂** | 6 自由度机械臂 + STM32 控制板 | 通过 TCP 控制，可选 |
| **计算机** | Windows/Linux，CPU 支持 AVX2 | 运行主程序和 AI 引擎 |
| **棋盘** | 标准中国象棋棋盘 | 建议固定位置和角度 |

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd chch-robot

# 安装 Python 依赖
pip install -r requirements.txt
```

### 2. 下载 Pikafish 引擎

从 [Pikafish 官方发布页](https://github.com/official-pikafish/Pikafish/releases) 下载对应平台的引擎文件，解压到 `./Pikafish/` 目录。

默认使用 `pikafish-avx2.exe`（Windows）。

### 3. 配置系统

编辑 `config.py` 修改以下关键配置：

```python
# 摄像头
CAMERA_INDEX = 1                          # USB 摄像头索引
USE_IP_CAMERA = True                      # 是否使用网络摄像头
IP_CAMERA_URL = "http://192.168.0.101:8080/?action=stream"

# AI 引擎
ENGINE_PATH = "./Pikafish/pikafish-avx2.exe"
ENGINE_DEPTH = 15                         # 搜索深度

# 机械臂网络
ROBOT_NETWORK_HOST = "192.168.0.102"      # STM32 下位机 IP
ROBOT_NETWORK_PORT = 8086                 # TCP 端口
```

### 4. 启动系统

#### Web 管理界面（推荐）

```bash
python web_simulation/app.py
```

浏览器访问 `http://localhost:5000`，支持：
- 摄像头实时预览和画面捕获
- 棋盘状态识别和 FEN 显示
- AI 走棋（异步思考，实时显示分析进度）
- 机械臂状态监控（hardware/simulation 模式切换）
- 游戏管理（开始、重置、走法历史）

启动时可在终端修改棋盘格距和下位机 IP 参数。

#### 命令行模式

```bash
python main.py
```

交互式命令：
- `start` — 开始游戏
- `calibrate` — 校准系统
- `demo` — 运行演示
- `test_camera` — 测试摄像头
- `test_engine` — 测试 AI 引擎

#### 命令行参数

```bash
python main.py --demo           # 演示模式
python main.py --test-camera    # 测试摄像头
python main.py --test-engine    # 测试 AI 引擎
```

## 项目结构

```
chch-robot/
├── main.py                     # 命令行入口
├── game_manager.py             # 游戏流程管理器
├── config.py                   # 全局配置
├── utils.py                    # FEN/坐标/记谱法工具函数
├── requirements.txt            # Python 依赖
│
├── vision/                     # 视觉识别模块
│   ├── camera.py               # 摄像头管理（USB + 网络摄像头）
│   ├── detector.py             # ONNX 检测器封装
│   ├── mapper.py               # 透视变换和坐标映射
│   ├── stabilizer.py           # 多帧稳定化 + 动态走子追踪
│   ├── network_camera.py       # 网络摄像头工具
│   └── recognizer.py           # 高层识别 API
│
├── ai/                         # AI 引擎模块
│   └── engine.py               # Pikafish UCI 协议通信
│
├── robot/                      # 机械臂控制模块
│   ├── controller.py           # 仿真控制器
│   ├── protocol.py             # 五值指令协议 + TCP 传输
│   └── tcp_client.py           # STM32 TCP 客户端
│
├── core/                       # 底层 ONNX 推理
│   ├── chessboard_detector.py  # 棋盘检测核心
│   ├── helper_4_kpt.py         # 关键点辅助
│   └── runonnx/                # ONNX 推理封装
│
├── web_simulation/             # Web 管理界面
│   ├── app.py                  # Flask 后端
│   ├── templates/index.html    # 前端页面
│   └── static/                 # CSS/JS 静态资源
│
├── model/                      # ONNX 模型文件
│   ├── pose/                   # 姿态估计模型
│   └── layout_recognition/     # 棋子分类模型
│
├── stm32-robot/                # STM32 下位机固件 (C)
│   ├── main.c
│   ├── robot_control.c/h       # 机械臂运动控制
│   ├── robot_tcp_server.c/h    # TCP 服务器
│   ├── json_parser.c/h         # JSON 解析
│   ├── Makefile
│   └── PROTOCOL.md             # 通信协议文档
│
├── orange-pi-camera/           # Orange Pi 网络摄像头服务
│   └── camera_server.py
│
├── raspberry_pi_zero2w_usb_camera_offline/  # 树莓派摄像头服务
│   └── usb_mjpeg_server.py
│
├── dataset/                    # 训练数据集
└── tests/                      # 单元测试
```

## 核心模块详解

### 视觉识别 (`vision/`)

**摄像头管理** (`camera.py`):
- 支持 USB 本地摄像头和网络摄像头（HTTP MJPEG / RTSP / RTMP）
- 后台线程持续读取帧，自动检测故障并恢复
- `HttpSnapshotCapture` 专门处理 HTTP 快照/MJPEG 流

**棋盘检测** (`detector.py`):
- 懒加载 ONNX 模型（首次推理时加载，避免重复创建会话）
- 线程安全的推理锁
- 输出：棋盘关键点 + 90 格棋子分类

**动态追踪** (`stabilizer.py`):
- `StableBoardBuffer`: 多帧投票稳定化
- `DynamicBoardTracker`: 连续帧对比，自动推断走法
- `infer_one_move_from_occupancy()`: 从占用差异推断走法，支持容错（噪声点容忍）
- `_is_legal_xiangqi_move()`: 中国象棋规则合法性校验（车马炮象士将卒）

**识别器** (`recognizer.py`):
- `recognize_board()`: 静态识别，返回稳定棋盘状态
- `recognize_dynamic_frame()`: 动态识别，返回事件（`move` / `unchanged` / `initial_locked`）
- `sync_dynamic_baseline()`: 同步游戏状态基线到追踪器

### AI 引擎 (`ai/`)

- 通过子进程启动 Pikafish，UCI 协议通信
- 设置 `UCI_Variant = xiangqi` 启用中国象棋模式
- `set_position()`: 同步 FEN 和走法历史
- `get_best_move()`: 获取引擎最佳走法
- `analyze_position()`: 分析局面（分数、深度、主变）
- `get_current_fen_after_moves()`: 通过引擎 `d` 命令获取当前 FEN

### 机械臂控制 (`robot/`)

**五值指令协议** (`protocol.py`):
```
startX, startY, endX, endY, signal
```
- `signal = 0`: 普通移动
- `signal = 1`: 吃子序列

**坐标转换**:
- `BoardToArmConfig`: UCI 方格 → 机械臂坐标（毫米）
- 原点在棋盘右上角（黑方右侧车位置）
- 横向间距 34mm，纵向间距 30mm，楚河汉界 32mm

**TCP 通信** (`protocol.py` 中的 `RobotPersistentClient`):
- 持久 TCP 连接，发送五值指令后等待 STM32 确认
- 确认条件：收到 `STATE:5,RESULT:1`
- 支持 Homing 归位指令（`m1_angle,m2_angle,0,0,99`）

**STM32 下位机** (`stm32-robot/`):
- C 语言固件，TCP 服务器监听端口
- JSON 格式指令解析
- 电机控制、夹爪控制、运动规划

### Web 管理界面 (`web_simulation/`)

**后端 API** (`app.py`):

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/status` | GET | 获取游戏状态 |
| `/api/cameras` | GET | 列出可用摄像头 |
| `/api/camera/stream` | GET | MJPEG 实时视频流 |
| `/api/camera/frame` | GET | 单帧 JPEG |
| `/api/camera/start` | POST | 启动摄像头 |
| `/api/camera/status` | GET | 摄像头状态 |
| `/api/network_camera/connect` | POST | 连接网络摄像头 |
| `/api/network_camera/disconnect` | POST | 断开网络摄像头 |
| `/api/recognize` | POST | 静态识别棋盘 |
| `/api/recognize/dynamic` | POST | 动态识别（追踪走子） |
| `/api/ai_move` | POST | 启动 AI 思考（异步） |
| `/api/ai_status` | GET | AI 分析状态 |
| `/api/player_move` | POST | 提交玩家走法 |
| `/api/robot/status` | GET | 机械臂连接状态 |
| `/api/game/start` | POST | 开始新游戏 |
| `/api/game/reset` | POST | 重置游戏 |

**游戏流程**:
1. 选择机械臂模式（hardware / simulation）
2. 硬件模式自动发送 Homing 归位指令
3. 使用标准初始布局作为识别基准
4. 玩家走棋（红方）→ 视觉动态检测 → 后端同步记录
5. AI 走棋（黑方）→ 引擎思考 → 机械臂执行 → 视觉暂停后恢复
6. 循环直到游戏结束

**关键机制**:
- **视觉暂停**: AI 走棋后暂停视觉识别，等待机械臂完成
- **物理基线确认**: 硬件模式下，机械臂落子后需连续 N 帧识别一致才解锁
- **防重复**: 基于 `ai_command_token` 和 `last_player_move` 防止重复走法

## 网络摄像头部署

### Orange Pi

```bash
cd orange-pi-camera
python camera_server.py
```

### Raspberry Pi Zero 2W

```bash
cd raspberry_pi_zero2w_usb_camera_offline
python usb_mjpeg_server.py
```

配置 `config.py` 中的 `IP_CAMERA_URL` 指向摄像头服务地址。

## 运行测试

```bash
# 运行全部测试
python -m pytest tests/ -v

# 运行单个测试文件
python -m pytest tests/test_stabilizer.py -v

# 运行特定测试
python -m pytest tests/test_robot_protocol.py -v -k "test_homing"
```

测试文件说明：
- `test_stabilizer.py` — 动态追踪器和走法推断
- `test_robot_protocol.py` — 五值指令协议和坐标转换
- `test_camera_source.py` — 摄像头源规范化
- `test_detector_runtime.py` — 检测器运行时
- `test_recognizer_concurrency.py` — 识别器并发安全
- `test_robot_backend_loop.py` — 机械臂后端循环
- `test_frontend_homing_contract.py` — 前端 Homing 契约
- `test_stm32_homing_contract.py` — STM32 Homing 契约
- `test_usb_camera_server.py` — USB 摄像头服务

## FEN 编码说明

标准中国象棋 FEN 格式：
```
rnbakabnr/9/1c5c1/p1p1p1p1p/9/9/P1P1P1P1P/1C5C1/9/RNBAKABNR w - - 0 1
```

- 大写字母 = 红方（R车 N马 B相 A仕 K帅 C炮 P兵）
- 小写字母 = 黑方（r车 n马 b象 a士 k将 c炮 p卒）
- 数字 = 连续空位数
- `w` = 红方走棋，`b` = 黑方走棋

UCI 走法格式：`h0h2`（从 h0 移动到 h2）

## 日志

日志文件：`./chchess.log`

配置日志级别（`config.py`）：
```python
LOG_LEVEL = "INFO"          # DEBUG, INFO, WARNING, ERROR
SAVE_LOG_TO_FILE = True
```

## 许可证

本项目采用 GPL v3.0 许可证。
