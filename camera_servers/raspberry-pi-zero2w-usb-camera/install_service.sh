#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

install_dir="$(pwd)"
run_user="$(id -un)"
service_file="/tmp/chro-usb-camera.service"

sed \
  -e "s|__INSTALL_DIR__|${install_dir}|g" \
  -e "s|__USER__|${run_user}|g" \
  chro-usb-camera.service > "${service_file}"

sudo cp "${service_file}" /etc/systemd/system/chro-usb-camera.service
sudo systemctl daemon-reload
sudo systemctl enable chro-usb-camera
sudo systemctl restart chro-usb-camera

echo "Installed and started chro-usb-camera."
echo "Check with: systemctl status chro-usb-camera --no-pager"

