from fastapi import FastAPI
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from pydantic import BaseModel

app = FastAPI()


class TextInput(BaseModel):
    text: str


# 检测是否有可用的GPU
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Using device: {device}")

# 标签映射
label_mapping = {"0": "否", "1": "是"}

# 固定的模型路径
model_path = "omni_bert"
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForSequenceClassification.from_pretrained(model_path)

# 将模型移动到GPU
model = model.to(device)
model.eval()


@app.post("/classify")
async def classify_emotion(input_data: TextInput):
    text = input_data.text
    # 预测
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True, max_length=512)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = model(**inputs)
        probabilities = torch.sigmoid(outputs.logits).cpu().numpy()[0]
        predictions = (probabilities > 0.5).astype(int)

    # 转换为文本标签并分开返回
    result_labels = [label_mapping[str(pred)] for pred in predictions]

    # 返回分开的标签结果
    return {
        "text": text,
        "Vision": result_labels[0],  # 第一个标签
        "core memory": result_labels[1]  # 第二个标签
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=6007)