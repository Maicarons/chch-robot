# Raspberry Pi Zero 2 W 首次启动与 USB 网络摄像头步骤

本文用于把 Raspberry Pi Zero 2 W 配置为 CH-RO 的局域网 USB 摄像头服务器。场景假设如下：

- 使用 USB UVC 摄像头。
- 树莓派和运行 CH-RO 的电脑在同一局域网。
- 树莓派首次启动后通过 SSH 管理。
- CH-RO Web 页面使用网络摄像头 URL 读取画面。

## 需要准备

- Raspberry Pi Zero 2 W。
- microSD 卡，建议 16GB 或以上。
- USB 摄像头和合适的 OTG 转接线。
- Raspberry Pi Imager。
- MobaXterm、PuTTY、Windows OpenSSH 或其他 SSH 工具。
- 本仓库目录：`camera_servers/raspberry-pi-zero2w-usb-camera/`。

## 1. 写入系统镜像

推荐使用 Raspberry Pi Imager，而不是只用 Win32DiskImager。Imager 可以在写入镜像时直接配置 Wi-Fi、SSH、用户名和密码。

1. 打开 Raspberry Pi Imager。
2. 设备选择 Raspberry Pi Zero 2 W。
3. 系统建议选择 Raspberry Pi OS Lite，或选择本地镜像。
4. 存储设备选择 microSD 卡，写入前再次确认盘符，写入会清空卡内数据。
5. 进入系统自定义设置：
   - 设置主机名，例如 `chro-camera`。
   - 设置用户名和密码。
   - 启用 SSH。
   - 填写局域网 Wi-Fi SSID 和密码。
   - Wi-Fi 国家/地区选择 `CN`。
6. 写入完成后安全弹出 microSD 卡。

## 2. 首次启动

1. 将 microSD 卡插入树莓派。
2. 连接 USB 摄像头。
3. 给树莓派上电。
4. 等待 1 到 2 分钟，让系统完成首次启动。

## 3. 查找 IP 并 SSH 登录

优先在路由器管理页面查看已连接设备。设备名通常是你在 Imager 中设置的主机名。

也可以在 Windows 终端尝试：

```powershell
ping chro-camera.local
```

SSH 登录示例：

```bash
ssh pi@<PI_IP>
```

如果首次连接提示是否信任主机，输入 `yes`。

## 4. 确认 USB 摄像头

登录树莓派后执行：

```bash
lsusb
ls /dev/video*
groups
```

如果能看到 `/dev/video0`，说明系统识别到了摄像头。如果当前用户不在 `video` 组中，执行：

```bash
sudo usermod -aG video $USER
sudo reboot
```

重启后重新 SSH 登录。

## 5. 复制摄像头服务

用 MobaXterm 的 SFTP 面板或 `scp` 将目录复制到树莓派：

```bash
scp -r camera_servers/raspberry-pi-zero2w-usb-camera pi@<PI_IP>:~/chro-camera
```

也可以先压缩后复制，再在树莓派上解压。

## 6. 启动摄像头服务

在树莓派 SSH 中执行：

```bash
cd ~/chro-camera
bash start_usb_camera_server.sh
```

看到服务启动后，查询树莓派 IP：

```bash
hostname -I
```

假设 IP 是 `192.168.1.24`，在电脑浏览器打开：

```text
http://192.168.1.24:8080/
```

能看到预览画面就说明服务可用。

## 7. 在 CH-RO 中使用

1. 在电脑上运行 CH-RO 后端：

```bash
python web_simulation/app.py
```

2. 打开 `http://localhost:5000`。
3. 选择网络摄像头模式。
4. 输入：

```text
http://<PI_IP>:8080
```

5. 点击连接，然后开始识别或开始对局。

## 8. 设置开机自启

手动启动确认正常后，可以安装 systemd 服务：

```bash
cd ~/chro-camera
bash install_service.sh
sudo systemctl status chro-usb-camera.service
```

查看日志：

```bash
journalctl -u chro-usb-camera.service -f
```

## 常见问题

如果打不开 URL：

- 确认电脑和树莓派在同一局域网。
- 确认服务正在运行。
- 确认 IP 地址没有变化。
- 确认浏览器访问的是 `http://<PI_IP>:8080/`。

如果日志提示摄像头不支持 MJPEG，说明纯离线 V4L2 模式不适配当前摄像头。可以临时让树莓派联网后安装 OpenCV 或 `fswebcam`，再重新运行服务。
