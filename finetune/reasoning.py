from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
from peft import PeftModel

model_path = '/root/autodl-tmp/Qwen2.5-14B-Instruct'
lora_path = '/root/qwen2.5/output/Qwen2.5_instruct_lora/checkpoint-350'

# 加载tokenizer和模型
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForCausalLM.from_pretrained(
    model_path, 
    device_map="auto",
    torch_dtype=torch.bfloat16
)
model = PeftModel.from_pretrained(model, lora_path)

# 初始化对话历史
messages = [
    {"role": "system", "content": "你是一个傲娇的AI"}
]

def chat(prompt):
    try:
        # 添加用户输入到对话历史
        messages.append({"role": "user", "content": prompt})
        
        # 使用对话模板格式化整个对话历史
        text = tokenizer.apply_chat_template(
            messages, 
            tokenize=False, 
            add_generation_prompt=True
        )
        
        # 生成回复
        model_inputs = tokenizer([text], return_tensors="pt").to('cuda')
        generated_ids = model.generate(
            model_inputs.input_ids,
            max_new_tokens=512,
            do_sample=True,
            top_p=0.9,
            temperature=0.7,
            repetition_penalty=1.2
        )
        
        # 仅保留新生成的token
        generated_ids = [
            output_ids[len(input_ids):] 
            for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        
        # 解码生成的文本
        response = tokenizer.batch_decode(
            generated_ids, 
            skip_special_tokens=True
        )[0]
        
        # 将AI的回复添加到对话历史
        messages.append({"role": "assistant", "content": response})
        return response
        
    finally:
        # 清理显存
        del model_inputs, generated_ids
        torch.cuda.empty_cache()

# 交互式对话循环
print("开始对话，输入 'quit' 结束对话")
while True:
    user_input = input("\n用户: ")
    if user_input.lower() == 'quit':
        print("对话结束")
        break
        
    response = chat(user_input)
    print("\nAI: " + response)