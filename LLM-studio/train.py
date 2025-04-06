import torch
import yaml
import argparse
import os
from transformers import AutoModelForCausalLM, AutoTokenizer, Seq2SeqTrainingArguments, Seq2SeqTrainer
from datasets import load_dataset, Dataset
from transformers import DataCollatorForSeq2Seq

# 解析命令行参数(仅用于指定配置文件路径)
parser = argparse.ArgumentParser(description="LLM训练脚本 - 基于YAML配置")
parser.add_argument("--config", type=str, required=True, help="YAML配置文件路径")
args = parser.parse_args()

# 加载YAML配置
with open(args.config, 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# 提取配置项
model_config = config['model']
training_config = config['training']
data_config = config['data']

# 确保路径存在
model_path = os.path.expanduser(model_config['path'])
if not os.path.exists(model_path):
    raise ValueError(f"模型路径不存在: {model_path}")

print(f"加载tokenizer和模型从 {model_path}...")
tokenizer = AutoTokenizer.from_pretrained(
    model_path, 
    use_fast=False, 
    trust_remote_code=True,
    local_files_only=True  # 确保只使用本地文件
)
model = AutoModelForCausalLM.from_pretrained(
    model_path,
    device_map="auto",
    torch_dtype=torch.bfloat16,
    local_files_only=True  # 确保只使用本地文件
)
print("模型加载完成")

# 如果使用LoRA，进行额外配置
if model_config.get('use_lora', False):
    print("使用LoRA进行训练...")
    try:
        from peft import LoraConfig, TaskType, get_peft_model
        
        # 配置LoRA
        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            target_modules=model_config.get('lora_target_modules', 
                        ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]),
            inference_mode=False,
            r=model_config.get('lora_r', 8),
            lora_alpha=model_config.get('lora_alpha', 32),
            lora_dropout=model_config.get('lora_dropout', 0.05)
        )
        
        # 将模型转换为PEFT模型
        model = get_peft_model(model, lora_config)
        print("PEFT模型准备完成")
    except ImportError:
        print("警告: 无法导入PEFT库，将使用全参数训练替代")
else:
    print("使用全参数训练...")

# 启用梯度检查点以节省显存
model.gradient_checkpointing_enable()
if model_config.get('use_lora', False):
    try:
        model.enable_input_require_grads()
    except:
        print("警告: 启用input_require_grads失败，但训练可能仍能继续")

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
    MAX_LENGTH = data_config.get('max_length', 2048)
    
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
data_path = os.path.expanduser(data_config['path'])
print(f"加载并处理数据集从 {data_path}...")
if not os.path.exists(data_path):
    raise ValueError(f"数据文件不存在: {data_path}")

dataset = load_dataset('json', data_files=data_path)

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

# 确保输出目录存在
output_dir = os.path.expanduser(training_config['output_dir'])
os.makedirs(output_dir, exist_ok=True)
print(f"输出目录: {output_dir}")

# 训练参数配置
print("配置训练参数...")

# 创建训练参数
training_args = Seq2SeqTrainingArguments(
    output_dir=output_dir,
    report_to=training_config.get('report_to', 'tensorboard'),
    per_device_train_batch_size=training_config.get('batch_size', 1),
    gradient_accumulation_steps=training_config.get('gradient_accumulation_steps', 16),
    learning_rate=training_config.get('learning_rate', 5e-5),
    warmup_steps=training_config.get('warmup_steps', 100),
    max_grad_norm=training_config.get('max_grad_norm', 1.0),
    logging_steps=training_config.get('logging_steps', 10),
    num_train_epochs=training_config.get('epochs', 3),
    save_steps=training_config.get('save_steps', 120),
    save_total_limit=training_config.get('save_total_limit', 3),
    save_on_each_node=training_config.get('save_on_each_node', True),
    gradient_checkpointing=training_config.get('gradient_checkpointing', True),
    bf16=training_config.get('bf16', True),
    fp16=training_config.get('fp16', False),
    remove_unused_columns=training_config.get('remove_unused_columns', False),
    optim=training_config.get('optimizer', "adamw_torch"),
    dataloader_pin_memory=training_config.get('dataloader_pin_memory', True),
    group_by_length=training_config.get('group_by_length', True),
    lr_scheduler_type=training_config.get('lr_scheduler_type', "cosine"),
    weight_decay=training_config.get('weight_decay', 0.01),
    max_steps=training_config.get('max_steps', -1),
    save_strategy=training_config.get('save_strategy', "steps"),
    save_safetensors=training_config.get('save_safetensors', True),
    overwrite_output_dir=training_config.get('overwrite_output_dir', True)
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