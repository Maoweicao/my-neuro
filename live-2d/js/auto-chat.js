// 自动对话模块
class AutoChatModule {
    constructor(config, ttsProcessor) {
        this.config = config;
        this.ttsProcessor = ttsProcessor;
        this.intervalId = null;
        this.isRunning = false;

        // 从配置中读取参数，完全依赖配置文件
        this.enabled = config.auto_chat.enabled;
        this.checkInterval = config.auto_chat.interval;
        this.idleTimeThreshold = config.auto_chat.idle_time || config.auto_chat.max_interval; // 如果没有idle_time参数，使用max_interval作为空闲触发时间
        
        // 记录最后交互时间
        this.lastInteractionTime = Date.now();
        
        // 获取全局变量的引用
        this.getIsPlayingTTS = () => global.isPlayingTTS;
        this.getIsProcessingBarrage = () => global.isProcessingBarrage;
    }

    // 启动自动对话
    start() {
        // 如果配置为禁用，则不启动
        if (!this.enabled) {
            console.log('自动对话已在配置中禁用，不会启动');
            return;
        }
        
        if (this.isRunning) return;
        
        console.log(`自动对话模块启动，空闲触发时间：${this.idleTimeThreshold}ms，检查间隔：${this.checkInterval}ms`);
        this.isRunning = true;
        
        // 初始化最后交互时间
        this.lastInteractionTime = Date.now();
        
        // 定期检查空闲状态
        this.intervalId = setInterval(() => {
            this.checkIdleState();
        }, this.checkInterval);
    }

    // 停止自动对话
    stop() {
        if (!this.isRunning) return;
        
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
        
        this.isRunning = false;
        console.log('自动对话模块已停止');
    }

    // 检查空闲状态
    checkIdleState() {
        if (!this.isRunning) return;
        
        const currentTime = Date.now();
        const idleTime = currentTime - this.lastInteractionTime;
        
        // 如果空闲时间超过阈值，尝试触发主动对话
        if (idleTime >= this.idleTimeThreshold) {
            this.triggerRandomChat();
            // 主动对话触发后，重置最后交互时间
            this.lastInteractionTime = Date.now();
        }
    }

    // 更新最后交互时间（在用户输入或AI回复后调用）
    updateLastInteractionTime() {
        this.lastInteractionTime = Date.now();
        console.log('自动对话：更新最后交互时间');
    }

    // 触发随机对话
    async triggerRandomChat() {
        // 检查是否能够触发对话
        if (this.getIsPlayingTTS() || 
            this.getIsProcessingBarrage() || 
            global.isProcessingUserInput) {
            console.log('TTS正在播放、处理弹幕中或正在处理用户输入，跳过自动对话');
            return;
        }

        // 随机选择提示词
        const promptTemplates = [
            "你看到主人一段时间没有说话，请基于对话历史，现有的上下文对话记录来回复。"
        ];
        
        const randomIndex = Math.floor(Math.random() * promptTemplates.length);
        const prompt = promptTemplates[randomIndex];
        
        console.log('触发自动对话，提示词:', prompt);
        
        try {
            // 获取voiceChat实例
            const voiceChat = global.voiceChat;
            if (!voiceChat) {
                console.error('voiceChat实例不存在，无法存入上下文记忆');
                return;
            }
            
            // 将提示词添加到上下文记忆（标记为特殊消息，便于识别）
            voiceChat.messages.push({
                'role': 'user',
                'content': `[自动触发] ${prompt}`
            });
            
            // 如果启用了上下文限制，需要裁剪消息
            if (voiceChat.enableContextLimit) {
                voiceChat.trimMessages();
            }
            
            // 发送请求到LLM，使用完整的上下文
            const response = await fetch(`${this.config.llm.api_url}/chat/completions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.config.llm.api_key}`
                },
                body: JSON.stringify({
                    model: this.config.llm.model,
                    messages: voiceChat.messages
                })
            });
            
            if (!response.ok) {
                throw new Error("LLM请求失败: " + response.statusText);
            }
            
            const result = await response.json();
            const replyContent = result.choices[0].message.content.trim();
            console.log('自动对话回复:', replyContent);
            
            // 将模型的回复存入上下文记忆
            voiceChat.messages.push({
                'role': 'assistant',
                'content': replyContent
            });
            
            // 再次裁剪消息
            if (voiceChat.enableContextLimit) {
                voiceChat.trimMessages();
            }
            
            // 使用TTS播放回复
            this.ttsProcessor.processTextToSpeech(replyContent);
        } catch (error) {
            console.error('自动对话处理错误:', error);
        }
    }
}

// 导出模块
module.exports = { AutoChatModule };