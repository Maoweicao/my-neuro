import re
import json
import os

def merge_conversations(conversations):
    merged_conversations = []
    prev_speaker = None
    merged_line = ""
    
    for line in conversations:
        match = re.match(r"^(问|答)[：:](.+)$", line.strip())
        if match:
            speaker, content = match.groups()
            if speaker == prev_speaker:
                merged_line += "。" + content
            else:
                if merged_line:
                    merged_conversations.append(f"{prev_speaker}：{merged_line}")
                prev_speaker = speaker
                merged_line = content
        else:
            if merged_line:
                merged_conversations.append(f"{prev_speaker}：{merged_line}")
            merged_conversations.append(line.strip())
            prev_speaker = None
            merged_line = ""
            
    if merged_line:
        merged_conversations.append(f"{prev_speaker}：{merged_line}")
    
    return merged_conversations

def parse_dialogue(merged_conversations):
    # 将合并后的对话拼接成字符串，以便按照空行分割
    content = '\n'.join(merged_conversations)
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
                output = valid_lines[1].split('：', 1)[1]  # 答的回应作为输出
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
        print(f"成功保存到: {output_path}")
    except Exception as e:
        print(f"保存JSON文件时出错: {e}")
        exit(1)

# 获取当前脚本所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 构建输入输出路径
input_file_path = os.path.join(current_dir, 'Dataset.txt')
merged_file_path = os.path.join(current_dir, 'merged_text.txt')
output_dir = os.path.join(current_dir, 'data')
output_json_path = os.path.join(output_dir, 'train.json')

# 确保输出目录存在
os.makedirs(os.path.dirname(merged_file_path), exist_ok=True)
os.makedirs(output_dir, exist_ok=True)

# 处理流程
try:
    # 1. 读取输入文件
    with open(input_file_path, 'r', encoding='utf-8') as file:
        conversations = file.readlines()
    
    # 2. 合并对话
    merged_conversations = merge_conversations(conversations)
    
    # 3. 保存合并后的文本文件(可选)
    with open(merged_file_path, 'w', encoding='utf-8') as file:
        for line in merged_conversations:
            file.write(line + '\n')
    print(f"对话合并完成！输出文件保存在: {merged_file_path}")
    
    # 4. 解析对话为训练数据格式
    parsed_data = parse_dialogue(merged_conversations)
    
    # 5. 保存为JSON格式
    save_to_json(parsed_data, output_json_path)
    
except FileNotFoundError:
    print(f"找不到输入文件: {input_file_path}")
    print(f"当前工作目录: {os.getcwd()}")
    exit(1)
except Exception as e:
    print(f"处理过程中出错: {e}")
    exit(1)
