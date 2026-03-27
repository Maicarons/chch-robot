# 中国象棋人机博弈项目 - 文件索引

## 📁 项目结构

```
chchess/
│
├── 📄 README.md                 # 项目概述和使用说明
├── 📄 QUICKSTART.md             # 快速开始指南（新手必读）
├── 📄 DEVELOPMENT.md            # 完整开发文档（详细说明）
├── 📄 INDEX.md                  # 本文件，项目导航
│
├── 🐍 main.py                   # 主程序入口（交互式命令行）
├── 🐍 game_manager.py           # 游戏管理器（核心协调器）
├── 🐍 board_recognition.py      # 棋盘识别模块（OpenCV）
├── 🐍 ai_engine.py              # AI 引擎模块（UCI 协议）
├── 🐍 robot_control.py          # 机械臂控制模块
├── 🐍 utils.py                  # 工具函数（FEN、坐标转换等）
├── 🐍 config.py                 # 配置文件
├── 🐍 test_all.py               # 综合测试脚本
│
├── 📦 requirements.txt          # Python 依赖包列表
└── 🤖 pikafish-avx2.exe         # AI 引擎（需自行下载）
```

---

## 🚀 快速导航

### 新手入门路径
1. **阅读 README.md** → 了解项目是什么
2. **阅读 QUICKSTART.md** → 快速安装和运行
3. **运行 test_all.py** → 测试所有组件
4. **运行 main.py --demo** → 查看演示
5. **开始游戏** → `python main.py` 输入 `start`

### 开发者路径
1. **阅读 DEVELOPMENT.md** → 深入理解架构
2. **研究源代码** → 学习实现细节
3. **修改配置** → 适应你的硬件
4. **扩展功能** → 添加新特性

---

## 📚 文档详解

### README.md - 项目封面
**适合人群**: 所有人  
**内容**:
- 项目概述
- 系统架构图
- 目录结构
- 核心模块说明
- 硬件需求
- 配置说明
- 使用示例
- 故障排除

**何时阅读**: 
- 第一次接触项目时
- 需要快速查找某个功能时

---

### QUICKSTART.md - 快速开始
**适合人群**: 新用户  
**内容**:
- 安装步骤（详细截图）
- 第一次使用指南
- 开始游戏的两种方式
- 游戏流程说明
- 常用命令速查表
- 常见问题快速解决
- 进阶使用技巧

**何时阅读**:
- 准备运行项目时
- 忘记某个命令时
- 遇到常见问题时

---

### DEVELOPMENT.md - 开发文档
**适合人群**: 开发者、高级用户  
**内容**:
- 完整系统架构
- 详细流程图
- 每个模块的深度解析
- 数据流分析
- 坐标系定义和转换公式
- 安装部署细节
- 故障诊断大全
- 性能优化技巧
- 扩展功能开发示例
- 安全注意事项
- 维护保养指南
- 技术栈详解
- 开发路线图

**何时阅读**:
- 需要修改代码时
- 想要理解内部原理时
- 进行二次开发时
- 遇到复杂问题时

---

## 💻 代码文件详解

### main.py - 主程序入口 ⭐⭐⭐
**重要性**: ★★★★★  
**功能**:
- 交互式命令行界面
- 命令解析和分发
- 参数处理
- 错误处理
- 日志配置

**关键类**:
- `InteractiveShell` - 交互式外壳

**常用命令**:
```bash
python main.py              # 交互模式
python main.py --demo       # 演示模式
python main.py --calibrate  # 校准系统
python main.py --test-camera  # 测试摄像头
```

**修改场景**:
- 添加新命令
- 修改界面样式
- 调整参数处理逻辑

---

### game_manager.py - 游戏管理器 ⭐⭐⭐
**重要性**: ★★★★★  
**功能**:
- 协调整个游戏流程
- 管理所有组件生命周期
- 维护游戏状态
- 控制回合切换
- 检测游戏结束

