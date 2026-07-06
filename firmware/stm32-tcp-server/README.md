# STM32 TCP 机器人控制固件

该目录包含 STM32 侧 TCP 服务和机器人控制参考代码，用于接收 CH-RO 主机发送的走棋指令，并驱动机械结构执行动作。

## 文件结构

```text
firmware/stm32-tcp-server/
├── main.c
├── robot_tcp_server.c
├── robot_tcp_server.h
├── robot_control.c
├── robot_control.h
├── json_parser.c
├── json_parser.h
├── lwipopts.h.example
├── Makefile
└── PROTOCOL.md
```

## 网络方案

可选方案包括：

- STM32 内置 ETH + LwIP。
- W5500 硬件 TCP/IP 芯片。
- ENC28J60 以太网模块。

实际项目中应根据板卡资源、网络稳定性和调试便利性选择方案。

## 构建

该目录提供 `Makefile` 作为 ARM GCC 构建示例。构建前需要安装交叉编译工具链和对应芯片支持文件。

```bash
cd firmware/stm32-tcp-server
make
```

## 协议

协议细节见 [PROTOCOL.md](./PROTOCOL.md)。上位机侧主要通过 `robot/protocol.py` 生成命令。

## 安全提示

机械臂调试必须先确认限位、急停、电源和运动范围。首次联调请使用低速、空载和 simulation 流程逐步验证。
