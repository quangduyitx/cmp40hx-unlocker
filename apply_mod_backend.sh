#!/bin/bash
# =============================================================================
# CMP 40HX Unlocker - Backend Execution Script
# Handles privileged operations: Kernel Module install, glcore patch,
# GSP configuration, ReBAR sizing, offline driver install, package installation,
# clean rollback, and GitHub updates.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CMP_DIR="${SCRIPT_DIR}/cmpunlocker"
DRIVER_VERSION="610.57.04"

RED='\033[0;31m'
GRN='\033[0;32m'
YEL='\033[1;33m'
BLU='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${GRN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YEL}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERR]${NC}   $*" >&2; }
step()  { echo -e "${BLU}[STEP]${NC}  $*"; }

die() {
    error "$*"
    exit 1
}

require_root() {
    if [[ "$(id -u)" -ne 0 ]]; then
        die "Thao tác này yêu cầu quyền root. Hãy chạy với sudo hoặc pkexec."
    fi
}

install_packages() {
    require_root
    step "Đang cài đặt các công cụ và thư viện hệ thống cần thiết..."
    export DEBIAN_FRONTEND=noninteractive
    apt-get update -qq || true
    apt-get install -y build-essential "linux-headers-$(uname -r)" pciutils patch curl wget mokutil pigz vulkan-tools clinfo kmod initramfs-tools
    info "Đã cài đặt thành công toàn bộ các thư viện và công cụ hệ thống!"
}

