#!/bin/bash
# Automatically install Desktop / App Menu launcher with dynamic paths

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${HOME}/.local/share/applications"
DESKTOP_DIR="${HOME}/Desktop"

mkdir -p "${TARGET_DIR}"

DESKTOP_FILE="${TARGET_DIR}/CMP-40HX-Unlocker.desktop"

cat << INNEREOF > "${DESKTOP_FILE}"
[Desktop Entry]
Name=NVIDIA CMP 40HX Unlocker
Comment=Mở khóa Compute, PCIe Gen2, ReBAR 8GB & Vulkan Throttle Bypass cho CMP 40HX
Exec="${SCRIPT_DIR}/run_gui.sh"
Path=${SCRIPT_DIR}
Icon=preferences-system-performance
Terminal=false
Type=Application
Categories=System;Settings;HardwareSettings;
StartupNotify=true
INNEREOF

chmod +x "${DESKTOP_FILE}"
echo "[✔] Đã cài đặt shortcut vào Menu ứng dụng: ${DESKTOP_FILE}"

if [[ -d "${DESKTOP_DIR}" ]]; then
    cp -f "${DESKTOP_FILE}" "${DESKTOP_DIR}/"
    chmod +x "${DESKTOP_DIR}/CMP-40HX-Unlocker.desktop"
    echo "[✔] Đã tạo biểu tượng trên Màn hình chính (Desktop): ${DESKTOP_DIR}/CMP-40HX-Unlocker.desktop"
fi
