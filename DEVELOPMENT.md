# 线下棋盘 + 人机博弈中国象棋项目 - 完整开发文档

## 项目概述

本项目实现了一个完整的线下中国象棋人机对弈系统，整合了计算机视觉、AI 引擎和机械臂控制技术。

### 核心功能
1. **视觉识别**: 通过摄像头拍摄棋盘，使用 OpenCV 识别棋子位置
2. **AI 决策**: 集成 Pikafish 引擎（基于 UCI 协议）进行智能决策
3. **机械臂控制**: 控制机械臂执行 AI 走法，实现物理移动棋子
4. **游戏管理**: 自动检测玩家走棋，验证合法性，管理游戏流程

---

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                     用户交互层                            │
│              (命令行界面 / 触摸屏界面)                      │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                    游戏管理层                             │
│            GameManager - 协调整个游戏流程                   │
└─────────────────────────────────────────────────────────┘
        ↓                       ↓                       ↓
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  棋盘识别模块  │      │   AI 引擎模块  │      │  机械臂控制模块 │
│BoardRecognizer│     │  AIEngine    │     │RobotController│
│  (OpenCV)    │      │ (Pikafish)   │      │ (仿真/真实)   │
└──────────────┘      └──────────────┘      └──────────────┘
        ↓                       ↓                       ↓
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   摄像头      │      │  UCI 协议     │      │  坐标转换     │
│   图像捕获    │      │  走法通信     │      │  路径规划     │
└──────────────┘      └──────────────┘      └──────────────┘
```

---

## 完整流程图

```
开始
  ↓
初始化系统
  ├→ 启动摄像头
  ├→ 加载 AI 引擎
  └→ 初始化机械臂
  ↓
校准系统
  ├→ 棋盘位置校准
  └→ 机械臂测试
  ↓
识别初始棋盘
  ├→ 拍摄棋盘
  ├→ OpenCV 处理
  ├→ 识别棋子
  └→ 生成 FEN (第 1 步记录)
  ↓
┌───────────────┐
│  游戏主循环    │
└───────────────┘
  ↓
检查游戏状态
  ├→ 是否结束？→ 是 → 显示结果 → 结束
  └→ 否
  ↓
判断当前回合
  ├→ 玩家回合
  │    ↓
  │  等待玩家走棋
  │    ↓
  │  检测棋盘变化
  │    ↓
  │  验证走法合法性
  │    ↓
  │  更新 FEN
  │    ↓
  └→ AI 回合
       ↓
     AI 思考
       ↓
     获取最佳走法 (UCI 格式)
       ↓
     记录走法 (第 2 步)
       ↓
     机械臂执行
       ├→ 坐标转换
       ├→ 路径规划
       ├→ 抓取棋子
       ├→ 移动到目标
       └→ 放置棋子
       ↓
     更新 FEN
  ↓
切换回合
  ↓
返回游戏主循环
```

---

## 文件结构

```
chchess/
├── main.py                  # 主程序入口（交互式命令行）
├── game_manager.py          # 游戏管理器（核心协调器）
├── board_recognition.py     # 棋盘识别模块（OpenCV）
├── ai_engine.py             # AI 引擎模块（UCI 协议）
├── robot_control.py         # 机械臂控制模块
├── utils.py                 # 工具函数（FEN、坐标转换等）
├── config.py                # 配置文件
├── requirements.txt         # Python 依赖
├── test_all.py              # 综合测试脚本
├── QUICKSTART.md            # 快速开始指南
├── README.md                # 项目说明文档
└── DEVELOPMENT.md           # 本开发文档
```

---

## 核心模块详解

### 1. BoardRecognizer - 棋盘识别模块

**职责**:
- 摄像头控制和图像捕获
- 棋盘网格检测（边缘检测、轮廓提取）
- 棋子识别（颜色识别、类型推断）
- FEN 串生成

**关键技术**:
```python
# 1. 边缘检测
edges = cv2.Canny(gray, threshold1, threshold2)

# 2. 轮廓查找
contours, _ = cv2.findContours(edges, RETR_EXTERNAL, CHAIN_APPROX_SIMPLE)

# 3. 四边形检测
epsilon = 0.02 * arcLength(contour, True)
approx = approxPolyDP(contour, epsilon, True)

# 4. 透视变换
matrix = getPerspectiveTransform(corners, dst_points)
warped = warpPerspective(image, matrix, dst_size)

# 5. 颜色识别（HSV 空间）
mask = inRange(hsv, lower_bound, upper_bound)
```

**改进方向**:
- 使用深度学习提高棋子识别准确率（CNN、YOLO）
- 添加棋盘角度自动校正
- 实现抗干扰算法（光照变化、部分遮挡）

---

### 2. AIEngine - AI 引擎模块

**职责**:
- UCI 协议实现
- 进程间通信（管道）
- 走法获取和验证
- 位置分析

**UCI 通信流程**:
```python
# 1. 启动引擎进程
process = Popen(engine_path, stdin=PIPE, stdout=PIPE)

# 2. 发送 uci 命令
send("uci")
wait_for("uciok")

