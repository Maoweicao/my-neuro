import os
import subprocess
import shutil
import zipfile
import time

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

# 检查下载的模型是否存在
ernie_model_path = os.path.join(bert_model_dir, "ernie-3.0-base-zh-Vision-FT")
if not os.path.exists(ernie_model_path):
    print(f"错误：下载后无法找到ernie模型路径 {ernie_model_path}")
    exit(1)

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

# 执行第二个下载命令，带重试机制
if not download_with_retry("cg down xxxiu/G2PWModel"):
    print("G2PWModel下载失败，终止程序")
    exit(1)

# 检查下载的模型是否存在
g2pw_model_path = os.path.join(text_dir, "G2PWModel")
if not os.path.exists(g2pw_model_path):
    print(f"错误：下载后无法找到G2PWModel路径 {g2pw_model_path}")
    exit(1)

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
    try:
        shutil.copytree(source_g2pw_dir, target_g2pw_dir)
        print("复制完成！")
    except Exception as e:
        print(f"复制过程中出错: {str(e)}")
        exit(1)
else:
    print(f"错误：源文件夹 {source_g2pw_dir} 不存在，无法复制")
    exit(1)

# 4. 下载并解压pretrained_models.zip到tts-studio/GPT_SoVITS/pretrained_models文件夹
# 创建目标目录
pretrained_models_dir = os.path.join(gpt_sovits_dir, "pretrained_models")
if not os.path.exists(pretrained_models_dir):
    os.makedirs(pretrained_models_dir)

# 切换到pretrained_models目录
os.chdir(pretrained_models_dir)
print(f"下载pretrained_models.zip到: {os.getcwd()}")

# 执行下载命令，带重试机制
if not download_with_retry("cg down xxxiu/fake_neuro_pretrained_models"):
    print("pretrained_models下载失败，终止程序")
    exit(1)

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
        try:
            shutil.move(zip_path, target_zip_path)
            print(f"已将zip文件移动到: {target_zip_path}")
        except Exception as e:
            print(f"移动zip文件时出错: {str(e)}")
            exit(1)
        
        # 删除下载的文件夹
        try:
            shutil.rmtree(downloaded_folder)
            print(f"已删除文件夹: {downloaded_folder}")
        except Exception as e:
            print(f"删除文件夹时出错: {str(e)}")
            # 不终止程序，因为这不是关键步骤
        
        # 解压zip文件
        print(f"正在解压 {target_zip_path}...")
        try:
            with zipfile.ZipFile(target_zip_path, 'r') as zip_ref:
                zip_ref.extractall(pretrained_models_dir)
            print("解压完成")
        except Exception as e:
            print(f"解压zip文件时出错: {str(e)}")
            exit(1)
        
        # 删除原始zip文件
        try:
            os.remove(target_zip_path)
            print(f"已删除压缩包: {target_zip_path}")
        except Exception as e:
            print(f"删除zip文件时出错: {str(e)}")
            # 不终止程序，因为这不是关键步骤
    else:
        print(f"错误：在 {downloaded_folder} 中找不到zip文件")
        exit(1)
else:
    print(f"错误：下载文件夹 {downloaded_folder} 不存在")
    exit(1)

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
    try:
        with zipfile.ZipFile(temp_zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(source_pretrained_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    # 计算相对路径
                    rel_path = os.path.relpath(file_path, source_pretrained_dir)
                    zipf.write(file_path, rel_path)
        
        print(f"临时压缩包创建完成: {temp_zip_path}")
    except Exception as e:
        print(f"创建临时压缩包时出错: {str(e)}")
        exit(1)
    
    # 解压文件
    print(f"正在解压到 {tts_pretrained_dir}...")
    try:
        with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
            zip_ref.extractall(tts_pretrained_dir)
    except Exception as e:
        print(f"解压临时压缩包时出错: {str(e)}")
        exit(1)
    
    # 删除临时zip文件
    try:
        os.remove(temp_zip_path)
        print(f"已删除临时压缩包")
    except Exception as e:
        print(f"删除临时压缩包时出错: {str(e)}")
        # 不终止程序，因为这不是关键步骤
    
    print("预训练模型复制完成")
else:
    print(f"错误：源预训练模型文件夹 {source_pretrained_dir} 不存在或为空")
    exit(1)

print("所有操作完成！")
