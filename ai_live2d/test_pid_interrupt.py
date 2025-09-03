#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试PID记录和进程中断功能
"""

import os
import time
import subprocess
import signal
import sys

def test_pid_recording():
    """测试PID记录功能"""
    print("=== 测试PID记录功能 ===")

    # 记录当前进程PID
    current_pid = os.getpid()
    print(f"当前进程PID: {current_pid}")

    # 模拟记录PID到文件
    with open('test_pid.txt', 'w', encoding='utf-8') as f:
        f.write(str(current_pid))

    print("PID已记录到 test_pid.txt")

    # 启动一个子进程来模拟音频播放
    print("启动模拟音频进程...")
    audio_process = subprocess.Popen([
        sys.executable, '-c',
        'import time; print("模拟音频播放进程启动，PID:", __import__("os").getpid()); time.sleep(30)'
    ])

    audio_pid = audio_process.pid
    print(f"音频进程PID: {audio_pid}")

    # 记录音频进程PID
    with open('audio_pid.txt', 'w', encoding='utf-8') as f:
        f.write(str(audio_pid))

    print("音频进程PID已记录到 audio_pid.txt")

    # 等待一段时间
    time.sleep(3)

    # 测试进程终止
    print("\n=== 测试进程终止功能 ===")

    # 读取PID文件
    pids_to_terminate = []
    pid_files = ['test_pid.txt', 'audio_pid.txt']

    for pid_file in pid_files:
        if os.path.exists(pid_file):
            try:
                with open(pid_file, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content.isdigit():
                        pids_to_terminate.append(int(content))
                        print(f"从{pid_file}读取到PID: {content}")
            except Exception as e:
                print(f"读取{pid_file}时出错: {e}")

    print(f"需要终止的进程: {pids_to_terminate}")

    # 终止进程
    for pid in pids_to_terminate:
        try:
            if pid == current_pid:
                print(f"跳过当前进程PID: {pid}")
                continue

            # 在Windows上使用taskkill
            if os.name == 'nt':
                result = subprocess.run(
                    ['taskkill', '/pid', str(pid), '/f'],
                    capture_output=True,
                    text=True,
                    encoding='gbk'
                )
                if result.returncode == 0:
                    print(f"✓ 成功终止进程PID: {pid}")
                    if result.stdout:
                        print(f"输出: {result.stdout.strip()}")
                else:
                    print(f"⚠ 终止进程PID {pid} 返回码: {result.returncode}")
                    if result.stderr:
                        print(f"错误: {result.stderr.strip()}")
            else:
                # 在Unix系统上使用kill
                os.kill(pid, signal.SIGTERM)
                print(f"✓ 发送SIGTERM到进程PID: {pid}")

        except Exception as e:
            print(f"⚠ 终止进程PID {pid} 时出错: {e}")

    # 清理文件
    print("\n=== 清理测试文件 ===")
    for pid_file in pid_files:
        try:
            if os.path.exists(pid_file):
                os.remove(pid_file)
                print(f"已删除: {pid_file}")
        except Exception as e:
            print(f"删除{pid_file}失败: {e}")

    print("测试完成！")

if __name__ == "__main__":
    test_pid_recording()
