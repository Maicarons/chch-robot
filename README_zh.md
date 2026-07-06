# CH-RO 中国象棋机器人

CH-RO 是一个中国象棋人机对弈机器人系统，集成摄像头棋盘识别、Pikafish AI 搜索、机械臂指令转换、STM32 TCP 控制和 Flask Web 管理界面。

English README: [README.md](README.md)

## 功能

- 支持 USB 摄像头和网络摄像头。
- 基于 ONNX 的姿态检测和棋子分类流程。
- 支持棋盘多帧稳定和动态走子识别。
- 集成 Pikafish UCI 中国象棋引擎。
- 支持 `simulation` 和 `hardware` 两种机器人模式。
- 支持 STM32 五值运动指令和 homing 握手。
- 提供 Flask Web 界面，用于摄像头预览、棋盘识别、AI 走棋和机器人状态查看。

## 项目结构

```text
ai/                                      Pikafish 引擎封装
core/                                    ONNX 推理辅助模块
vision/                                  摄像头、检测、映射、稳定和识别
robot/                                   机器人协议、TCP 客户端和控制器
web_simulation/                          Flask 后端和浏览器界面
model/                                   ONNX 模型文件
tests/                                   Python 测试和样例图片
docs/                                    VitePress 文档源码
firmware/stm32-tcp-server/               STM32 TCP 服务固件
firmware/stm32-f103-keil-robot/          STM32F103 Keil 工程
firmware/stm32-f103-angle-plan/          STM32F103 角度规划参考代码
camera_servers/orange-pi-camera/         Orange Pi 摄像头服务
camera_servers/raspberry-pi-zero2w-usb-camera/  Raspberry Pi 摄像头服务
```

## 快速开始

安装 Python 依赖：

```bash
pip install -r requirements.txt
```

下载 Pikafish，将二进制文件放入 `Pikafish/`。如果文件名不同，修改 `config.py` 中的 `ENGINE_PATH`。

启动 Web 界面：

```bash
python web_simulation/app.py
```

浏览器打开 `http://localhost:5000`。

启动命令行：

```bash
python main.py
python main.py --demo
python main.py --test-camera
python main.py --test-engine
```

## 测试

```bash
python -m pytest tests/ -v
```

## 文档

文档使用 VitePress 管理，包含英文和中文页面。

```bash
npm install
npm run docs:dev
npm run docs:build
```

文档入口是 `docs/index.md`。

## 配置

主要运行参数在 `config.py` 中，包括摄像头来源、模型路径、Pikafish 路径、机器人网络地址、棋盘格距和超时参数。无人值守启动 Flask 时可设置：

```bash
CHRO_SKIP_STARTUP_PROMPT=1
```

## 硬件说明

STM32 控制器接收五值指令：

```text
startX,startY,endX,endY,signal
```

归位指令：

```text
m1_angle,m2_angle,0,0,99
```

完成确认是 `STATE:5,RESULT:1`。
