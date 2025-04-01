import json
import os

# 获取当前脚本所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 构建输入输出路径
input_file = os.path.join(current_dir, '..', 'Dataset.txt')
output_dir = os.path.join(current_dir, '..', 'data')
output_file = os.path.join(output_dir, 'train.json')

def parse_dialogue(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()
    except FileNotFoundError:
        print(f"找不到输入文件: {file_path}")
        print(f"当前工作目录: {os.getcwd()}")
        exit(1)
        
    dialogues = content.strip().split('\n\n')
    parsed_data = []
    
    for dialogue in dialogues:
        lines = dialogue.split('\n')
        
        # 跳过不包含分隔符的行
        valid_lines = [line for line in lines if '：' in line]
        if not valid_lines:
            continue
        
        first_speaker, first_sentence = valid_lines[0].split('：', 1)
        
        # 检查对话的第一个发言者是答还是问，并相应设置
        if first_speaker == "问":
            instruction = first_sentence
            if len(valid_lines) > 1:
                output = valid_lines[1].split('：', 1)[1]  # B的回答作为输出
            else:
                output = ""
        else:
            instruction = "你好"
            output = first_sentence
        
        parsed_data.append({
            "instruction": instruction,
            "input": "",
            "output": output
        })
    
    return parsed_data

def save_to_json(data, output_path):
    # 确保输出目录存在
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    try:
        with open(output_path, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"保存JSON文件时出错: {e}")
        exit(1)

try:
    parsed_data = parse_dialogue(input_file)
    save_to_json(parsed_data, output_file)
    print(f"成功保存到: {output_file}")
except Exception as e:
    print(f"处理过程中出错: {e}")
