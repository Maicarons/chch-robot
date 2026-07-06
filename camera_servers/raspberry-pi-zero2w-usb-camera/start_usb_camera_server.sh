#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

python3 usb_mjpeg_server.py \
  --host 0.0.0.0 \
  --port 8080 \
  --device /dev/video0 \
  --width 640 \
  --height 480 \
  --fps 8 \
  --jpeg-quality 80 \
  --backend auto
