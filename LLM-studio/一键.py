import re
import json
import os

def merge_conversations(conversations):
    merged_conversations = []
    prev_speaker = None
    merged_line = ""
    
    for line in conversations:
        # 修改正则表达式以匹配"指令："、"问："和"答："
        match = re.match(r"^(指令|问|答)[：:](.+)$", line.strip())
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
    content = '\n'.join(merged_conversations)
    dialogues = content.strip().split('\n\n')
    parsed_data = []
    
    for dialogue in dialogues:
        lines = dialogue.split('\n')
        
        # 跳过不包含分隔符的行
        valid_lines = [line for line in lines if '：' in line]
        if not valid_lines:
            continue
        
        # 检查是否包含"指令："
        has_instruction = any(line.startswith("指令：") for line in valid_lines)
        
        if has_instruction:
            # 处理带有"指令："的对话格式
            instruction_line = next((line for line in valid_lines if line.startswith("指令：")), None)
            qa_pairs = [(line for line in valid_lines if line.startswith("问：") or line.startswith("答："))]
            
            # 提取指令内容
            _, instruction_content = instruction_line.split('：', 1)
            
            # 组织问答对
            history = []
            input_text = ""
            
            # 处理问答对
            question_lines = [line for line in valid_lines if line.startswith("问：")]
            answer_lines = [line for line in valid_lines if line.startswith("答：")]
            
            if question_lines and answer_lines:
                # 第一个问作为input
                _, input_text = question_lines[0].split('：', 1)
                
                # 其余问答对作为history
                for i in range(1, min(len(question_lines), len(answer_lines))):
                    _, q = question_lines[i].split('：', 1)
                    _, a = answer_lines[i-1].split('：', 1)
                    history.append([q, a])
                
                # 最后一个答案作为output
                _, output_text = answer_lines[-1].split('：', 1)
                
                parsed_data.append({
                    "instruction": instruction_content,
                    "input": input_text,
                    "output": output_text,
                    "history": history
                })
        else:
            # 原有的处理逻辑
            processed_turns = []
            for i in range(0, len(valid_lines), 2):
                if i + 1 < len(valid_lines):
                    question_line = valid_lines[i]
                    answer_line = valid_lines[i + 1]
                    
                    # 分割问题和答案
                    _, question = question_line.split('：', 1)
                    _, answer = answer_line.split('：', 1)
                    
                    processed_turns.append([question, answer])
            
            # 构造最终的训练数据结构
            if processed_turns:
                # 第一轮对话作为instruction和output
                first_turn = processed_turns[0]
                
                # 第二轮及以后的对话作为history
                history = processed_turns[1:] if len(processed_turns) > 1 else []
                
                parsed_data.append({
                    "instruction": first_turn[0],
                    "input": "",
                    "output": first_turn[1],
                    "history": history
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
