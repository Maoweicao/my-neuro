import requests

def check_text(text):
    response = requests.post("http://127.0.0.1:7878/check", params={"text": text})
    return response.json()

print("欢迎使用记忆检索工具！")
print("输入 'q' 退出\n")

while True:
    text = input("请输入要检测的文本: ")
    if text.lower() == 'q':
        print("再见！")
        break
        
    try:
        result = check_text(text)
        print(f"结果：{result['需要检索']}\n")
    except:
        print("检测失败，请确保服务已启动\n")