ensure_dartraiden_modded_driver() {
    local driver_dir="${SCRIPT_DIR}/NVIDIA-Linux-x86_64-${DRIVER_VERSION}"
    local installer_bin="${driver_dir}/nvidia-installer"
    local nv_kernel_obj="${driver_dir}/kernel/nvidia/nv-kernel.o_binary"
    local run_file="${SCRIPT_DIR}/NVIDIA-Linux-x86_64-${DRIVER_VERSION}.run"
    local tar_file="${SCRIPT_DIR}/NVIDIA-Linux-x86_64-${DRIVER_VERSION}.tar.gz"
    local dart_zip="${SCRIPT_DIR}/NVIDIA-Linux-x86_64-${DRIVER_VERSION}.zip"

    local expected_mod_sha="c4f765e92507f350cd7aa7f45fe4c8c6496a9d244d192849e3d9fa31e69a2a57"
    local expected_zip_sha="6126674523dbac854c93d31a74a45950e5c2322586c362cd4d9b3b8aade9f781"

    step "Kiểm tra tính sẵn sàng của bộ cài Driver mod Dartraiden..."

    # 1. Kiểm tra nếu thư mục giải nén đã có và đã khớp SHA256 của bản mod Dartraiden
    if [[ -x "${installer_bin}" && -f "${nv_kernel_obj}" ]]; then
        local current_sha
        current_sha="$(sha256sum "${nv_kernel_obj}" 2>/dev/null | awk '{print $1}')"
        if [[ "${current_sha}" == "${expected_mod_sha}" ]]; then
            info "Thư mục giải nén đã sẵn sàng và khớp 100% chuẩn mod Dartraiden (SHA256: ${current_sha:0:16}...)."
            return 0
        else
            warn "Thư mục driver đã tồn tại nhưng nv-kernel.o_binary chưa được nạp mod Dartraiden (SHA256: ${current_sha:0:16}...). Đang áp dụng bản mod..."
        fi
    fi

    # 2. Nếu thư mục chưa có, kiểm tra nếu có file tar.gz (đã mod sẵn) để bung nén nhanh
    if [[ ! -x "${installer_bin}" && -f "${tar_file}" ]]; then
        info "Phát hiện gói nén lưu trữ offline ${tar_file}. Đang tiến hành bung nén..."
        tar -xzf "${tar_file}" -C "${SCRIPT_DIR}"
        if [[ -x "${installer_bin}" && -f "${nv_kernel_obj}" ]]; then
            local tar_sha
            tar_sha="$(sha256sum "${nv_kernel_obj}" 2>/dev/null | awk '{print $1}')"
            if [[ "${tar_sha}" == "${expected_mod_sha}" ]]; then
                info "Giải nén thành công gói tar.gz! nv-kernel.o_binary chuẩn mod Dartraiden (SHA256: ${tar_sha:0:16}...)."
                return 0
            fi
        fi
    fi

    # 3. Nếu chưa có thư mục giải nén: kiểm tra file .run, nếu chưa có thì tải từ NVIDIA
    if [[ ! -x "${installer_bin}" ]]; then
        if [[ ! -f "${run_file}" ]]; then
            step "Chưa tìm thấy bộ cài đặt gốc. Đang tự động tải driver NVIDIA ${DRIVER_VERSION} từ NVIDIA..."
            info "URL: https://us.download.nvidia.com/XFree86/Linux-x86_64/${DRIVER_VERSION}/NVIDIA-Linux-x86_64-${DRIVER_VERSION}.run"
            local official_url="https://us.download.nvidia.com/XFree86/Linux-x86_64/${DRIVER_VERSION}/NVIDIA-Linux-x86_64-${DRIVER_VERSION}.run"
            if command -v curl >/dev/null 2>&1; then
                curl -fSL "${official_url}" -o "${run_file}"
            else
                wget -c "${official_url}" -O "${run_file}"
            fi
            chmod +x "${run_file}"
            info "Tải thành công bộ cài NVIDIA: ${run_file}"
        fi

        step "Đang giải nén bộ cài đặt driver bằng lệnh --extract-only..."
        chmod +x "${run_file}"
        "${run_file}" --extract-only --target "${driver_dir}"
        info "Đã giải nén driver ra thư mục: ${driver_dir}"
    fi

    # 4. Tải bản mod Dartraiden từ GitHub nếu chưa có và áp dụng (ghi đè nv-kernel.o_binary)
    if [[ ! -f "${dart_zip}" ]]; then
        step "Đang tải bản mod Dartraiden từ GitHub..."
        info "URL: https://github.com/dartraiden/NVIDIA-patcher/releases/download/${DRIVER_VERSION}/NVIDIA-Linux-x86_64-${DRIVER_VERSION}.zip"
        local dart_url="https://github.com/dartraiden/NVIDIA-patcher/releases/download/${DRIVER_VERSION}/NVIDIA-Linux-x86_64-${DRIVER_VERSION}.zip"
        if command -v curl >/dev/null 2>&1; then
            curl -fSL "${dart_url}" -o "${dart_zip}"
        else
            wget -c "${dart_url}" -O "${dart_zip}"
        fi
        info "Tải thành công gói mod Dartraiden: ${dart_zip}"
    fi

    info "Đang giải nén và ghi đè kernel/nvidia/nv-kernel.o_binary từ bản mod Dartraiden..."
    unzip -o "${dart_zip}" -d "${driver_dir}"

    local final_sha
    final_sha="$(sha256sum "${nv_kernel_obj}" 2>/dev/null | awk '{print $1}')"
    if [[ "${final_sha}" == "${expected_mod_sha}" ]]; then
        info "Xác nhận thành công: Thư mục driver đã được tích hợp bản mod Dartraiden chuẩn 100%!"
    else
        warn "Lưu ý: SHA256 nv-kernel.o_binary hiện tại là ${final_sha}, kỳ vọng: ${expected_mod_sha}."
    fi

    # Phân quyền lại thư mục về cho người dùng bình thường
    local real_user="${SUDO_USER:-}"
    if [[ -z "${real_user}" ]]; then
        real_user="$(logname 2>/dev/null || stat -c '%U' "${SCRIPT_DIR}")"
    fi
    if [[ -n "${real_user}" && "${real_user}" != "root" && -d "${driver_dir}" ]]; then
        chown -R "${real_user}:${real_user}" "${driver_dir}" 2>/dev/null || true
    fi
}