**关键类**:
- `GameManager` - 游戏主控制器

**核心方法**:
```python
initialize()              # 初始化
start_components()        # 启动组件
recognize_initial_board() # 识别初始棋盘
get_ai_move()             # 获取 AI 走法
execute_ai_move()         # 执行 AI 走法
wait_for_player_move()    # 等待玩家
play_game()               # 主游戏循环
```

**修改场景**:
- 改变游戏流程
- 添加新的游戏模式
- 调整回合控制逻辑

---

### board_recognition.py - 棋盘识别 ⭐⭐
**重要性**: ★★★★☆  
**功能**:
- 摄像头控制
- 图像捕获和处理
- 棋盘网格检测
- 棋子识别
- FEN 生成

**关键类**:
- `BoardRecognizer` - 棋盘识别器

**核心技术**:
```python
detect_board_grid()      # 检测棋盘边界
recognize_pieces()       # 识别棋子
get_fen_from_recognition() # 生成 FEN
calibrate_board()        # 校准
```

**修改场景**:
- 改进识别算法
- 适配不同的摄像头
- 提高识别准确率
- 添加特殊效果处理

---

### ai_engine.py - AI 引擎 ⭐⭐⭐
**重要性**: ★★★★★  
**功能**:
- UCI 协议实现
- 进程间通信
- 走法获取和验证
- 位置分析

**关键类**:
- `AIEngine` - AI 引擎控制器

**UCI 通信流程**:
```python
start()          # 启动引擎
set_position()   # 设置位置
get_best_move()  # 获取最佳走法
analyze_position() # 分析局面
```

**修改场景**:
- 更换 AI 引擎
- 调整 UCI 参数
- 优化通信效率
- 添加引擎管理功能

---

### robot_control.py - 机械臂控制 ⭐⭐
**重要性**: ★★★★☆  
**功能**:
- 运动控制
- 夹爪控制
- 路径规划
- 坐标转换
- 支持仿真和真实硬件

**关键类**:
- `RobotController` - 机械臂控制器

**运动序列**:
```python
move_to()           # 点到点移动
pick_piece()        # 抓取棋子
place_piece()       # 放置棋子
execute_uci_move()  # 执行 UCI 走法
```

**修改场景**:
- 集成不同的机械臂
- 优化运动轨迹
- 添加力反馈
- 改进安全性

---

### utils.py - 工具函数 ⭐⭐⭐
**重要性**: ★★★★★  
**功能**:
- FEN 串解析和生成
- 坐标转换
- 记谱法转换
- 棋盘状态工具

**关键类**:
- `FENUtils` - FEN 处理工具
- `CoordinateUtils` - 坐标转换工具
- `MoveNotationUtils` - 记谱法转换工具
- `BoardUtils` - 棋盘状态工具

**核心方法**:
```python
FENUtils.parse_fen(fen)     # 解析 FEN
FENUtils.to_fen(board)      # 生成 FEN
CoordinateUtils.uci_to_indices()  # UCI→索引
CoordinateUtils.indices_to_uci()  # 索引→UCI
```

**修改场景**:
- 添加新的工具函数
- 优化转换算法
- 支持新的记谱格式

---

### config.py - 配置文件 ⭐
**重要性**: ★★★☆☆  
**功能**:
- 集中管理所有配置参数
- 便于调整和实验

**配置分类**:
- 摄像头配置
- 棋盘识别配置
- AI 引擎配置
- 机械臂配置
- 游戏配置
- 显示配置
- 日志配置

**修改场景**:
- 适配不同硬件
- 调整性能参数
- 启用/禁用功能

---

### test_all.py - 综合测试 ⭐
**重要性**: ★★★☆☆  
**功能**:
- 测试所有模块
- 验证系统集成
- 回归测试

**测试覆盖**:
```python
test_utils()            # 工具函数
test_ai_engine()        # AI 引擎
test_board_recognition() # 棋盘识别
test_robot_control()    # 机械臂
test_game_manager()     # 游戏管理器
```

