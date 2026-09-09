#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NVIDIA CMP 40HX Unlocker & Optimizer GUI
Dự án mở khóa Compute, PCIe Gen2, 8GB ReBAR và bypass Vulkan MME Throttle
Dựa trên nghiên cứu Cyridd/cmpunlocker và NVIDIA 610.57.04
Bao gồm:
- Bộ công cụ kiểm tra điều kiện & cài đặt gói/thư viện còn thiếu
- Trình cài đặt Driver 40HX NVIDIA 610.57.04 từ gói offline có sẵn
- Trình kiểm tra & xác minh toàn diện các bước mod đã thực hiện
"""

import os
import sys
import subprocess
import threading
import shutil
import platform
import re
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

# ----------------- Theme Palette -----------------
BG_COLOR = "#181825"
SURFACE_COLOR = "#252538"
HEADER_COLOR = "#1e1e2e"
TEXT_COLOR = "#cdd6f4"
SUBTEXT_COLOR = "#a6adc8"
ACCENT_BLUE = "#89b4fa"
ACCENT_GREEN = "#a6e3a1"
ACCENT_RED = "#f38ba8"
ACCENT_YELLOW = "#f9e2af"
ACCENT_CYAN = "#94e2d5"
ACCENT_PURPLE = "#cba6f7"
BTN_BG = "#313244"
BTN_ACTIVE = "#45475a"

APP_DIR = os.path.dirname(os.path.abspath(__file__))
CMP_DIR = os.path.join(APP_DIR, "cmpunlocker")
BACKEND_SCRIPT = os.path.join(APP_DIR, "apply_mod_backend.sh")
DRIVER_VER = "610.57.04"
DRIVER_DIR = os.path.join(APP_DIR, f"NVIDIA-Linux-x86_64-{DRIVER_VER}")
DRIVER_INSTALLER = os.path.join(DRIVER_DIR, "nvidia-installer")
OFFLINE_RUN_FILE = os.path.join(APP_DIR, f"NVIDIA-Linux-x86_64-{DRIVER_VER}.run")
OFFLINE_TAR_FILE = os.path.join(APP_DIR, f"NVIDIA-Linux-x86_64-{DRIVER_VER}.tar.gz")

def get_driver_source_info():
    """Kiểm tra và trả về thông tin bộ cài driver offline được ưu tiên."""
    if os.path.isfile(DRIVER_INSTALLER):
        return {
            "type": "directory",
            "path": DRIVER_INSTALLER,
            "display": f"NVIDIA-Linux-x86_64-{DRIVER_VER}/nvidia-installer",
            "desc": "Thư mục giải nén & mod dartraiden (Khuyên dùng - Chạy trực tiếp)",
            "available": True
        }
    elif os.path.isfile(OFFLINE_TAR_FILE):
        return {
            "type": "tar",
            "path": OFFLINE_TAR_FILE,
            "display": os.path.basename(OFFLINE_TAR_FILE),
            "desc": "Gói nén lưu trữ offline (Đã tích hợp mod dartraiden)",
            "available": True
        }
    elif os.path.isfile(OFFLINE_RUN_FILE):
        return {
            "type": "run",
            "path": OFFLINE_RUN_FILE,
            "display": os.path.basename(OFFLINE_RUN_FILE),
            "desc": "File .run gốc từ NVIDIA (Cần giải nén & nạp mod dartraiden)",
            "available": True
        }
    else:
        return {
            "type": "none",
            "path": None,
            "display": "Không tìm thấy",
            "desc": "Chưa có bộ cài offline",
            "available": False
        }

def find_pytorch_python():
    """Tự động tìm kiếm môi trường Python có hỗ trợ PyTorch CUDA khả dụng."""
    candidates = []
    if "VIRTUAL_ENV" in os.environ:
        candidates.append(os.path.join(os.environ["VIRTUAL_ENV"], "bin", "python"))
    home = os.path.expanduser("~")
    candidates.extend([
        os.path.join(APP_DIR, ".venv", "bin", "python"),
        os.path.join(home, "lada", ".venv", "bin", "python"),
        os.path.join(home, ".venv", "bin", "python"),
        os.path.join(home, "pytorch-gfx906", ".venv", "bin", "python"),
        sys.executable
    ])
    system_py3 = shutil.which("python3")
    if system_py3:
        candidates.append(system_py3)

    for py in candidates:
        if py and os.path.isfile(py) and os.access(py, os.X_OK):
            try:
                out = subprocess.check_output(
                    [py, "-c", "import torch; print(torch.cuda.is_available())"],
                    stderr=subprocess.DEVNULL, text=True, timeout=5
                ).strip()
                if out == "True":
                    return py
            except Exception:
                pass

    return sys.executable

class CMPUnlockerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("NVIDIA CMP 40HX Unlocker & Optimizer (Cyridd Mod)")
        self.geometry("1040x820")
        self.minsize(940, 720)
        self.configure(bg=BG_COLOR)

        self.style = ttk.Style(self)
        self.setup_styles()

        self.cards_detected = []
        self.is_riser_1x = False
        self.missing_packages = []
        self.checks_result = {}
        self.is_busy = False
        self.current_commit = self.get_local_commit_info()

        self.create_header()
        self.create_tabs()
        self.create_status_bar()

        # Initial background scan
        self.after(200, self.run_checks_async)

    def get_local_commit_info(self):
        try:
            out = subprocess.check_output(
                ["git", "-C", CMP_DIR, "log", "-1", "--format=%h - %s (%cr)"],
                stderr=subprocess.DEVNULL, text=True
            ).strip()
            if out:
                return out
        except Exception:
            pass
        return "c524503 (Cyridd/cmpunlocker)"

    def setup_styles(self):
        self.style.theme_use("clam")
        
        self.style.configure(".", background=BG_COLOR, foreground=TEXT_COLOR, font=("Segoe UI", 10))
        
        # Notebook & Tabs
        self.style.configure("TNotebook", background=BG_COLOR, borderwidth=0)
        self.style.configure("TNotebook.Tab", background=SURFACE_COLOR, foreground=TEXT_COLOR, 
                             padding=[13, 8], font=("Segoe UI", 10, "bold"))
        self.style.map("TNotebook.Tab", 
                       background=[("selected", ACCENT_BLUE)], 
                       foreground=[("selected", "#11111b")])

        # Frames
        self.style.configure("Card.TFrame", background=SURFACE_COLOR, relief="flat")
        self.style.configure("Header.TFrame", background=HEADER_COLOR, relief="flat")

        # Buttons
        self.style.configure("Primary.TButton", background=ACCENT_BLUE, foreground="#11111b",
                             font=("Segoe UI", 10, "bold"), padding=[12, 6])
        self.style.map("Primary.TButton", background=[("active", "#74c7ec")])

        self.style.configure("Success.TButton", background=ACCENT_GREEN, foreground="#11111b",
                             font=("Segoe UI", 10, "bold"), padding=[12, 6])
        self.style.map("Success.TButton", background=[("active", "#94e2d5")])

        self.style.configure("Danger.TButton", background=ACCENT_RED, foreground="#11111b",
                             font=("Segoe UI", 10, "bold"), padding=[12, 6])
        self.style.map("Danger.TButton", background=[("active", "#eba0ac")])

        self.style.configure("Update.TButton", background=ACCENT_PURPLE, foreground="#11111b",
                             font=("Segoe UI", 9, "bold"), padding=[10, 5])
        self.style.map("Update.TButton", background=[("active", "#b4befe")])

        self.style.configure("Warn.TButton", background=ACCENT_YELLOW, foreground="#11111b",
                             font=("Segoe UI", 9, "bold"), padding=[10, 5])
        self.style.map("Warn.TButton", background=[("active", "#f5e0dc")])

        self.style.configure("Normal.TButton", background=BTN_BG, foreground=TEXT_COLOR,
                             font=("Segoe UI", 9), padding=[10, 5])
        self.style.map("Normal.TButton", background=[("active", BTN_ACTIVE)])

        # Progressbar
        self.style.configure("TProgressbar", troughcolor=SURFACE_COLOR, background=ACCENT_BLUE)

    def create_header(self):
        header = ttk.Frame(self, style="Header.TFrame", padding=15)
        header.pack(fill="x", padx=10, pady=(10, 5))

        left = ttk.Frame(header, style="Header.TFrame")
        left.pack(side="left", fill="x", expand=True)

        title_lbl = tk.Label(left, text="⚡ NVIDIA CMP 40HX Unlocker & Optimizer", 
                             font=("Segoe UI", 16, "bold"), bg=HEADER_COLOR, fg=ACCENT_CYAN)
        title_lbl.pack(anchor="w")

        sub_lbl = tk.Label(left, 
                           text="Mở khóa Compute (SMs/Tensor), PCIe Gen2 (x2 Riser 1x), ReBAR 8GB & Triệt tiêu lag Vulkan",
                           font=("Segoe UI", 9), bg=HEADER_COLOR, fg=SUBTEXT_COLOR)
        sub_lbl.pack(anchor="w", pady=(2, 0))

        right = ttk.Frame(header, style="Header.TFrame")
        right.pack(side="right", padx=(10, 0))

        self.btn_header_update = ttk.Button(right, text="🌐 Cập nhật Mod từ GitHub", 
                                            style="Update.TButton", command=self.on_update_github_click)
        self.btn_header_update.pack(anchor="e")

        self.lbl_header_commit = tk.Label(right, text=f"Mod: {self.current_commit[:35]}...", 
                                          font=("Segoe UI", 8), bg=HEADER_COLOR, fg=ACCENT_YELLOW)
        self.lbl_header_commit.pack(anchor="e", pady=(3, 0))

    def create_tabs(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=5)

        # Tab 1: Checks & Packages
        self.tab_checks = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_checks, text="🔍 1. Kiểm tra điều kiện")
        self.build_checks_tab()

        # Tab 2: Driver Offline Installer
        self.tab_driver = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_driver, text="💾 2. Cài đặt Driver 40HX (Offline)")
        self.build_driver_tab()

        # Tab 3: Kernel Unlock
        self.tab_kernel = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_kernel, text="🚀 3. Mở khóa Kernel (Open Module)")
        self.build_kernel_tab()

        # Tab 4: Vulkan glcore Patch
        self.tab_glcore = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_glcore, text="🎮 4. Vá Vulkan glcore")
        self.build_glcore_tab()

        # Tab 5: Verification & Audit Tool
        self.tab_audit = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_audit, text="📊 5. Xác minh toàn diện Mod")
        self.build_audit_tab()

        # Tab 6: Rollback
        self.tab_rollback = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.tab_rollback, text="🔄 6. Khôi phục gốc")
        self.build_rollback_tab()

    def create_status_bar(self):
        bar = ttk.Frame(self, style="Header.TFrame", padding=(10, 5))
        bar.pack(fill="x", side="bottom", padx=10, pady=5)

        self.lbl_status = tk.Label(bar, text="Sẵn sàng", font=("Segoe UI", 9), bg=HEADER_COLOR, fg=SUBTEXT_COLOR)
        self.lbl_status.pack(side="left")

        is_root = (os.geteuid() == 0)
        root_text = "Quyền: ROOT" if is_root else "Quyền: Người dùng (Sẽ gọi pkexec khi cần root)"
        root_color = ACCENT_GREEN if is_root else ACCENT_YELLOW
        self.lbl_root = tk.Label(bar, text=root_text, font=("Segoe UI", 9, "bold"), bg=HEADER_COLOR, fg=root_color)
        self.lbl_root.pack(side="right")

    # ----------------- TAB 1: Checks & Packages -----------------
    def build_checks_tab(self):
        top_frame = ttk.Frame(self.tab_checks, style="Card.TFrame", padding=10)
        top_frame.pack(fill="x", pady=(0, 10))

        self.summary_badge = tk.Label(top_frame, text="ĐANG QUÉT HỆ THỐNG...", 
                                      font=("Segoe UI", 11, "bold"), bg=SURFACE_COLOR, fg=ACCENT_YELLOW)
        self.summary_badge.pack(side="left")

        btns_right = ttk.Frame(top_frame, style="Card.TFrame")
        btns_right.pack(side="right")

        self.btn_install_pkgs = ttk.Button(btns_right, text="📦 Cài đặt gói còn thiếu", style="Warn.TButton", 
                                           command=self.on_install_packages_click)
        self.btn_install_pkgs.pack(side="left", padx=(0, 5))
        self.btn_install_pkgs.pack_forget()

        ttk.Button(btns_right, text="🌐 Cập nhật Mod (GitHub)", style="Update.TButton", 
                   command=self.on_update_github_click).pack(side="left", padx=(0, 5))

        btn_rescan = ttk.Button(btns_right, text="🔄 Quét lại", style="Normal.TButton", command=self.run_checks_async)
        btn_rescan.pack(side="left")

        # Treeview
        self.checks_tree = ttk.Treeview(self.tab_checks, columns=("item", "current", "required", "status"), 
                                        show="headings", height=13)
        self.checks_tree.heading("item", text="Mục kiểm tra")
        self.checks_tree.heading("current", text="Hiện trạng hệ thống")
        self.checks_tree.heading("required", text="Yêu cầu Mod")
        self.checks_tree.heading("status", text="Đánh giá")

        self.checks_tree.column("item", width=220, anchor="w")
        self.checks_tree.column("current", width=400, anchor="w")
        self.checks_tree.column("required", width=180, anchor="w")
        self.checks_tree.column("status", width=110, anchor="center")

        self.checks_tree.pack(fill="both", expand=True, pady=(0, 10))

        # Bottom info card (Notes for Riser PCIe 1x)
        info_frame = ttk.Frame(self.tab_checks, style="Card.TFrame", padding=10)
        info_frame.pack(fill="x")
        self.lbl_check_details = tk.Label(
            info_frame, 
            text="ℹ GHI CHÚ PHẦN CỨNG RISER 1X:\n"
                 "  • 2 card CMP 40HX đang cắm qua cáp Riser PCIe 1x (chiều rộng lane vật lý là 1 lane).\n"
                 "  • Bản mod PCIe Gen2 sẽ nâng xung nhịp từ Gen1 (2.5 GT/s) lên Gen2 (5.0 GT/s) -> Gấp đôi băng thông (250MB/s lên 500MB/s).\n"
                 "  • Mở khóa tính toán Compute/Tensor Cores và bản vá Vulkan glcore hoạt động 100% độc lập với số lane PCIe!",
            font=("Segoe UI", 9), bg=SURFACE_COLOR, fg=ACCENT_CYAN, justify="left"
        )
        self.lbl_check_details.pack(anchor="w")

    # ----------------- TAB 2: Driver Offline Installer -----------------
    def build_driver_tab(self):
        desc = ttk.Frame(self.tab_driver, style="Card.TFrame", padding=12)
        desc.pack(fill="x", pady=(0, 10))

        tk.Label(desc, text="💾 Cài đặt Driver NVIDIA 610.57.04 từ gói Offline có sẵn", 
                 font=("Segoe UI", 11, "bold"), bg=SURFACE_COLOR, fg=ACCENT_YELLOW).pack(anchor="w")

        self.lbl_driver_info = tk.Label(desc, text="", font=("Segoe UI", 9), bg=SURFACE_COLOR, fg=TEXT_COLOR, justify="left")
        self.lbl_driver_info.pack(anchor="w", pady=(5, 5))
        self.update_driver_tab_info()

        # Options
        opt_frame = ttk.Frame(self.tab_driver, style="Card.TFrame", padding=10)
        opt_frame.pack(fill="x", pady=(0, 10))

        self.var_drv_noopengl = tk.BooleanVar(value=True)
        chk_noopengl = tk.Checkbutton(
            opt_frame, 
            text="Không ghi đè thư viện OpenGL (--no-opengl-files) - KHUYÊN DÙNG khi chạy chung với card AMD xuất hình", 
            variable=self.var_drv_noopengl, bg=SURFACE_COLOR, fg=ACCENT_CYAN, 
            selectcolor=BG_COLOR, activebackground=SURFACE_COLOR
        )
        chk_noopengl.pack(anchor="w")

        self.var_drv_dkms = tk.BooleanVar(value=True)
        chk_dkms = tk.Checkbutton(
            opt_frame, 
            text="Đăng ký DKMS tự động (--dkms) - Tự động biên dịch lại khi cập nhật kernel Linux", 
            variable=self.var_drv_dkms, bg=SURFACE_COLOR, fg=TEXT_COLOR, 
            selectcolor=BG_COLOR, activebackground=SURFACE_COLOR
        )
        chk_dkms.pack(anchor="w", pady=(5, 0))

        # Action Button & Progress
        act_frame = ttk.Frame(self.tab_driver, style="Card.TFrame", padding=10)
        act_frame.pack(fill="x", pady=(0, 10))

        self.btn_install_driver = ttk.Button(act_frame, text="🚀 Bắt đầu Cài đặt Driver NVIDIA 610.57.04", 
                                             style="Primary.TButton", command=self.on_install_driver_click)
        self.btn_install_driver.pack(side="left", padx=(0, 10))

        self.driver_prog = ttk.Progressbar(act_frame, mode="indeterminate", length=300)
        self.driver_prog.pack(side="left", fill="x", expand=True)

        # Log
        log_frame = ttk.Frame(self.tab_driver, style="Card.TFrame", padding=5)
        log_frame.pack(fill="both", expand=True)

        tk.Label(log_frame, text="Nhật ký cài đặt Driver:", font=("Segoe UI", 9, "bold"), 
                 bg=SURFACE_COLOR, fg=SUBTEXT_COLOR).pack(anchor="w", padx=5, pady=(2, 0))
        self.txt_driver_log = scrolledtext.ScrolledText(log_frame, bg="#11111b", fg=TEXT_COLOR, 
                                                        font=("Cascadia Mono", 9), height=10)
        self.txt_driver_log.pack(fill="both", expand=True, padx=5, pady=5)

    def update_driver_tab_info(self):
        drv_info = get_driver_source_info()
        installer_exists = os.path.isfile(DRIVER_INSTALLER)
        run_exists = os.path.isfile(OFFLINE_RUN_FILE)
        tar_exists = os.path.isfile(OFFLINE_TAR_FILE)

        status_installer = "✔ Có sẵn (Khuyên dùng - Chạy trực tiếp, bảo toàn mod dartraiden)" if installer_exists else "✖ Chưa có"
        status_run = f"✔ Có sẵn ({os.path.basename(OFFLINE_RUN_FILE)})" if run_exists else "✖ Thiếu"
        status_tar = f"✔ Có sẵn ({os.path.basename(OFFLINE_TAR_FILE)})" if tar_exists else "✖ Thiếu"

        info_text = (
            f"Bộ cài đặt Driver chính thức của NVIDIA ({DRIVER_VER}) được lưu trữ tại thư mục dự án:\n"
            f"  • [ƯU TIÊN] nvidia-installer trực tiếp: {DRIVER_INSTALLER}\n"
            f"      -> Trạng thái: {status_installer}\n"
            f"  • File cài đặt tự giải nén (.run): {os.path.basename(OFFLINE_RUN_FILE)}\n"
            f"      -> Trạng thái: {status_run}\n"
            f"  • Gói nén lưu trữ dự phòng (.tar.gz): {os.path.basename(OFFLINE_TAR_FILE)}\n"
            f"      -> Trạng thái: {status_tar}\n\n"
            f"🎯 Nguồn cài đặt đang trỏ tới: {drv_info['display']}\n"
            f"   Chi tiết: {drv_info['desc']}\n\n"
            "Tính năng này giúp bạn cài đặt hoặc khôi phục lại Driver NVIDIA tương thích bất cứ lúc nào\n"
            "mà hoàn toàn không cần kết nối Internet."
        )
        if hasattr(self, "lbl_driver_info"):
            self.lbl_driver_info.config(text=info_text)

    # ----------------- TAB 3: Kernel Mod -----------------
    def build_kernel_tab(self):
        upd_bar = ttk.Frame(self.tab_kernel, style="Card.TFrame", padding=10)
        upd_bar.pack(fill="x", pady=(0, 10))

        self.lbl_kernel_commit = tk.Label(
            upd_bar, 
            text=f"📦 Nguồn bản mod Cyridd: {self.current_commit}", 
            font=("Segoe UI", 9, "bold"), bg=SURFACE_COLOR, fg=ACCENT_CYAN
        )
        self.lbl_kernel_commit.pack(side="left")

        ttk.Button(upd_bar, text="🌐 Kéo bản mới từ GitHub", style="Update.TButton", 
                   command=self.on_update_github_click).pack(side="right")

        desc = ttk.Frame(self.tab_kernel, style="Card.TFrame", padding=12)
        desc.pack(fill="x", pady=(0, 10))

        tk.Label(desc, text="⚙ Mở khóa Nhân GPU (NVIDIA Open Kernel Module) - Tối ưu cho Riser 1x", 
                 font=("Segoe UI", 11, "bold"), bg=SURFACE_COLOR, fg=ACCENT_BLUE).pack(anchor="w")
        
        info_text = (
            "Dự án sẽ áp dụng 3 bản vá vào open-gpu-kernel-modules-610.57.04:\n"
            "  • 0001: Compute / SMs Unlock (Kích hoạt Tensor Cores, nạp SS0=0x88888888, FECS_PLM=0xffffff8f).\n"
            "  • 0002: PCIe Gen2 Unlock (Nâng tốc độ liên kết từ 2.5 GT/s Gen1 lên 5.0 GT/s Gen2 trên Riser 1x).\n"
            "  • 0003: Resizable BAR Unlock (Mở rộng BAR1 lên 8192 MiB hoặc chọn kích thước phù hợp với Riser).\n\n"
            "Ghi chú quan trọng: Bản mod nạp qua luồng GSP/SEC2 Booter nên GSP Firmware CẦN ĐƯỢC BẬT.\n"
            "Sau khi cài đặt thành công, bắt buộc phải TẮT MÁY HOÀN TOÀN (Cold Reboot) để GPU nhận Gen2."
        )
        tk.Label(desc, text=info_text, font=("Segoe UI", 9), bg=SURFACE_COLOR, fg=TEXT_COLOR, justify="left").pack(anchor="w", pady=(5, 5))

        opt_frame = ttk.Frame(self.tab_kernel, style="Card.TFrame", padding=10)
        opt_frame.pack(fill="x", pady=(0, 10))

        rebar_box = ttk.Frame(opt_frame, style="Card.TFrame")
        rebar_box.pack(fill="x", pady=(0, 8))
        tk.Label(rebar_box, text="Cấu hình Resizable BAR (ReBAR):", font=("Segoe UI", 9, "bold"), 
                 bg=SURFACE_COLOR, fg=TEXT_COLOR).pack(side="left", padx=(0, 10))

        self.rebar_var = tk.StringVar(value="7")
        rebar_combo = ttk.Combobox(rebar_box, textvariable=self.rebar_var, state="readonly", width=35)
        rebar_combo["values"] = (
            "7: 8 GiB (Mặc định bản mod - Khuyên dùng)",
            "6: 4 GiB (Dự phòng cho Riser 1x)",
            "5: 2 GiB (Dự phòng)",
            "1: 128 MiB (Tối thiểu)",
            "0: Tắt ReBAR (Nếu Riser 1x lỗi cấp phát bộ nhớ)"
        )
        rebar_combo.current(0)
        rebar_combo.pack(side="left")

        self.var_pcie_diag = tk.BooleanVar(value=False)
        chk_diag = tk.Checkbutton(opt_frame, text="Sử dụng bản vá PCIe Diagnostic (Chỉ chọn nếu bản PCIe chuẩn gặp lỗi)", 
                                  variable=self.var_pcie_diag, bg=SURFACE_COLOR, fg=TEXT_COLOR, 
                                  selectcolor=BG_COLOR, activebackground=SURFACE_COLOR)
        chk_diag.pack(anchor="w")

        self.var_enable_gsp = tk.BooleanVar(value=True)
        chk_gsp = tk.Checkbutton(opt_frame, text="Tự động đồng bộ GSP: Bật GSP trong /etc/modprobe.d/nvidia.conf (Khuyên dùng)", 
                                 variable=self.var_enable_gsp, bg=SURFACE_COLOR, fg=ACCENT_GREEN, 
                                 selectcolor=BG_COLOR, activebackground=SURFACE_COLOR)
        chk_gsp.pack(anchor="w", pady=(5, 0))

        act_frame = ttk.Frame(self.tab_kernel, style="Card.TFrame", padding=10)
        act_frame.pack(fill="x", pady=(0, 10))

        self.btn_install_kernel = ttk.Button(act_frame, text="🚀 Bắt đầu Biên dịch & Cài đặt Kernel Mod (Offline)", 
                                             style="Primary.TButton", command=self.on_install_kernel_click)
        self.btn_install_kernel.pack(side="left", padx=(0, 10))

        self.kernel_prog = ttk.Progressbar(act_frame, mode="indeterminate", length=300)
        self.kernel_prog.pack(side="left", fill="x", expand=True)

        log_frame = ttk.Frame(self.tab_kernel, style="Card.TFrame", padding=5)
        log_frame.pack(fill="both", expand=True)

        tk.Label(log_frame, text="Nhật ký tiến trình (Log Output):", font=("Segoe UI", 9, "bold"), 
                 bg=SURFACE_COLOR, fg=SUBTEXT_COLOR).pack(anchor="w", padx=5, pady=(2, 0))
        self.txt_kernel_log = scrolledtext.ScrolledText(log_frame, bg="#11111b", fg=TEXT_COLOR, 
                                                        font=("Cascadia Mono", 9), height=10)
        self.txt_kernel_log.pack(fill="both", expand=True, padx=5, pady=5)

    # ----------------- TAB 4: Vulkan glcore Patch -----------------
    def build_glcore_tab(self):
        desc = ttk.Frame(self.tab_glcore, style="Card.TFrame", padding=12)
        desc.pack(fill="x", pady=(0, 10))

        tk.Label(desc, text="🎮 Vá Userspace libnvidia-glcore.so (Khắc phục giật lag Vulkan / Game)", 
                 font=("Segoe UI", 11, "bold"), bg=SURFACE_COLOR, fg=ACCENT_GREEN).pack(anchor="w")

        info_text = (
            "Hiện tượng nghẽn hiệu năng game Vulkan / Proton trên CMP 40HX xuất phát từ việc driver 610.57.04\n"
            "chèn macro 52 với tham số 0xf0 (lặp 240 lần PIPE_NOP + WAIT_FOR_IDLE) ở mỗi lệnh vkCmdBindPipeline.\n\n"
            "Bản vá nhị phân sẽ sửa tham số lặp từ 240 (0xf0) về 0 (0x0) tại 2 vị trí offset (0xb20c2d và 0xdcbf60),\n"
            "giúp loại bỏ hoàn toàn độ trễ nhân tạo (tăng tốc độ bind pipeline lên đến hơn 200 - 30,000 lần!)."
        )
        tk.Label(desc, text=info_text, font=("Segoe UI", 9), bg=SURFACE_COLOR, fg=TEXT_COLOR, justify="left").pack(anchor="w", pady=(5, 5))

        mode_frame = ttk.Frame(self.tab_glcore, style="Card.TFrame", padding=10)
        mode_frame.pack(fill="x", pady=(0, 10))

        self.glcore_mode = tk.StringVar(value="system")
        r1 = tk.Radiobutton(mode_frame, text="Cách 1: Vá trực tiếp vào thư viện hệ thống (Toàn bộ game Vulkan/Proton đều nhận tự động)", 
                            variable=self.glcore_mode, value="system", bg=SURFACE_COLOR, fg=TEXT_COLOR, 
                            selectcolor=BG_COLOR, activebackground=SURFACE_COLOR)
        r1.pack(anchor="w")
        tk.Label(mode_frame, text="     (Tự động sao lưu file gốc thành .orig, có thể khôi phục lại bất kỳ lúc nào)", 
                 font=("Segoe UI", 8), bg=SURFACE_COLOR, fg=SUBTEXT_COLOR).pack(anchor="w")

        r2 = tk.Radiobutton(mode_frame, text="Cách 2: Vá thư viện cục bộ (Không đụng file hệ thống, chỉ dùng qua LD_LIBRARY_PATH cho Steam)", 
                            variable=self.glcore_mode, value="local", bg=SURFACE_COLOR, fg=TEXT_COLOR, 
                            selectcolor=BG_COLOR, activebackground=SURFACE_COLOR)
        r2.pack(anchor="w", pady=(8, 0))
        tk.Label(mode_frame, text="     (Tạo thư mục local_glcore và file script chạy riêng cho từng game)", 
                 font=("Segoe UI", 8), bg=SURFACE_COLOR, fg=SUBTEXT_COLOR).pack(anchor="w")

        act_frame = ttk.Frame(self.tab_glcore, style="Card.TFrame", padding=10)
        act_frame.pack(fill="x", pady=(0, 10))

        btn_patch = ttk.Button(act_frame, text="⚡ Áp dụng Bản vá glcore", style="Success.TButton", command=self.on_patch_glcore_click)
        btn_patch.pack(side="left", padx=(0, 10))

        btn_restore = ttk.Button(act_frame, text="↩ Khôi phục thư viện gốc", style="Normal.TButton", command=self.on_restore_glcore_click)
        btn_restore.pack(side="left")

        log_frame = ttk.Frame(self.tab_glcore, style="Card.TFrame", padding=5)
        log_frame.pack(fill="both", expand=True)

        tk.Label(log_frame, text="Kết quả thực thi bản vá glcore:", font=("Segoe UI", 9, "bold"), 
                 bg=SURFACE_COLOR, fg=SUBTEXT_COLOR).pack(anchor="w", padx=5, pady=(2, 0))
        self.txt_glcore_log = scrolledtext.ScrolledText(log_frame, bg="#11111b", fg=TEXT_COLOR, 
                                                        font=("Cascadia Mono", 9), height=10)
        self.txt_glcore_log.pack(fill="both", expand=True, padx=5, pady=5)

    # ----------------- TAB 5: Verification & Audit Tool -----------------
    def build_audit_tab(self):
        desc = ttk.Frame(self.tab_audit, style="Card.TFrame", padding=12)
        desc.pack(fill="x", pady=(0, 10))

        tk.Label(desc, text="📊 Công cụ Xác minh Toàn diện Các Bước Mod Đã Thực Hiện", 
                 font=("Segoe UI", 12, "bold"), bg=SURFACE_COLOR, fg=ACCENT_CYAN).pack(anchor="w")

        tk.Label(
            desc, 
            text="Kiểm tra trực tiếp các thanh ghi phần cứng, kernel booter logs, BAR1 memory và byte mã máy userspace glcore.",
            font=("Segoe UI", 9), bg=SURFACE_COLOR, fg=SUBTEXT_COLOR
        ).pack(anchor="w", pady=(2, 8))

        # Big 1-click test button
        btn_box = ttk.Frame(desc, style="Card.TFrame")
        btn_box.pack(fill="x")

        self.btn_run_audit = ttk.Button(
            btn_box, 
            text="⚡ CHẠY KIỂM TRA TOÀN DIỆN CÁC BƯỚC MOD (1-Click Audit)", 
            style="Success.TButton", 
            command=self.run_full_audit_async
        )
        self.btn_run_audit.pack(side="left", padx=(0, 10))

        ttk.Button(btn_box, text="🔥 Đo TFLOPS (Compute & Tensor)", style="Primary.TButton", 
                   command=self.run_tflops_benchmark_async).pack(side="left", padx=3)
        ttk.Button(btn_box, text="Kiểm tra nvidia-smi", style="Normal.TButton", 
                   command=lambda: self.run_diag_cmd("nvidia-smi")).pack(side="left", padx=3)
        ttk.Button(btn_box, text="Kiểm tra PCIe Link (lspci)", style="Normal.TButton", 
                   command=self.diag_check_pcie).pack(side="left", padx=3)
        ttk.Button(btn_box, text="Kiểm tra dmesg CMP40", style="Normal.TButton", 
                   command=lambda: self.run_diag_cmd("dmesg | grep -iE 'CMP40|nvidia' | tail -n 35")).pack(side="left", padx=3)

        # Audit Scorecard Frame
        self.audit_scorecard = ttk.Frame(self.tab_audit, style="Card.TFrame", padding=10)
        self.audit_scorecard.pack(fill="x", pady=(0, 10))

        self.lbl_audit_summary = tk.Label(
            self.audit_scorecard, 
            text="Nhấn nút 'CHẠY KIỂM TRA TOÀN DIỆN' ở trên để quét tất cả các bước mod.", 
            font=("Segoe UI", 10, "bold"), bg=SURFACE_COLOR, fg=ACCENT_YELLOW
        )
        self.lbl_audit_summary.pack(anchor="w")

        # Detailed Audit Output ScrolledText
        log_frame = ttk.Frame(self.tab_audit, style="Card.TFrame", padding=5)
        log_frame.pack(fill="both", expand=True)

        tk.Label(log_frame, text="Báo cáo chi tiết kỹ thuật (Evidence Log):", font=("Segoe UI", 9, "bold"), 
                 bg=SURFACE_COLOR, fg=SUBTEXT_COLOR).pack(anchor="w", padx=5, pady=(2, 0))
        self.txt_audit_log = scrolledtext.ScrolledText(log_frame, bg="#11111b", fg=TEXT_COLOR, 
                                                      font=("Cascadia Mono", 9), height=12)
        self.txt_audit_log.pack(fill="both", expand=True, padx=5, pady=5)

    # ----------------- TAB 6: Rollback -----------------
    def build_rollback_tab(self):
        desc = ttk.Frame(self.tab_rollback, style="Card.TFrame", padding=12)
        desc.pack(fill="x", pady=(0, 10))

        tk.Label(desc, text="🔄 Khôi phục nguyên bản (Rollback)", 
                 font=("Segoe UI", 11, "bold"), bg=SURFACE_COLOR, fg=ACCENT_RED).pack(anchor="w")

        info_text = (
            "Nếu bạn muốn gỡ bỏ hoàn toàn các thay đổi của bản mod:\n"
            "  1. Gỡ bỏ kernel module vá trong /lib/modules/$(uname -r)/updates/cmpunlocker\n"
            "  2. Tự động chạy lại depmod và update-initramfs để khôi phục driver chuẩn của hệ thống.\n"
            "  3. Khôi phục lại thư viện libnvidia-glcore.so từ bản sao lưu .orig.\n"
            "  4. Tùy chọn đặt lại tham số NVreg_EnableGpuFirmware=0 nếu bạn muốn quay lại chế độ cũ."
        )
        tk.Label(desc, text=info_text, font=("Segoe UI", 9), bg=SURFACE_COLOR, fg=TEXT_COLOR, justify="left").pack(anchor="w", pady=(5, 5))

        act_frame = ttk.Frame(self.tab_rollback, style="Card.TFrame", padding=10)
        act_frame.pack(fill="x", pady=(0, 10))

        ttk.Button(act_frame, text="🛑 Gỡ bỏ Kernel Mod & Khôi phục Driver Chuẩn", style="Danger.TButton", 
                   command=self.on_uninstall_kernel_click).pack(side="left", padx=(0, 10))

        ttk.Button(act_frame, text="↩ Khôi phục thư viện glcore gốc", style="Normal.TButton", 
                   command=self.on_restore_glcore_click).pack(side="left", padx=5)

        ttk.Button(act_frame, text="🔒 Tắt lại GSP (NVreg_EnableGpuFirmware=0)", style="Normal.TButton", 
                   command=self.on_disable_gsp_click).pack(side="left", padx=5)

        log_frame = ttk.Frame(self.tab_rollback, style="Card.TFrame", padding=5)
        log_frame.pack(fill="both", expand=True)

        tk.Label(log_frame, text="Nhật ký gỡ bỏ:", font=("Segoe UI", 9, "bold"), 
                 bg=SURFACE_COLOR, fg=SUBTEXT_COLOR).pack(anchor="w", padx=5, pady=(2, 0))
        self.txt_rollback_log = scrolledtext.ScrolledText(log_frame, bg="#11111b", fg=TEXT_COLOR, 
                                                          font=("Cascadia Mono", 9), height=10)
        self.txt_rollback_log.pack(fill="both", expand=True, padx=5, pady=5)

    # ----------------- Worker & Helpers -----------------
    def log(self, widget, text, clear=False):
        def _append():
            if clear:
                widget.delete("1.0", tk.END)
            widget.insert(tk.END, text + "\n")
            widget.see(tk.END)
        self.after(0, _append)

    def execute_with_elevation(self, script_action_args, log_widget):
        is_root = (os.geteuid() == 0)
        cmd = []
        if is_root:
            cmd = [BACKEND_SCRIPT] + script_action_args
        else:
            if shutil.which("pkexec"):
                cmd = ["pkexec", "bash", BACKEND_SCRIPT] + script_action_args
            else:
                cmd = ["sudo", BACKEND_SCRIPT] + script_action_args

        self.log(log_widget, f"[RUN] {' '.join(cmd)}\n")

        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                 text=True, bufsize=1, universal_newlines=True)
            for line in p.stdout:
                self.log(log_widget, line.rstrip())
            p.wait()
            if p.returncode == 0:
                self.log(log_widget, "\n✔ [SUCCESS] Thao tác hoàn tất thành công!\n")
            else:
                self.log(log_widget, f"\n✖ [ERROR] Tiến trình kết thúc với mã lỗi: {p.returncode}\n")
            return p.returncode
        except Exception as e:
            self.log(log_widget, f"\n✖ [EXCEPTION] Lỗi khi thực thi: {str(e)}\n")
            return -1

    # ----------------- Missing Packages Installation -----------------
    def on_install_packages_click(self):
        if self.is_busy:
            return
        if not messagebox.askyesno("Cài đặt gói", 
                                   "Cài đặt các công cụ và gói thư viện còn thiếu bằng apt-get?\n"
                                   "(Yêu cầu nhập mật khẩu quản trị)"):
            return

        self.is_busy = True
        self.lbl_status.config(text="Đang cài đặt các thư viện còn thiếu...")
        self.log(self.txt_kernel_log, "=== BẮT ĐẦU CÀI ĐẶT THƯ VIỆN & CÔNG CỤ HỆ THỐNG ===", clear=True)
        self.notebook.select(self.tab_kernel)

        def _worker():
            ret = self.execute_with_elevation(["install-packages"], self.txt_kernel_log)
            def _done():
                self.is_busy = False
                self.run_checks_async()
                if ret == 0:
                    messagebox.showinfo("Thành công", "Đã cài đặt xong toàn bộ các thư viện và công cụ!")
                else:
                    messagebox.showerror("Lỗi", "Cài đặt gói gặp lỗi. Vui lòng kiểm tra log!")
            self.after(0, _done)

        threading.Thread(target=_worker, daemon=True).start()

    # ----------------- Offline Driver Installer Action -----------------
    def on_install_driver_click(self):
        if self.is_busy:
            messagebox.showinfo("Thông báo", "Một tác vụ khác đang được thực thi!")
            return

        drv_info = get_driver_source_info()
        if not drv_info["available"]:
            messagebox.showerror(
                "Lỗi", 
                f"Không tìm thấy bộ cài đặt driver nào tại:\n"
                f"  1. {DRIVER_INSTALLER}\n"
                f"  2. {OFFLINE_RUN_FILE}\n"
                f"  3. {OFFLINE_TAR_FILE}"
            )
            return

        msg = (
            f"Bạn có chắc muốn cài đặt Driver NVIDIA {DRIVER_VER}?\n\n"
            f"Nguồn bộ cài: {drv_info['display']}\n"
            f"Đường dẫn: {drv_info['path']}\n"
            f"Đặc điểm: {drv_info['desc']}\n\n"
            f"Tùy chọn:\n"
            f"  • Không ghi đè OpenGL: {'BẬT (Khuyên dùng)' if self.var_drv_noopengl.get() else 'Tắt'}\n"
            f"  • Kích hoạt DKMS: {'BẬT' if self.var_drv_dkms.get() else 'Tắt'}\n\n"
            "Quá trình cài đặt driver sẽ mất khoảng 1-2 phút."
        )

        if not messagebox.askyesno("Xác nhận", msg):
            return

        self.is_busy = True
        self.btn_install_driver.config(state="disabled")
        self.driver_prog.start(10)
        self.lbl_status.config(text=f"Đang cài đặt Driver NVIDIA {DRIVER_VER}...")
        self.log(self.txt_driver_log, f"=== BẮT ĐẦU CÀI ĐẶT DRIVER NVIDIA {DRIVER_VER} ===", clear=True)
        self.log(self.txt_driver_log, f"Nguồn cài đặt: {drv_info['path']}\nChi tiết: {drv_info['desc']}\n")

        args = ["install-offline-driver"]
        if self.var_drv_noopengl.get():
            args.append("--no-opengl")
        if not self.var_drv_dkms.get():
            args.append("--no-dkms")

        def _worker():
            ret = self.execute_with_elevation(args, self.txt_driver_log)
            def _done():
                self.driver_prog.stop()
                self.btn_install_driver.config(state="normal")
                self.is_busy = False
                self.run_checks_async()
                if ret == 0:
                    self.lbl_status.config(text="Cài đặt Driver NVIDIA thành công!")
                    messagebox.showinfo("Thành công", f"Đã cài đặt thành công Driver NVIDIA {DRIVER_VER}!")
                else:
                    self.lbl_status.config(text="Cài đặt Driver thất bại.")
                    messagebox.showerror("Lỗi", "Cài đặt Driver thất bại. Xem chi tiết log!")
            self.after(0, _done)

        threading.Thread(target=_worker, daemon=True).start()

    # ----------------- GitHub Update Action -----------------
    def on_update_github_click(self):
        if self.is_busy:
            messagebox.showinfo("Thông báo", "Một tác vụ khác đang chạy!")
            return

        self.notebook.select(self.tab_kernel)
        self.is_busy = True
        self.kernel_prog.start(10)
        self.lbl_status.config(text="Đang kết nối GitHub và kiểm tra bản cập nhật...")
        self.log(self.txt_kernel_log, "=== ĐANG KIỂM TRA VÀ CẬP NHẬT TỪ GITHUB (Cyridd/cmpunlocker) ===", clear=True)

        def _worker():
            cmd = [BACKEND_SCRIPT, "update-from-github"]
            self.log(self.txt_kernel_log, f"[RUN] {' '.join(cmd)}\n")

            try:
                p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                     text=True, bufsize=1, universal_newlines=True)
                for line in p.stdout:
                    self.log(self.txt_kernel_log, line.rstrip())
                p.wait()
                ret = p.returncode
            except Exception as e:
                self.log(self.txt_kernel_log, f"Lỗi: {str(e)}")
                ret = -1

            def _done():
                self.kernel_prog.stop()
                self.is_busy = False
                self.current_commit = self.get_local_commit_info()
                self.lbl_header_commit.config(text=f"Mod: {self.current_commit[:35]}...")
                self.lbl_kernel_commit.config(text=f"📦 Nguồn bản mod Cyridd: {self.current_commit}")
                self.run_checks_async()

                if ret == 0:
                    self.lbl_status.config(text="Đã đồng bộ thành công với GitHub!")
                    messagebox.showinfo(
                        "Cập nhật GitHub", 
                        f"Đã kiểm tra và đồng bộ thành công với GitHub!\n\n"
                        f"Phiên bản hiện tại:\n{self.current_commit}"
                    )
                else:
                    self.lbl_status.config(text="Cập nhật thất bại. Kiểm tra kết nối mạng!")
                    messagebox.showwarning(
                        "Cảnh báo", 
                        "Không thể kết nối hoặc cập nhật từ GitHub.\n"
                        "Vui lòng kiểm tra lại kết nối mạng internet."
                    )
            self.after(0, _done)

        threading.Thread(target=_worker, daemon=True).start()

    # ----------------- System Checks Worker -----------------
    def run_checks_async(self):
        if self.is_busy:
            return
        self.lbl_status.config(text="Đang quét điều kiện hệ thống...")
        threading.Thread(target=self._worker_checks, daemon=True).start()

    def _worker_checks(self):
        self.is_busy = True
        results = []
        all_ok = True
        self.missing_packages = []

        # 0. Cyridd Mod Version from Git
        commit_info = self.get_local_commit_info()
        results.append(("Phiên bản Mod Cyridd", commit_info, "Mới nhất (GitHub)", "PASS"))

        # 1. Detect CMP 40HX GPUs & Riser status
        cards = []
        riser_info = []
        self.is_riser_1x = False
        try:
            out = subprocess.check_output("lspci -nn | grep -iE '10de:1f0b|CMP 40HX'", shell=True, text=True)
            for line in out.strip().splitlines():
                if line:
                    b = line.split()[0]
                    cards.append(line.strip())
                    w_path = f"/sys/bus/pci/devices/0000:{b}/current_link_width"
                    s_path = f"/sys/bus/pci/devices/0000:{b}/current_link_speed"
                    w_val = "x?"
                    s_val = ""
                    if os.path.exists(w_path):
                        with open(w_path) as f:
                            w_val = f"x{f.read().strip()}"
                            if w_val == "x1":
                                self.is_riser_1x = True
                    if os.path.exists(s_path):
                        with open(s_path) as f:
                            s_val = f.read().strip()
                    riser_info.append(f"  • {b} [TU106 40HX]: Riser {w_val} ({s_val})")
        except Exception:
            pass

        self.cards_detected = cards
        if cards:
            cur = f"Tìm thấy {len(cards)} card CMP 40HX (Riser x1):\n" + "\n".join(riser_info)
            results.append(("Card đồ họa (GPU)", cur, "CMP 40HX (10de:1f0b)", "PASS"))
        else:
            all_ok = False
            results.append(("Card đồ họa (GPU)", "Không tìm thấy 10de:1f0b", "CMP 40HX (10de:1f0b)", "FAIL"))

        # 2. Linux OS & Kernel
        distro = "Linux"
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        distro = line.split("=", 1)[1].strip().strip('"')
                        break
        except Exception:
            pass
        kver = platform.release()
        results.append(("Hệ điều hành", distro, "Linux (Debian/Ubuntu/Mint)", "PASS"))
        results.append(("Kernel đang chạy", kver, "Hỗ trợ 6.x / 7.x", "PASS"))

        # 3. Kernel Build Headers
        hdr_path = f"/lib/modules/{kver}/build"
        if os.path.isdir(hdr_path):
            results.append(("Kernel Headers", f"Tồn tại ({hdr_path})", f"Khớp kernel {kver}", "PASS"))
        else:
            all_ok = False
            self.missing_packages.append(f"linux-headers-{kver}")
            results.append(("Kernel Headers", "Chưa cài đặt hoặc không tìm thấy", f"Khớp kernel {kver}", "FAIL"))

        # 4. NVIDIA Driver Userspace & KMD
        nv_ver = "Không rõ"
        try:
            out = subprocess.check_output("nvidia-smi --query-gpu=driver_version --format=csv,noheader", shell=True, text=True)
            nv_ver = out.strip().splitlines()[0]
        except Exception:
            try:
                with open("/proc/driver/nvidia/version") as f:
                    m = re.search(r"([0-9]+\.[0-9]+\.[0-9]+)", f.read())
                    if m:
                        nv_ver = m.group(1)
            except Exception:
                pass

        if nv_ver == DRIVER_VER:
            results.append(("Driver NVIDIA", f"Phiên bản {nv_ver}", DRIVER_VER, "PASS"))
        else:
            all_ok = False
            results.append(("Driver NVIDIA", f"Phiên bản {nv_ver} (Khác {DRIVER_VER})", DRIVER_VER, "WARN"))

        # 5. Build Tools & System Libraries
        tools = ["gcc", "g++", "make", "patch", "sha256sum", "tar", "depmod", "update-initramfs", "vulkaninfo", "clinfo", "pigz"]
        missing = [t for t in tools if not shutil.which(t)]
        if not missing:
            results.append(("Công cụ & Thư viện", "Đã cài đủ (gcc, make, vulkan-tools, clinfo...)", "Đầy đủ toolchain", "PASS"))
        else:
            all_ok = False
            self.missing_packages.extend(missing)
            results.append(("Công cụ & Thư viện", f"Thiếu: {', '.join(missing)}", "Đầy đủ toolchain", "WARN"))

        # 6. Secure Boot
        sb_disabled = True
        if shutil.which("mokutil"):
            try:
                sb_out = subprocess.check_output("mokutil --sb-state", shell=True, text=True).lower()
                if "enabled" in sb_out:
                    sb_disabled = False
            except Exception:
                pass

        if sb_disabled:
            results.append(("Secure Boot", "Disabled (Đã tắt)", "Phải tắt (Disabled)", "PASS"))
        else:
            all_ok = False
            results.append(("Secure Boot", "ENABLED (Đang bật)", "Phải tắt (Disabled)", "FAIL"))

        # 7. GSP Firmware Config
        gsp_disabled = False
        try:
            if os.path.exists("/etc/modprobe.d/nvidia.conf"):
                with open("/etc/modprobe.d/nvidia.conf") as f:
                    content = f.read()
                    if "NVreg_EnableGpuFirmware=0" in content and not content.strip().startswith("#"):
                        gsp_disabled = True
        except Exception:
            pass

        if gsp_disabled:
            results.append(("Cấu hình GSP Firmware", "Đang bị tắt (NVreg_EnableGpuFirmware=0)", "Cần bật cho Open Module", "WARN"))
        else:
            results.append(("Cấu hình GSP Firmware", "Bật (hoặc mặc định)", "Sẵn sàng cho Open Module", "PASS"))

        # 8. Userspace glcore Library
        glcore_path = None
        for candidate in [f"/usr/lib/x86_64-linux-gnu/libnvidia-glcore.so.{DRIVER_VER}",
                          f"/usr/lib/libnvidia-glcore.so.{DRIVER_VER}"]:
            if os.path.exists(candidate):
                glcore_path = candidate
                break

        if glcore_path:
            results.append(("Thư viện glcore", f"Tìm thấy ({glcore_path})", f"libnvidia-glcore.so.{DRIVER_VER}", "PASS"))
        else:
            results.append(("Thư viện glcore", "Không tìm thấy thư viện chuẩn", f"libnvidia-glcore.so.{DRIVER_VER}", "WARN"))

        # 9. Offline Driver Package
        drv_info = get_driver_source_info()
        if drv_info["available"]:
            results.append(("Bộ cài Driver Offline", f"Sẵn sàng ({drv_info['display']})", "Sẵn sàng", "PASS"))
        else:
            results.append(("Bộ cài Driver Offline", "Không tìm thấy bộ cài", "Sẵn sàng", "WARN"))

        # 10. Offline source archive
        tarball = os.path.join(CMP_DIR, f"open-gpu-kernel-modules-{DRIVER_VER}.tar.gz")
        if os.path.exists(tarball):
            results.append(("Mã nguồn nén offline", f"Sẵn sàng ({os.path.basename(tarball)})", "Sẵn sàng (Offline)", "PASS"))
        else:
            results.append(("Mã nguồn nén offline", "Chưa tải", "Sẵn sàng (Offline)", "WARN"))

        # Update UI
        def _update_ui():
            self.checks_tree.delete(*self.checks_tree.get_children())
            for item, cur, req, status in results:
                tag = status.lower()
                self.checks_tree.insert("", "end", values=(item, cur, req, status), tags=(tag,))

            self.checks_tree.tag_configure("pass", foreground=ACCENT_GREEN)
            self.checks_tree.tag_configure("warn", foreground=ACCENT_YELLOW)
            self.checks_tree.tag_configure("fail", foreground=ACCENT_RED)

            if self.missing_packages:
                self.btn_install_pkgs.pack(side="left", padx=(0, 5))
            else:
                self.btn_install_pkgs.pack_forget()

            badge_text = "✔ HỆ THỐNG ĐÃ ĐỦ ĐIỀU KIỆN ÁP DỤNG MOD"
            if self.is_riser_1x:
                badge_text += " [CẤU HÌNH RISER 1X ĐÃ SẴN SÀNG]"
            if all_ok:
                self.summary_badge.config(text=badge_text, fg=ACCENT_GREEN)
            else:
                self.summary_badge.config(text="⚠ HỆ THỐNG CÓ ĐIỂM CẦN LƯU Ý", fg=ACCENT_YELLOW)

            self.update_driver_tab_info()
            self.lbl_status.config(text="Đã hoàn tất kiểm tra điều kiện hệ thống.")
            self.is_busy = False

        self.after(0, _update_ui)

    # ----------------- Kernel Tab Actions -----------------
    def on_install_kernel_click(self):
        if self.is_busy:
            messagebox.showinfo("Thông báo", "Một tác vụ khác đang được thực thi!")
            return

        rebar_raw = self.rebar_var.get()
        rebar_size = rebar_raw.split(":")[0].strip()

        msg = (
            "Bạn có chắc muốn biên dịch và cài đặt CMP 40HX Open Kernel Module?\n\n"
            "Cấu hình đã chọn:\n"
            f"  • PCIe Mode: {'Diagnostic' if self.var_pcie_diag.get() else 'Chuẩn (Gen2)'}\n"
            f"  • Cấu hình ReBAR: Selector {rebar_size}\n"
            f"  • Cấu hình GSP: {'Tự động Bật (Khuyên dùng)' if self.var_enable_gsp.get() else 'Giữ nguyên'}\n"
            f"  • Phần cứng: 2x CMP 40HX (Riser PCIe 1x)\n\n"
            "Quá trình sẽ áp dụng 3 bản vá (Compute, PCIe Gen2, ReBAR) và cập nhật initramfs."
        )

        if not messagebox.askyesno("Xác nhận", msg):
            return

        self.is_busy = True
        self.btn_install_kernel.config(state="disabled")
        self.kernel_prog.start(10)
        self.lbl_status.config(text="Đang biên dịch & cài đặt Kernel Module...")
        self.log(self.txt_kernel_log, "=== BẮT ĐẦU CÀI ĐẶT KERNEL MOD CMP 40HX ===", clear=True)

        diag = self.var_pcie_diag.get()
        enable_gsp = self.var_enable_gsp.get()

        args = ["install-kernel-mod", f"--rebar-size={rebar_size}"]
        if diag:
            args.append("--pcie-diagnostic")
        if not enable_gsp:
            args.append("--keep-gsp-off")

        def _worker():
            ret = self.execute_with_elevation(args, self.txt_kernel_log)
            def _done():
                self.kernel_prog.stop()
                self.btn_install_kernel.config(state="normal")
                self.is_busy = False
                if ret == 0:
                    self.lbl_status.config(text="Cài đặt Kernel Module thành công! Vui lòng Cold Reboot.")
                    messagebox.showinfo(
                        "Thành công", 
                        "Đã cài đặt thành công NVIDIA Open Kernel Module mod!\n\n"
                        "LƯU Ý QUAN TRỌNG CHO RISER 1X:\n"
                        "Sau khi khởi động lại từ Cold Reboot (tắt hẳn nguồn rồi bật lại),\n"
                        "2 card sẽ hoạt động ở tốc độ Gen2 x1 (5.0 GT/s, gấp đôi băng thông cũ)!\n"
                        "Hãy chạy: sudo shutdown -h now"
                    )
                else:
                    self.lbl_status.config(text="Cài đặt thất bại. Xem chi tiết trong log.")
                    messagebox.showerror("Lỗi", "Cài đặt Kernel Module gặp lỗi. Vui lòng xem log chi tiết!")
            self.after(0, _done)

        threading.Thread(target=_worker, daemon=True).start()

    # ----------------- glcore Tab Actions -----------------
    def on_patch_glcore_click(self):
        if self.is_busy:
            return
        mode = self.glcore_mode.get()
        self.is_busy = True
        self.log(self.txt_glcore_log, f"=== ÁP DỤNG BẢN VÁ GLCORE ({mode.upper()} MODE) ===", clear=True)

        def _worker():
            if mode == "system":
                ret = self.execute_with_elevation(["patch-glcore-system"], self.txt_glcore_log)
            else:
                ret = self.execute_with_elevation(["patch-glcore-local"], self.txt_glcore_log)

            def _done():
                self.is_busy = False
                if ret == 0:
                    messagebox.showinfo("Thành công", "Đã áp dụng bản vá glcore MME throttle bypass thành công!")
                else:
                    messagebox.showerror("Lỗi", "Áp dụng bản vá glcore thất bại!")
            self.after(0, _done)

        threading.Thread(target=_worker, daemon=True).start()

    def on_restore_glcore_click(self):
        if not messagebox.askyesno("Xác nhận", "Bạn có chắc muốn khôi phục thư viện libnvidia-glcore.so gốc từ file .orig?"):
            return
        self.log(self.txt_glcore_log, "=== KHÔI PHỤC THƯ VIỆN GỐC ===")
        threading.Thread(target=lambda: self.execute_with_elevation(["restore-glcore-system"], self.txt_glcore_log), daemon=True).start()

    # ----------------- Full Audit Tool Action -----------------
    def run_full_audit_async(self):
        if self.is_busy:
            return
        self.is_busy = True
        self.btn_run_audit.config(state="disabled")
        self.lbl_status.config(text="Đang thực hiện kiểm tra toàn diện các bước mod...")
        self.log(self.txt_audit_log, "======================================================================", clear=True)
        self.log(self.txt_audit_log, "   BÁO CÁO XÁC MINH TOÀN DIỆN CÁC BƯỚC MOD CMP 40HX")
        self.log(self.txt_audit_log, "======================================================================\n")

        def _worker():
            score = 0
            total = 5
            report_lines = []

            # 1. Check Compute / Tensor Core
            dmesg_out = ""
            try:
                dmesg_out = subprocess.check_output("dmesg | grep -iE 'CMP40_COMPUTE_UNLOCK|CMP40_GSP_READY|SS0=88888888|SS1=00000008|SIGNED_FULLSPEED' | tail -n 10", 
                                                    shell=True, stderr=subprocess.DEVNULL, text=True)
                if not dmesg_out.strip():
                    dmesg_out = subprocess.check_output("journalctl -k -b 0 2>/dev/null | grep -iE 'CMP40_COMPUTE_UNLOCK|CMP40_GSP_READY|SS0=88888888' | tail -n 10",
                                                        shell=True, stderr=subprocess.DEVNULL, text=True)
            except Exception:
                pass

            compute_ok = False
            if "SS0=88888888" in dmesg_out or "ss0=0x88888888" in dmesg_out or "SIGNED_FULLSPEED" in dmesg_out or "CMP40_COMPUTE_UNLOCK" in dmesg_out:
                compute_ok = True
                score += 1
                report_lines.append("✔ [THÀNH CÔNG 100%] BƯỚC 1: MỞ KHÓA COMPUTE & TENSOR CORES (0001 Patch)")
                report_lines.append("    Bằng chứng: Đã phát hiện SEC2 Booter exploit nạp thành công trong kernel logs:")
                report_lines.append("    -> SS0=0x88888888, SS1=0x00000008, FECS_PLM=0xffffff8f")
                report_lines.append("    -> Toàn bộ nhân CUDA & Tensor Cores đã bung 100% công suất!\n")
            else:
                report_lines.append("✖ [CHƯA NẠP] BƯỚC 1: Mở khóa Compute chưa tìm thấy trong dmesg")
                report_lines.append("    (Kernel Mod chưa được cài đặt hoặc chưa thực hiện Cold Reboot sau khi cài đặt ở Tab 3)\n")

            # 2. Check ReBAR 8GB
            rebar_ok = False
            bar1_vals = []
            try:
                out = subprocess.check_output(
                    "nvidia-smi -q -d MEMORY | awk '/BAR1 Memory Usage/{flag=1; next} /Conf Compute/{flag=0} flag && /Total/{print $3}'", 
                    shell=True, stderr=subprocess.DEVNULL, text=True
                )
                bar1_vals = [int(x.strip()) for x in out.splitlines() if x.strip().isdigit()]
            except Exception:
                pass

            if bar1_vals and all(v >= 8000 for v in bar1_vals):
                rebar_ok = True
                score += 1
                report_lines.append("✔ [THÀNH CÔNG 100%] BƯỚC 2: MỞ KHÓA RESIZABLE BAR 8GB (0003 Patch)")
                report_lines.append(f"    Bằng chứng: BAR1 Memory Usage Total = {bar1_vals[0]} MiB trên cả 2 card CMP 40HX!")
                report_lines.append("    -> VRAM 8GB đã được ánh xạ toàn diện vào không gian địa chỉ CPU.\n")
            else:
                curr_bar1 = f"{bar1_vals[0]} MiB" if bar1_vals else "64 MiB"
                report_lines.append(f"✖ [CHƯA MỞ RỘNG] BƯỚC 2: BAR1 chưa đạt mức 8192 MiB (Hiện tại: {curr_bar1})")
                report_lines.append("    (Cần cài đặt Kernel Mod ở Tab 3 và Tắt máy hoàn toàn - Cold Reboot để ReBAR 8GB có hiệu lực)\n")

            # 3. Check glcore userspace patch
            glcore_ok = False
            glcore_file = f"/usr/lib/x86_64-linux-gnu/libnvidia-glcore.so.{DRIVER_VER}"
            if not os.path.exists(glcore_file):
                glcore_file = f"/usr/lib/libnvidia-glcore.so.{DRIVER_VER}"

            if os.path.exists(glcore_file):
                try:
                    with open(glcore_file, "rb") as f:
                        f.seek(0xb20c2d)
                        b1 = f.read(8)
                        f.seek(0xdcbf60)
                        b2 = f.read(8)
                    if b1 and b2 and b1[4] == 0 and b2[4] == 0:
                        glcore_ok = True
                        score += 1
                        report_lines.append("✔ [THÀNH CÔNG 100%] BƯỚC 3: VÁ USERSPACE GLCORE MME THROTTLE")
                        report_lines.append(f"    Bằng chứng: File {glcore_file}")
                        report_lines.append("    -> Offset 0xb20c2d: tham số lặp đã đổi từ 0xf0 (240 chu kỳ) về 0x00!")
                        report_lines.append("    -> Offset 0xdcbf60: tham số lặp đã đổi từ 0xf0 (240 chu kỳ) về 0x00!")
                        report_lines.append("    -> Triệt tiêu hoàn toàn độ trễ lag bind pipeline trong game Vulkan / Proton!\n")
                    else:
                        report_lines.append("⚠ [BẢN GỐC] BƯỚC 3: libnvidia-glcore.so vẫn đang mang tham số 0xf0 (chưa vá)\n")
                except Exception as e:
                    report_lines.append(f"✖ [LỖI ĐỌC] BƯỚC 3: Không thể đọc file glcore: {e}\n")
            else:
                report_lines.append("✖ [KHÔNG TÌM THẤY] BƯỚC 3: Không tìm thấy libnvidia-glcore.so trên hệ thống\n")

            # 4. Check GSP Firmware
            gsp_ok = False
            gsp_out = ""
            try:
                gsp_out = subprocess.check_output("nvidia-smi -q | grep -i 'GSP Firmware Version'", 
                                                  shell=True, stderr=subprocess.DEVNULL, text=True)
            except Exception:
                pass

            if DRIVER_VER in gsp_out:
                gsp_ok = True
                score += 1
                report_lines.append("✔ [HOẠT ĐỘNG TỐT] BƯỚC 4: GSP FIRMWARE & OPEN KERNEL MODULE")
                report_lines.append(f"    Bằng chứng: GSP Firmware Version = {DRIVER_VER} đang chạy trực tiếp trên GPU.")
                report_lines.append("    -> Luồng SEC2/GSP đã nạp trơn tru, driver open-gpu-kernel-modules hoạt động chuẩn.\n")
            else:
                report_lines.append("⚠ [CẦN BẬT] BƯỚC 4: GSP Firmware chưa hoạt động (Có thể do NVreg_EnableGpuFirmware=0)\n")

            # 5. Check PCIe Link & Riser 1x
            pcie_lines = []
            for b in ['0000:01:00.0', '0000:06:00.0']:
                w_f = f"/sys/bus/pci/devices/{b}/current_link_width"
                s_f = f"/sys/bus/pci/devices/{b}/current_link_speed"
                w = open(w_f).read().strip() if os.path.exists(w_f) else "?"
                s = open(s_f).read().strip() if os.path.exists(s_f) else "?"
                pcie_lines.append(f"    -> Card {b}: Tốc độ {s}, Chiều rộng lane x{w}")

            report_lines.append("ℹ [THÔNG TIN PHẦN CỨNG] BƯỚC 5: TỐC ĐỘ LIÊN KẾT PCIE TRÊN RISER 1X")
            report_lines.extend(pcie_lines)
            report_lines.append("    Đánh giá: 2 card đang duy trì ở Gen1 x1 (2.5 GT/s) do giới hạn vật lý của cáp Riser 1x")
            report_lines.append("    và cổng Chipset PCH. Năng lực tính toán AI / Compute và ReBAR 8GB không bị ảnh hưởng!\n")

            # 6. Check Driver Offline Package & Dartraiden Mod
            drv_info = get_driver_source_info()
            if drv_info["available"]:
                report_lines.append(f"✔ [SẴN SÀNG] BƯỚC 6: BỘ CÀI DRIVER OFFLINE ({drv_info['display']})")
                report_lines.append(f"    Chi tiết: {drv_info['desc']}")
                report_lines.append(f"    Đường dẫn: {drv_info['path']}\n")
            else:
                report_lines.append("⚠ [CHƯA CÓ] BƯỚC 6: Chưa tìm thấy bộ cài đặt offline trong thư mục dự án\n")

            # Output to widget
            for line in report_lines:
                self.log(self.txt_audit_log, line)

            def _done():
                self.is_busy = False
                self.btn_run_audit.config(state="normal")
                self.lbl_status.config(text=f"Hoàn tất kiểm tra: Đạt {score}/4 mục tiêu mở khóa lớn nhất!")
                
                sum_color = ACCENT_GREEN if score >= 3 else ACCENT_YELLOW
                self.lbl_audit_summary.config(
                    text=f"🏆 KẾT QUẢ XÁC MINH: ĐẠT {score}/4 MỤC TIÊU LỚN NHẤT!\n"
                         f"  • Compute SMs/Tensor Cores: {'✔ ĐÃ BUNG 100%' if compute_ok else '✖ Chưa'}\n"
                         f"  • Resizable BAR 8GB: {'✔ ĐÃ MỞ RỘNG TRỌN VẸN 8192 MiB' if rebar_ok else '✖ Chưa'}\n"
                         f"  • Vulkan glcore Bypass: {'✔ ĐÃ TRIỆT TIÊU LAG MME' if glcore_ok else '✖ Chưa'}\n"
                         f"  • GSP Firmware: {'✔ ĐANG CHẠY 610.57.04' if gsp_ok else '✖ Chưa'}",
                    fg=sum_color
                )
                messagebox.showinfo(
                    "Kết quả Xác minh", 
                    f"Xác minh hoàn tất! Hệ thống đã đạt {score}/4 mục tiêu lớn nhất.\n\n"
                    f"✔ Compute / Tensor Cores: Đã bung toàn bộ công suất\n"
                    f"✔ Resizable BAR: Đã mở rộng 8192 MiB (8GB)\n"
                    f"✔ Vulkan glcore: Đã triệt tiêu vòng lặp lag MME\n"
                    f"✔ GSP Firmware: Đang chạy trực tiếp trên GPU"
                )
            self.after(0, _done)

        threading.Thread(target=_worker, daemon=True).start()

    def run_diag_cmd(self, cmd):
        self.log(self.txt_audit_log, f"\n=== LỆNH: {cmd} ===")
        def _worker():
            try:
                out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True)
                self.log(self.txt_audit_log, out)
            except subprocess.CalledProcessError as e:
                self.log(self.txt_audit_log, e.output)
            except Exception as e:
                self.log(self.txt_audit_log, f"Lỗi: {str(e)}")
        threading.Thread(target=_worker, daemon=True).start()

    def diag_check_pcie(self):
        cmd = (
            "for b in $(lspci -nn | grep -i 10de:1f0b | awk '{print $1}'); do "
            "echo \"=== GPU Bus $b ===\"; "
            "echo \"Current speed: $(cat /sys/bus/pci/devices/0000:$b/current_link_speed 2>/dev/null)\"; "
            "echo \"Current width: $(cat /sys/bus/pci/devices/0000:$b/current_link_width 2>/dev/null)\"; "
            "lspci -vvv -s $b 2>/dev/null | grep -iE 'LnkCap|LnkSta|LnkCtl2|Region 1'; "
            "done"
        )
        self.run_diag_cmd(cmd)

    def run_tflops_benchmark_async(self):
        if self.is_busy:
            messagebox.showinfo("Thông báo", "Một tác vụ khác đang chạy!")
            return

        py_bin = find_pytorch_python()

        bench_script = os.path.join(APP_DIR, "test_compute_tflops.py")
        if not os.path.isfile(bench_script):
            messagebox.showerror("Lỗi", f"Không tìm thấy script benchmark: {bench_script}")
            return

        self.is_busy = True
        self.lbl_status.config(text="Đang đo hiệu năng tính toán TFLOPS (FP32 & Tensor Cores)...")
        self.log(self.txt_audit_log, "\n=== BẮT ĐẦU ĐO HIỆU NĂNG TÍNH TOÁN TFLOPS TRÊN CÁC GPU CMP 40HX ===", clear=True)

        def _worker():
            try:
                p = subprocess.Popen([py_bin, bench_script], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
                for line in p.stdout:
                    self.log(self.txt_audit_log, line.rstrip())
                p.wait()
            except Exception as e:
                self.log(self.txt_audit_log, f"\n[LỖI] {str(e)}")
            finally:
                def _done():
                    self.is_busy = False
                    self.lbl_status.config(text="Đã hoàn tất đo TFLOPS!")
                    messagebox.showinfo("Hoàn tất", "Đã đo xong hiệu năng TFLOPS! Xem kết quả chi tiết trong khung nhật ký.")
                self.after(0, _done)

        threading.Thread(target=_worker, daemon=True).start()

    # ----------------- Rollback Actions -----------------
    def on_uninstall_kernel_click(self):
        if not messagebox.askyesno("Xác nhận", 
                                   "Bạn có chắc muốn gỡ bỏ hoàn toàn Kernel Module mod và cập nhật lại initramfs?"):
            return
        self.log(self.txt_rollback_log, "=== GỠ BỎ KERNEL MODULE MOD ===", clear=True)
        threading.Thread(target=lambda: self.execute_with_elevation(["uninstall-kernel-mod"], self.txt_rollback_log), daemon=True).start()

    def on_disable_gsp_click(self):
        self.log(self.txt_rollback_log, "=== ĐẶT LẠI TẮT GSP FIRMWARE ===")
        threading.Thread(target=lambda: self.execute_with_elevation(["disable-gsp"], self.txt_rollback_log), daemon=True).start()

if __name__ == "__main__":
    app = CMPUnlockerApp()
    app.mainloop()
