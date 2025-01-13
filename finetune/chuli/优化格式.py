import re

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


input_file_path = '/root/qwen2.5/放置数据集.txt'
output_file_path = '/root/qwen2.5/chuli/多轮对话处理合并.txt'

# Read the input file
with open(input_file_path, 'r', encoding='utf-8') as file:
    conversations = file.readlines()

# Process the conversations
merged_conversations = merge_conversations(conversations)

# Write the output to a new file
with open(output_file_path, 'w', encoding='utf-8') as file:
    for line in merged_conversations:
        file.write(line + '\n')

output_file_path
