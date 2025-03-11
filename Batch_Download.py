import os
import subprocess
import shutil
import zipfile
import glob

def create_directory_if_not_exists(directory_path):
    """创建目录如果它不存在"""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        print(f"创建目录: {directory_path}")

def download_g2pw_model(model_path="xxxiu/G2PWModel"):
    """下载G2PWModel到当前目录"""
    print(f"正在下载模型 {model_path}...")
    subprocess.run(["cg", "down", model_path], check=True)
    print(f"模型 {model_path} 下载完成")
    
    # 假设下载后的模型文件夹名称为模型名的最后部分
    return model_path.split("/")[-1]

def download_pretrained_models(model_path="xxxiu/fake_neuro_pretrained_models"):
    """下载pretrained_models并处理zip文件"""
    # 创建临时下载目录
    temp_dir = "temp_download_dir"
    create_directory_if_not_exists(temp_dir)
    
    # 切换到临时目录下载
    original_dir = os.getcwd()
    os.chdir(temp_dir)
    
    print(f"正在下载模型 {model_path}...")
    subprocess.run(["cg", "down", model_path], check=True)
    print(f"模型 {model_path} 下载完成")
    
    # 切回原始目录
    os.chdir(original_dir)
    
    # 查找下载的zip文件
    zip_pattern = os.path.join(temp_dir, "**", "*.zip")
    zip_files = glob.glob(zip_pattern, recursive=True)
    
    if not zip_files:
        raise FileNotFoundError(f"在{temp_dir}目录下未找到zip文件")
    
    zip_file = zip_files[0]
    print(f"找到压缩包: {zip_file}")
    
    # 确保目标目录存在
    target_dir = "pretrained_models"
    create_directory_if_not_exists(target_dir)
    
    # 将zip文件移动到目标目录
    target_zip = os.path.join(target_dir, os.path.basename(zip_file))
    shutil.copy2(zip_file, target_zip)
    print(f"已移动压缩包到: {os.path.abspath(target_zip)}")
    
    # 解压缩
    print(f"正在解压 {target_zip}...")
    with zipfile.ZipFile(target_zip, 'r') as zip_ref:
        zip_ref.extractall(target_dir)
    print(f"解压完成")
    
    # 删除压缩包
    os.remove(target_zip)
    print(f"已删除压缩包: {target_zip}")
    
    # 删除临时下载目录
    shutil.rmtree(temp_dir)
    print(f"已删除临时下载目录: {temp_dir}")
    
    return target_dir

def copy_model_to_directory(model_folder, target_directory):
    """复制模型文件夹到目标目录"""
    if not os.path.exists(target_directory):
        create_directory_if_not_exists(target_directory)
    
    target_path = os.path.join(target_directory, os.path.basename(model_folder))
    
    # 检查目标路径是否已存在模型
    if os.path.exists(target_path):
        print(f"目标路径 {target_path} 已存在模型，跳过复制")
        return
    
    print(f"正在复制模型到 {target_path}...")
    shutil.copytree(model_folder, target_path)
    print(f"复制完成: {target_path}")

def process_g2pw_model():
    """处理G2PWModel模型的下载和复制"""
    target_directories = [
        os.path.join("text"),
        os.path.join("GPT_SoVITS", "text")
    ]
    
    # 检查是否已经下载过模型
    if os.path.exists("G2PWModel"):
        print("检测到G2PWModel已下载，将直接复制到目标目录")
        model_folder = "G2PWModel"
    else:
        # 下载模型到当前目录
        model_folder = download_g2pw_model("xxxiu/G2PWModel")
    
    # 复制模型到每个目标目录
    for target_dir in target_directories:
        copy_model_to_directory(model_folder, target_dir)

def process_neuro_pretrained_models():
    """处理fake_neuro_pretrained_models模型的下载和复制"""
    target_directories = [
        os.path.join("GPT_SoVITS", "pretrained_models")
    ]
    
    # 检查是否已经下载并解压过模型
    if os.path.exists("pretrained_models") and any(os.listdir("pretrained_models")):
        print("检测到pretrained_models已下载并解压，将直接复制到目标目录")
        model_folder = "pretrained_models"
    else:
        # 下载并解压模型到pretrained_models目录
        model_folder = download_pretrained_models("xxxiu/fake_neuro_pretrained_models")
    
    # 复制模型到其他目标目录(GPT_SoVITS/pretrained_models)
    for target_dir in target_directories:
        # 确保目标目录存在
        create_directory_if_not_exists(target_dir)
        
        # 获取source目录中的所有文件和文件夹
        source_items = os.listdir(model_folder)
        
        # 复制每个文件/文件夹到目标目录
        for item in source_items:
            source_path = os.path.join(model_folder, item)
            target_path = os.path.join(target_dir, item)
            
            if os.path.exists(target_path):
                print(f"{target_path} 已存在，跳过复制")
                continue
                
            if os.path.isdir(source_path):
                print(f"正在复制目录 {source_path} 到 {target_path}")
                shutil.copytree(source_path, target_path)
            else:
                print(f"正在复制文件 {source_path} 到 {target_path}")
                shutil.copy2(source_path, target_path)

def main():
    # 处理G2PWModel
    print("===== 处理G2PWModel =====")
    process_g2pw_model()
    
    # 处理fake_neuro_pretrained_models
    print("\n===== 处理fake_neuro_pretrained_models =====")
    process_neuro_pretrained_models()
    
    print("\n所有操作完成！")

if __name__ == "__main__":
    main()