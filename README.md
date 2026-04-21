# 中国象棋人机博弈机器人系统

> **注意**: Pikafish引擎文件需自行下载并放置在 `./Pikafish/` 目录下（默认使用 `pikafish-avx2.exe`）

## 📋 目录

- [项目简介](#项目简介)
- [系统架构](#系统架构)
- [工作环境](#工作环境)
- [快速开始](#快速开始)
- [模块说明](#模块说明)
- [开发指南](#开发指南)
- [故障排除](#故障排除)

---

## 项目简介

本项目实现了一个完整的**线下中国象棋人机对弈机器人系统**,整合了:

- 🎥 **视觉识别**: 基于ONNX模型的棋盘检测和棋子识别
- 🤖 **AI引擎**: 集成Pikafish(皮卡鱼)中国象棋引擎
- 🦾 **机械臂控制**: 支持仿真和真实机械臂执行走法
- 🌐 **Web仿真环境**: 全真模拟测试平台(TODO)

### 核心特性

✅ 实时棋盘状态识别  
✅ UCI协议通信  
✅ 多帧稳定化消除抖动  
✅ 模块化设计易于扩展  
✅ 完整的日志系统  

---

## 系统架构

```
┌─────────────────────────────────────────────────────┐
│                   主程序 (main.py)                    │
└──────────────────┬──────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        │                     │
┌───────▼────────┐   ┌──────▼─────────┐
│ 游戏管理器      │   │  配置文件       │
│ (game_manager) │   │  (config.py)    │
└───┬────┬───────┘   └────────────────┘
    │    │
    │    └──────────────────┐
    │                       │
┌───▼────────┐     ┌───────▼──────────┐
│ 视觉识别模块│     │   AI引擎模块      │
│ (vision/)  │     │   (ai/)          │
│            │     │                  │
│ • 摄像头   │     │ • 引擎通信       │
│ • 检测器   │     │ • 走法分析       │
│ • 映射器   │     │ • 位置更新       │
│ • 稳定化   │     └──────────────────┘
└────────────┘
    │
    │              ┌──────────────────┐
    └─────────────►│  机械臂控制模块   │
                   │  (robot/)        │
                   │                  │
                   │ • 坐标转换       │
                   │ • 运动规划       │
                   │ • 夹爪控制       │
                   └──────────────────┘
```

### 数据流

```
摄像头图像 
    ↓
棋盘检测(RTMPose) 
    ↓
棋子分类(Full Classifier) 
    ↓
布局字符串解析 
    ↓
FEN生成 
    ↓
AI引擎思考(Pikafish) 
    ↓
UCI走法输出 
    ↓
机械臂坐标转换 
    ↓
执行走法
```

---

## 工作环境

### 硬件需求

| 组件 | 要求 | 说明 |
|------|------|------|
| **摄像头** | USB摄像头 720p+ | 用于拍摄棋盘 |
| **机械臂** | 6自由度机械臂 | 如DOBOT、大象机器人等(可选) |
| **计算机** | Windows/Linux | CPU支持AVX2指令集 |
| **棋盘** | 标准中国象棋棋盘 | 建议固定位置和角度 |

### 软件依赖

#### 系统要求

- **操作系统**: Windows 10/11 或 Linux
- **Python**: 3.8+
- **Pikafish引擎**: 从官网下载并解压到 `./Pikafish/`

#### Python依赖包

```txt
opencv-python>=4.5.0
numpy>=1.20.0
onnxruntime-gpu>=1.15.0
pandas>=1.3.0
flask>=2.0.0  # Web仿真环境(可选)
```

安装命令:
```bash
pip install -r requirements.txt
```

### 目录结构

```
chch-robot/
├── vision/                 # 视觉识别模块
│   ├── __init__.py
│   ├── camera.py          # 摄像头管理
│   ├── detector.py        # ONNX检测器
│   ├── mapper.py          # 坐标映射器
│   ├── stabilizer.py      # 稳定化缓冲
│   └── recognizer.py      # 识别器主类
│
├── ai/                     # AI引擎模块
│   ├── __init__.py
│   ├── engine.py          # UCI引擎通信
│   └── analyzer.py        # 走法分析器
│
├── robot/                  # 机械臂控制模块
│   ├── __init__.py
│   ├── controller.py      # 控制器基类
│   ├── simulator.py       # 仿真机械臂
│   └── coordinate.py      # 坐标转换
│
├── web_simulation/         # Web仿真环境(TODO)
│   ├── app.py             # Flask后端
│   ├── templates/         # HTML模板
│   └── static/            # 静态资源
│
├── core/                   # 核心检测模型
│   ├── runonnx/           # ONNX推理封装
│   ├── chessboard_detector.py
│   └── helper_4_kpt.py
│
├── model/                  # 模型文件
│   ├── pose/              # 姿态估计模型
│   └── layout_recognition/# 棋子分类模型
│
├── Pikafish/              # 皮卡鱼引擎
│   └── pikafish-*.exe
│
├── config/                # 配置模块
│   └── settings.py
│
├── tests/                 # 测试文件
│   ├── test_vision.py
│   ├── test_ai.py
│   └── test_robot.py
│
├── main.py                # 主程序入口
├── game_manager.py        # 游戏管理器
├── utils.py               # 工具函数
├── config.py              # 全局配置
├── requirements.txt       # 依赖列表
└── README.md              # 本文档
```

---

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd chch-robot

# 安装依赖
pip install -r requirements.txt

# 下载Pikafish引擎
# 访问 https://github.com/official-pikafish/Pikafish/releases
# 下载Windows版本并解压到 ./Pikafish/ 目录
```

### 2. 配置系统

编辑 `config.py`:

```python
# 摄像头配置
CAMERA_INDEX = 0              # 摄像头索引
CAMERA_WIDTH = 1280           # 宽度
CAMERA_HEIGHT = 720           # 高度

# AI引擎配置
ENGINE_PATH = "./Pikafish/pikafish-avx2.exe"  # 引擎路径
ENGINE_DEPTH = 15             # 搜索深度
THINK_TIME = 5000             # 思考时间(毫秒)

# 机械臂配置
ROBOT_TYPE = "simulation"     # "simulation" 或真实机械臂类型
```

### 3. 运行系统

#### 方式一: 交互式命令行

```bash
python main.py
```

可用命令:
- `start` - 开始游戏
- `calibrate` - 校准系统
- `demo` - 运行演示
- `test_camera` - 测试摄像头
- `test_engine` - 测试AI引擎
- `help` - 显示帮助
- `quit` - 退出

#### 方式二: 直接启动

```bash
# 运行演示模式
python main.py --demo

# 测试摄像头
python main.py --test-camera

# 测试AI引擎
python main.py --test-engine
```

### 4. 游戏流程

```
1. 启动系统 → python main.py
2. 校准系统 → 输入 'calibrate'
3. 开始游戏 → 输入 'start'
4. 系统自动识别初始棋盘
5. AI思考并走棋(机械臂执行)
6. 玩家走棋后等待系统检测
7. 重复步骤5-6直到游戏结束
```

---

## 模块说明

### 1. 视觉识别模块 (`vision/`)

**职责**: 从摄像头图像中识别棋盘状态

#### 子模块

- **CameraManager** (`camera.py`): 摄像头控制和图像捕获
- **ChessboardDetector** (`detector.py`): ONNX模型封装,关键点检测和棋子分类
- **BoardMapper** (`mapper.py`): 透视变换和坐标映射
- **StableBoardBuffer** (`stabilizer.py`): 多帧投票稳定化
- **BoardRecognizer** (`recognizer.py`): 高层API,整合所有功能

#### 使用示例

```python
from vision import BoardRecognizer

# 初始化识别器
recognizer = BoardRecognizer(camera_index=0)

with recognizer:
    # 识别棋盘
    board_state = recognizer.recognize_board()
    print(f"检测到 {len(board_state)} 个棋子")
    
    # 获取FEN
    fen = recognizer.get_fen()
    print(f"FEN: {fen}")
```

### 2. AI引擎模块 (`ai/`)

**职责**: 与Pikafish引擎通信,获取最佳走法

#### 子模块

- **AIEngine** (`engine.py`): UCI协议实现,引擎进程管理
- **Analyzer** (`analyzer.py`): 位置分析和评估

#### 使用示例

```python
from ai import AIEngine

with AIEngine() as engine:
    # 获取最佳走法
    move = engine.get_best_move(depth=15)
    print(f"AI走法: {move}")
    
    # 分析局面
    analysis = engine.analyze_position(fen, think_time=3.0)
    print(f"评估分数: {analysis['score']}")
```

### 3. 机械臂控制模块 (`robot/`)

**职责**: 控制机械臂执行走法

#### 子模块

- **RobotController** (`controller.py`): 控制器基类
- **SimulationRobot** (`simulator.py`): 仿真机械臂
- **CoordinateConverter** (`coordinate.py`): 坐标转换工具

#### 支持的机械臂类型

- `simulation` - 仿真模式(默认)
- `dobot` - DOBOT机械臂(TODO)
- `elephant_robotics` - 大象机器人(TODO)

#### 使用示例

```python
from robot import RobotController

with RobotController(robot_type="simulation") as robot:
    # 移动棋子
    robot.move_piece(
        from_x=100, from_y=100,
        to_x=150, to_y=150
    )
    
    # 执行UCI走法
    robot.execute_uci_move("h3e3", board_origin=(0, 0, 0))
```

### 4. 游戏管理器 (`game_manager.py`)

**职责**: 协调整个游戏流程

```python
from game_manager import GameManager

with GameManager() as manager:
    manager.initialize()
    manager.start_components()
    manager.play_game()
```

### 5. 工具函数 (`utils.py`)

提供FEN转换、坐标转换、记谱法等工具:

- **FENUtils**: FEN串解析和生成
- **CoordinateUtils**: 坐标转换(UCI↔行列索引↔机械臂坐标)
- **MoveNotationUtils**: 记谱法转换(UCI↔中文记谱)
- **BoardUtils**: 棋盘状态工具

---

## 开发指南

### 添加新机械臂支持

1. 在 `robot/` 下创建新的控制器类:

```python
# robot/my_robot.py
from .controller import RobotController

class MyRobotController(RobotController):
    def initialize(self):
        # 初始化你的机械臂
        pass
    
    def move_to(self, x, y, z):
        # 实现移动逻辑
        pass
```

2. 在 `config.py` 中添加配置:

```python
MY_ROBOT_CONFIG = {
    "port": "COM3",
    "baudrate": 115200
}
```

### 添加新功能

遵循模块化原则:
1. 在对应模块下创建新文件
2. 编写完整的docstring和类型注解
3. 添加单元测试到 `tests/`
4. 更新本README

### 代码规范

- 使用Google风格的docstring
- 添加类型注解
- 遵循PEP 8编码规范
- 每个模块都有独立的日志记录器

---

## 故障排除

### 常见问题

#### 1. 摄像头无法打开

**症状**: `无法打开摄像头 0`

**解决**:
- 检查摄像头是否被其他程序占用
- 尝试更改 `CAMERA_INDEX` 为其他值
- 确认摄像头驱动已正确安装

#### 2. AI引擎启动失败

**症状**: `引擎未返回 uciok`

**解决**:
- 确认Pikafish引擎文件存在且可执行
- 检查 `ENGINE_PATH` 配置是否正确
- 确认CPU支持AVX2指令集

#### 3. 棋盘识别失败

**症状**: `棋盘检测失败`

**解决**:
- 改善光照条件,避免反光
- 确保棋盘完整出现在画面中
- 调整摄像头角度和距离
- 检查模型文件是否存在

#### 4. 机械臂移动异常

**症状**: 坐标不准确或碰撞

**解决**:
- 重新校准坐标系
- 检查 `BOARD_ORIGIN` 配置
- 调整安全高度参数

### 日志查看

日志文件保存在 `chchess.log`,可通过以下级别过滤:

```python
# config.py
LOG_LEVEL = "DEBUG"  # DEBUG, INFO, WARNING, ERROR
```

---

## 许可证

本项目采用 GPL v3.0 许可证

---

## 贡献指南

欢迎提交Issue和Pull Request!

### 提交PR前请检查:

- [ ] 代码符合规范
- [ ] 添加了必要的注释
- [ ] 通过了单元测试
- [ ] 更新了文档