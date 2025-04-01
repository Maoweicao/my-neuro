import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, Seq2SeqTrainingArguments, Seq2SeqTrainer
from datasets import load_dataset, Dataset
from peft import LoraConfig, TaskType, get_peft_model
from transformers import DataCollatorForSeq2Seq
import json

print("加载tokenizer和模型...")
tokenizer = AutoTokenizer.from_pretrained('tokenizer路径（和模型相同的路径）', 
                                       use_fast=False, 
                                       trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained('LLM模型路径',
                                           device_map="auto",
                                           torch_dtype=torch.bfloat16)
print("模型加载完成")

class CustomDataCollator(DataCollatorForSeq2Seq):
    def __call__(self, features):
        # 过滤掉None值
        features = [f for f in features if f is not None]
        if not features:
            return None
            
        # 确保所有的features都是正确的格式
        for feature in features:
            for k, v in feature.items():
                if isinstance(v, list):
                    feature[k] = torch.tensor(v)
        
        batch = super().__call__(features)
        return batch

def process_func(example):
    # 增加最大长度
    MAX_LENGTH = 1024
    
    # 检查必要字段
    if not example['instruction'] or not example['output']:
        return None
    
    # 构建简化的prompt格式
    prompt = (f"<|im_start|>user\n{example['instruction']}{example['input']}<|im_end|>\n"
             f"<|im_start|>assistant\n{example['output']}<|im_end|>")
    
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
    
    # 找到assistant回答的起始位置
    assistant_start = prompt.find("<|im_start|>assistant\n")
    assistant_token_start = len(tokenizer(prompt[:assistant_start], add_special_tokens=False)['input_ids'])
    
    # 设置标签
    labels[assistant_token_start:] = encodings['input_ids'][assistant_token_start:]
    
    return {
        "input_ids": encodings['input_ids'],
        "attention_mask": encodings['attention_mask'],
        "labels": labels
    }

# 加载并处理数据集
print("加载并处理数据集...")
dataset = load_dataset('json', data_files='data/train.json')

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

# 配置LoRA
print("配置LoRA参数...")
lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    inference_mode=False,
    r=8,
    lora_alpha=32,
    lora_dropout=0.05
)

# 将模型转换为PEFT模型
model = get_peft_model(model, lora_config)
# 优化设置：开启梯度检查点和输入梯度
model.gradient_checkpointing_enable()
model.enable_input_require_grads()
print("PEFT模型准备完成")

# 优化后的训练参数
print("配置训练参数...")
training_args = Seq2SeqTrainingArguments(
    output_dir="./output/Qwen2.5_instruct_lora",
    # 批处理和梯度累积
    per_device_train_batch_size=1,
    gradient_accumulation_steps=16,
    
    # 学习率设置
    learning_rate=2e-4,
    warmup_steps=0,
    max_grad_norm=1.0,
    
    # 训练步数设置
    logging_steps=10,
    num_train_epochs=15,
    
    # 保存策略
    save_steps=50,
    save_total_limit=5,
    save_on_each_node=True,
    
    # 显存和性能优化
    gradient_checkpointing=True,
    bf16=True,                # 使用 bfloat16 精度
    fp16=False,              # 不使用 float16
    remove_unused_columns=False,
    optim="adamw_torch",
    
    # 其他优化
    dataloader_pin_memory=True,   # 数据加载优化
    group_by_length=True,         # 相似长度样本分组
    lr_scheduler_type="linear",   # 不使用余弦学习率调度
    weight_decay=0.01,            # 权重衰减
    max_steps=-1,                 
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
    # 保存模型
    print("保存模型...")
    trainer.save_model()
    print("模型保存完成!")
