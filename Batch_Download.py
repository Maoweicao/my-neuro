import os
import subprocess
import shutil
import zipfile
import time
import modelscope

# 设置最大重试次数
MAX_RETRY = 3
# 重试等待时间（秒）
RETRY_WAIT = 5

# 定义下载函数，包含重试机制
def download_with_retry(command, max_retry=MAX_RETRY, wait_time=RETRY_WAIT):
    print(f"执行命令: {command}")
    for attempt in range(max_retry):
        if attempt > 0:
            print(f"第 {attempt+1} 次尝试下载...")
        
        result = subprocess.Popen(
            command,
            shell=True,
            stdout=None,
            stderr=None
        ).wait()
        
        if result == 0:
            print("下载成功!")
            return True
        else:
            print(f"下载失败，返回值: {result}")
            if attempt < max_retry - 1:
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
    
    print(f"经过 {max_retry} 次尝试后，下载仍然失败")
    return False

# 获取当前工作目录
current_dir = os.getcwd()

# 1. 下载第一个模型 - ernie到bert-model文件夹
bert_model_dir = os.path.join(current_dir, "bert-model")
if not os.path.exists(bert_model_dir):
    os.makedirs(bert_model_dir)

# 切换到bert-model目录
os.chdir(bert_model_dir)
print(f"下载ernie模型到: {os.getcwd()}")

# 使用ModelScope下载ernie模型，带重试机制
if not download_with_retry("modelscope download --model morelle/ernie-3.0-base-zh-Vision-FT --local_dir ./"):
    print("ernie模型下载失败，终止程序")
    exit(1)

# 检查下载的模型是否存在 - ModelScope直接下载到指定目录
# 检查一些关键文件是否存在来确认模型是否下载成功
ernie_model_files = ["config.json", "model.safetensors", "vocab.txt"]
missing_files = [f for f in ernie_model_files if not os.path.exists(os.path.join(bert_model_dir, f))]
if missing_files:
    print(f"错误：下载后无法找到ernie模型的关键文件: {', '.join(missing_files)}")
    exit(1)
print("ernie模型检查通过，关键文件已找到")

# 2. 下载第二个模型 - G2PWModel到tts-studio/text文件夹
# 返回到原始目录
os.chdir(current_dir)

# 创建tts-studio/text路径
tts_studio_dir = os.path.join(current_dir, "tts-studio")
text_dir = os.path.join(tts_studio_dir, "text")
if not os.path.exists(text_dir):
    os.makedirs(text_dir)

# 创建专门的G2PWModel文件夹
g2pw_model_dir = os.path.join(text_dir, "G2PWModel")
if not os.path.exists(g2pw_model_dir):
    os.makedirs(g2pw_model_dir)

# 切换到G2PWModel目录
os.chdir(g2pw_model_dir)
print(f"下载G2PWModel到: {os.getcwd()}")

# 使用ModelScope下载G2PWModel，带重试机制
if not download_with_retry("modelscope download --model zxm2493188292/G2PWModel --local_dir ./"):
    print("G2PWModel下载失败，终止程序")
    exit(1)

# 检查下载的G2PWModel是否存在
if not os.listdir(g2pw_model_dir):
    print(f"错误：下载后G2PWModel目录为空 {g2pw_model_dir}")
    exit(1)
print("G2PWModel模型下载检查通过，文件已找到")

# 3. 复制G2PWModel到tts-studio/GPT_SoVITS/text文件夹
# 返回到原始目录
os.chdir(current_dir)

# 源文件夹路径 - 现在是专门的G2PWModel文件夹
source_g2pw_dir = g2pw_model_dir

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
print(f"复制G2PWModel从 {source_g2pw_dir} 到 {target_g2pw_dir}")
# 如果目标文件夹已存在，先删除
if os.path.exists(target_g2pw_dir):
    shutil.rmtree(target_g2pw_dir)
# 复制整个文件夹
try:
    shutil.copytree(source_g2pw_dir, target_g2pw_dir)
    print("复制完成！")
