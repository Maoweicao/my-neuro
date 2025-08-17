import os
import numpy as np
import torch
import torch.nn as nn
import math
from model import Model_args,GPT
import time

# 模型参数
block_size = 128 # 窗口大小GPT2为1024
batch_size = 16 # 暂定，之后再看显存占用
n_layer = 12
n_head = 6
n_embed = 768
bias = False
dropout = 0.0
dataset_path = 'data/dmbj'
init_from = 'scratch' # 'scratch' or 'resume' # 从头训练还是继续
checkpoint_save_dir = 'checkpoints'
eval_iters = 200
eval_interval = 200 # 每n步eval和保存checkpoint一次

# 学习率衰减 - 调整为更合理的值
learning_rate = 3e-4  # 降低学习率
warmup_iters = 200
lr_decay_iters = 2000  # 延长衰减周期
min_lr = 3e-5

# 优化器参数
max_iters = 20000 # 增加训练步数
weight_decay = 1e-1
betas = (0.9,0.95)
grad_clip = 1.0 # 梯度裁剪

# system
device = 'cuda'
device_type = 'cuda'
dtype = 'bfloat16' if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else 'float16'

ptdtype = {'float32': torch.float32, 'bfloat16': torch.bfloat16, 'float16': torch.float16}[dtype]
ctx = torch.amp.autocast(device_type=device_type, dtype=ptdtype)

# dataloader
data_dir = os.path.join(dataset_path)
def get_batch(split):
    if split == 'train':
        data = np.memmap(os.path.join(data_dir, 'train.bin'), dtype=np.uint32, mode='r')
    else:
        data = np.memmap(os.path.join(data_dir, 'val.bin'), dtype=np.uint32, mode='r')
    
    ix = torch.randint(len(data)-block_size,(batch_size,))
    x = torch.stack([torch.from_numpy((data[i:i+block_size].astype(np.int64))) for i in ix])
    y = torch.stack([torch.from_numpy((data[i+1:i+1+block_size].astype(np.int64))) for i in ix])

    x,y = x.pin_memory().to(device,non_blocking=True),y.pin_memory().to(device,non_blocking=True)
    return x,y

model_args = dict(n_layer=n_layer, n_head=n_head, n_embed=n_embed, block_size=block_size,
                  bias=bias, vocab_size=None, dropout=dropout)

iter_num = 0
best_val_loss = 1e9

assert init_from == 'scratch' or init_from == 'resume'
if init_from == 'scratch': 
    print("从头训练模型")
    # 根据prepare.py的输出，最大token ID是151603，所以设置为151604
    model_args['vocab_size'] = 200000  # 修正词汇表大小
    gpt_args = Model_args(**model_args)
    model = GPT(gpt_args)

elif init_from == 'resume':
    print("继续训练模型")
    ckpt_path = os.path.join(checkpoint_save_dir,'checkpoint.pt')
    checkpoint = torch.load(ckpt_path, map_location=device)
    checkpoint_model_args = checkpoint['model_args']
    for k in ['n_layer', 'n_head', 'n_embed', 'block_size', 'bias', 'vocab_size']:
        model_args[k] = checkpoint_model_args[k]
    gpt_args = Model_args(**model_args)
    model = GPT(gpt_args)
    state_dict = checkpoint['model']
    model.load_state_dict(state_dict)
    iter_num = checkpoint['iter_num']
    best_val_loss = checkpoint['best_val_loss']

scaler = torch.cuda.amp.GradScaler(enabled=(dtype == 'float16'))
model.to(device)
optimizer = model.configure_optimizers(weight_decay,learning_rate,betas,device_type)
if init_from == 'resume':
    optimizer.load_state_dict(checkpoint['optimizer'])
checkpoint = None

def estimate_loss():
    model.eval()
    out = {}
    for split in ['train','val']:
        losses = torch.zeros(eval_iters)
        for k in range(eval_iters):
            X,Y = get_batch(split)
            with ctx:
                _,loss = model(X,Y)
            losses[k] = loss.item()
        out[split] = losses.mean()
    model.train()
    return out

def get_lr(now_iter):
    if(now_iter<warmup_iters):
        return learning_rate*now_iter/warmup_iters
    elif(now_iter>lr_decay_iters):
        return min_lr
    else:
        rate = (now_iter-warmup_iters)/(lr_decay_iters-warmup_iters)
        return min_lr + 0.5*(1.0+math.cos(math.pi*rate)) * (learning_rate-min_lr)

# 创建checkpoint目录
os.makedirs(checkpoint_save_dir, exist_ok=True)

# 训练代码
t_before = time.time()

# 初始评估
if iter_num == 0:
    loss_dict = estimate_loss()
    print(f"初始状态 - train_loss: {loss_dict['train']:.4f}, val_loss: {loss_dict['val']:.4f}")

while True:
    lr = get_lr(iter_num)
    for param_group in optimizer.param_groups:
        param_group['lr'] = lr
    
    if iter_num > 0 and iter_num % eval_interval == 0:
        loss_dict = estimate_loss()
        print(f"iter {iter_num} - train_loss: {loss_dict['train']:.4f}, val_loss: {loss_dict['val']:.4f}, lr: {lr:.2e}")
        
        if loss_dict['val'] < best_val_loss:
            best_val_loss = loss_dict['val']
            print(f"新的最佳验证loss: {best_val_loss:.4f}")
        
        # 修复checkpoint保存的bug
        checkpoint = {
            'model': model.state_dict(),
            'optimizer': optimizer.state_dict(),  # 修复：添加了()
            'model_args': model_args,
            'iter_num': iter_num,
            'best_val_loss': best_val_loss
        }
        torch.save(checkpoint, os.path.join(checkpoint_save_dir, 'checkpoint.pt'))
        print(f"checkpoint保存在{checkpoint_save_dir}/checkpoint.pt")
    
    # 🔥 关键修复：每次迭代都重新采样数据
    X, Y = get_batch('train')
    
    with ctx:
        logits, loss = model(X, Y)
        # 添加loss合理性检查
        if torch.isnan(loss) or torch.isinf(loss):
            print(f"警告：检测到异常loss值: {loss.item()}")
            break
            
        if iter_num % 50 == 0:  # 每50步打印一次，减少输出
            print(f"iter: {iter_num}, loss: {loss.item():.4f}, lr: {lr:.2e}")
        
        scaler.scale(loss).backward()
    
    if grad_clip > 0.0:
        scaler.unscale_(optimizer)
        nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
    
    scaler.step(optimizer)
    scaler.update()
    optimizer.zero_grad(set_to_none=True)

    t_after = time.time()
    dt = t_after - t_before
    t_before = t_after

    iter_num += 1
    if iter_num > max_iters:
        print(f"训练完成！总共训练了{max_iters}步")
        break

# 最终评估
print("进行最终评估...")
final_losses = estimate_loss()
print(f"最终结果 - train_loss: {final_losses['train']:.4f}, val_loss: {final_losses['val']:.4f}")
