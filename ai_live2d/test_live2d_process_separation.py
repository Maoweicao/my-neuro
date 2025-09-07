# coding:utf-8
"""
测试Live2D预览进程分离功能
"""

import os
import sys
import subprocess
import time
import argparse

def test_live2d_preview_process():
    """测试Live2D预览进程分离功能"""
    print("🧪 测试Live2D预览进程分离功能")

    # 检查脚本文件是否存在
    script_path = os.path.join(os.path.dirname(__file__), 'live2d_preview_process.py')
    if not os.path.exists(script_path):
        print("❌ 错误: 找不到 live2d_preview_process.py 文件")
        return False

    # 查找一个可用的Live2D模型文件进行测试
    model_path = find_test_model()
    if not model_path:
        print("❌ 错误: 找不到可用的Live2D模型文件进行测试")
        return False

    print(f"📁 找到测试模型: {model_path}")

    # 构建命令
    python_exe = sys.executable
    cmd = [python_exe, script_path, '--model-path', model_path]

    print(f"🚀 启动命令: {' '.join(cmd)}")

    try:
        # 启动进程
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )

        print(f"✅ Live2D预览进程已启动 (PID: {process.pid})")

        # 等待一段时间让进程启动
        time.sleep(3)

        # 检查进程是否仍在运行
        if process.poll() is None:
            print("✅ 进程运行正常")

            # 终止测试进程
            print("🛑 终止测试进程...")
            process.terminate()

            try:
                process.wait(timeout=5.0)
                print("✅ 进程已正常终止")
            except subprocess.TimeoutExpired:
                print("⚠️ 进程未在预期时间内终止，强制结束")
                process.kill()
                process.wait()

            return True
        else:
            # 进程已经退出，检查退出码
            stdout, stderr = process.communicate()
            exit_code = process.returncode

            if exit_code == 0:
                print("✅ 进程正常退出")
                return True
            else:
                print(f"❌ 进程异常退出 (代码: {exit_code})")
                if stderr:
                    print(f"错误信息: {stderr.decode('utf-8', errors='ignore')}")
                return False

    except Exception as e:
        print(f"❌ 启动进程时出错: {e}")
        return False

def find_test_model():
    """查找可用的Live2D模型文件进行测试"""
    # 可能的模型路径
    possible_paths = [
        'models',  # models目录
        'resources/models',  # resources/models目录
        'data/models',  # data/models目录
        '.',  # 当前目录
    ]

    # 查找model3.json文件
    for base_path in possible_paths:
        if os.path.exists(base_path):
            for root, dirs, files in os.walk(base_path):
                for file in files:
                    if file.endswith('.model3.json'):
                        return os.path.join(root, file)

    return None

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='测试Live2D预览进程分离功能')
    parser.add_argument('--model-path', help='指定测试模型路径')

    args = parser.parse_args()

    if args.model_path:
        if not os.path.exists(args.model_path):
            print(f"❌ 指定的模型文件不存在: {args.model_path}")
            sys.exit(1)
        # 这里可以添加使用指定模型的测试逻辑
        print(f"使用指定模型进行测试: {args.model_path}")
    else:
        # 运行自动测试
        success = test_live2d_preview_process()
        if success:
            print("\n🎉 Live2D预览进程分离功能测试通过!")
            sys.exit(0)
        else:
            print("\n💥 Live2D预览进程分离功能测试失败!")
            sys.exit(1)

if __name__ == '__main__':
    main()
