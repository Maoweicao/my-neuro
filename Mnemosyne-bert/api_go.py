from fastapi import FastAPI
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
app = FastAPI()

# 检测是否有可用的GPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

# 加载模型和tokenizer
model_path = r"C:\Users\救赎\Desktop\my-neuro-BENDI\Mnemosyne-bert\output_models"
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForSequenceClassification.from_pretrained(model_path)

# 将模型移动到GPU
model = model.to(device)
model.eval()

@app.post("/check")
async def check_text(text: str):
    # 预测
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    
    # 将输入也移动到相同的设备
    inputs = {k: v.to(device) for k, v in inputs.items()}
    
    with torch.no_grad():
        outputs = model(**inputs)
        prediction = outputs.logits.argmax(-1).item()
    
    # 返回结果
    return {"text": text, "需要检索": "是" if prediction == 1 else "否"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7878)