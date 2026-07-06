# 系统架构

## 运行流程

```text
摄像头画面
  -> 视觉检测和棋子分类
  -> 稳定棋盘状态
  -> FEN 和走法历史
  -> Pikafish UCI 搜索
  -> 机械臂坐标转换
  -> STM32 TCP 指令
```

## 主要模块

- `web_simulation/`：Flask 后端、HTML 模板、CSS 和 JavaScript 前端。
- `vision/`：摄像头管理、网络摄像头、检测、映射、稳定和棋盘识别。
- `core/`：底层 ONNX Runtime 封装。
- `ai/`：Pikafish 进程管理和 UCI 协议命令。
- `robot/`：棋盘到机械臂坐标转换、TCP 客户端、指令协议和仿真控制。
- `model/`：视觉栈使用的 ONNX 模型。
- `firmware/stm32-tcp-server/`：嵌入式 C TCP 服务和机器人控制固件。
- `firmware/stm32-f103-keil-robot/`：STM32F103 Keil 工程和板级代码。
- `firmware/stm32-f103-angle-plan/`：角度规划参考代码。
- `tests/`：协议、后端循环、摄像头、识别器和稳定器测试。

## Web 后端说明

`web_simulation/app.py` 负责 Flask 路由和运行时编排。棋盘、回合、模式等纯逻辑逐步拆分到 `web_simulation/domain.py`，用于降低路由层与游戏状态转换之间的耦合。
