import json
import os

# 获取当前文件所在目录，然后构建config.json的路径
current_dir = os.path.dirname(__file__)
config_path = os.path.join(current_dir, 'config.json')

def load_config():
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
        return config

if __name__ == '__main__':
    config_data = load_config()
    print(config_data)