# Web仿真环境使用说明

## 功能概述

Web仿真环境集成了项目的核心功能模块：
- **视觉识别** (`vision.BoardRecognizer`) - 棋盘检测和棋子识别
- **AI引擎** (`ai.AIEngine`) - Pikafish中国象棋AI
- **机械臂控制** (`robot.RobotController`) - 模拟机械臂执行走法

## 启动方式

```bash
cd G:\GitHub\chch-robot\web_simulation
python app.py
```

访问 http://localhost:5000

## 使用流程

### 1. 标准对局（从头开始）

1. 打开网页
2. 点击"开始新对局"
3. 玩家执红先行，点击棋子选择起始位置，再点击目标位置
4. 点击"获取AI走法"让AI思考
5. AI走法会通过模拟机械臂执行

### 2. 残局对局（从图片识别）

1. 点击"选择图片文件"上传残局图片
2. 点击"识别棋盘"进行识别
3. 查看识别结果和FEN码
4. 点击"开始新对局"（系统会自动使用识别的布局）
5. 开始对弈

### 3. 摄像头实时识别

1. 确保摄像头已连接
2. 选择"网络摄像头"模式
3. 点击"捕获图像"
4. 点击"识别棋盘"

## 技术架构

### 后端 (Flask)

- `app.py` - Flask应用，提供REST API
- 调用项目核心模块：
  - `from vision import BoardRecognizer`
  - `from ai import AIEngine`
  - `from robot import RobotController`

### 前端

- `templates/index.html` - 主页面
- `static/js/app.js` - 前端逻辑
- `static/css/style.css` - 样式

### 关键API

| 接口 | 方法 | 功能 |
|------|------|------|
| `/api/recognize` | POST | 识别棋盘状态 |
| `/api/game/start` | POST | 开始新游戏 |
| `/api/player_move` | POST | 处理玩家走法 |
| `/api/ai_move` | POST | 获取AI走法 |
| `/api/simulate_robot` | POST | 模拟机械臂移动 |

## FEN码生成

残局识别后，系统会：
1. 将识别的`board_state`转换为标准FEN格式
2. 使用`board_state_to_fen()`函数生成FEN
3. 将FEN传递给AI引擎作为初始局面

## 注意事项

1. **必须先点击"开始新对局"** 才能开始走棋
2. 游戏中禁用"识别棋盘"按钮，防止误操作
3. AI操控玩家棋子时判定为AI失败
4. UCI坐标系统使用方案1（行号反转）

## 调试信息

前端日志会显示：
- UCI走法解析过程
- 棋盘状态变化
- AI思考和机械臂执行状态

后端日志会显示：
- AI引擎通信详情
- FEN更新情况
- 走法历史同步状态