install_offline_driver() {
    require_root
    local driver_dir="${SCRIPT_DIR}/NVIDIA-Linux-x86_64-${DRIVER_VERSION}"
    local installer_bin="${driver_dir}/nvidia-installer"

    local no_opengl=0
    local use_dkms=1

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --no-opengl) no_opengl=1 ;;
            --no-dkms) use_dkms=0 ;;
            *) ;;
        esac
        shift
    done

    # Đảm bảo thư mục giải nén chuẩn mod Dartraiden đã sẵn sàng
    ensure_dartraiden_modded_driver

    [[ -x "${installer_bin}" ]] || die "Không tìm thấy nvidia-installer tại: ${installer_bin} sau khi chuẩn bị!"

    step "Bắt đầu cài đặt Driver NVIDIA ${DRIVER_VERSION} đã tích hợp mod Dartraiden..."
    local args=(
        "--silent"
        "--no-questions"
        "--ui=none"
        "--no-x-check"
        "--no-nouveau-check"
        "--no-check-for-alternate-installs"
        "--allow-installation-with-running-driver"
    )
    if [[ "${no_opengl}" -eq 1 ]]; then
        args+=("--no-opengl-files")
        info "Tùy chọn: Không ghi đè OpenGL (an toàn cho máy chạy song song card AMD)."
    fi
    if [[ "${use_dkms}" -eq 1 ]]; then
        args+=("--dkms")
        info "Tùy chọn: Kích hoạt DKMS để tự động cập nhật khi đổi kernel."
    fi

    chmod +x "${installer_bin}"
    cd "${driver_dir}"
    info "Đang chạy bộ cài đặt: ./nvidia-installer ${args[*]}"
    if ! ./nvidia-installer "${args[@]}"; then
        if [[ -f /var/log/nvidia-installer.log ]]; then
            warn "Trích xuất 25 dòng cuối log cài đặt /var/log/nvidia-installer.log:"
            tail -n 25 /var/log/nvidia-installer.log
        fi
        die "Cài đặt Driver NVIDIA bằng nvidia-installer thất bại!"
    fi

    # Trả quyền thư mục giải nén về cho người dùng bình thường nếu có
    local real_user="${SUDO_USER:-}"
    if [[ -z "${real_user}" ]]; then
        real_user="$(logname 2>/dev/null || stat -c '%U' "${SCRIPT_DIR}")"
    fi
    if [[ -n "${real_user}" && "${real_user}" != "root" && -d "${driver_dir}" ]]; then
        chown -R "${real_user}:${real_user}" "${driver_dir}" 2>/dev/null || true
    fi

    info "Cài đặt thành công Driver NVIDIA ${DRIVER_VERSION}!"
}

find_glcore_lib() {
    local candidate
    for candidate in \
        "/usr/lib/x86_64-linux-gnu/libnvidia-glcore.so.${DRIVER_VERSION}" \
        "/usr/lib64/libnvidia-glcore.so.${DRIVER_VERSION}" \
        "/usr/lib/libnvidia-glcore.so.${DRIVER_VERSION}"; do
        if [[ -f "${candidate}" ]]; then
            echo "${candidate}"
            return 0
        fi
    done
    return 1
}

configure_gsp() {
    local enable="$1"
    info "Cấu hình GSP Firmware: enable=${enable}"
    
    local conf_file="/etc/modprobe.d/nvidia.conf"
    if [[ "${enable}" -eq 1 ]]; then
        if [[ -f "${conf_file}" ]]; then
            cp -f "${conf_file}" "${conf_file}.bak.$(date +%s)"
            sed -i 's/.*NVreg_EnableGpuFirmware=0.*/# options nvidia NVreg_EnableGpuFirmware=0/g' "${conf_file}"
            info "Đã tắt tham số vô hiệu hóa GSP trong ${conf_file}."
        fi
        if grep -qs "NVreg_EnableGpuFirmware=0" "${conf_file}" 2>/dev/null; then
            sed -i '/NVreg_EnableGpuFirmware=0/d' "${conf_file}"
        fi
        info "GSP Firmware đã được kích hoạt sẵn sàng cho Open Kernel Module."
    else
        mkdir -p /etc/modprobe.d
        cat <<'INNEREOF' > "${conf_file}"
options nvidia NVreg_EnableGpuFirmware=0
INNEREOF
        info "Đã đặt options nvidia NVreg_EnableGpuFirmware=0 trong ${conf_file}."
    fi
}

configure_rebar_size() {
    local selector="$1"
    local rebar_conf="/etc/modprobe.d/nvidia-cmp-rebar.conf"
    if [[ "${selector}" -eq 7 ]]; then
        rm -f "${rebar_conf}"
        info "ReBAR size: 8 GiB (mặc định của bản mod)."
    else
        info "Thiết lập kích thước ReBAR: selector=${selector} (0=off, 1=128M..6=4G, 7=8G)"
        echo "options nvidia cmp40_rebar_size=${selector}" > "${rebar_conf}"
        info "Đã ghi cấu hình ReBAR vào ${rebar_conf}."
    fi
}

