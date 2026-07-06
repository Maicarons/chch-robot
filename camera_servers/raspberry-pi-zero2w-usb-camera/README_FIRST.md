# CH-RO Raspberry Pi Zero 2 W USB Camera Offline Pack

This folder is for the Raspberry Pi, not for the Windows PC.

Goal:

- USB camera plugs into Raspberry Pi Zero 2 W.
- Raspberry Pi starts an HTTP MJPEG camera server.
- The Windows CH-RO web page connects to:

```text
http://<PI_IP>:8080
```

## Why This Pack Exists

Your router only provides the local network and the Pi cannot download packages
from the internet. The bundled server therefore tries this order:

1. Pure Linux V4L2 MJPEG capture, using only Python standard library.
2. OpenCV capture, if `python3-opencv` is already installed.
3. `fswebcam` snapshot fallback, if `fswebcam` is already installed.

The first mode works only when the USB camera supports MJPEG output. Most UVC
webcams do, but not all of them.

## First SSH Test

After the Pi has booted and you have logged in through SSH:

```bash
lsusb
ls /dev/video*
groups
```

If your user is not in the `video` group:

```bash
sudo usermod -a -G video $USER
sudo reboot
```

## Run Manually

Copy this whole folder to the Pi, for example:

```text
/home/pi/chro-usb-camera
```

Then run:

```bash
cd ~/chro-usb-camera
bash start_usb_camera_server.sh
```

Expected output contains a URL like:

```text
Preview URL: http://0.0.0.0:8080/
```

Find the Pi LAN address:

```bash
hostname -I
```

Then open this on the Windows PC:

```text
http://<PI_IP>:8080/
```

Example:

```text
http://192.168.1.24:8080/
```

In the CH-RO web page network camera input, prefer:

```text
http://<PI_IP>:8080
```

The backend will try `/snapshot.jpg`, then `/frame.jpg`, and finally fall back
to parsing the MJPEG stream if needed.

## Install As Auto-Start Service

After manual run works:

```bash
cd ~/chro-usb-camera
bash install_service.sh
```

Check status:

```bash
systemctl status chro-usb-camera --no-pager
```

View logs:

```bash
journalctl -u chro-usb-camera -f
```

## Useful Low-Load Settings

Pi Zero 2 W is small. Start conservative:

```bash
python3 usb_mjpeg_server.py --device /dev/video0 --width 640 --height 480 --fps 8 --jpeg-quality 80
```

If the picture is unstable, try lower settings:

```bash
python3 usb_mjpeg_server.py --device /dev/video0 --width 480 --height 360 --fps 8 --jpeg-quality 65
```

For chess recognition, a stable clear frame is more important than high FPS.

## If The V4L2 Backend Fails

The camera may not support MJPEG mode. If the Pi can temporarily access the
internet later, install one fallback:

```bash
sudo apt update
sudo apt install -y fswebcam
```

or:

```bash
sudo apt update
sudo apt install -y python3-opencv
```

Then rerun:

```bash
bash start_usb_camera_server.sh
```
