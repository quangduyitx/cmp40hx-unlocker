#!/bin/bash
# Launcher script for NVIDIA CMP 40HX Unlocker & Optimizer GUI

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export DISPLAY="${DISPLAY:-:0}"

cd "${SCRIPT_DIR}"
exec python3 "${SCRIPT_DIR}/gui.py" "$@"
