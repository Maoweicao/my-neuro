# coding:utf-8
"""
日志管理功能演示脚本
用于演示新增的日志管理功能
"""
import os
import time

def create_sample_logs():
    """创建一些示例日志文件用于测试"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 创建示例日志内容
    sample_logs = {
        "llm_interactions.log": [
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] USER: 你好",
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] LLM: 你好！有什么可以帮助你的吗？",
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] USER: 介绍一下你自己",
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] LLM: 我是AI助手，很高兴为您服务。",
        ],
        "asr_interactions.log": [
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] AUDIO_INPUT: 开始录音",
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ASR_RESULT: 你好世界",
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] AUDIO_INPUT: 录音结束",
        ],
        "tts_interactions.log": [
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] TEXT_INPUT: 欢迎使用AI Live2D",
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] SYNTHESIS_REQUEST: 开始语音合成",
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] SYNTHESIS_RESULT: 合成成功",
        ],
        "webapi_interactions.log": [
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] REQUEST_START: POST /api/chat from 127.0.0.1",
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] CHAT_REQUEST: MessageLength=5, HasApiKey=true", 
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] REQUEST_END: POST /api/chat -> 200 (150.25ms)",
        ]
    }
    
    # 写入示例日志
    for filename, lines in sample_logs.items():
        filepath = os.path.join(log_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')
    
    # 创建其他日志文件
    with open("chat_log.txt", 'w', encoding='utf-8') as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 聊天记录开始\n")
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 用户: 测试消息\n")
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] AI: 收到测试消息\n")
    
    with open("pet_system.log", 'w', encoding='utf-8') as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 系统启动\n")
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Live2D模型加载完成\n")
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 宠物系统初始化完成\n")
    
    print("✓ 示例日志文件创建完成")
    print(f"  - logs目录: {len(sample_logs)}个文件")
    print(f"  - 其他日志: 2个文件")

def show_log_status():
    """显示当前日志状态"""
    print("\n=== 当前日志状态 ===")
    
    log_dir = "logs"
    if os.path.exists(log_dir):
        total_size = 0
        file_count = 0
        print(f"日志目录: {log_dir}")
        
        for filename in os.listdir(log_dir):
            if filename.endswith('.log'):
                filepath = os.path.join(log_dir, filename)
                size = os.path.getsize(filepath)
                total_size += size
                file_count += 1
                print(f"  - {filename}: {size} bytes")
        
        print(f"logs目录总计: {file_count}个文件, {total_size} bytes")
    else:
        print("logs目录不存在")
    
    # 检查其他日志文件
    other_logs = ["chat_log.txt", "pet_system.log"]
    for log_file in other_logs:
        if os.path.exists(log_file):
            size = os.path.getsize(log_file)
            print(f"{log_file}: {size} bytes")
        else:
            print(f"{log_file}: 不存在")

def test_instructions():
    """显示测试说明"""
    print("\n=== 日志管理功能测试说明 ===")
    print("1. 运行 'python UI.py' 启动应用")
    print("2. 点击导航栏中的 '设置' 选项")
    print("3. 滚动到页面底部找到 '日志管理' 分组")
    print("4. 测试以下功能：")
    print("   a) 查看日志状态显示")
    print("   b) 点击 '保存日志包' 按钮测试打包功能")
    print("   c) 点击 '查看日志目录' 按钮测试目录打开")
    print("   d) 点击 '清空日志' 按钮测试清空功能（注意备份！）")
    print("\n预期结果：")
    print("- 状态显示正确的文件数量和大小")
    print("- 保存功能生成包含所有日志的ZIP文件")
    print("- 查看功能打开logs目录") 
    print("- 清空功能清空所有日志内容")

if __name__ == "__main__":
    print("=== AI Live2D 日志管理功能演示 ===")
    
    # 创建示例日志
    create_sample_logs()
    
    # 显示当前状态
    show_log_status()
    
    # 显示测试说明
    test_instructions()
    
    print("\n✓ 演示准备完成，可以开始测试了！")
