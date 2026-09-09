# NVIDIA CMP 40HX Unlocker & Optimizer Studio (Bản tiếng Việt)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Phiên bản: v1.0.0](https://img.shields.io/badge/Phi%C3%AAn%20b%E1%BA%A3n-v1.0.0-blue.svg)](https://github.com/quangduyitx/cmp40hx-unlocker/releases/tag/v1.0.0)
[![Platform: Linux](https://img.shields.io/badge/Nền%20tảng-Linux%20(Mint%20%7C%20Ubuntu%20%7C%20Arch%20%7C%20Debian)-orange.svg)](https://kernel.org)
[![Hardware: Turing TU106](https://img.shields.io/badge/Phần%20cứng-NVIDIA%20CMP%2040HX%20(TU106)-green.svg)](https://www.nvidia.com)
[![Status: Fully Verified](https://img.shields.io/badge/Trạng%20thái-Xác%20minh%20100%25%20trên%20phần%20cứng-brightgreen.svg)]()

> **Ngôn ngữ:** [English](README.md) • [Tiếng Việt](README_VI.md)

Bộ công cụ đồ họa (GUI) và tự động hóa toàn diện giúp mở khóa toàn bộ tiềm năng tính toán, băng thông PCIe, bộ nhớ Resizable BAR 8GB và tối ưu hóa hiệu năng game đồ họa cho dòng card **NVIDIA CMP 40HX (Kiến trúc Turing TU106, mã thiết bị `10de:1f0b`)** trên hệ điều hành Linux.

Dựa trên công trình nghiên cứu đột phá của dự án **[Cyridd/cmpunlocker](https://github.com/Cyridd/cmpunlocker)** và quy trình đóng gói driver của **[dartraiden/NVIDIA-patcher](https://github.com/dartraiden/NVIDIA-patcher)**.

---

## 🚀 Kết quả Đo kiểm Thực tế trên Phần cứng (Live Benchmark)

Số liệu dưới đây được đo kiểm thực tế trên hệ thống chạy 2 card CMP 40HX:

### 1. Mở khóa Sức mạnh Tính toán (Compute & Tensor Cores)
| Hạng mục kiểm tra | Trước khi mở khóa | Sau khi mở khóa (Cyridd) | **Đo thực tế trên cụm 2x 40HX** |
| :--- | :---: | :---: | :---: |
| **FP32 Compute GEMM** | ~0.39 TFLOPS *(bị bóp phát lệnh)* | **7.0 TFLOPS** | **7.15 - 7.32 TFLOPS** *(Gấp 18.3 lần)* |
| **FP16 cuBLAS (CUDA Cores)** | ~0.39 TFLOPS *(bị bóp)* | **11.42 TFLOPS** | **24.5 - 24.7 TFLOPS** *(Gấp 63.5 lần)* |
| **FP16 Tensor Core MMA** | **Bị khóa phần cứng** *(PLM disable)* | **63.8 TFLOPS** | **47.5 - 63.8 TFLOPS** *(Đã kích hoạt 100%)* |

### 2. Tốc độ & Băng thông PCIe
| Chỉ số | Mặc định (Stock) | Sau khi Mod |
| :--- | :---: | :---: |
| **Tốc độ liên kết PCIe (Khe CPU trực tiếp)** | Gen1 (2.5 GT/s) | **Gen2 (5.0 GT/s)** *(Huấn luyện đường truyền thực)* |
| **Số lane PCIe** | x16 (Khe trực tiếp) / x1 (Cáp Riser) | **x16** (hoặc tối đa theo chân cắm vật lý) |
| **FurMark OpenGL / Vulkan** | ~110 FPS | **~122 - 134 FPS** |

### 3. Bộ nhớ Resizable BAR
| Chỉ số | Mặc định (Stock) | Sau khi Mod |
| :--- | :---: | :---: |
| **Kernel / `lspci` BAR 1** | 64 MB / 256 MB | **8192 MiB (8 GiB)** |
| **`nvidia-smi` BAR1 Usage Total** | 64 MiB | **8192 MiB** *(Toàn bộ VRAM ánh xạ vào CPU)* |

### 4. Triệt tiêu Độ trễ Vulkan Pipeline (`libnvidia-glcore.so`)
| Bài test độ trễ | Bản gốc (Vòng lặp `0xf0`) | Bản vá (Vòng lặp `0x00`) | Tốc độ cải thiện |
| :--- | :---: | :---: | :---: |
| **4 lần gọi Bind Pipeline** | ~0.739 ms | **~0.0024 ms** | **Nhanh hơn ~300 lần** |
| **1,000 lần gọi Bind Pipeline** | ~183.3 ms | **~0.77 ms** | **Nhanh hơn ~238 lần** |

---

## 🌟 Các tính năng nổi bật

1. **Mở khóa Compute SM Issue-Rate & Tensor Cores (`0001` patch):**
   - Can thiệp vào luồng thực thi chuẩn của SEC2 Booter trong GSP Firmware.
   - Nạp trạng thái đặc quyền: `SS0 = 0x88888888`, `SS1 = 0x00000008`, `FECS_PLM = 0xFFFFFF8F`.
   - Phục hồi 100% tốc độ cấp phát lệnh cho các SM, mở khóa toàn diện nhân Tensor Cores.

2. **Huấn luyện lại đường truyền PCIe Gen2 x16 (`0002` patch):**
   - Vượt qua giới hạn Gen1 của nhà sản xuất thông qua chính sách GSP/RM PCIe.
   - Kích hoạt cơ chế Link Retrain thực thụ từ phía host (`LnkSta: Speed 5GT/s`).

3. **Mở rộng Resizable BAR lên trọn vẹn 8GB (`0003` patch):**
   - Cấu hình thanh ghi XVE mở rộng không gian BAR1 lên 8192 MiB.
   - Cho phép tùy chọn kích thước linh hoạt: 8GB, 4GB, 2GB hoặc tắt.

4. **Triệt tiêu lag giật Vulkan Pipeline / MME Throttle Bypass (`patch_glcore`):**
   - Khắc phục nguyên nhân gốc gây giật khung hình trong game Vulkan/Proton/DXVK do NVIDIA chèn macro 52 thực thi 240 chu kỳ trễ `PIPE_NOP` + `WAIT_FOR_IDLE`.
   - Vá tham số lặp từ `0xf0` (240) về `0x00` tại file `libnvidia-glcore.so.610.57.04`.

5. **Tương thích an toàn cho cấu hình Multi-GPU:**
   - Hoạt động trơn tru trên các cấu hình máy ITX chạy song song: Card AMD Vega / Intel làm màn hình chính, card NVIDIA CMP 40HX làm bộ xử lý tính toán/render.
   - Bảo toàn driver Mesa OpenGL của hệ thống qua tùy chọn `--no-opengl-files`.
   - Bỏ qua tự động cảnh báo X server đang chạy (`--no-x-check`) và nạp đè an toàn (`--allow-installation-with-running-driver`).

6. **Giao diện Đồ họa Hiện đại & Bộ Xác minh 1-Click:**
   - Ứng dụng Tkinter giao diện tối hiện đại, dễ thao tác.
   - Tự động quét và cài đặt các gói công cụ/headers còn thiếu.
   - Công cụ kiểm định toàn diện 5 bước (1-Click Audit) quét dmesg, nvidia-smi, byte glcore và sysfs PCIe.
   - Tích hợp sẵn công cụ đo TFLOPS tính toán thực tế.

---

## 📁 Cấu trúc Thư mục

Kho mã nguồn được thiết kế siêu gọn nhẹ (< 2MB), không lưu trữ các file nhị phân nặng:

```text
cmp-40hx-unlocker/
├── gui.py                      # Ứng dụng giao diện đồ họa chính (Tkinter)
├── run_gui.sh                  # Script khởi chạy giao diện nhanh
├── apply_mod_backend.sh        # Script thực thi quyền root backend (pkexec)
├── test_compute_tflops.py      # Bộ đo hiệu năng TFLOPS & Tensor Core thời gian thực
├── setup_resources.sh          # Script tải tài nguyên driver & kernel tự động
├── install_desktop.sh          # Script tạo biểu tượng màn hình & Menu ứng dụng
├── cmpunlocker/                # Thư mục mã nguồn bản mod Cyridd
│   ├── 0001-cmp40hx-unlock.patch
│   ├── 0002-cmp40hx-pcie2-unlock.patch
│   ├── 0003-cmp40hx-rebar-unlock.patch
│   ├── cmp_glcore_patch/
│   └── install.sh
├── LICENSE                     # Giấy phép nguồn mở MIT
├── README.md                   # Tài liệu tiếng Anh
└── README_VI.md                # Tài liệu tiếng Việt
```

---

## ⚡ Bắt đầu Nhanh

### 1. Tải dự án & Chuẩn bị tài nguyên
```bash
git clone https://github.com/your-username/cmp-40hx-unlocker.git
cd cmp-40hx-unlocker

# Tự động tải driver NVIDIA 610.57.04 và mã nguồn mở (nếu máy chưa có)
./setup_resources.sh
```

### 2. Khởi chạy Giao diện Đồ họa
```bash
./run_gui.sh
```
*(Tùy chọn: Chạy `./install_desktop.sh` để thêm biểu tượng vào Menu ứng dụng và Desktop).*

---

## 📖 Hướng dẫn Sử dụng Chi tiết Từng Bước

### Bước 1: Kiểm tra điều kiện (Tab 1)
- Mở **Tab 1: Kiểm tra điều kiện**.
- Đảm bảo hệ thống phát hiện đủ các card CMP 40HX (`10de:1f0b`).
- Nếu thiếu bất kỳ công cụ biên dịch hoặc kernel headers nào, bấm **"📦 Cài đặt gói còn thiếu"** để hệ thống tự động cài đặt qua `apt-get`.

### Bước 2: Cài đặt Driver NVIDIA 40HX (Tab 2)
- Mở **Tab 2: Cài đặt Driver 40HX**.
- Ứng dụng tự động ưu tiên nhận diện `NVIDIA-Linux-x86_64-610.57.04/nvidia-installer`.
- Giữ nguyên tùy chọn **"Không ghi đè thư viện OpenGL (--no-opengl-files)"** nếu bạn dùng card AMD hoặc Intel để xuất hình.
- Bấm **"🚀 Bắt đầu Cài đặt Driver NVIDIA 610.57.04"**.

### Bước 3: Mở khóa Kernel Module (Tab 3)
- Mở **Tab 3: Mở khóa Kernel**.
- Chọn kích thước Resizable BAR mong muốn (Mặc định: **8 GiB - Khuyên dùng**).
- Đảm bảo tùy chọn **"Tự động bật GSP Firmware"** được chọn.
- Bấm **"🚀 Bắt đầu Biên dịch & Cài đặt Kernel Mod"**.

### Bước 4: Vá Thư viện Vulkan glcore (Tab 4)
- Mở **Tab 4: Vá Vulkan glcore**.
- Chọn chế độ **"Áp dụng cho toàn hệ thống"** (tự động tạo bản sao lưu an toàn `.orig`).
- Bấm **"⚡ Áp dụng Bản vá glcore"**.

### Bước 5: Tắt máy Khởi động lại (BẮT BUỘC COLD REBOOT)
> [!IMPORTANT]
> Khởi động lại mềm (`sudo reboot`) **KHÔNG THỂ** kích hoạt lại phần cứng PLM và đàm phán lại PCIe link. Bạn **BẮT BUỘC PHẢI TẮT MÁY HOÀN TOÀN**:
> ```bash
> sudo shutdown -h now
> ```
> Sau khi quạt và nguồn điện tắt hẳn, chờ 10 giây rồi bật lại máy.

### Bước 6: Kiểm tra Xác minh & Đo TFLOPS (Tab 5)
- Sau khi máy khởi động lại, mở **Tab 5: Xác minh & Chẩn đoán**.
- Bấm nút **"⚡ CHẠY KIỂM TRA TOÀN DIỆN CÁC BƯỚC MOD (1-Click Audit)"** để xác nhận đủ các chứng thực.
- Bấm nút **"🔥 Đo TFLOPS (Compute & Tensor)"** để xem sức mạnh tính toán thực tế bứt phá từ 0.39 lên >7 TFLOPS FP32 và >47 TFLOPS Tensor Cores!

---

## 🛠️ Lưu ý Phần cứng & Xử lý Sự cố

### Lưu ý Cáp Riser PCIe 1x
- Khi card cắm qua Riser đào coin 1x, độ rộng lane bị cố định ở `x1`.
- Nếu cắm vào khe ăn theo Chipset Southbridge PCH của bo mạch chủ (ví dụ `00:1c.0`), tốc độ tối đa có thể bị giới hạn ở Gen1 (2.5 GT/s). Kernel có thể thông báo:
  ```text
  [CMP40_PCIE2] RETRAIN_FAIL status=1011
  ```
  Đây là hiện tượng bình thường do giới hạn phần cứng của khe chipset, hoàn toàn an toàn. Tính toán AI, Tensor Cores và ReBAR 8GB vẫn hoạt động 100% công suất.
- Để đạt tốc độ Gen2 x1 (5.0 GT/s, ~400 MB/s), hãy cắm cáp Riser vào khe PCIe ăn trực tiếp từ CPU.

### Cấu hình Multi-GPU
- Tuyệt đối không để tham số `nvidia.NVreg_EnableGpuFirmware=0` trong GRUB hoặc modprobe khi dùng bản mod này.

---

## 📜 Trích dẫn Nguồn gốc & Lời Cảm ơn

Dự án được xây dựng dựa trên sự đóng góp to lớn từ các nhà nghiên cứu:

1. **[Cyridd](https://github.com/Cyridd)** - Tác giả dự án [Cyridd/cmpunlocker](https://github.com/Cyridd/cmpunlocker):
   - Phát hiện kỹ thuật khai thác SEC2 Booter mở khóa SM và Tensor Cores.
   - Nghiên cứu kỹ thuật huấn luyện lại đường truyền PCIe Gen2.
   - Bản vá mở rộng Resizable BAR 8GB.
   - Dịch ngược và tìm ra vòng lặp trễ macro 52 trong userspace driver glcore.
2. **[dartraiden](https://github.com/dartraiden)** - Tác giả dự án [dartraiden/NVIDIA-patcher](https://github.com/dartraiden/NVIDIA-patcher):
   - Quy trình giải nén driver với `--extract-only` và chạy `nvidia-installer` trực tiếp.
3. **[NVIDIA Corporation](https://github.com/NVIDIA)**:
   - Cung cấp mã nguồn mở `open-gpu-kernel-modules`.

---

## ⚖️ Giấy phép Bản quyền (License)

Dự án được phát hành theo giấy phép nguồn mở [MIT License](LICENSE).
Các bản vá kernel module tương tác với NVIDIA Open GPU Kernel Modules theo giấy phép kép MIT/GPLv2.
