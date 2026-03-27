# 快速开始指南

## 安装步骤

### 1. 安装 Python 依赖
```bash
cd chchess
pip install -r requirements.txt
```

### 2. 准备 AI 引擎
> **注意**: Pikafish 的可执行文件请自行下载并放置在项目根目录下（默认引擎：./Pikafish/pikafish-avx2.exe，如需更改请到 config.py 中修改）。

下载 Pikafish-avx2 引擎并放到 chchess 目录：
```bash
# 从 https://github.com/pikafish-chess/Pikafish/releases 下载最新版本
# 重命名为 pikafish-avx2.exe 并放到当前目录
```

### 3. 配置系统
编辑 `config.py` 文件，根据你的硬件调整参数。

## 第一次使用

### 步骤 1: 测试各个组件
```bash
# 测试摄像头
python main.py --test-camera

# 测试 AI 引擎
python main.py --test-engine

# 测试机械臂（仿真模式）
python main.py --test-robot
```

### 步骤 2: 校准系统
```bash
python main.py --calibrate
```

按照屏幕提示：
1. 将棋盘放置在摄像头视野中心
2. 按 Enter 键捕获图像
3. 系统会自动检测棋盘边界
4. 机械臂会执行测试动作

### 步骤 3: 运行演示
```bash
python main.py --demo
```

## 开始游戏

### 方式 1: 交互式命令行
```bash
python main.py
```

然后输入命令：
```
>>> start
```

### 方式 2: 直接启动游戏
```bash
python game_manager.py
```

## 游戏流程说明

1. **初始设置**
   - 系统启动摄像头
   - 拍摄当前棋盘
   - 识别棋子位置生成 FEN

2. **AI 回合**
   - AI 引擎分析局面
   - 计算最佳走法
   - 机械臂执行移动

3. **玩家回合**
   - 等待玩家走棋
   - 摄像头检测棋盘变化
   - 验证走法合法性

4. **循环继续**
   - 重复步骤 2-3
   - 直到游戏结束

## 常用命令

| 命令 | 说明 |
|------|------|
| `start` | 开始游戏 |
| `calibrate` | 校准系统 |
| `demo` | 演示模式 |
| `status` | 显示状态 |
| `help` | 帮助信息 |
| `quit` | 退出程序 |

## 故障排除

### 问题 1: 摄像头无法启动
**解决**: 
- 检查摄像头连接
- 确认没有其他程序占用摄像头
- 修改 `config.py` 中的 `CAMERA_INDEX`

### 问题 2: 棋盘识别失败
**解决**:
- 确保光照充足且均匀
- 调整摄像头角度使棋盘完整可见
- 清洁棋盘表面

### 问题 3: AI 引擎无响应
**解决**:
- 确认 Pikafish 引擎路径正确
- 检查引擎文件是否有执行权限
- 查看日志文件获取详细错误

### 问题 4: 机械臂移动异常
**解决**:
- 重新校准坐标系
- 检查目标位置是否在可达范围内
- 降低移动速度确保安全

## 进阶使用

### 调整 AI 难度
编辑 `config.py`:
```python
ENGINE_DEPTH = 10  # 降低深度（1-20）
THINK_TIME = 3000  # 减少思考时间（毫秒）
```

### 自定义棋盘尺寸
编辑 `config.py`:
```python
SQUARE_SIZE_MM = 60  # 格子尺寸（毫米）
BOARD_ROWS = 10      # 行数
BOARD_COLS = 9       # 列数
```

### 更换机械臂类型
编辑 `config.py`:
```python
ROBOT_TYPE = "dobot"  # 或 "elephant_robotics"
```

## 性能优化建议

1. **提高识别速度**
   - 降低摄像头分辨率
   - 减少图像处理区域
   - 使用 GPU 加速 OpenCV

2. **提高 AI 强度**
   - 增加搜索深度
   - 延长思考时间
   - 增大哈希表大小

3. **提高机械臂精度**
   - 定期校准坐标系
   - 使用更慢的移动速度
   - 添加视觉反馈校正

## 扩展功能开发

项目支持以下扩展：
- 添加触摸屏界面
- 集成语音播报
- 支持多种棋类变体
- 添加在线对战功能
- 实现棋谱分析和回放

## 技术支持

遇到问题可以：
1. 查看日志文件 `chchess.log`
2. 运行诊断测试 `python main.py --test-*`
3. 提交 Issue 到项目仓库

祝你游戏愉快！♟️
