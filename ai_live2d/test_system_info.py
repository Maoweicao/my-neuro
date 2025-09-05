#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试系统信息获取功能
"""

import sys
import os
import platform
import subprocess

def test_system_info():
    """测试系统信息获取"""
    print("=== 测试系统信息获取功能 ===\n")
    
    try:
        import psutil
        HAS_PSUTIL = True
        print("✓ psutil 库已安装")
    except ImportError:
        HAS_PSUTIL = False
        print("✗ psutil 库未安装")
    
    print(f"\n=== 基本系统信息 ===")
    print(f"操作系统: {platform.system()} {platform.release()}")
    print(f"计算机名: {platform.node()}")
    print(f"处理器: {platform.processor()}")
    print(f"架构: {platform.machine()}")
    print(f"Python版本: {platform.python_version()}")
    
    # 测试CPU信息
    print(f"\n=== CPU信息 ===")
    if HAS_PSUTIL:
        try:
            print(f"物理核心数: {psutil.cpu_count(logical=False)}")
            print(f"逻辑核心数: {psutil.cpu_count(logical=True)}")
            cpu_freq = psutil.cpu_freq()
            if cpu_freq:
                print(f"CPU频率: {cpu_freq.current:.2f} MHz")
            print(f"CPU使用率: {psutil.cpu_percent(interval=1):.1f}%")
        except Exception as e:
            print(f"CPU信息获取失败: {e}")
    
    # 测试内存信息
    print(f"\n=== 内存信息 ===")
    if HAS_PSUTIL:
        try:
            memory = psutil.virtual_memory()
            print(f"总内存: {memory.total / (1024**3):.2f} GB")
            print(f"可用内存: {memory.available / (1024**3):.2f} GB")
            print(f"内存使用率: {memory.percent:.1f}%")
        except Exception as e:
            print(f"内存信息获取失败: {e}")
    
    # 测试显卡信息
    print(f"\n=== 显卡信息 ===")
    try:
        # 测试NVIDIA GPU
        try:
            result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,driver_version', '--format=csv,noheader,nounits'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                gpu_lines = result.stdout.strip().split('\n')
                for i, line in enumerate(gpu_lines):
                    parts = line.split(', ')
                    if len(parts) >= 3:
                        print(f"NVIDIA GPU {i+1}: {parts[0]}")
                        print(f"  显存: {parts[1]} MB")
                        print(f"  驱动版本: {parts[2]}")
            else:
                print("未检测到NVIDIA显卡或nvidia-smi不可用")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("nvidia-smi 不可用")
        
        # 测试Windows显卡信息
        if platform.system() == "Windows":
            try:
                result = subprocess.run(['wmic', 'path', 'win32_VideoController', 'get', 'name'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')[1:]  # 跳过标题行
                    for line in lines:
                        line = line.strip()
                        if line and 'Name' not in line:
                            print(f"显卡: {line}")
            except Exception as e:
                print(f"Windows显卡信息获取失败: {e}")
                
    except Exception as e:
        print(f"显卡信息获取失败: {e}")
    
    # 测试CUDA信息
    print(f"\n=== CUDA信息 ===")
    try:
        # 检查NVCC
        try:
            result = subprocess.run(['nvcc', '--version'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'release' in line.lower():
                        print(f"NVCC版本: {line.strip()}")
                        break
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("NVCC 未安装或不在PATH中")
        
        # 检查PyTorch CUDA
        try:
            import torch
            print(f"PyTorch CUDA可用: {torch.cuda.is_available()}")
            if torch.cuda.is_available():
                print(f"PyTorch CUDA版本: {torch.version.cuda}")
                print(f"可用GPU数量: {torch.cuda.device_count()}")
                for i in range(torch.cuda.device_count()):
                    print(f"  GPU {i}: {torch.cuda.get_device_name(i)}")
        except ImportError:
            print("PyTorch 未安装")
        except Exception as e:
            print(f"PyTorch CUDA检查失败: {e}")
            
    except Exception as e:
        print(f"CUDA信息获取失败: {e}")
    
    # 测试声卡信息
    print(f"\n=== 声卡信息 ===")
    if platform.system() == "Windows":
        try:
            result = subprocess.run(['wmic', 'sounddev', 'get', 'name'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # 跳过标题行
                for line in lines:
                    line = line.strip()
                    if line and 'Name' not in line:
                        print(f"声卡: {line}")
        except Exception as e:
            print(f"声卡信息获取失败: {e}")
    else:
        print("仅支持Windows系统的声卡信息获取")

if __name__ == "__main__":
    test_system_info()