# 3. 设置变体
send("setoption name UCI_Variant value xiangqi")

# 4. 设置位置
send(f"position fen {fen} moves {moves}")

# 5. 开始思考
send(f"go depth {depth}")

# 6. 接收 bestmove
bestmove = parse_bestmove()
```

**支持的 UCI 命令**:
- `uci` - 初始化
- `setoption` - 设置参数
- `position` - 设置位置
- `go` - 开始思考
- `stop` - 停止思考
- `quit` - 退出

---

### 3. RobotController - 机械臂控制模块

**职责**:
- 运动控制（点到点移动）
- 夹爪控制（开合）
- 路径规划
- 坐标转换

**运动学模型**:
```python
# 棋盘坐标 → 机械臂坐标
robot_x = origin_x + col * square_size + offset_x
robot_y = origin_y + row * square_size + offset_y
robot_z = origin_z + pick_height

# 运动序列
1. 移动到起点上方 (safe_z)
2. 下降到抓取位置
3. 闭合夹爪
4. 抬起
5. 移动到终点上方
6. 下降到放置位置
7. 打开夹爪
8. 抬起
```

**真实机械臂集成**:
- **Dobot**: 使用 Dobot SDK
- **大象机器人**: 使用 pymycobot 库
- **自定义**: 通过串口/网络通信

---

### 4. GameManager - 游戏管理器

**职责**:
- 组件生命周期管理
- 游戏状态维护
- 回合控制
- 走法验证
- 游戏结束检测

**状态机**:
```
IDLE → INITIALIZING → READY → PLAYING → GAME_OVER
                              ↓
                          CALIBRATING
```

**关键方法**:
- `initialize()` - 初始化所有组件
- `start_components()` - 启动硬件设备
- `recognize_initial_board()` - 识别初始局面
- `get_ai_move()` - 获取 AI 走法
- `execute_ai_move()` - 执行 AI 走法
- `wait_for_player_move()` - 等待玩家走棋
- `detect_player_move()` - 检测玩家走法

---

## 数据流说明

### FEN 数据流
```
摄像头 → 图像 → 棋盘识别 → FEN 串 → AI 引擎
                                      ↓
                                  新 FEN 串 ← 走法
                                      ↓
                                显示/存储
```

### 走法数据流
```
AI 思考 → UCI 走法 → 坐标转换 → 机械臂坐标 → 运动控制
                                                    ↓
玩家走棋 ← 棋盘检测 ← 图像捕获 ← 执行完成
```

---

## 坐标系定义

### 棋盘坐标系
- **原点**: 左下角（红方视角）
- **X 轴**: 从左到右（a-i，9 列）
- **Y 轴**: 从下到上（1-10，10 行）

### 机械臂坐标系
- **原点**: 机械臂基座中心
- **X 轴**: 水平方向
- **Y 轴**: 垂直方向  
- **Z 轴**: 高度方向

### 坐标转换公式
```python
# 棋盘格 (row, col) → 机械臂坐标 (x, y, z)
x = board_origin_x + col * square_size + square_size / 2
y = board_origin_y + row * square_size + square_size / 2
z = board_origin_z + safe_height
```

---

## 安装和部署

### 系统要求
- **操作系统**: Windows 10/11, Linux, macOS
- **Python**: 3.8+
- **内存**: 至少 4GB
- **存储**: 至少 500MB

### 硬件要求
- **摄像头**: USB 摄像头（720p 以上，推荐 1080p）
- **机械臂**: 6 自由度机械臂（工作半径>300mm）
- **计算设备**: Intel i5 或同等性能 CPU

### 安装步骤

1. **克隆项目**
```bash
git clone <repository_url>
cd chchess
```

2. **创建虚拟环境**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **下载 AI 引擎**
```bash
# 下载 Pikafish-avx2.exe
# 放到 chchess 目录
```

5. **配置系统**
```bash
# 编辑 config.py
# 根据实际硬件调整参数
```

6. **测试运行**
```bash
python test_all.py
```

---

## 故障诊断

### 常见问题及解决方案

#### 1. 摄像头无法启动
**症状**: `BoardRecognizer.start_camera()` 失败

**排查步骤**:
1. 检查设备连接：`ls /dev/video*` (Linux) 或设备管理器 (Windows)
2. 测试其他应用是否能使用摄像头
3. 修改 `CAMERA_INDEX` 参数尝试不同设备

**解决**:
```python
# 尝试不同的摄像头索引
CAMERA_INDEX = 0  # 或 1, 2...
```

#### 2. 棋盘识别率低
**症状**: 经常检测不到棋盘或棋子识别错误

**排查**:
1. 检查光照条件
2. 确认摄像头角度
3. 清洁棋盘表面

**优化**:
```python
# 调整 Canny 阈值
CANNY_THRESHOLD1 = 30  # 降低以提高敏感度
CANNY_THRESHOLD2 = 100

# 调整颜色识别范围
RED_LOWER1 = (0, 80, 80)  # 扩大范围
```

#### 3. AI 引擎超时
**症状**: AI 长时间不返回走法

**排查**:
1. 检查引擎进程是否运行
2. 查看引擎日志输出
3. 增加超时时间

**解决**:
```python
# 增加思考时间
THINK_TIME = 10000  # 10 秒

