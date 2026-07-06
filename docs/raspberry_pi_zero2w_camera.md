# Raspberry Pi Zero 2 W USB Network Camera Guide

This guide is written for the CH-RO chess robot project:

- Camera type: USB UVC camera
- Pi model: Raspberry Pi Zero 2 W
- Network: same LAN Wi-Fi router, no internet needed after setup
- PC usage: enter a URL in the CH-RO web page, then start recognition

## Performance Expectation

Raspberry Pi Zero 2 W can work as a LAN camera server, but treat it as a stable
low-load camera, not a high-frame-rate webcam.

Recommended target:

- Resolution: `640x480`
- Frame rate: `8 fps`
- Stream type: MJPEG over HTTP
- Browser preview URL: `http://<PI_IP>:8080/`
- CH-RO camera URL: `http://<PI_IP>:8080`

If a direct PC USB camera is already stuttering, Pi Wi-Fi streaming can add
latency. For chess recognition this is acceptable as long as frames are clear
and stable. A good single frame matters more than 30 fps.

## Tutorial Folder Screening

Useful for this task:

- Raspberry Pi Imager setup guide: use Raspberry Pi Imager; set hostname, username,
  password, Wi-Fi country `CN`, Wi-Fi SSID/password, and enable SSH while
  writing the image.
- Win32DiskImager guide: fallback only when you already have a local
  `.img` file. It does not help configure Wi-Fi and SSH as conveniently.
- Raspberry Pi remote SSH guide: find the Pi IP from router/client list or IP scanner; use
  MobaXterm, PuTTY, Xshell, or Windows SSH.
- Raspberry Pi file transfer guide: transfer files by SFTP using IP, username,
  password, and port `22`.
- USB camera guide: verify USB camera detection with `lsusb` and
  `ls /dev/video*`; add the user to the `video` group if needed.
- Raspberry Pi static IP guide: useful only after first successful SSH login. On new
  Raspberry Pi OS, use `nmcli` / `nmtui` instead of editing old `dhcpcd.conf`.
- raspi-config guide: useful for enabling interfaces later, but Raspberry Pi
  Imager should already enable SSH during burning.
- Linux command reference: useful as general terminal reference.

Not useful for the current USB network-camera goal:

- C/Python basics, HDMI resolution, VNC desktop, CSI camera, GPIO pins, screen
  always-on, display troubleshooting, and software-source replacement.

## Offline Camera Server Pack

The project includes a Pi-side offline server pack:

```text
camera_servers/raspberry-pi-zero2w-usb-camera/
```

It contains:

- `usb_mjpeg_server.py`: HTTP MJPEG server.
- `start_usb_camera_server.sh`: manual start command.
- `install_service.sh`: optional systemd auto-start installer.
- `README_FIRST.md`: Pi-side quick instructions.

The server tries:

1. Pure Linux V4L2 MJPEG capture, no extra packages.
2. OpenCV, if already installed.
3. `fswebcam`, if already installed.

The first mode needs the USB camera to support MJPEG output. Most UVC webcams
do, but not every camera does.

## First Boot Plan

1. Burn Raspberry Pi OS Lite to the SD card with Raspberry Pi Imager.
2. In Imager customization:
   - Hostname: `raspberrypi`
   - Username: `pi`
   - Password: choose an English password, at least 7 characters
   - Enable SSH
   - Configure Wi-Fi SSID/password
   - Wi-Fi country: `CN`
   - Locale/timezone: `Asia/Shanghai`
3. Copy `camera_servers/raspberry-pi-zero2w-usb-camera` to the Pi after SSH works.
4. Plug USB camera into the Pi.
5. Start the server:

```bash
cd ~/chro-usb-camera
bash start_usb_camera_server.sh
```

6. Find the IP:

```bash
hostname -I
```

7. Test from the Windows PC:

```text
http://<PI_IP>:8080/
```

8. In CH-RO web UI network camera mode, enter:

```text
http://<PI_IP>:8080
```

## SSH With MobaXterm

Use the MobaXterm executable on the desktop:

```text
C:\Users\Henry Lau\Desktop\MobaXterm_Portable_v22.2\MobaXterm_Personal_22.2.exe
```

Connection:

- Session type: SSH
- Remote host: the Pi IP, for example `192.168.1.24`
- Port: `22`
- Username: `pi`
- Password: the password configured during burning

MobaXterm also shows an SFTP file browser after login. Drag the offline camera
folder to:

```text
/home/pi/chro-usb-camera
```

## CH-RO Web UI

1. Start the CH-RO Flask backend on the PC.
2. Open the CH-RO web page.
3. Select network camera mode.
4. Enter:

```text
http://<PI_IP>:8080
```

5. Click connect.
6. Start game / recognition.

The PC backend now prefers the Pi snapshot endpoint for HTTP cameras, then
falls back to the MJPEG stream only when needed, so preview, capture, manual
recognition, and dynamic recognition use the same stable frame source.
