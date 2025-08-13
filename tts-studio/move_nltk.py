import zipfile
import os


def extract_nltk_data():
    # 目标路径
    target_dir = os.path.expanduser("~/AppData/Roaming/nltk_data")

    # 创建目录
    os.makedirs(target_dir, exist_ok=True)

    corpora = os.path.exists(os.path.join(target_dir,'corpora'))
    taggers = os.path.exists(os.path.join(target_dir,'taggers'))
    tokenizers = os.path.exists(os.path.join(target_dir,'tokenizers'))

    if corpora and taggers and tokenizers:
        print('nltk_data文件已存在，成功读取')
        return

    # 解压
    with zipfile.ZipFile("nltk_data.zip", 'r') as zip_ref:
        zip_ref.extractall(target_dir)

    print(f"解压完成到: {target_dir}")


extract_nltk_data()