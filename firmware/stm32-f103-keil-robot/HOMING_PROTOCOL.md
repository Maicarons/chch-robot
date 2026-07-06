# 启动 Homing 通信协议

本文说明 CH-RO 主机和 STM32F103 Keil 固件之间的启动归位握手。

## 网络角色

- STM32/ESP8266 侧提供 TCP 服务。
- CH-RO 主机作为 TCP Client 连接下位机。
- NetAssist 可作为人工调试工具，但不是上位机程序的转发器。

## Homing 指令

上位机开始游戏前发送：

```text
m1_angle,m2_angle,0,0,99
```

字段含义：

- 第 1 项：M1 相对转角，单位为度。
- 第 2 项：M2 相对转角，单位为度。
- 第 3、4 项：保留字段，当前固定为 `0`。
- 第 5 项：`99` 表示 homing 指令。

## 完成回执

STM32 完成 M1、M2 运动后返回：

```text
STATE:5,RESULT:1,CMD:99
```

旧固件也可能返回：

```text
STATE:5,RESULT:1
```

上位机只有收到 homing 成功回执后，才会开启棋局和视觉识别。普通走棋完成仍使用 `STATE:5,RESULT:1`，不能误判为 homing 完成。

## 普通走棋指令

普通走棋使用五值格式：

```text
startX,startY,endX,endY,signal
```

- `signal = 0`：普通移动。
- `signal = 1`：吃子流程。

## 联调步骤

1. 在 Keil 中打开 `stm32-f103-robot.uvprojx`。
2. 重新编译固件，确认无错误。
3. 将固件烧录到 STM32F103C8。
4. 确认 ESP8266 已连接到目标 Wi-Fi，并获得 IP。
5. 启动 CH-RO Web 后端。
6. 在 Web 页面选择 hardware 模式并开始游戏。

未连接下位机时，硬件模式开始游戏应被拒绝，不应启动视觉识别流程。
