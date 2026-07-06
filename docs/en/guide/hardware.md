# Hardware

## Camera Options

- USB camera connected directly to the host.
- Orange Pi network camera server in `camera_servers/orange-pi-camera/`.
- Raspberry Pi Zero 2 W USB MJPEG server in `camera_servers/raspberry-pi-zero2w-usb-camera/`.

For Pi setup details, see `docs/raspberry_pi_zero2w_camera.md` and `docs/raspberry_pi_zero2w_first_boot_steps.md`.

## STM32 Controller

The robot controller receives five-value commands:

```text
startX,startY,endX,endY,signal
```

`signal = 0` means a normal move. `signal = 1` means a capture sequence. Homing uses:

```text
m1_angle,m2_angle,0,0,99
```

The expected completion acknowledgement is `STATE:5,RESULT:1`.

## Firmware

- `firmware/stm32-tcp-server/` contains TCP server firmware and protocol notes.
- `firmware/stm32-f103-angle-plan/` contains motion-plan protocol work.
- `firmware/stm32-f103-keil-robot/` contains Keil project files and board-specific code.
