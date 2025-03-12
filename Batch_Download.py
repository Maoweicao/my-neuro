import os
import subprocess
import shutil
import zipfile

# 获取当前工作目录
current_dir = os.getcwd()

# 1. 下载第一个模型 - ernie到bert-model文件夹
bert_model_dir = os.path.join(current_dir, "bert-model")
if not os.path.exists(bert_model_dir):
    os.makedirs(bert_model_dir)

# 切换到bert-model目录
os.chdir(bert_model_dir)
print(f"下载ernie模型到: {os.getcwd()}")

# 执行第一个下载命令
subprocess.Popen(
    "cg down xxxiu/ernie-3.0-base-zh-Vision-FT",
    shell=True,
    stdout=None,
    stderr=None
).wait()

# 2. 下载第二个模型 - G2PWModel到tts-studio/text文件夹
# 返回到原始目录
os.chdir(current_dir)

# 创建tts-studio/text路径
tts_studio_dir = os.path.join(current_dir, "tts-studio")
text_dir = os.path.join(tts_studio_dir, "text")
if not os.path.exists(text_dir):
    os.makedirs(text_dir)

# 切换到tts-studio/text目录
os.chdir(text_dir)
print(f"下载G2PWModel到: {os.getcwd()}")

# 执行第二个下载命令
subprocess.Popen(
    "cg down xxxiu/G2PWModel",
    shell=True,
    stdout=None,
    stderr=None
).wait()

# 3. 复制G2PWModel到tts-studio/GPT_SoVITS/text文件夹
# 返回到原始目录
os.chdir(current_dir)

# 源文件夹路径
source_g2pw_dir = os.path.join(text_dir, "G2PWModel")

# 目标文件夹路径
gpt_sovits_dir = os.path.join(tts_studio_dir, "GPT_SoVITS")
gpt_text_dir = os.path.join(gpt_sovits_dir, "text")
target_g2pw_dir = os.path.join(gpt_text_dir, "G2PWModel")

# 创建目标目录结构
if not os.path.exists(gpt_sovits_dir):
    os.makedirs(gpt_sovits_dir)
if not os.path.exists(gpt_text_dir):
    os.makedirs(gpt_text_dir)

# 复制文件夹
if os.path.exists(source_g2pw_dir):
    print(f"复制G2PWModel从 {source_g2pw_dir} 到 {target_g2pw_dir}")
    # 如果目标文件夹已存在，先删除
    if os.path.exists(target_g2pw_dir):
        shutil.rmtree(target_g2pw_dir)
    # 复制整个文件夹
    shutil.copytree(source_g2pw_dir, target_g2pw_dir)
    print("复制完成！")
else:
    print(f"错误：源文件夹 {source_g2pw_dir} 不存在，无法复制")

# 4. 下载并解压pretrained_models.zip到tts-studio/GPT_SoVITS/pretrained_models文件夹
# 创建目标目录
pretrained_models_dir = os.path.join(gpt_sovits_dir, "pretrained_models")
if not os.path.exists(pretrained_models_dir):
    os.makedirs(pretrained_models_dir)

# 切换到pretrained_models目录
os.chdir(pretrained_models_dir)
print(f"下载pretrained_models.zip到: {os.getcwd()}")

# 执行下载命令
subprocess.Popen(
    "cg down xxxiu/fake_neuro_pretrained_models",
    shell=True,
    stdout=None,
    stderr=None
).wait()

# 处理下载的文件
downloaded_folder = os.path.join(pretrained_models_dir, "fake_neuro_pretrained_models")
if os.path.exists(downloaded_folder):
    print(f"找到下载的文件夹: {downloaded_folder}")
    
    # 查找文件夹中的zip文件
    zip_path = os.path.join(downloaded_folder, "pretrained_models.zip")
    if os.path.exists(zip_path):
        print(f"找到zip文件: {zip_path}")
        
        # 将zip文件移动到上层目录
        target_zip_path = os.path.join(pretrained_models_dir, "pretrained_models.zip")
        shutil.move(zip_path, target_zip_path)
        print(f"已将zip文件移动到: {target_zip_path}")
        
        # 删除下载的文件夹
        shutil.rmtree(downloaded_folder)
        print(f"已删除文件夹: {downloaded_folder}")
        
        # 解压zip文件
        print(f"正在解压 {target_zip_path}...")
        with zipfile.ZipFile(target_zip_path, 'r') as zip_ref:
            zip_ref.extractall(pretrained_models_dir)
        print("解压完成")
        
        # 删除原始zip文件
        os.remove(target_zip_path)
        print(f"已删除压缩包: {target_zip_path}")
    else:
        print(f"错误：在 {downloaded_folder} 中找不到zip文件")
else:
    print(f"错误：下载文件夹 {downloaded_folder} 不存在")

# 5. 复制预训练模型到tts-studio/pretrained_models文件夹
# 返回到原始目录
os.chdir(current_dir)

# 创建目标目录
tts_pretrained_dir = os.path.join(tts_studio_dir, "pretrained_models")
if not os.path.exists(tts_pretrained_dir):
    os.makedirs(tts_pretrained_dir)
    print(f"创建目录: {tts_pretrained_dir}")

# 源文件夹中的所有文件
source_pretrained_dir = pretrained_models_dir
print(f"正在将预训练模型从 {source_pretrained_dir} 复制到 {tts_pretrained_dir}")

# 检查源文件夹中是否有文件
if os.path.exists(source_pretrained_dir) and os.listdir(source_pretrained_dir):
    # 创建临时zip文件
    temp_zip_path = os.path.join(tts_pretrained_dir, "pretrained_models.zip")
    
    print("创建临时压缩包...")
    # 创建一个临时压缩文件
    with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_pretrained_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # 计算相对路径
                rel_path = os.path.relpath(file_path, source_pretrained_dir)
                zipf.write(file_path, rel_path)
    
    print(f"临时压缩包创建完成: {temp_zip_path}")
    
    # 解压文件
    print(f"正在解压到 {tts_pretrained_dir}...")
    with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
        zip_ref.extractall(tts_pretrained_dir)
    
    # 删除临时zip文件
    os.remove(temp_zip_path)
    print(f"已删除临时压缩包")
    print("预训练模型复制完成")
else:
    print(f"错误：源预训练模型文件夹 {source_pretrained_dir} 不存在或为空")

print("所有操作完成！")