install_kernel_mod() {
    require_root
    local diag_flag=""
    local enable_gsp=1
    local rebar_size=7

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --pcie-diagnostic) diag_flag="--pcie-diagnostic" ;;
            --keep-gsp-off) enable_gsp=0 ;;
            --rebar-size=*) rebar_size="${1#--rebar-size=}" ;;
            *) ;;
        esac
        shift
    done

    step "Bắt đầu cài đặt CMP 40HX Open Kernel Module (Offline Mode)..."
    
    if [[ "${enable_gsp}" -eq 1 ]]; then
        configure_gsp 1
    fi

    configure_rebar_size "${rebar_size}"

    cd "${CMP_DIR}"
    chmod +x install.sh

    local tarball="${CMP_DIR}/open-gpu-kernel-modules-${DRIVER_VERSION}.tar.gz"
    local src_dir="${CMP_DIR}/open-gpu-kernel-modules-${DRIVER_VERSION}"

    if [[ ! -f "${tarball}" ]]; then
        info "Chưa có file nén mã nguồn mở kernel ${tarball}. Đang tự động tải từ NVIDIA GitHub..."
        local src_url="https://github.com/NVIDIA/open-gpu-kernel-modules/archive/refs/tags/${DRIVER_VERSION}.tar.gz"
        curl -fSL "${src_url}" -o "${tarball}" || wget -c "${src_url}" -O "${tarball}"
    fi

    # Luôn làm sạch thư mục nguồn đã giải nén cũ nếu có file tarball nguyên bản,
    # tránh lỗi "cannot be applied / already partially modified" do dấu vết biên dịch cũ.
    if [[ -d "${src_dir}" && -f "${tarball}" ]]; then
        info "Làm sạch thư mục mã nguồn tạm cũ (${src_dir}) để giải nén nguyên bản và áp dụng mod đồng bộ..."
        rm -rf "${src_dir}"
    fi

    info "Thực thi install.sh với gói lưu trữ offline..."
    if [[ -n "${diag_flag}" ]]; then
        ./install.sh --no-download --pcie-diagnostic
    else
        ./install.sh --no-download
    fi

    # Trả quyền sở hữu thư mục về cho người dùng bình thường để tránh bị khóa bởi root
    local real_user="${SUDO_USER:-}"
    if [[ -z "${real_user}" ]]; then
        real_user="$(logname 2>/dev/null || stat -c '%U' "${SCRIPT_DIR}")"
    fi
    if [[ -n "${real_user}" && "${real_user}" != "root" ]]; then
        chown -R "${real_user}:${real_user}" "${CMP_DIR}" 2>/dev/null || true
    fi

    info "Hoàn tất cài đặt Kernel Module!"
}

patch_glcore_system() {
    require_root
    step "Bắt đầu vá thư viện userspace libnvidia-glcore.so hệ thống..."

    local target_lib
    target_lib="$(find_glcore_lib)" || die "Không tìm thấy libnvidia-glcore.so.${DRIVER_VERSION} trên hệ thống!"
    info "Thư viện đích: ${target_lib}"

    local patcher_dir="${CMP_DIR}/cmp_glcore_patch"
    local patcher_bin="${patcher_dir}/patch_glcore"

    if [[ ! -x "${patcher_bin}" ]]; then
        info "Đang biên dịch patch_glcore..."
        g++ -std=c++17 -O2 -Wall -Wextra "${patcher_dir}/patch_glcore.cpp" -o "${patcher_bin}" \
            || die "Biên dịch patch_glcore thất bại!"
    fi

    local backup_file="${target_lib}.orig"
    if [[ ! -f "${backup_file}" ]]; then
        info "Tạo bản sao lưu thư viện gốc: ${backup_file}"
        cp -p "${target_lib}" "${backup_file}"
    else
        info "Bản sao lưu đã tồn tại: ${backup_file}"
    fi

    local temp_patched="/tmp/libnvidia-glcore.so.${DRIVER_VERSION}.patched.$$"
    info "Đang thực hiện vá nhị phân (argument 0xf0 -> 0x0)..."
    "${patcher_bin}" "${backup_file}" "${temp_patched}" 0 \
        || die "Lỗi khi thực hiện patch_glcore!"

    install -m 0755 "${temp_patched}" "${target_lib}"
    rm -f "${temp_patched}"

    info "Đã áp dụng bản vá glcore cho toàn hệ thống thành công!"
    info "Thư viện gốc đã được lưu an toàn tại: ${backup_file}"
}

