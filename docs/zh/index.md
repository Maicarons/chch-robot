---
layout: home
hero:
  name: CH-RO Robot
  text: 中国象棋人机对弈机器人文档
  tagline: 视觉棋盘识别、Pikafish 决策引擎、STM32 运动控制与 Flask 操作台。
  image:
    src: /hero.svg
    alt: CH-RO Robot Team
  actions:
    - theme: brand
      text: 中文指南
      link: /zh/guide/getting-started
    - theme: alt
      text: English
      link: /en/
features:
  - title: 视觉棋盘识别
    details: RTMPose 四角关键点 + 透视校正；单一全局分类器一次性输出整盘 90 个交叉点；多帧稳定与基于规则的动态走子推断。
  - title: Pikafish 决策引擎
    details: UCI_Variant=xaingqi 走法生成，扩展 FEN 表示棋局，可驱动硬件与仿真两种对弈模式。
  - title: STM32 运动控制
    details: 五值 ASCII 指令协议（TCP 8086），下位机完成运动学解算，并以 STATE/RESULT 握手与 homing 协同。
  - title: Flask 操作台
    details: 实时视频流、单步/连续识别，以及硬件/仿真双模式的人机对弈 Web 界面。
---
