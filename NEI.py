from flask import Flask, request, Response
import requests
import logging
import json
import time
from flask_cors import CORS
import os
from datetime import datetime
from io import BytesIO

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # 启用CORS支持

# 确保对话记录目录存在
LOGS_DIR = "conversation_logs"
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# 当前对话文件路径
CURRENT_CONVERSATION_FILE = os.path.join(LOGS_DIR, "conversation.txt")


@app.route('/v1/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy(path):
    try:
        # 记录用户请求内容
        user_data = request.get_data()
        user_data_str = user_data.decode('utf-8', errors='replace') if user_data else ""

        logger.info(f"用户请求路径: /{path}")
        logger.info(f"用户请求方法: {request.method}")

        # 转发请求到中转URL
        target_url = f'https://api.zhizengzeng.com/v1/{path}'
        logger.info(f"转发到: {target_url}")

        # 过滤请求头
        headers = {key: value for (key, value) in request.headers.items()
                   if key.lower() not in ('host', 'content-length')}

        # 发送请求并获取响应
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=user_data,
            cookies=request.cookies,
            stream=True,
            timeout=120  # 增加超时时间到2分钟
        )

        # 获取响应头信息
        response_headers = dict(resp.headers)
        if 'Transfer-Encoding' in response_headers:
            del response_headers['Transfer-Encoding']

        logger.info(f"响应状态码: {resp.status_code}")

        # 判断是否为流式响应
        is_stream = 'text/event-stream' in response_headers.get('Content-Type', '')

        # 如果是流式响应，我们需要特殊处理
        if is_stream:
            # 使用内存缓冲区记录完整响应
            buffer = BytesIO()

            def generate():
                for chunk in resp.iter_content(chunk_size=1024):
                    if chunk:
                        # 保存到缓冲区
                        buffer.write(chunk)
                        yield chunk

                # 在流式输出完成后记录对话
                try:
                    user_request = json.loads(user_data_str)
                    messages = user_request.get("messages", [])

                    # 从流式响应中提取完整的AI回复文本
                    buffer.seek(0)
                    response_content = buffer.getvalue().decode('utf-8', errors='replace')
                    ai_response = extract_full_response(response_content)

                    # 保存到持续对话文件
                    append_to_conversation(messages, ai_response)

                except Exception as e:
                    logger.error(f"保存对话记录时出错: {str(e)}")

            return Response(
                generate(),
                status=resp.status_code,
                headers=response_headers,
                direct_passthrough=True
            )
        else:
            # 非流式响应，直接获取全部内容
            response_content = resp.content

            try:
                # 提取用户消息
                user_request = json.loads(user_data_str)
                messages = user_request.get("messages", [])

                # 提取响应
                response_str = response_content.decode('utf-8', errors='replace')
                try:
                    response_json = json.loads(response_str)
                    ai_response = response_json.get("choices", [{}])[0].get("message", {}).get("content", "")
                except:
                    ai_response = response_str

                # 保存到持续对话文件
                append_to_conversation(messages, ai_response)

            except Exception as e:
                logger.error(f"保存对话记录时出错: {str(e)}")

            # 返回响应
            return Response(
                response_content,
                status=resp.status_code,
                headers=response_headers
            )

    except Exception as e:
        logger.error(f"处理请求时发生错误: {str(e)}")
        return Response(f"代理服务器错误: {str(e)}", status=500)


def extract_full_response(sse_content):
    """从SSE格式的响应中提取完整的AI回复文本"""
    full_text = ""

    for line in sse_content.split('\n'):
        if line.startswith('data:') and line.strip() != 'data: [DONE]':
            data_content = line[5:].strip()
            if data_content:
                try:
                    chunk_json = json.loads(data_content)
                    content = chunk_json.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if content:
                        full_text += content
                except:
                    pass

    return full_text


def append_to_conversation(messages, ai_response):
    """将对话追加到单个文件中，用空行分隔不同对话"""
    try:
        # 检查是否是新对话的开始（通过判断system消息是否出现在第一位）
        is_new_conversation = False
        if messages and messages[0].get("role") == "system":
            # 如果第一条消息是system消息，并且用户只发送了一条或两条消息，认为是新对话
            if len(messages) <= 2:  # system + 可能的第一条用户消息
                is_new_conversation = True

        # 准备要追加的文本
        text_content = ""

        # 如果是新对话，添加空行
        if is_new_conversation:
            logger.info("检测到新对话开始")

            # 检查文件是否存在，如果不存在则创建
            file_exists = os.path.exists(CURRENT_CONVERSATION_FILE)

            # 如果文件已存在，添加两个空行作为分隔
            if file_exists:
                with open(CURRENT_CONVERSATION_FILE, 'a+', encoding='utf-8') as f:
                    f.write("\n\n")

            # 找到system消息和用户消息
            system_msg = None
            user_msg = None

            for msg in messages:
                if msg.get("role") == "system":
                    system_msg = msg.get("content", "")
                elif msg.get("role") == "user":
                    user_msg = msg.get("content", "")

            # 添加system和用户消息
            if system_msg:
                text_content += f"system: {system_msg}\n"
            if user_msg:
                text_content += f"用户: {user_msg}\n"
        else:
            # 不是新对话，只添加最后一条用户消息
            for msg in reversed(messages):
                if msg.get("role") == "user":
                    text_content += f"用户: {msg.get('content', '')}\n"
                    break

        # 添加模型的回复（替换掉回复中的换行符）
        formatted_response = ai_response.replace('\n', ' ')
        text_content += f"模型: {formatted_response}\n"

        # 追加到文件
        with open(CURRENT_CONVERSATION_FILE, 'a+', encoding='utf-8') as f:
            f.write(text_content)

        logger.info(f"对话已追加到: {CURRENT_CONVERSATION_FILE}")
    except Exception as e:
        logger.error(f"追加对话记录时出错: {str(e)}")


if __name__ == '__main__':
    logger.info("启动代理服务器...")
    # 检查是否服务器重启
    if os.path.exists(CURRENT_CONVERSATION_FILE):
        # 在文件末尾添加重启标记
        with open(CURRENT_CONVERSATION_FILE, 'a+', encoding='utf-8') as f:
            restart_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"\n\n[服务器于 {restart_time} 重启]\n\n")
        logger.info(f"检测到服务器重启，已在对话记录中添加标记")

    app.run(host='0.0.0.0', port=7000, threaded=True)