restore_glcore_system() {
    require_root
    step "Khôi phục thư viện libnvidia-glcore.so gốc..."

    local target_lib
    target_lib="$(find_glcore_lib)" || die "Không tìm thấy libnvidia-glcore.so.${DRIVER_VERSION} trên hệ thống!"

    local backup_file="${target_lib}.orig"
    if [[ -f "${backup_file}" ]]; then
        cp -p "${backup_file}" "${target_lib}"
        info "Đã khôi phục thành công thư viện gốc từ: ${backup_file}"
    else
        warn "Không tìm thấy bản sao lưu ${backup_file}. Thư viện hệ thống có thể vẫn là bản gốc."
    fi
}

patch_glcore_local() {
    step "Tạo thư viện glcore vá cục bộ (không chạm file hệ thống)..."

    local target_lib
    target_lib="$(find_glcore_lib)" || die "Không tìm thấy libnvidia-glcore.so.${DRIVER_VERSION} trên hệ thống!"

    local local_dir="${SCRIPT_DIR}/local_glcore"
    mkdir -p "${local_dir}"

    local patcher_dir="${CMP_DIR}/cmp_glcore_patch"
    local patcher_bin="${patcher_dir}/patch_glcore"

    if [[ ! -x "${patcher_bin}" ]]; then
        info "Đang biên dịch patch_glcore..."
        g++ -std=c++17 -O2 -Wall -Wextra "${patcher_dir}/patch_glcore.cpp" -o "${patcher_bin}" \
            || die "Biên dịch patch_glcore thất bại!"
    fi

    local out_lib="${local_dir}/libnvidia-glcore.so.${DRIVER_VERSION}"
    "${patcher_bin}" "${target_lib}" "${out_lib}" 0 \
        || die "Lỗi khi vá thư viện cục bộ!"

    chmod 0755 "${out_lib}"
    
    cat <<'LAUNCHER_EOF' > "${local_dir}/launch_with_glcore_mod.sh"
#!/bin/bash
export LD_LIBRARY_PATH="${local_dir}:${LD_LIBRARY_PATH:-}"
echo "[CMP-40HX] Đang chạy với glcore mod MME throttle bypass..."
exec "$@"
LAUNCHER_EOF
    chmod +x "${local_dir}/launch_with_glcore_mod.sh"

    info "Thư viện cục bộ đã tạo tại: ${out_lib}"
    info "Script chạy: ${local_dir}/launch_with_glcore_mod.sh <lệnh_game>"
    info "Steam Launch Option: LD_LIBRARY_PATH=${local_dir}:\$LD_LIBRARY_PATH %command%"
}

uninstall_kernel_mod() {
    require_root
    step "Bắt đầu gỡ bỏ Kernel Module CMP 40HX..."

    local kver="$(uname -r)"
    local update_dir="/lib/modules/${kver}/updates/cmpunlocker"

    if [[ -d "${update_dir}" ]]; then
        info "Xóa thư mục: ${update_dir}"
        rm -rf "${update_dir}"
    else
        info "Thư mục ${update_dir} không tồn tại hoặc đã được gỡ bỏ."
    fi

    rm -f /etc/modprobe.d/nvidia-cmp-rebar.conf

    info "Chạy depmod -a..."
    depmod -a "${kver}"

    if command -v update-initramfs >/dev/null 2>&1; then
        info "Cập nhật initramfs..."
        update-initramfs -u -k "${kver}"
    fi

    info "Đã gỡ bỏ Kernel Module mod. Hệ thống sẽ quay về driver NVIDIA mặc định sau khi khởi động lại."
}

