# CH-RO 机器人文档

CH-RO 是一个中国象棋人机对弈机器人系统，集成 ONNX 棋盘识别、Pikafish UCI 引擎、STM32 TCP 机械臂控制和 Flask Web 管理界面。

本文档用于安装依赖、配置摄像头和下位机、运行 Web 界面，并理解项目结构。

## 核心能力

- USB 摄像头或网络摄像头采集。
- RTMPose 与分类器 ONNX 推理。
- 多帧稳定和动态走子识别。
- Pikafish 中国象棋 AI 走法生成。
- 软件仿真和真实硬件两种机器人模式。
- STM32 五值指令协议和 homing 握手。

## 推荐入口

- 本地启动：[快速开始](./guide/getting-started.md)
- 模块划分：[系统架构](./guide/architecture.md)
- 运行参数：[配置](./guide/configuration.md)
- 参与开发：[开发](./guide/development.md)
- 旧文档索引：[参考索引](./reference/index.md)
