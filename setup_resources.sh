#!/bin/bash
# ==============================================================================
# CMP 40HX Unlocker - Resource & Dependency Setup Helper
# Downloads official NVIDIA 610.57.04 driver and open kernel modules if missing.
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DRIVER_VER="610.57.04"
RUN_FILE="${SCRIPT_DIR}/NVIDIA-Linux-x86_64-${DRIVER_VER}.run"
EXTRACTED_DIR="${SCRIPT_DIR}/NVIDIA-Linux-x86_64-${DRIVER_VER}"
CMP_DIR="${SCRIPT_DIR}/cmpunlocker"
SRC_TARBALL="${CMP_DIR}/open-gpu-kernel-modules-${DRIVER_VER}.tar.gz"

DRIVER_URL="https://us.download.nvidia.com/XFree86/Linux-x86_64/${DRIVER_VER}/NVIDIA-Linux-x86_64-${DRIVER_VER}.run"
SRC_URL="https://github.com/NVIDIA/open-gpu-kernel-modules/archive/refs/tags/${DRIVER_VER}.tar.gz"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${GREEN}[INFO]${NC} $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
step() { echo -e "${BLUE}[STEP]${NC} $*"; }

echo "======================================================================"
echo "    CMP 40HX Unlocker - Setup Resources & Offline Packages"
echo "======================================================================"

# 1. Check / Download NVIDIA official driver package
if [[ -d "${EXTRACTED_DIR}" && -x "${EXTRACTED_DIR}/nvidia-installer" ]]; then
    info "Đã có sẵn thư mục driver giải nén: ${EXTRACTED_DIR}"
elif [[ -f "${RUN_FILE}" ]]; then
    info "Đã có sẵn file bộ cài đặt: ${RUN_FILE}"
    read -rp "Bạn có muốn giải nén ra thư mục để chạy nhanh và patch dartraiden không? (y/n): " ans
    if [[ "${ans,,}" == "y" ]]; then
        step "Đang giải nén bộ cài đặt driver bằng --extract-only..."
        chmod +x "${RUN_FILE}"
        "${RUN_FILE}" --extract-only --target "${EXTRACTED_DIR}"
        info "Đã giải nén thành công vào: ${EXTRACTED_DIR}"
    fi
else
    warn "Chưa tìm thấy bộ cài đặt driver NVIDIA ${DRIVER_VER}."
    read -rp "Tải bộ cài đặt NVIDIA ${DRIVER_VER} chính thức từ NVIDIA (~442MB)? (y/n): " ans
    if [[ "${ans,,}" == "y" ]]; then
        step "Đang tải ${DRIVER_URL}..."
        curl -fSL "${DRIVER_URL}" -o "${RUN_FILE}" || wget -c "${DRIVER_URL}" -O "${RUN_FILE}"
        chmod +x "${RUN_FILE}"
        step "Tự động giải nén bộ cài đặt ra thư mục..."
        "${RUN_FILE}" --extract-only --target "${EXTRACTED_DIR}"
        info "Đã chuẩn bị xong bộ cài đặt driver tại: ${EXTRACTED_DIR}"
    fi
fi

# 2. Check & Apply Dartraiden Patch to unpacked driver folder
DART_ZIP="${SCRIPT_DIR}/NVIDIA-Linux-x86_64-${DRIVER_VER}.zip"
DART_URL="https://github.com/dartraiden/NVIDIA-patcher/releases/download/${DRIVER_VER}/NVIDIA-Linux-x86_64-${DRIVER_VER}.zip"

if [[ -d "${EXTRACTED_DIR}" ]]; then
    if [[ ! -f "${DART_ZIP}" ]]; then
        step "Đang tải bản vá dartraiden mod cho CMP 40HX..."
        curl -fSL "${DART_URL}" -o "${DART_ZIP}" || wget -c "${DART_URL}" -O "${DART_ZIP}"
    fi
    info "Đang nạp file kernel mod dartraiden (nv-kernel.o_binary) vào ${EXTRACTED_DIR}..."
    unzip -o "${DART_ZIP}" -d "${EXTRACTED_DIR}"
    info "Đã tích hợp hoàn tất bản mod dartraiden cho driver!"
fi

# 3. Check / Clone Cyridd/cmpunlocker repository
if [[ ! -d "${CMP_DIR}/.git" ]]; then
    step "Đang tải mã nguồn bản mod từ https://github.com/Cyridd/cmpunlocker..."
    git clone https://github.com/Cyridd/cmpunlocker "${CMP_DIR}"
    info "Đã clone thành công thư mục cmpunlocker!"
else
    info "Thư mục mã nguồn cmpunlocker đã sẵn sàng."
fi

# 4. Check / Download Open GPU Kernel Modules source
mkdir -p "${CMP_DIR}"
if [[ -f "${SRC_TARBALL}" ]]; then
    info "Đã có sẵn file mã nguồn kernel open modules: ${SRC_TARBALL}"
else
    step "Đang tải mã nguồn mở open-gpu-kernel-modules-${DRIVER_VER}.tar.gz..."
    curl -fSL "${SRC_URL}" -o "${SRC_TARBALL}" || wget -c "${SRC_URL}" -O "${SRC_TARBALL}"
    info "Đã tải thành công mã nguồn open module!"
fi

info "Toàn bộ tài nguyên đã sẵn sàng để sử dụng offline!"
