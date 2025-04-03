from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from threading import Thread

model_name = "模型路径"

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype="auto",
    device_map="auto"
)
tokenizer = AutoTokenizer.from_pretrained(model_name)
messages = [
    {"role": "system","content": ""}
]

def chat():
    while True:
        user = input('你：')
        messages.append({"role": "user","content": user})

        text = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
        input_length = model_inputs.input_ids.shape[1]  # 记录输入长度

        streamer = TextIteratorStreamer(tokenizer, skip_special_tokens=True, skip_prompt=True)
        generation_kwargs = dict(
            **model_inputs,
            streamer=streamer,
            max_new_tokens=512
        )
        
        thread = Thread(target=model.generate, kwargs=generation_kwargs)
        thread.start()

        print("AI: ", end="", flush=True)
        response = ""
        for new_text in streamer:
            print(new_text, end="", flush=True)
            response += new_text
        print()  # 换行
        
        messages.append({"role": "assistant","content": response})

if __name__ == '__main__':
    chat()