# 降低搜索深度
ENGINE_DEPTH = 10
```

#### 4. 机械臂定位不准
**症状**: 机械臂无法准确抓取棋子

**排查**:
1. 重新校准坐标系
2. 检查机械臂零点标定
3. 验证棋盘尺寸参数

**解决**:
```python
# 精细调整原点偏移
BOARD_TOP_LEFT_X = -5  # 微调 X 偏移
BOARD_TOP_LEFT_Y = 3   # 微调 Y 偏移
```

---

## 性能优化

### 1. 图像识别优化
```python
# 使用 GPU 加速
cv2.cuda_GpuMat()

# 降低处理分辨率
CAMERA_WIDTH = 640  # 降低宽度
CAMERA_HEIGHT = 480

# ROI 优化（只处理棋盘区域）
roi = image[y1:y2, x1:x2]
```

### 2. AI 引擎优化
```python
# 使用哈希表
USE_HASH_TABLE = True
HASH_SIZE_MB = 256

# 多线程搜索
THREADS = 4

# 开局库
USE_BOOK = True
```

### 3. 机械臂优化
```python
# 优化路径规划
# 减少不必要的移动
# 使用梯形速度曲线
```

---

## 扩展功能开发

### 1. 添加语音播报
```python
import pyttsx3

class VoiceAnnouncer:
    def __init__(self):
        self.engine = pyttsx3.init()
    
    def announce(self, text):
        self.engine.say(text)
        self.engine.runAndWait()

# 使用
announcer = VoiceAnnouncer()
announcer.announce("炮二平五")
```

### 2. 触摸屏界面
```python
import tkinter as tk

class TouchUI:
    def __init__(self):
        self.root = tk.Tk()
        # 添加触摸按钮和显示
```

### 3. 棋谱记录和回放
```python
import json

class GameRecorder:
    def save_game(self, moves, result):
        record = {
            'moves': moves,
            'result': result,
            'timestamp': time.time()
        }
        with open('records.json', 'a') as f:
            json.dump(record, f)
```

### 4. 在线对战功能
```python
import websocket

class OnlineClient:
    def connect(self, server_url):
        self.ws = websocket.WebSocket()
        self.ws.connect(server_url)
    
    def send_move(self, move):
        self.ws.send(json.dumps({'move': move}))
```

---

## 安全注意事项

### 机械臂安全
1. **工作区域**: 设置物理围栏或警示线
2. **急停开关**: 安装紧急停止按钮
3. **速度限制**: 在人员附近时降低速度
4. **力反馈**: 添加碰撞检测

### 电气安全
1. **电源隔离**: 使用隔离变压器
2. **接地保护**: 确保良好接地
3. **过载保护**: 添加保险丝或断路器

### 激光安全（如使用）
1. **防护眼镜**: 佩戴相应波长防护镜
2. **警示标识**: 张贴激光警告标志

---

## 维护和保养

### 日常维护
- **摄像头镜头**: 定期清洁
- **机械臂关节**: 润滑和紧固
- **棋盘表面**: 保持清洁无划痕

### 定期校准
- **每周**: 棋盘坐标系校准
- **每月**: 机械臂零点标定
- **每季度**: 全面系统检查

---

## 技术栈总结

| 模块 | 技术 | 版本 |
|------|------|------|
| 编程语言 | Python | 3.8+ |
| 图像处理 | OpenCV | 4.5+ |
| 数值计算 | NumPy | 1.20+ |
| AI 引擎 | Pikafish | latest |
| 通信协议 | UCI | 1.0 |
| 机械臂 | 仿真/真实 | - |

---

## 开发路线图

### Phase 1: 基础功能 ✓
- [x] 框架搭建
- [x] UCI 协议实现
- [x] 基本走法生成
- [ ] 棋盘识别（基础版）

### Phase 2: 功能完善
- [ ] 棋盘识别（增强版）
- [ ] 机械臂集成
- [ ] 走法验证
- [ ] 游戏界面

### Phase 3: 优化提升
- [ ] 性能优化
- [ ] AI 强度提升
- [ ] 用户体验改进
- [ ] 稳定性增强

### Phase 4: 扩展功能
- [ ] 多棋类支持
- [ ] 在线对战
- [ ] 棋谱分析
- [ ] 教学功能

---

## 参考资料

### UCI 协议
- [UCI Protocol Specification](https://www.shredderchess.com/download/UCI.pdf)
- [Stockfish UCI Implementation](https://github.com/official-stockfish/Stockfish)

### 中国象棋
- [中国象棋规则](http://www.xqbase.com/)
- [FEN 格式说明](https://en.wikipedia.org/wiki/Forsyth%E2%80%93Edwards_Notation)

### OpenCV
- [OpenCV 官方文档](https://docs.opencv.org/)
- [计算机视觉教程](https://www.pyimagesearch.com/)

### 机械臂控制
- [ROS MoveIt](https://moveit.ros.org/)
- [机械臂运动学](https://www.qccad.com/mechanism/robotics/)