update_from_github() {
    step "Kiểm tra và cập nhật mã nguồn từ https://github.com/Cyridd/cmpunlocker..."
    cd "${CMP_DIR}"
    
    if [[ -f cmp_glcore_patch/patch_glcore ]]; then
        git checkout -- cmp_glcore_patch/patch_glcore 2>/dev/null || true
    fi

    info "Đang kết nối tới GitHub..."
    if ! git fetch origin main; then
        die "Không thể kết nối tới GitHub. Vui lòng kiểm tra kết nối mạng!"
    fi

    local local_hash="$(git rev-parse --short HEAD)"
    local remote_hash="$(git rev-parse --short origin/main)"
    
    info "Commit hiện tại trên máy: ${local_hash}"
    info "Commit mới nhất trên GitHub: ${remote_hash}"

    if [[ "${local_hash}" == "${remote_hash}" ]]; then
        info "Mã nguồn mod đang ở phiên bản mới nhất (${local_hash})!"
    else
        info "Phát hiện bản cập nhật mới! Đang đồng bộ..."
        git pull --ff-only origin main || git pull origin main
        info "Đã cập nhật thành công lên commit mới: $(git rev-parse --short HEAD)"
        info "Nhật ký commit mới nhất:"
        git log -n 5 --oneline
        
        info "Đang cập nhật file nén lưu trữ offline cmpunlocker_mods_offline.tar.gz..."
        if command -v pigz >/dev/null 2>&1; then
            tar --use-compress-program=pigz -cf "${SCRIPT_DIR}/cmpunlocker_mods_offline.tar.gz" -C "${SCRIPT_DIR}" cmpunlocker 2>/dev/null || true
        else
            tar -czf "${SCRIPT_DIR}/cmpunlocker_mods_offline.tar.gz" -C "${SCRIPT_DIR}" cmpunlocker 2>/dev/null || true
        fi
    fi

    if [[ -f cmp_glcore_patch/patch_glcore.cpp ]]; then
        info "Đang biên dịch lại patch_glcore..."
        g++ -std=c++17 -O2 -Wall -Wextra cmp_glcore_patch/patch_glcore.cpp -o cmp_glcore_patch/patch_glcore 2>/dev/null || true
    fi

    info "Hoàn tất kiểm tra và cập nhật từ GitHub!"
}

# ---------- CLI Entrypoint ----------
ACTION="${1:-help}"
shift || true

case "${ACTION}" in
    install-packages)
        install_packages
        ;;
    install-offline-driver)
        install_offline_driver "$@"
        ;;
    prepare-driver)
        ensure_dartraiden_modded_driver
        ;;
    install-kernel-mod)
        install_kernel_mod "$@"
        ;;
    patch-glcore-system)
        patch_glcore_system
        ;;
    restore-glcore-system)
        restore_glcore_system
        ;;
    patch-glcore-local)
        patch_glcore_local
        ;;
    uninstall-kernel-mod)
        uninstall_kernel_mod
        ;;
    enable-gsp)
        require_root
        configure_gsp 1
        ;;
    disable-gsp)
        require_root
        configure_gsp 0
        ;;
    update-from-github)
        update_from_github
        ;;
    *)
        echo "Cách sử dụng: $0 [lệnh]"
        echo "Lệnh:"
        echo "  install-packages                                         : Cài đặt các gói thư viện/toolchain hệ thống còn thiếu"
        echo "  install-offline-driver [--no-opengl] [--no-dkms]         : Cài đặt driver NVIDIA 610.57.04 (ưu tiên nvidia-installer / .run)"
        echo "  update-from-github                                       : Cập nhật mod từ Cyridd/cmpunlocker trên GitHub"
        echo "  install-kernel-mod [--pcie-diagnostic] [--keep-gsp-off] [--rebar-size=N] : Cài đặt open module mod"
        echo "  patch-glcore-system                                      : Vá thư viện hệ thống glcore (MME 240 -> 0)"
        echo "  restore-glcore-system                                    : Khôi phục thư viện gốc"
        echo "  patch-glcore-local                                       : Tạo thư viện vá cục bộ cho Steam/Game"
        echo "  uninstall-kernel-mod                                     : Gỡ bỏ kernel module mod"
        echo "  enable-gsp                                               : Bật GSP (chuẩn bị cho open module)"
        echo "  disable-gsp                                              : Tắt GSP"
        exit 1
        ;;
esac
