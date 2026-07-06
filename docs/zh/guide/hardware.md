# 硬件

## 摄像头方案

- 直接连接主机的 USB 摄像头。
- `camera_servers/orange-pi-camera/` 中的 Orange Pi 网络摄像头服务。
- `camera_servers/raspberry-pi-zero2w-usb-camera/` 中的 Raspberry Pi Zero 2 W USB MJPEG 服务。

树莓派部署细节见 `docs/raspberry_pi_zero2w_camera.md` 和 `docs/raspberry_pi_zero2w_first_boot_steps.md`。

## STM32 控制器

机器人控制器接收五值指令：

```text
startX,startY,endX,endY,signal
```

`signal = 0` 表示普通移动，`signal = 1` 表示吃子流程。归位指令为：

```text
m1_angle,m2_angle,0,0,99
```

期望完成确认是 `STATE:5,RESULT:1`。

## 固件目录

- `firmware/stm32-tcp-server/`：TCP 服务固件和协议说明。
- `firmware/stm32-f103-angle-plan/`：角度规划协议相关代码。
- `firmware/stm32-f103-keil-robot/`：Keil 工程文件和板级代码。
