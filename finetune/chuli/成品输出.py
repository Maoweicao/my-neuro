import json

input_file = '/root/qwen2.5/chuli/多轮对话处理合并.txt'
output_file = '/root/qwen2.5/data/train.json'

def parse_dialogue(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
        
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
    with open(output_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=2)

parsed_data = parse_dialogue(input_file)
save_to_json(parsed_data, output_file)
print(f"成功保存： {output_file}")