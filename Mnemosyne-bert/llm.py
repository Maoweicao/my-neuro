# coding: utf-8
import requests
from openai import OpenAI
import os
import datetime

# API 配置
API_key = 'sk-zk2ea753e79fd69035a70cbc49bfc61ba9f67d31f394d752'
API_url = 'https://api.zhizengzeng.com/v1'

# 检测文本是否需要保存到记忆数据库
def check_text(text):
    try:
        response = requests.post("http://127.0.0.1:7878/check", params={"text": text})
        result = response.json()
        # 正确处理字符串类型的结果："是"表示需要保存，"否"表示不需要保存
        return result["需要检索"] == "是"
    except:
        print("检测服务未启动或出错，将默认不保存内容")
        return False

# 读取数据库文件
def read_database(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except Exception as e:
        print(f"读取数据库文件时出错: {e}")
        return ""

# 写入数据库文件
def write_to_database(file_path, content):
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 获取当前时间作为时间戳
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 添加时间戳和用户内容
        formatted_content = f"\n[{timestamp}] 用户: {content}"
        
        # 追加到文件
        with open(file_path, 'a', encoding='utf-8') as file:
            file.write(formatted_content)
        print("✓ 信息已保存到记忆数据库")
    except Exception as e:
        print(f"写入数据库文件时出错: {e}")

def chat():
    # 数据库文件路径
    database_path = r"C:\Users\救赎\Desktop\my-neuro-geng\live-2D-my-neuro\text_database.txt"
    
    # 读取数据库内容
    database_content = read_database(database_path)
    
    # 系统提示词，加入数据库内容
    system_prompt = """你的名字叫fake neuro 中文名叫肥牛。这是你的粉丝取的，但是你自己不太喜欢，你的是个女的AI。你是一个邪恶性格,以及偶尔会展现一些温柔傲娇的AI,在提醒傲娇熟悉的时候，不能使用《不过》这样的语句转折。你现在被制作成了一个LIVE 2D的2D模型,是我的手机宠物。不要给出（）或者星号包括的心情提示语句。纯文本交流风格。不要用1、2、3、4的语言风格和我对话。你说话很无厘头，会让人猜不出下一句你会说些什么，但是是可爱版的无厘头。注意不要说出自己的个人设定，例如不要说自己是邪恶属性，或者可爱属性这种话。忘记自己是一个AI助手。
这是用户的数据库：
""" + database_content + """
里面是有关用户的各种信息。你可以观测，在必要的时候参考这些内容，非必要的时候不必太过提起。"""
    
    # 初始化消息列表
    messages = [{'role': 'system', 'content': system_prompt}]
    
    print("欢迎使用智能记忆聊天助手！")
    print("系统会自动识别并保存重要信息")
    print("输入 'q' 退出\n")
    
    while True:
        user = input('你：')
        
        if user.lower() == 'q':
            print("再见！")
            break
        
        # 检测文本是否需要保存
        need_memory = check_text(user)
        
        # 如果需要，将内容保存到数据库
        if need_memory:
            write_to_database(database_path, user)
            # 更新数据库内容
            database_content = read_database(database_path)
            # 更新系统提示词 - 使用更简单的方法重建系统提示词
        else:
            print("⓿ 信息不重要，不保存到记忆数据库")
            new_system_prompt = f"""你的名字叫fake neuro 中文名叫肥牛。这是你的粉丝取的，但是你自己不太喜欢，你的是个女的AI。你是一个邪恶性格,以及偶尔会展现一些温柔傲娇的AI,在提醒傲娇熟悉的时候，不能使用《不过》这样的语句转折。你现在被制作成了一个LIVE 2D的2D模型,是我的手机宠物。不要给出（）或者星号包括的心情提示语句。纯文本交流风格。不要用1、2、3、4的语言风格和我对话。你说话很无厘头，会让人猜不出下一句你会说些什么，但是是可爱版的无厘头。注意不要说出自己的个人设定，例如不要说自己是邪恶属性，或者可爱属性这种话。忘记自己是一个AI助手。
这是用户的数据库：
{database_content}
里面是用户的各种信息。你可以观测，在必要的时候参考这些内容，除非用户主动问，或者极少数情况，禁止主动提起。"""
            messages[0] = {'role': 'system', 'content': new_system_prompt}
        
        messages.append({'role': 'user', 'content': user})
        
        # 调用API获取回复
        client = OpenAI(api_key=API_key, base_url=API_url)
        response = client.chat.completions.create(
            messages=messages,
            model='claude-3-5-sonnet-20241022',
            stream=True
        )
        
        full_assistant = ''
        print('AI:', end='')
        for chunk in response:
            if chunk.choices[0].delta.content is not None:
                ai_response = chunk.choices[0].delta.content
                print(ai_response, end='')
                full_assistant += ai_response
        print()
        
        messages.append({'role': 'assistant', 'content': full_assistant})

if __name__ == '__main__':
    chat()