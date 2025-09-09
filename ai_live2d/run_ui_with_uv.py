#!/usr/bin/env python
"""
使用本地 uv.exe 启动 UI.py 的小工具。

优先查找顺序：
1) 项目根目录下的 uv.exe
2) .venv/Scripts/uv.exe 或 venv/Scripts/uv.exe
3) 系统 PATH 中的 uv.exe/uv

用法：
    python run_ui_with_uv.py [UI.py 的可选参数]

示例：
    python run_ui_with_uv.py --debug
"""
from __future__ import annotations
import os
import sys
import shutil
import subprocess
from pathlib import Path


def find_uv_executable(base_dir: Path) -> str:
    """查找 uv.exe 的路径，找不到则抛出 FileNotFoundError。"""
    candidates = [
        base_dir / "uv.exe",
        base_dir / "dependies" / "uv.exe",
        base_dir / ".venv" / "Scripts" / "uv.exe",
        base_dir / "venv" / "Scripts" / "uv.exe",
    ]
    for p in candidates:
        if p.is_file():
            return str(p)

    uv_in_path = shutil.which("uv.exe") or shutil.which("uv")
    if uv_in_path:
        return uv_in_path

    raise FileNotFoundError(
        "未找到 uv.exe。请将 uv.exe 放到项目根目录，或确保它在 PATH 中，"
        "或安装到 .venv/venv 的 Scripts 目录下。"
    )


def main() -> int:
    base_dir = Path(__file__).resolve().parent
    ui_py = base_dir / "UI.py"
    if not ui_py.exists():
        print(f"未找到文件：{ui_py}")
        return 1

    try:
        uv = find_uv_executable(base_dir)
    except FileNotFoundError as e:
        print(e)
        return 2

    # 通过 uv 运行 Python 启动 UI.py
    cmd = [uv, "run", "python", str(ui_py)]

    # 透传给 UI.py 的命令行参数
    if len(sys.argv) > 1:
        cmd.extend(sys.argv[1:])

    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")

    try:
        proc = subprocess.run(cmd, cwd=str(base_dir), env=env)
        return proc.returncode
    except KeyboardInterrupt:
        # Ctrl+C 退出码按约定返回 130
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
