import re
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

# 获取当前脚本所在的目录
current_dir = os.path.dirname(os.path.abspath(__file__))

# 构建输入输出路径
input_file_path = os.path.join(current_dir, '..', 'Dataset.txt')
output_file_path = os.path.join(current_dir, 'meger_text.txt')

# 确保输出目录存在
os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

# 读取输入文件
try:
    with open(input_file_path, 'r', encoding='utf-8') as file:
        conversations = file.readlines()
except FileNotFoundError:
    print(f"找不到输入文件: {input_file_path}")
    print(f"当前工作目录: {os.getcwd()}")
    exit(1)

# 处理对话
merged_conversations = merge_conversations(conversations)

# 写入输出文件
try:
    with open(output_file_path, 'w', encoding='utf-8') as file:
        for line in merged_conversations:
            file.write(line + '\n')
    print(f"处理完成！输出文件保存在: {output_file_path}")
except Exception as e:
    print(f"写入文件时出错: {e}")
