import os
import sys
from pathlib import Path

def fix_pyvenv_cfg(venv_path=".venv"):
    # 获取虚拟环境配置文件路径
    cfg_path = Path(venv_path) / "pyvenv.cfg"
    
    if not cfg_path.exists():
        print(f"错误: 未找到 {cfg_path}")
        return False

    # 获取当前有效的Python解释器目录（去除最后的python.exe）
    current_python = Path(sys.executable).parent

    # 读取原始文件内容
    with open(cfg_path, 'r') as f:
        lines = f.readlines()

    # 处理每一行
    new_lines = []
    home_updated = False
    for line in lines:
        # 检查是否是 home 行
        if line.strip().startswith('home'):
            # 更新 home 路径
            new_line = f"home = {current_python}\n"
            new_lines.append(new_line)
            home_updated = True
        else:
            # 保留其他行不变
            new_lines.append(line)
    
    # 如果文件中没有 home 行，添加一个新行
    if not home_updated:
        new_lines.append(f"home = {current_python}\n")
    
    # 写入更新后的内容
    with open(cfg_path, 'w') as f:
        f.writelines(new_lines)
    
    print(f"成功更新虚拟环境配置!")
    print(f"新的 Python 路径: {current_python}")
    return True

if __name__ == "__main__":
    fix_pyvenv_cfg()