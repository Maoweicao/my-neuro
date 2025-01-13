
### 下面的部署教程暂时仅限于Linux 系统

### 第一步，创建虚拟环境并激活

```bash
conda create -n my-neuro python=3.10 -y #首先创建一个虚拟环境
source activate my-neuro #激活环境
```

### 第二步，下载需要的依赖包

```bash
pip install -r requirements.txt
```

### 第三步，下载开源LLM模型

```bash
modelscope download --model Qwen/Qwen2.5-7B-Instruct #下载指令
```
