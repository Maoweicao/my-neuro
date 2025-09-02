#!/usr/bin/env python3
"""
MCP工具自动下载器
自动下载和安装UV和Bun工具包管理器
"""

import os
import sys
import platform
import subprocess
import urllib.request
import zipfile
import tarfile
import tempfile
import shutil
from pathlib import Path
import json

class MCPToolDownloader:
    def __init__(self):
        self.system = platform.system().lower()
        self.machine = platform.machine().lower()
        self.temp_dir = tempfile.mkdtemp()

    def get_uv_download_url(self):
        """获取UV下载URL"""
        base_url = "https://github.com/astral-sh/uv/releases/latest/download"

        # 确定平台和架构
        if self.system == "windows":
            if "amd64" in self.machine or "x86_64" in self.machine:
                return f"{base_url}/uv-x86_64-pc-windows-msvc.zip"
            elif "arm64" in self.machine:
                return f"{base_url}/uv-aarch64-pc-windows-msvc.zip"
        elif self.system == "linux":
            if "amd64" in self.machine or "x86_64" in self.machine:
                return f"{base_url}/uv-x86_64-unknown-linux-gnu.tar.gz"
            elif "arm64" in self.machine or "aarch64" in self.machine:
                return f"{base_url}/uv-aarch64-unknown-linux-gnu.tar.gz"
        elif self.system == "darwin":  # macOS
            if "amd64" in self.machine or "x86_64" in self.machine:
                return f"{base_url}/uv-x86_64-apple-darwin.tar.gz"
            elif "arm64" in self.machine or "aarch64" in self.machine:
                return f"{base_url}/uv-arm64-apple-darwin.tar.gz"

        raise Exception(f"不支持的平台: {self.system} {self.machine}")

    def get_bun_download_url(self):
        """获取Bun下载URL"""
        base_url = "https://github.com/oven-sh/bun/releases/latest/download"

        # 确定平台和架构
        if self.system == "windows":
            if "amd64" in self.machine or "x86_64" in self.machine:
                return f"{base_url}/bun-windows-x64.zip"
            elif "arm64" in self.machine:
                return f"{base_url}/bun-windows-arm64.zip"
        elif self.system == "linux":
            if "amd64" in self.machine or "x86_64" in self.machine:
                return f"{base_url}/bun-linux-x64.tar.gz"
            elif "arm64" in self.machine or "aarch64" in self.machine:
                return f"{base_url}/bun-linux-arm64.tar.gz"
        elif self.system == "darwin":  # macOS
            if "amd64" in self.machine or "x86_64" in self.machine:
                return f"{base_url}/bun-darwin-x64.tar.gz"
            elif "arm64" in self.machine or "aarch64" in self.machine:
                return f"{base_url}/bun-darwin-arm64.tar.gz"

        raise Exception(f"不支持的平台: {self.system} {self.machine}")

    def download_file(self, url, dest_path):
        """下载文件"""
        print(f"下载: {url}")
        try:
            with urllib.request.urlopen(url) as response:
                with open(dest_path, 'wb') as f:
                    shutil.copyfileobj(response, f)
            print(f"下载完成: {dest_path}")
        except Exception as e:
            print(f"下载失败: {e}")
            raise

    def extract_archive(self, archive_path, extract_to):
        """解压归档文件"""
        print(f"解压: {archive_path}")
        if archive_path.endswith('.zip'):
            with zipfile.ZipFile(archive_path, 'r') as zip_ref:
                zip_ref.extractall(extract_to)
        elif archive_path.endswith('.tar.gz'):
            with tarfile.open(archive_path, 'r:gz') as tar_ref:
                tar_ref.extractall(extract_to)
        print(f"解压完成: {extract_to}")

    def install_uv(self):
        """安装UV"""
        print("检查UV是否已安装...")
        if self.is_command_available("uv"):
            print("UV已安装，跳过")
            return True

        try:
            download_url = self.get_uv_download_url()
            archive_name = os.path.basename(download_url)
            archive_path = os.path.join(self.temp_dir, archive_name)

            # 下载
            self.download_file(download_url, archive_path)

            # 解压
            extract_dir = os.path.join(self.temp_dir, "uv_extract")
            self.extract_archive(archive_path, extract_dir)

            # 查找可执行文件
            uv_exe = None
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file == "uv" or file == "uv.exe":
                        uv_exe = os.path.join(root, file)
                        break
                if uv_exe:
                    break

            if not uv_exe:
                raise Exception("未找到UV可执行文件")

            # 安装到系统PATH
            install_dir = self.get_install_dir()
            uv_install_path = os.path.join(install_dir, "uv.exe" if self.system == "windows" else "uv")

            shutil.copy2(uv_exe, uv_install_path)
            os.chmod(uv_install_path, 0o755)

            print(f"UV安装完成: {uv_install_path}")
            return True

        except Exception as e:
            print(f"UV安装失败: {e}")
            return False

    def install_bun(self):
        """安装Bun"""
        print("检查Bun是否已安装...")
        if self.is_command_available("bun"):
            print("Bun已安装，跳过")
            return True

        try:
            download_url = self.get_bun_download_url()
            archive_name = os.path.basename(download_url)
            archive_path = os.path.join(self.temp_dir, archive_name)

            # 下载
            self.download_file(download_url, archive_path)

            # 解压
            extract_dir = os.path.join(self.temp_dir, "bun_extract")
            self.extract_archive(archive_path, extract_dir)

            # 查找可执行文件
            bun_exe = None
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    if file == "bun" or file == "bun.exe":
                        bun_exe = os.path.join(root, file)
                        break
                if bun_exe:
                    break

            if not bun_exe:
                raise Exception("未找到Bun可执行文件")

            # 安装到系统PATH
            install_dir = self.get_install_dir()
            bun_install_path = os.path.join(install_dir, "bun.exe" if self.system == "windows" else "bun")

            shutil.copy2(bun_exe, bun_install_path)
            os.chmod(bun_install_path, 0o755)

            print(f"Bun安装完成: {bun_install_path}")
            return True

        except Exception as e:
            print(f"Bun安装失败: {e}")
            return False

    def get_install_dir(self):
        """获取安装目录"""
        if self.system == "windows":
            # Windows下安装到用户本地目录
            local_app_data = os.environ.get("LOCALAPPDATA", os.path.expanduser("~\\AppData\\Local"))
            install_dir = os.path.join(local_app_data, "MCPTools")
        else:
            # Unix-like系统安装到用户本地bin目录
            home = os.path.expanduser("~")
            install_dir = os.path.join(home, ".local", "bin")

        os.makedirs(install_dir, exist_ok=True)
        return install_dir

    def is_command_available(self, command):
        """检查命令是否可用"""
        try:
            subprocess.run([command, "--version"],
                         capture_output=True,
                         check=True,
                         timeout=10)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            return False

    def update_path(self):
        """更新PATH环境变量"""
        install_dir = self.get_install_dir()
        current_path = os.environ.get("PATH", "")

        if install_dir not in current_path:
            new_path = f"{install_dir}{os.pathsep}{current_path}"
            print(f"请将以下路径添加到您的PATH环境变量: {install_dir}")
            print("或者运行以下命令更新当前会话的PATH:")
            if self.system == "windows":
                print(f'$env:PATH = "{install_dir};" + $env:PATH')
            else:
                print(f'export PATH="{install_dir}:$PATH"')

    def cleanup(self):
        """清理临时文件"""
        try:
            shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"清理临时文件失败: {e}")

    def run(self):
        """运行安装程序"""
        print("MCP工具自动下载器")
        print("=" * 30)

        success_count = 0

        # 安装UV
        if self.install_uv():
            success_count += 1

        # 安装Bun
        if self.install_bun():
            success_count += 1

        # 更新PATH
        if success_count > 0:
            print("\n安装完成！")
            self.update_path()
        else:
            print("\n所有工具已安装或安装失败。")

        # 清理
        self.cleanup()

def main():
    downloader = MCPToolDownloader()
    try:
        downloader.run()
    except KeyboardInterrupt:
        print("\n用户取消操作")
    except Exception as e:
        print(f"发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