**使用场景**:
- 安装后验证
- 修改后测试
- 定期健康检查

---

## 🔧 配置说明

### config.py 关键参数

#### 摄像头配置
```python
CAMERA_INDEX = 0          # 摄像头索引
CAMERA_WIDTH = 1280       # 分辨率宽度
CAMERA_HEIGHT = 720       # 分辨率高度
```

#### 棋盘识别配置
```python
CANNY_THRESHOLD1 = 50     # 边缘检测阈值 1
CANNY_THRESHOLD2 = 150    # 边缘检测阈值 2
SQUARE_SIZE_MM = 50       # 格子尺寸（毫米）
```

#### AI 引擎配置
```python
ENGINE_PATH = "./pikafish-avx2.exe"  # 引擎路径
ENGINE_DEPTH = 15         # 搜索深度
THINK_TIME = 5000         # 思考时间（毫秒）
HASH_SIZE_MB = 128        # 哈希表大小
```

#### 机械臂配置
```python
ROBOT_TYPE = "simulation"  # 类型：simulation/dobot/elephant_robotics
HOME_POSITION_X = 100      # home 点 X 坐标
HOME_POSITION_Y = 100      # home 点 Y 坐标
HOME_POSITION_Z = 150      # home 点 Z 坐标
```

---

## 🛠️ 常见任务速查

### 1. 开始游戏
```bash
python main.py
>>> start
```

### 2. 校准系统
```bash
python main.py --calibrate
```

### 3. 运行演示
```bash
python main.py --demo
```

### 4. 测试组件
```bash
python test_all.py
```

### 5. 查看日志
```bash
tail -f chchess.log  # Linux/Mac
type chchess.log     # Windows
```

### 6. 修改配置
编辑 `config.py` 相应参数

### 7. 调试模式
```python
# config.py 中设置
DEBUG_MODE = True
LOG_LEVEL = "DEBUG"
```

---

## 📊 性能指标

### 典型性能数据
| 操作 | 耗时 | 备注 |
|------|------|------|
| 棋盘识别 | ~500ms | 包括图像捕获和处理 |
| AI 思考（深度 15） | ~3-5s | 取决于局面复杂度 |
| 机械臂移动 | ~2-3s | 单步移动 |
| 走法验证 | <100ms | 简单验证 |

### 优化空间
- 使用 GPU 加速识别 → 提升 2-3x
- 降低 AI 深度到 10 → 提升 2x 速度
- 并行处理图像 → 提升 1.5x

---

## 🎯 学习路径建议

### 初学者
1. 理解整体流程（README）
2. 学会使用和配置（QUICKSTART）
3. 修改 config.py 参数
4. 阅读 utils.py 了解数据结构

### 进阶开发者
1. 深入研究各模块（DEVELOPMENT）
2. 理解 UCI 协议（ai_engine.py）
3. 掌握图像处理（board_recognition.py）
4. 学习运动控制（robot_control.py）

### 专家级
1. 优化性能和算法
2. 添加新功能
3. 集成更多硬件
4. 贡献代码到社区

---

## 🔗 相关资源链接

### 官方文档
- [OpenCV 文档](https://docs.opencv.org/)
- [UCI 协议规范](https://www.shredderchess.com/download/UCI.pdf)
- [Pikafish 引擎](https://github.com/pikafish-chess/Pikafish)

### 教程
- [Python OpenCV 教程](https://pyimagesearch.com/)
- [机械臂控制基础](https://www.qccad.com/mechanism/robotics/)
- [中国象棋规则](http://www.xqbase.com/)


## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

### 提交 Bug
1. 描述问题
2. 提供复现步骤
3. 附上日志文件
4. 说明环境信息

### 提交功能
1. Fork 项目
2. 创建特性分支
3. 实现功能并测试
4. 提交 Pull Request

---

## 📄 许可证

GPL v3.0
