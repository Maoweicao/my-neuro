# 保存为 download_model.py
import os

# 获取用户输入的模型名称
model_name = input("请输入要下载的模型名称: ")

# 构建完整的模型路径
if not model_name.startswith("Qwen/"):
    full_model_name = f"Qwen/{model_name}"
else:
    full_model_name = model_name

# 创建目标目录
target_dir = os.path.join("./models", model_name)
os.makedirs(target_dir, exist_ok=True)

# 执行下载命令
download_cmd = f"modelscope download --model {full_model_name} --local_dir {target_dir}"
print(f"执行命令: {download_cmd}")
os.system(download_cmd)