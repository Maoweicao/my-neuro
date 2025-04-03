import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, Seq2SeqTrainingArguments, Seq2SeqTrainer
from datasets import load_dataset, Dataset
from transformers import DataCollatorForSeq2Seq

print("加载tokenizer和模型...")
tokenizer = AutoTokenizer.from_pretrained('/root/autodl-tmp/Qwen2.5-7B-Instruct', 
                                       use_fast=False, 
                                       trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained('/root/autodl-tmp/Qwen2.5-7B-Instruct',
                                           device_map="auto",
                                           torch_dtype=torch.bfloat16)
print("模型加载完成")

class CustomDataCollator(DataCollatorForSeq2Seq):
    def __call__(self, features):
        features = [f for f in features if f is not None]
        if not features:
            return None
            
        for feature in features:
            for k, v in feature.items():
                if isinstance(v, list):
                    feature[k] = torch.tensor(v)
        
        batch = super().__call__(features)
        return batch

def build_conversation_prompt(example):
    """
    构建对话prompt
    example: 包含history、instruction和output的字典
    """
    prompt = ""
    
    # 添加历史对话
    if example.get('history'):
        for user_msg, assistant_msg in example['history']:
            prompt += f"<|im_start|>user\n{user_msg}<|im_end|>\n"
            prompt += f"<|im_start|>assistant\n{assistant_msg}<|im_end|>\n"
    
    # 添加当前轮次的对话
    current_input = example.get('instruction', '')
    if example.get('input'):  # 如果有额外输入，添加到instruction后
        current_input += example['input']
    
    prompt += f"<|im_start|>user\n{current_input}<|im_end|>\n"
    prompt += f"<|im_start|>assistant\n{example['output']}<|im_end|>\n"
    
    return prompt.strip()

def process_func(example):
    MAX_LENGTH = 2548  # 增加最大长度以支持更长的对话
    
    # 检查必要字段
    if not example.get('instruction') or not example.get('output'):
        return None
    
    # 构建对话prompt
    prompt = build_conversation_prompt(example)
    
    # 检查总长度
    if len(tokenizer(prompt)['input_ids']) > MAX_LENGTH:
        return None
    
    # 编码
    encodings = tokenizer(prompt, 
                         truncation=True,
                         max_length=MAX_LENGTH,
                         padding=False,
                         return_tensors=None)
    
    # 构建标签
    labels = [-100] * len(encodings['input_ids'])
    
    # 找到最后一个assistant回答的起始位置
    last_assistant_start = prompt.rindex("<|im_start|>assistant\n")
    assistant_token_start = len(tokenizer(prompt[:last_assistant_start], add_special_tokens=False)['input_ids'])
    
    # 只对最后一轮assistant的回复进行训练
    labels[assistant_token_start:] = encodings['input_ids'][assistant_token_start:]
    
    return {
        "input_ids": encodings['input_ids'],
        "attention_mask": encodings['attention_mask'],
        "labels": labels
    }

# 加载并处理数据集
print("加载并处理数据集...")
dataset = load_dataset('json', data_files='/root/my-neuro/data/train.json')

# 添加数据验证
def validate_and_process_dataset(dataset):
    valid_examples = []
    for example in dataset['train']:
        processed = process_func(example)
        if processed is not None:
            valid_examples.append(processed)
    return Dataset.from_list(valid_examples)

tokenized_dataset = validate_and_process_dataset(dataset)
print(f"数据集处理完成,共有{len(tokenized_dataset)}条有效样本")

# 开启梯度检查点以节省显存
model.gradient_checkpointing_enable()

# 训练参数配置
print("配置训练参数...")
training_args = Seq2SeqTrainingArguments(
    output_dir="/root/autodl-tmp/output",
    per_device_train_batch_size=1,
    gradient_accumulation_steps=32,
    learning_rate=5e-5,
    warmup_steps=100,
    max_grad_norm=1.0,
    logging_steps=10,
    num_train_epochs=4,
    save_steps=120,
    save_total_limit=1,     # 只保留最新的一个检查点
    save_on_each_node=True,
    gradient_checkpointing=True,
    bf16=True,
    fp16=False,
    remove_unused_columns=False,
    optim="adamw_torch",
    dataloader_pin_memory=True,
    group_by_length=True,
    lr_scheduler_type="cosine",
    weight_decay=0.01,
    max_steps=-1,
    save_strategy="steps",
    save_only_model=True,    # 只保存模型权重
    save_safetensors=True,   # 使用safetensors格式保存
    overwrite_output_dir=True  # 如果输出目录已存在则覆盖
)

# 创建Trainer并开始训练
print("创建Trainer并开始训练...")
trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,
    data_collator=CustomDataCollator(
        tokenizer,
        padding=True,
        return_tensors="pt"
    ),
)

# 开始训练
print("开始训练...")
try:
    trainer.train()
    print("训练成功完成!")
except Exception as e:
    print(f"训练过程中发生错误: {str(e)}")
finally:
    print("保存模型...")
    trainer.save_model()
    print("模型保存完成!")