except Exception as e:
    print(f"复制过程中出错: {str(e)}")
    exit(1)

# 4. 下载并解压pretrained_models.zip到tts-studio/GPT_SoVITS/pretrained_models文件夹
# 创建目标目录
pretrained_models_dir = os.path.join(gpt_sovits_dir, "pretrained_models")
if not os.path.exists(pretrained_models_dir):
    os.makedirs(pretrained_models_dir)

# 返回到原始目录
os.chdir(current_dir)

# 切换到GPT_SoVITS目录
print(f"下载GPT-SoVITS预训练模型到: {gpt_sovits_dir}")

# 使用ModelScope下载GPT-SoVITS预训练模型，带重试机制
if not download_with_retry("modelscope download --model AI-ModelScope/GPT-SoVITS --local_dir ./tts-studio/GPT_SoVITS/pretrained_models"):
    print("GPT-SoVITS预训练模型下载失败，终止程序")
    exit(1)

# 确认模型已下载
if not os.path.exists(pretrained_models_dir) or not os.listdir(pretrained_models_dir):
    print(f"错误：下载后无法找到预训练模型目录或目录为空: {pretrained_models_dir}")
    exit(1)

print(f"预训练模型已成功下载到: {pretrained_models_dir}")

# 5. 复制预训练模型到tts-studio/pretrained_models文件夹
# 确保我们在当前工作目录
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
    # 复制文件夹中的所有内容
    print(f"复制预训练模型文件...")
    try:
        # 遍历源目录中的所有文件和文件夹
        for item in os.listdir(source_pretrained_dir):
            source_item = os.path.join(source_pretrained_dir, item)
            target_item = os.path.join(tts_pretrained_dir, item)
            
            # 如果是文件夹，递归复制整个文件夹
            if os.path.isdir(source_item):
                if os.path.exists(target_item):
                    shutil.rmtree(target_item)  # 如果目标已存在，先删除
                shutil.copytree(source_item, target_item)
                print(f"已复制文件夹: {item}")
            # 如果是文件，直接复制
            else:
                shutil.copy2(source_item, target_item)
                print(f"已复制文件: {item}")
        
        print("预训练模型复制完成")
    except Exception as e:
        print(f"复制预训练模型时出错: {str(e)}")
        exit(1)
else:
    print(f"错误：源预训练模型文件夹 {source_pretrained_dir} 不存在或为空")
    exit(1)

print("所有操作完成！")

# 6. 下载fake_neuro_V1模型
print("\n开始下载fake_neuro_V1模型...")

# 创建tts-model目录
tts_model_dir = os.path.join(tts_studio_dir, "tts-model")
if not os.path.exists(tts_model_dir):
    os.makedirs(tts_model_dir)
    print(f"创建目录: {tts_model_dir}")

# 切换到tts-model目录
os.chdir(tts_model_dir)
print(f"下载fake_neuro_V1模型到: {os.getcwd()}")

# 使用ModelScope下载fake_neuro_V1模型，带重试机制
if not download_with_retry("modelscope download --model morelle/fake_neuro_V1 --local_dir ./"):
    print("fake_neuro_V1模型下载失败")
    # 不终止程序，因为这是额外的模型
else:
    print("fake_neuro_V1模型下载成功！")

# 7. 下载Mnemosyne-V1-bert模型
print("\n开始下载Mnemosyne-V1-bert模型...")

# 返回到原始目录
os.chdir(current_dir)
print(f"下载Mnemosyne-V1-bert模型到: {current_dir}")

# 使用ModelScope下载Mnemosyne-V1-bert模型，带重试机制
if not download_with_retry("modelscope download --model morelle/Mnemosyne-V1-bert --local_dir ./Mnemosyne-bert"):
    print("Mnemosyne-V1-bert模型下载失败")
    # 不终止程序，可以根据需要决定是否终止
else:
    print("Mnemosyne-V1-bert模型下载成功！")

print("所有下载操作全部完成！")
