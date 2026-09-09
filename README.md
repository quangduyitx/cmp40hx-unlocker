# NVIDIA CMP 40HX Unlocker & Optimizer Studio

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Release: v1.0.0](https://img.shields.io/badge/Release-v1.0.0-blue.svg)](https://github.com/quangduyitx/cmp40hx-unlocker/releases/tag/v1.0.0)
[![Platform: Linux](https://img.shields.io/badge/Platform-Linux%20(Mint%20%7C%20Ubuntu%20%7C%20Arch%20%7C%20Debian)-orange.svg)](https://kernel.org)
[![GPU: Turing TU106](https://img.shields.io/badge/Hardware-NVIDIA%20CMP%2040HX%20(TU106)-green.svg)](https://www.nvidia.com)
[![Status: Fully Verified](https://img.shields.io/badge/Status-100%25%20Verified%20on%20Hardware-brightgreen.svg)]()

> **Languages:** [English](README.md) • [Tiếng Việt](README_VI.md)

A comprehensive, fully automated graphical suite (GUI) and CLI toolchain designed to unlock the full computational potential, PCIe bandwidth, Resizable BAR, and gaming performance of **NVIDIA CMP 40HX (Turing TU106, `10de:1f0b`)** GPUs on Linux.

Based on groundbreaking research from **[Cyridd/cmpunlocker](https://github.com/Cyridd/cmpunlocker)** and the driver packaging workflow of **[dartraiden/NVIDIA-patcher](https://github.com/dartraiden/NVIDIA-patcher)**.

---

## 🚀 Verified Hardware Benchmark Results

The following numbers were verified on real hardware running dual CMP 40HX GPUs:

### 1. Compute & Tensor Core Unlock
| Workload / Benchmark | Stock / Locked | Unlocked (Cyridd) | **Verified on Live Dual 40HX** |
| :--- | :---: | :---: | :---: |
| **FP32 Compute GEMM** | ~0.39 TFLOPS *(throttled)* | **7.0 TFLOPS** | **7.15 - 7.32 TFLOPS** *(18.3× boost)* |
| **FP16 cuBLAS (CUDA Cores)** | ~0.39 TFLOPS *(throttled)* | **11.42 TFLOPS** | **24.5 - 24.7 TFLOPS** *(63.5× boost)* |
| **FP16 Tensor Core MMA** | **Unavailable** *(hardware PLM locked)* | **63.8 TFLOPS** | **47.5 - 63.8 TFLOPS** *(Fully Active)* |

### 2. PCIe Link & Bandwidth
| Metric | Stock State | Unlocked State |
| :--- | :---: | :---: |
| **PCIe Link Speed (Direct CPU slot)** | Gen1 (2.5 GT/s) | **Gen2 (5.0 GT/s)** *(Real trained link)* |
| **PCIe Width** | x16 (Direct slot) / x1 (Riser) | **x16** (or max physical lane limit) |
| **FurMark OpenGL / Vulkan** | ~110 FPS | **~122 - 134 FPS** |

### 3. Resizable BAR Memory Aperture
| Metric | Stock State | Unlocked State |
| :--- | :---: | :---: |
| **Kernel / `lspci` BAR 1** | 64 MB / 256 MB | **8192 MiB (8 GiB)** |
| **`nvidia-smi` BAR1 Usage Total** | 64 MiB | **8192 MiB** *(Full VRAM CPU-mapped)* |

### 4. Vulkan Pipeline Throttle Bypass (`libnvidia-glcore.so`)
| Benchmark | Stock (`0xf0` loops) | Patched (`0x00` loops) | Speedup |
| :--- | :---: | :---: | :---: |
| **4 Pipeline Binds** | ~0.739 ms | **~0.0024 ms** | **~300× faster** |
| **1,000 Pipeline Binds** | ~183.3 ms | **~0.77 ms** | **~238× faster** |

---

## 🌟 Key Features

1. **Compute SM Issue-Rate & Tensor Core Restore (`0001` patch):**
   - Injects a privileged payload into the standard GSP SEC2 Booter execution flow.
   - Restores the privileged state: `SS0 = 0x88888888`, `SS1 = 0x00000008`, `FECS_PLM = 0xFFFFFF8F`.
   - Restores 100% compute issue rate and activates all Turing Tensor Cores.

2. **PCIe Gen2 x16 Link Retrain (`0002` patch):**
   - Overrides default factory Gen1 lock via protected GSP/RM PCIe policy.
   - Triggers genuine host-side Link Retrain (`LnkSta: Speed 5GT/s`).

3. **8GB Resizable BAR Aperture Expansion (`0003` patch):**
   - Programs XVE registers to expose full 8192 MiB BAR1 aperture.
   - Configurable selectors: 8GB, 4GB, 2GB, or 0 (off).

4. **Vulkan Pipeline-Bind / MME Throttle Bypass (`patch_glcore`):**
   - Eliminates macro 52 (`PIPE_NOP` + `WAIT_FOR_IDLE`) 240 delay loops inside `libnvidia-glcore.so.610.57.04`.
   - Cures severe micro-stuttering in DXVK, VKD3D-Proton, and native Vulkan titles.

5. **Multi-GPU & Hybrid Display Safe:**
   - Seamlessly integrates with headless setups and dual-GPU configurations (e.g. AMD Vega / Intel display card + NVIDIA CMP 40HX compute card).
   - Preserves system Mesa OpenGL via `--no-opengl-files`.
   - Non-interactive installer overrides (`--no-x-check`, `--allow-installation-with-running-driver`).

6. **Modern GUI & 1-Click Verification Suite:**
   - Tkinter dark-theme GUI orchestrator.
   - Automated prerequisite scanning and missing package installer.
   - 1-Click System Audit tool verifying `dmesg`, `nvidia-smi`, `glcore`, and sysfs PCIe.
   - Built-in live TFLOPS compute and Tensor Core benchmark tool.

---

## 📂 Repository Structure

The repository is structured to remain lightweight (< 2MB) by excluding heavy binary archives:

```text
cmp-40hx-unlocker/
├── gui.py                      # Main Tkinter dark GUI orchestrator
├── run_gui.sh                  # GUI launch wrapper
├── apply_mod_backend.sh        # Privileged root backend script (pkexec)
├── test_compute_native.sh      # Native C++ compute & VRAM benchmark (clpeak, no Python)
├── test_compute_tflops.py      # Real-time TFLOPS & Tensor Core benchmark (PyTorch)
├── setup_resources.sh          # One-click resource downloader & extractor
├── install_desktop.sh          # Desktop & App Menu icon installer
├── bin/                        # Standalone native benchmark binaries
│   └── clpeak                  # Lightweight OpenCL peak compute profiler (123KB)
├── cmpunlocker/                # Cyridd kernel patches & glcore patcher
│   ├── 0001-cmp40hx-unlock.patch
│   ├── 0002-cmp40hx-pcie2-unlock.patch
│   ├── 0003-cmp40hx-rebar-unlock.patch
│   ├── cmp_glcore_patch/
│   └── install.sh
├── LICENSE                     # MIT License
├── README.md                   # English documentation
└── README_VI.md                # Vietnamese documentation
```

---

## ⚡ Quick Start

### 1. Clone & Setup Resources
```bash
git clone https://github.com/quangduyitx/cmp40hx-unlocker.git
cd cmp-40hx-unlocker

# Download & prepare required NVIDIA driver & kernel modules
./setup_resources.sh
```

### 2. Launch the GUI
```bash
./run_gui.sh
```
*(Optional: Run `./install_desktop.sh` to add the app to your desktop and application menu).*

---

## 📖 Step-by-Step Installation Guide

### Step 1: Pre-checks & Dependency Installation (Tab 1)
- Open **Tab 1: Kiểm tra điều kiện (Prerequisites)**.
- Verify that your GPUs are detected (`10de:1f0b`).
- If any build tools or headers are missing, click **"📦 Cài đặt gói còn thiếu"** to install them automatically via `apt-get`.

### Step 2: Driver Installation (Tab 2)
- Open **Tab 2: Cài đặt Driver 40HX**.
- The app points to `NVIDIA-Linux-x86_64-610.57.04/nvidia-installer`.
- Keep **"Không ghi đè thư viện OpenGL (--no-opengl-files)"** checked if you use an AMD or Intel card for display output.
- Click **"🚀 Bắt đầu Cài đặt Driver NVIDIA 610.57.04"**.

### Step 3: Open Kernel Module Unlock (Tab 3)
- Open **Tab 3: Mở khóa Kernel**.
- Select desired Resizable BAR size (Default: **8 GiB - Khuyên dùng**).
- Keep **"Tự động bật GSP Firmware"** checked (required for SEC2 booter exploits).
- Click **"🚀 Bắt đầu Biên dịch & Cài đặt Kernel Mod"**.

### Step 4: Vulkan glcore Patching (Tab 4)
- Open **Tab 4: Vá Vulkan glcore**.
- Select **"Áp dụng cho toàn hệ thống"** (creates automatic `.orig` backup).
- Click **"⚡ Áp dụng Bản vá glcore"**.

### Step 5: Cold Reboot (MANDATORY)
> [!IMPORTANT]
> A warm reboot (`sudo reboot`) is **NOT** sufficient to re-initialize hardware PLM and PCIe link negotiation. You **MUST** shut down the system completely:
> ```bash
> sudo shutdown -h now
> ```
> Wait 10 seconds after fans stop, then turn power back on.

### Step 6: Verify & Benchmark (Tab 5)
- After boot, open **Tab 5: Xác minh & Chẩn đoán**.
- Click **"⚡ CHẠY KIỂM TRA TOÀN DIỆN CÁC BƯỚC MOD (1-Click Audit)"** to confirm all 5 unlock steps.
- Click **"🔥 Đo TFLOPS (Compute & Tensor)"** to benchmark live FP32 and Tensor Core speed!

---

## 🛠️ Hardware Notes & Troubleshooting

### PCIe Riser 1x Notes
- When cards are connected via USB PCIe 1x mining risers, physical lane width is locked to `x1`.
- If connected to Motherboard PCH Chipset ports (e.g. `00:1c.0`), maximum hardware link speed may be capped at Gen1 (2.5 GT/s). The kernel may log:
  ```text
  [CMP40_PCIE2] RETRAIN_FAIL status=1011
  ```
  This is normal and safe; Compute, Tensor Cores, and 8GB ReBAR operate at 100% capacity regardless of PCIe lane width.
- To achieve Gen2 x1 (5.0 GT/s, ~400 MB/s), connect the riser to a CPU-direct PCIe port.

### Multi-GPU Dual Card Environments
- When combining an AMD card for display and CMP 40HX for compute, **always** ensure `nvidia.NVreg_EnableGpuFirmware=0` is **NOT** present in `/etc/default/grub` or `/etc/modprobe.d/`.

---

## 📜 Credits & Acknowledgments

This project builds upon the work of exceptional researchers and engineers:

1. **[Cyridd](https://github.com/Cyridd)** - Author of [Cyridd/cmpunlocker](https://github.com/Cyridd/cmpunlocker):
   - SEC2 Booter exploit discovery & SM/Tensor Core restore implementation.
   - PCIe Gen2 link retrain technique.
   - Resizable BAR 8GB aperture patch.
   - Reverse-engineering the userspace Vulkan macro 52 pipeline delay.
2. **[dartraiden](https://github.com/dartraiden)** - Author of [dartraiden/NVIDIA-patcher](https://github.com/dartraiden/NVIDIA-patcher):
   - Extracted package patcher workflow and `nvidia-installer` methodology.
3. **[NVIDIA Corporation](https://github.com/NVIDIA)**:
   - For providing the open-source `open-gpu-kernel-modules`.

---

## ⚖️ License

This project is licensed under the [MIT License](LICENSE).
Kernel module patches interact with NVIDIA Open GPU Kernel Modules under dual MIT/GPLv2 license.
