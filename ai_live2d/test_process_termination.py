#!/usr/bin/env python3
"""
测试改进后的进程终止功能
"""

import sys
import os
import subprocess
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_process_termination():
    """测试进程终止功能"""
    print("开始测试进程终止功能...")

    # 定义要终止的进程列表
    audio_processes = [
        'ffplay.exe',      # FFmpeg播放器
        'sox.exe',         # SoX音频处理
        'vlc.exe',         # VLC媒体播放器
        'wmplayer.exe',    # Windows Media Player
        'python.exe',      # Python进程（可能在播放音频）
        'node.exe',        # Node.js进程（可能在播放音频）
    ]

    terminated_processes = []

    # 测试taskkill方法
    for proc_name in audio_processes:
        try:
            # 使用taskkill终止进程，不捕获输出以显示结果
            result = subprocess.run(
                ['taskkill', '/f', '/im', proc_name],
                capture_output=False,  # 不捕获输出，让用户看到结果
                timeout=5  # 设置超时
            )
            if result.returncode == 0:
                terminated_processes.append(proc_name)
                print(f"✓ 已终止进程: {proc_name}")
            elif result.returncode == 128:  # 进程未找到
                print(f"ℹ 进程 {proc_name} 未找到")
            else:
                print(f"⚠ 终止进程 {proc_name} 时返回码: {result.returncode}")
        except subprocess.TimeoutExpired:
            print(f"⚠ 终止进程 {proc_name} 超时")
        except Exception as e:
            print(f"⚠ 终止进程 {proc_name} 时出错: {e}")

    if terminated_processes:
        print(f"🎵 成功终止 {len(terminated_processes)} 个音频相关进程")
        print(f"📋 终止的进程: {', '.join(terminated_processes)}")
    else:
        print("ℹ 未找到正在运行的音频相关进程")

    print("进程终止功能测试完成！")

if __name__ == "__main__":
    test_process_termination()
