#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
独立的WebAPI服务器
可以在不启动UI的情况下运行WebAPI服务
"""

import json
import os
import sys
import threading
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests

class WebAPIHandler(BaseHTTPRequestHandler):
    """WebAPI请求处理器"""
    
    def do_POST(self):
        """处理POST请求"""
        try:
            if self.path == '/api/chat':
                self._handle_chat_request()
            elif self.path == '/api/live2d/motion':
                self._handle_live2d_motion_request()
            elif self.path == '/api/live2d/expression':
                self._handle_live2d_expression_request()
            else:
                self._send_error_response(404, "Not Found")
        except Exception as e:
            self._send_error_response(500, f"Internal Server Error: {str(e)}")
    
    def do_GET(self):
        """处理GET请求"""
        if self.path == '/api/status':
            self._send_json_response({"status": "running", "message": "WebAPI服务正在运行"})
        else:
            self._send_error_response(404, "Not Found")
    
    def _handle_chat_request(self):
        """处理聊天请求"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_error_response(400, "Empty request body")
                return
            
            # 读取请求体
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # 验证必需字段
            if 'message' not in data:
                self._send_error_response(400, "Missing 'message' field")
                return
            
            message = data['message'].strip()
            if not message:
                self._send_error_response(400, "Empty message")
                return
            
            # 验证API密钥（如果配置了）
            config = self.server.config
            api_key = config.get('webapi', {}).get('api_key', '')
            if api_key and data.get('api_key') != api_key:
                self._send_error_response(401, "Invalid API key")
                return
            
            # 处理LLM请求
            response_text = self._process_llm_request(message, config)
            
            self._send_json_response({
                "response": response_text,
                "status": "success",
                "timestamp": time.time()
            })
            
        except json.JSONDecodeError:
            self._send_error_response(400, "Invalid JSON")
        except Exception as e:
            self._send_error_response(500, f"Server error: {str(e)}")
    
    def _process_llm_request(self, message, config):
        """处理LLM请求"""
        try:
            # 获取LLM配置
            llm_config = config.get('llm', {})
            if not llm_config.get('api_url') or not llm_config.get('api_key'):
                return "错误：LLM配置不完整，请检查API URL和API Key设置"
            
            # 构建请求
            api_url = llm_config['api_url'].rstrip('/') + '/chat/completions'
            api_key = llm_config['api_key']
            model = llm_config.get('model', 'gpt-3.5-turbo')
            system_prompt = llm_config.get('system_prompt', '你是一个有用的AI助手。')
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            
            # 构建消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": message}
            ]
            
            data = {
                "model": model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 1000
            }
            
            print(f"🔄 [LLM请求] 用户: {message}")
            
            # 发送请求
            response = requests.post(api_url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    llm_response = result['choices'][0]['message']['content']
                    print(f"✅ [LLM响应] AI: {llm_response[:100]}...")
                    return llm_response
                else:
                    return "错误：LLM返回的响应格式不正确"
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                print(f"❌ [LLM错误] {error_msg}")
                return f"错误：LLM API请求失败 - {error_msg}"
                
        except requests.exceptions.Timeout:
            return "错误：LLM API请求超时"
        except requests.exceptions.ConnectionError:
            return "错误：无法连接到LLM API服务"
        except Exception as e:
            return f"错误：处理LLM请求时发生异常 - {str(e)}"
    
    def _handle_live2d_motion_request(self):
        """处理Live2D动作请求"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_error_response(400, "Empty request body")
                return
            
            # 读取请求体
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # 验证必需字段
            if 'motion_index' not in data:
                self._send_error_response(400, "Missing 'motion_index' field")
                return
            
            motion_index = data['motion_index']
            motion_group = data.get('motion_group', 'TapBody')
            priority = data.get('priority', 3)
            
            # 尝试控制Live2D模型
            success = self._control_live2d_motion(motion_index, motion_group, priority)
            
            if success:
                self._send_json_response({
                    "status": "success",
                    "message": f"Motion {motion_index} triggered successfully",
                    "motion_group": motion_group,
                    "timestamp": time.time()
                })
            else:
                self._send_error_response(500, "Failed to trigger Live2D motion")
                
        except json.JSONDecodeError:
            self._send_error_response(400, "Invalid JSON")
        except Exception as e:
            self._send_error_response(500, f"Server error: {str(e)}")
    
    def _handle_live2d_expression_request(self):
        """处理Live2D表情请求"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self._send_error_response(400, "Empty request body")
                return
            
            # 读取请求体
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # 验证必需字段
            if 'expression_name' not in data:
                self._send_error_response(400, "Missing 'expression_name' field")
                return
            
            expression_name = data['expression_name']
            
            # 尝试控制Live2D模型
            success = self._control_live2d_expression(expression_name)
            
            if success:
                self._send_json_response({
                    "status": "success",
                    "message": f"Expression '{expression_name}' set successfully",
                    "expression_name": expression_name,
                    "timestamp": time.time()
                })
            else:
                self._send_error_response(500, "Failed to set Live2D expression")
                
        except json.JSONDecodeError:
            self._send_error_response(400, "Invalid JSON")
        except Exception as e:
            self._send_error_response(500, f"Server error: {str(e)}")
    
    def _control_live2d_motion(self, motion_index, motion_group, priority):
        """控制Live2D动作"""
        try:
            # 方法1：尝试从全局获取Live2D模型实例
            try:
                import models.live2d_model as live2d_module
                if hasattr(live2d_module, '_model') and live2d_module._model:
                    model = live2d_module._model
                    # 临时设置动作组名称
                    original_group = getattr(model, 'motion_group_name', None)
                    model.motion_group_name = motion_group
                    model.play_tapbody_motion(motion_index)
                    # 恢复原来的动作组名称
                    if original_group:
                        model.motion_group_name = original_group
                    return True
            except Exception as e:
                print(f"通过全局模块控制Live2D动作失败: {e}")
            
            # 方法2：写入文件触发器
            motion_file = "motion_trigger.tmp"
            with open(motion_file, 'w', encoding='utf-8') as f:
                f.write(json.dumps({
                    "action": "trigger_motion",
                    "motion_index": motion_index,
                    "motion_group": motion_group,
                    "priority": priority,
                    "timestamp": time.time()
                }))
            return True
            
        except Exception as e:
            print(f"控制Live2D动作失败: {e}")
            return False
    
    def _control_live2d_expression(self, expression_name):
        """控制Live2D表情"""
        try:
            # 方法1：尝试从全局获取Live2D模型实例
            try:
                import models.live2d_model as live2d_module
                if hasattr(live2d_module, '_model') and live2d_module._model:
                    model = live2d_module._model
                    if hasattr(model, 'set_expression'):
                        if expression_name == "random":
                            model.set_random_expression()
                        else:
                            model.set_expression(expression_name)
                        return True
            except Exception as e:
                print(f"通过全局模块控制Live2D表情失败: {e}")
            
            # 方法2：写入文件触发器
            expression_file = "expression_trigger.tmp"
            with open(expression_file, 'w', encoding='utf-8') as f:
                f.write(json.dumps({
                    "action": "trigger_expression",
                    "expression_name": expression_name,
                    "timestamp": time.time()
                }))
            return True
            
        except Exception as e:
            print(f"控制Live2D表情失败: {e}")
            return False
    
    def _send_json_response(self, data):
        """发送JSON响应"""
        response_data = json.dumps(data, ensure_ascii=False, indent=2)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(response_data.encode('utf-8'))
    
    def _send_error_response(self, code, message):
        """发送错误响应"""
        error_data = {
            "error": message,
            "status": "error",
            "code": code
        }
        response_data = json.dumps(error_data, ensure_ascii=False, indent=2)
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response_data.encode('utf-8'))
    
    def do_OPTIONS(self):
        """处理OPTIONS请求（CORS预检）"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def log_message(self, format, *args):
        """重写日志方法，使用自定义格式"""
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {format % args}")

def load_config():
    """加载配置文件"""
    config_path = 'config.json'
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ 配置文件加载失败: {e}")
            return {}
    else:
        print("⚠️ 配置文件不存在，使用默认配置")
        return {}

def main():
    """主函数"""
    print("🚀 独立WebAPI服务器")
    print("=" * 50)
    
    # 加载配置
    config = load_config()
    
    # 检查LLM配置
    llm_config = config.get('llm', {})
    if not llm_config.get('api_key') or not llm_config.get('api_url'):
        print("⚠️ LLM配置不完整，请先在config.json中配置API Key和API URL")
        print("示例配置:")
        print('''{
  "llm": {
    "api_key": "your-api-key",
    "api_url": "https://api.openai.com/v1",
    "model": "gpt-3.5-turbo",
    "system_prompt": "你是一个有用的AI助手。"
  },
  "webapi": {
    "enabled": true,
    "host": "127.0.0.1",
    "port": 8888,
    "api_key": ""
  }
}''')
        return
    
    # 获取WebAPI配置
    webapi_config = config.get('webapi', {})
    host = webapi_config.get('host', '127.0.0.1')
    port = webapi_config.get('port', 8888)
    api_key = webapi_config.get('api_key', '')
    
    print(f"📋 配置信息:")
    print(f"   LLM API: {llm_config.get('api_url')}")
    print(f"   LLM Model: {llm_config.get('model', 'gpt-3.5-turbo')}")
    print(f"   WebAPI地址: {host}:{port}")
    print(f"   API密钥: {'已设置' if api_key else '未设置'}")
    
    try:
        # 创建服务器
        server = HTTPServer((host, port), WebAPIHandler)
        server.config = config  # 将配置传递给处理器
        
        print(f"\n✅ WebAPI服务器启动成功!")
        print(f"📍 监听地址: http://{host}:{port}")
        print(f"📖 API文档:")
        print(f"   状态检查: GET  http://{host}:{port}/api/status")
        print(f"   聊天接口: POST http://{host}:{port}/api/chat")
        print(f"\n💡 测试命令:")
        print(f"   python quick_test.py")
        print(f"   python curl_test.py --status")
        print(f"   python curl_test.py --message \"你好\"")
        print(f"\n按 Ctrl+C 停止服务...")
        
        # 启动服务器
        server.serve_forever()
        
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ 端口 {port} 已被占用")
            print("💡 解决方案:")
            print("   1. 更改配置文件中的端口号")
            print("   2. 或者停止占用该端口的程序")
        else:
            print(f"❌ 启动失败: {str(e)}")
    except KeyboardInterrupt:
        print(f"\n👋 WebAPI服务器已停止")
    except Exception as e:
        print(f"❌ 服务器错误: {str(e)}")

if __name__ == "__main__":
    main()
