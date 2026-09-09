#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CMP 40HX TFLOPS Compute & Tensor Core Benchmark
Kiểm tra hiệu năng thực tế sau khi áp dụng bản mod Cyridd:
- FP32 Compute Benchmark (Mục tiêu: ~7.0 - 7.3 TFLOPS, Trước mod: ~0.39 TFLOPS)
- FP16 cuBLAS Benchmark (Mục tiêu: ~11.4 - 14.0 TFLOPS, Trước mod: ~0.39 TFLOPS)
- FP16 Tensor Core MMA Benchmark (Mục tiêu: ~48.0 - 63.8 TFLOPS, Trước mod: Bị khóa)
"""

import os
import sys
import time

def run_benchmark():
    try:
        import torch
    except ImportError:
        # Tự động tìm kiếm môi trường venv có sẵn PyTorch CUDA (ví dụ: ~/lada/.venv)
        candidates = [
            os.path.expanduser("~/lada/.venv/bin/python"),
            os.path.expanduser("~/.venv/bin/python"),
            os.path.expanduser("~/pytorch-gfx906/.venv/bin/python")
        ]
        for venv_py in candidates:
            if os.path.isfile(venv_py) and os.access(venv_py, os.X_OK):
                try:
                    out = os.popen(f"'{venv_py}' -c 'import torch; print(torch.cuda.is_available())'").read().strip()
                    if out == "True":
                        os.execv(venv_py, [venv_py] + sys.argv)
                except Exception:
                    pass

        print("[LỖI / ERROR] PyTorch chưa được cài đặt trong môi trường Python hiện tại.")
        print("Gợi ý / Tip: Hãy chạy bằng môi trường Python có PyTorch CUDA, ví dụ:")
        print("  <path-to-venv>/bin/python " + sys.argv[0])
        print("  hoặc cài đặt: pip install torch --index-url https://download.pytorch.org/whl/cu124")
        sys.exit(1)

    if not torch.cuda.is_available():
        print("[LỖI] Không tìm thấy CUDA khả dụng cho PyTorch!")
        sys.exit(1)

    gpu_count = torch.cuda.device_count()
    print("=" * 72)
    print("           BỘ ĐO HIỆU NĂNG TÍNH TOÁN NVIDIA CMP 40HX (TFLOPS)")
    print("=" * 72)
    print(f"Phiên bản PyTorch: {torch.__version__}")
    print(f"Số lượng GPU NVIDIA phát hiện: {gpu_count}\n")

    results_summary = []

    for dev_idx in range(gpu_count):
        dev = torch.device(f"cuda:{dev_idx}")
        dev_name = torch.cuda.get_device_name(dev_idx)
        print(f"------------------------------------------------------------------------")
        print(f"  Đang đo kiểm tra GPU {dev_idx}: {dev_name}")
        print(f"------------------------------------------------------------------------")

        # ---------------- 1. FP32 Compute Benchmark ----------------
        # GEMM N=4096 (2 * N^3 FLOPs)
        N_fp32 = 4096
        A_f32 = torch.randn(N_fp32, N_fp32, dtype=torch.float32, device=dev)
        B_f32 = torch.randn(N_fp32, N_fp32, dtype=torch.float32, device=dev)
        
        # Warmup
        for _ in range(5):
            _ = torch.matmul(A_f32, B_f32)
        torch.cuda.synchronize(dev)

        iters = 20
        t0 = time.perf_counter()
        for _ in range(iters):
            _ = torch.matmul(A_f32, B_f32)
        torch.cuda.synchronize(dev)
        t_fp32 = (time.perf_counter() - t0) / iters
        tflops_fp32 = (2 * (N_fp32 ** 3) / t_fp32) / 1e12

        del A_f32, B_f32
        torch.cuda.empty_cache()

        # ---------------- 2. FP16 cuBLAS (CUDA Cores) Benchmark ----------------
        # Dùng ma trận kích thước lẻ để ép tính toán trên FP16 CUDA Cores thông thường
        N_fp16 = 4095
        A_f16 = torch.randn(N_fp16, N_fp16, dtype=torch.float16, device=dev)
        B_f16 = torch.randn(N_fp16, N_fp16, dtype=torch.float16, device=dev)

        for _ in range(5):
            _ = torch.matmul(A_f16, B_f16)
        torch.cuda.synchronize(dev)

        t0 = time.perf_counter()
        for _ in range(25):
            _ = torch.matmul(A_f16, B_f16)
        torch.cuda.synchronize(dev)
        t_fp16 = (time.perf_counter() - t0) / 25
        tflops_fp16 = (2 * (N_fp16 ** 3) / t_fp16) / 1e12

        del A_f16, B_f16
        torch.cuda.empty_cache()

        # ---------------- 3. FP16 Tensor Core MMA Benchmark ----------------
        # GEMM N=8192 kích hoạt tối đa các nhân Turing Tensor Cores (HMMA)
        N_tc = 8192
        A_tc = torch.randn(N_tc, N_tc, dtype=torch.float16, device=dev)
        B_tc = torch.randn(N_tc, N_tc, dtype=torch.float16, device=dev)

        for _ in range(5):
            _ = torch.matmul(A_tc, B_tc)
        torch.cuda.synchronize(dev)

        t0 = time.perf_counter()
        for _ in range(25):
            _ = torch.matmul(A_tc, B_tc)
        torch.cuda.synchronize(dev)
        t_tc = (time.perf_counter() - t0) / 25
        tflops_tc = (2 * (N_tc ** 3) / t_tc) / 1e12

        del A_tc, B_tc
        torch.cuda.empty_cache()

        print(f"  • FP32 Compute Benchmark        : {tflops_fp32:6.2f} TFLOPS  [Trước mod: ~0.39 TFLOPS | Mục tiêu: ~7.0 TFLOPS]")
        print(f"  • FP16 cuBLAS (CUDA Cores)      : {tflops_fp16:6.2f} TFLOPS  [Trước mod: ~0.39 TFLOPS | Mục tiêu: ~11.4 TFLOPS]")
        print(f"  • FP16 Tensor Core MMA Benchmark: {tflops_tc:6.2f} TFLOPS  [Trước mod: Bị khóa      | Mục tiêu: 48 - 64 TFLOPS]")

        status_fp32 = "PASS (BUNG 100%)" if tflops_fp32 >= 5.0 else "FAIL (Bị bóp)"
        status_tc = "PASS (BUNG 100%)" if tflops_tc >= 35.0 else "FAIL (Bị khóa)"
        print(f"  => Đánh giá: FP32 [{status_fp32}], Tensor Cores [{status_tc}]\n")

        results_summary.append((dev_idx, dev_name, tflops_fp32, tflops_fp16, tflops_tc))

    print("=" * 72)
    print("                       BẢNG TỔNG KẾT SO SÁNH")
    print("=" * 72)
    print(f"{'Hạng mục kiểm tra':<30} | {'Trước khi mở khóa':<18} | {'Kết quả thực tế':<16}")
    print("-" * 72)
    for dev_idx, dev_name, f32, f16, tc in results_summary:
        print(f"[GPU {dev_idx}] FP32 Compute          | ~0.39 TFLOPS        | {f32:6.2f} TFLOPS (Gấp {f32/0.39:4.1f}x)")
        print(f"[GPU {dev_idx}] FP16 cuBLAS           | ~0.39 TFLOPS        | {f16:6.2f} TFLOPS (Gấp {f16/0.39:4.1f}x)")
        print(f"[GPU {dev_idx}] FP16 Tensor Core MMA  | Bị vô hiệu hóa      | {tc:6.2f} TFLOPS (Đã bung)")
        print("-" * 72)

if __name__ == "__main__":
    run_benchmark()
