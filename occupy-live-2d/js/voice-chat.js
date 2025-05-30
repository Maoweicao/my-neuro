const { ipcRenderer } = require('electron');
const fs = require('fs');
const path = require('path');
const os = require('os');

class VoiceChatInterface {
    constructor(vadUrl, asrUrl, ttsProcessor, showSubtitle, hideSubtitle, config) {
        // 直接使用传入的配置
        this.config = config;
        
        // LLM配置
        this.API_KEY = this.config.llm.api_key;
        this.API_URL = this.config.llm.api_url;
        this.MODEL = this.config.llm.model;
        
        this.ttsProcessor = ttsProcessor;
        this.showSubtitle = showSubtitle;
        this.hideSubtitle = hideSubtitle;
        
        // 初始化ASR处理器
        const { ASRProcessor } = require('./asr-processor.js');
        this.asrProcessor = new ASRProcessor(vadUrl, asrUrl);
        
        // 上下文限制相关属性
        this.maxContextMessages = this.config.context.max_messages;
        this.enableContextLimit = this.config.context.enable_limit;
        
        // 添加截图相关的属性
        this.screenshotEnabled = this.config.vision.enabled;
        this.screenshotPath = this.config.vision.screenshot_path;
        this.visionCheckUrl = this.config.vision.check_url;
        
        // 记忆文件路径
        this.memoryFilePath = this.config.memory.file_path;
        this.memoryCheckUrl = this.config.memory.check_url;
        
        // 模型引用
        this.model = null;
        
        // 情绪动作映射器引用
        this.emotionMapper = null;

        // 确保对话记录文件存在
        const dialogLogPath = path.join(__dirname, '..', '对话记录.txt');
        try {
            // 检查文件是否存在
            if (!fs.existsSync(dialogLogPath)) {
                fs.writeFileSync(dialogLogPath, '', 'utf8');
            }

            // 添加新会话的开始标记 - 只精确到天
            const currentDate = new Date().toISOString().split('T')[0]; // 格式: YYYY-MM-DD
            const sessionStart = `=== 新会话开始：${currentDate} ===\n`;
            fs.appendFileSync(dialogLogPath, sessionStart, 'utf8');
            console.log('对话记录文件已准备好');
        } catch (error) {
            console.error('准备对话记录文件失败:', error);
        }

        // 读取记忆库文件内容
        let memoryContent = "";
        try {
            memoryContent = fs.readFileSync(this.memoryFilePath, 'utf8');
            console.log('成功读取记忆库内容');
        } catch (error) {
            console.error('读取记忆库文件失败:', error);
            memoryContent = "无法读取记忆库内容";
        }

        // 获取系统提示词并添加记忆库内容
        const baseSystemPrompt = this.config.llm.system_prompt;

        const systemPrompt = `${baseSystemPrompt}这些数据里面是有关用户的各种信息。你可以观测，在必要的时候参考这些内容，正常普通的对话不要提起：
${memoryContent}`;

        // 初始化消息数组，只包含系统消息
        this.messages = [
            {
                'role': 'system',
                'content': systemPrompt
            }
        ];

        // 设置ASR回调
        this.asrProcessor.setOnSpeechRecognized(async (text) => {
            // 显示用户ASR字幕的功能
            this.showSubtitle(`用户: ${text}`, 3000);

            // 设置锁定标志，防止主动对话插入
            global.isProcessingUserInput = true;

            try {
                // 检查消息是否需要记忆，并保存
                const needMemory = await this.checkMessageForMemory(text);
                if (needMemory) {
                    await this.saveToMemory(text);
                    console.log('用户消息已保存到记忆库');
                } else {
                    console.log('用户消息不需要保存到记忆库');
                }

                await this.sendToLLM(text);
            } finally {
                // 无论成功与否，处理完毕后都解除锁定
                global.isProcessingUserInput = false;

                // 获取最后一次用户消息和AI回复
                const lastUserMsg = this.messages.filter(m => m.role === 'user').pop();
                const lastAIMsg = this.messages.filter(m => m.role === 'assistant').pop();

                // 只追加新的对话内容，而不是覆盖整个文件
                if (lastUserMsg && lastAIMsg) {
                    // 构建要追加的新对话内容 - 不包含时间戳和空行
                    const newContent = `【用户】: ${lastUserMsg.content}\n【Fake Neuro】: ${lastAIMsg.content}\n`;

                    // 追加到对话记录文件
                    try {
                        fs.appendFileSync(
                            path.join(__dirname, '..', '对话记录.txt'),
                            newContent,
                            'utf8'
                        );
                    } catch (error) {
                        console.error('保存对话记录失败:', error);
                    }
                }
            }
        });
    }

    // 设置模型
    setModel(model) {
        this.model = model;
        console.log('模型已设置到VoiceChat');
    }

    // 设置情绪动作映射器
    setEmotionMapper(emotionMapper) {
        this.emotionMapper = emotionMapper;
        console.log('情绪动作映射器已设置到VoiceChat');
    }

    // 检查消息是否需要记忆
    async checkMessageForMemory(text) {
        try {
            const response = await fetch(`${this.memoryCheckUrl}?text=${encodeURIComponent(text)}`, {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error('记忆检查API请求失败');
            }

            const data = await response.json();
            console.log('记忆检查结果:', data);
            return data["需要检索"] === "是";
        } catch (error) {
            console.error('记忆检查错误:', error);
            return false;
        }
    }

    // 保存消息到记忆文件
    async saveToMemory(text) {
        try {
            const timestamp = new Date().toISOString().replace('T', ' ').substring(0, 19);
            const memoryEntry = `[${timestamp}] ${text}\n`;

            fs.appendFileSync(this.memoryFilePath, memoryEntry, 'utf8');
            console.log('已保存到记忆文件:', text);
            return true;
        } catch (error) {
            console.error('保存记忆失败:', error);
            return false;
        }
    }

    // 暂停录音
    async pauseRecording() {
        this.asrProcessor.pauseRecording();
        console.log('Recording paused due to TTS playback');
    }

    // 恢复录音
    async resumeRecording() {
        this.asrProcessor.resumeRecording();
        console.log('Recording resumed after TTS playback, ASR unlocked');
    }

    // 设置上下文限制
    setContextLimit(enable) {
        this.enableContextLimit = enable;
        if (enable) {
            this.trimMessages();
        }
    }

    // 设置最大上下文消息数
    setMaxContextMessages(count) {
        if (count < 1) throw new Error('最大消息数不能小于1');
        this.maxContextMessages = count;
        if (this.enableContextLimit) {
            this.trimMessages();
        }
    }

    // 裁剪消息 - 修复上下文复读问题
    trimMessages() {
        if (!this.enableContextLimit) return;

        // 获取系统消息（始终保留）
        const systemMessages = this.messages.filter(msg => msg.role === 'system');

        // 获取非系统消息（可能需要裁剪）
        const nonSystemMessages = this.messages.filter(msg => msg.role !== 'system');

        // 调试日志
        console.log(`裁剪前: 系统消息 ${systemMessages.length} 条, 非系统消息 ${nonSystemMessages.length} 条`);

        // 只保留最新的 maxContextMessages 条非系统消息
        const recentMessages = nonSystemMessages.slice(-this.maxContextMessages);

        // 重构消息数组
        this.messages = [...systemMessages, ...recentMessages];

        console.log(`裁剪后: 消息总数 ${this.messages.length} 条, 非系统消息 ${recentMessages.length} 条`);
    }

    // 添加截图功能
    async takeScreenshot() {
        try {
            // 请求主进程进行截图，不显示任何提示
            const filepath = await ipcRenderer.invoke('take-screenshot', this.screenshotPath);
            console.log('截图已保存:', filepath);
            return filepath;
        } catch (error) {
            console.error('截图错误:', error);
            throw error;
        }
    }

    // 将图片转换为base64编码
    async imageToBase64(imagePath) {
        return new Promise((resolve, reject) => {
            fs.readFile(imagePath, (err, data) => {
                if (err) {
                    console.error('读取图片失败:', err);
                    reject(err);
                    return;
                }
                const base64Image = Buffer.from(data).toString('base64');
                resolve(base64Image);
            });
        });
    }

    // 判断是否需要截图
    async shouldTakeScreenshot(text) {
        if (!this.screenshotEnabled) return false;

        try {
            const url = `${this.visionCheckUrl}?text=${encodeURIComponent(text)}`;
            const response = await fetch(url, {
                method: 'POST',
            });

            const data = await response.json();
            const result = data["需要视觉"];
            console.log(`截图判断结果: ${result}`);

            return result === "是";
        } catch (error) {
            console.error('判断截图错误:', error);
            return false;
        }
    }

    // 开始录音
    async startRecording() {
        await this.asrProcessor.startRecording();
    }

    // 停止录音
    stopRecording() {
        this.asrProcessor.stopRecording();
    }

    // 发送消息到LLM
    async sendToLLM(prompt) {
        try {
            // 重置TTS处理器的状态
            this.ttsProcessor.reset();

            // 清除之前的字幕，准备显示新对话
            // 这里不直接隐藏字幕，因为用户的ASR字幕还在显示中

            let fullResponse = "";

            // 创建新的消息数组，确保不会修改原始消息
            let messagesForAPI = JSON.parse(JSON.stringify(this.messages));

            // 判断是否需要截图
            const needScreenshot = await this.shouldTakeScreenshot(prompt);

            // 保存用户消息到上下文（只保存文本）
            this.messages.push({'role': 'user', 'content': prompt});

            // 先进行裁剪，确保只保留最新的消息
            if (this.enableContextLimit) {
                this.trimMessages();
                // 重建API消息数组，基于裁剪后的消息
                messagesForAPI = JSON.parse(JSON.stringify(this.messages));
            }

            // 如果需要截图，创建多模态消息
            if (needScreenshot) {
                try {
                    console.log("需要截图");
                    const screenshotPath = await this.takeScreenshot();
                    const base64Image = await this.imageToBase64(screenshotPath);

                    // 创建包含图片的消息用于API请求
                    // 找到最后一条用户消息替换为多模态消息
                    const lastUserMsgIndex = messagesForAPI.findIndex(
                        msg => msg.role === 'user' && msg.content === prompt
                    );

                    if (lastUserMsgIndex !== -1) {
                        messagesForAPI[lastUserMsgIndex] = {
                            'role': 'user',
                            'content': [
                                {'type': 'text', 'text': prompt},
                                {'type': 'image_url', 'image_url': {'url': `data:image/jpeg;base64,${base64Image}`}}
                            ]
                        };
                    }
                } catch (error) {
                    console.error("截图处理失败:", error);
                    // 如果截图失败，使用纯文本消息，已经设置好了
                }
            }

            // 调试消息数组
            console.log(`发送给LLM的消息数: ${messagesForAPI.length}`);

            // 发送请求到LLM
            const response = await fetch(`${this.API_URL}/chat/completions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.API_KEY}`
                },
                body: JSON.stringify({
                    model: this.MODEL,
                    messages: messagesForAPI,
                    stream: true
                })
            });

            if (!response.ok) {
                // 根据HTTP状态码提供具体错误信息
                let errorMessage = "";
                switch(response.status) {
                    case 401:
                        errorMessage = "API密钥验证失败，请检查你的API密钥";
                        break;
                    case 403:
                        errorMessage = "API访问被禁止，你的账号可能被限制";
                        break;
                    case 404:
                        errorMessage = "API接口未找到，请检查API地址";
                        break;
                    case 429:
                        errorMessage = "请求过于频繁，超出API限制";
                        break;
                    case 500:
                    case 502:
                    case 503:
                    case 504:
                        errorMessage = "服务器错误，AI服务当前不可用";
                        break;
                    default:
                        errorMessage = `API错误: ${response.status} ${response.statusText}`;
                }
                throw new Error(errorMessage);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");

            while (true) {
                const { value, done } = await reader.read();
                if (done) {
                    // 确保所有待处理文本都被发送到TTS
                    this.ttsProcessor.finalizeStreamingText();
                    break;
                }

                const text = decoder.decode(value);
                const lines = text.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        if (line.includes('[DONE]')) continue;

                        try {
                            const data = JSON.parse(line.slice(6));
                            if (data.choices[0].delta.content) {
                                const newContent = data.choices[0].delta.content;
                                fullResponse += newContent;

                                // 将新的文本片段传递给TTS处理器进行实时处理
                                this.ttsProcessor.addStreamingText(newContent);
                            }
                        } catch (e) {
                            console.error('解析响应错误:', e);
                        }
                    }
                }
            }

            if (fullResponse) {
                // 保存原始回复（包含情绪标签）到上下文
                this.messages.push({'role': 'assistant', 'content': fullResponse});

                // 在接收响应后再次进行消息裁剪
                if (this.enableContextLimit) {
                    this.trimMessages();
                }
            }
        } catch (error) {
            console.error("LLM处理错误:", error);

            // 检查错误类型，显示具体错误信息
            let errorMessage = "抱歉，出现了一个错误";

            if (error.message.includes("API密钥验证失败")) {
                errorMessage = "API密钥错误，请检查配置";
            } else if (error.message.includes("API访问被禁止")) {
                errorMessage = "API访问受限，请联系支持";
            } else if (error.message.includes("API接口未找到")) {
                errorMessage = "无效的API地址，请检查配置";
            } else if (error.message.includes("请求过于频繁")) {
                errorMessage = "请求频率超限，请稍后再试";
            } else if (error.message.includes("服务器错误")) {
                errorMessage = "AI服务不可用，请稍后再试";
            } else if (error.name === "TypeError" && error.message.includes("fetch")) {
                errorMessage = "网络错误，请检查网络连接";
            } else if (error.name === "SyntaxError") {
                errorMessage = "解析API响应出错，请重试";
            }

            this.showSubtitle(errorMessage, 3000);
            // 出错时也要解锁ASR
            this.asrProcessor.resumeRecording();
            // 出错时也要隐藏字幕
            setTimeout(() => this.hideSubtitle(), 3000);
        } finally {
            // 确保解除处理用户输入的锁定状态
            global.isProcessingUserInput = false;
        }
    }

    handleTextMessage(text) {
        // 显示用户消息
        this.addChatMessage('user', text);

        // 锁定ASR，防止语音输入干扰
        this.asrLocked = true;

        // 处理文本消息
        this.sendToLLM(text);
    }

    addChatMessage(role, content) {
        const chatMessages = document.getElementById('chat-messages');
        const messageElement = document.createElement('div');
        messageElement.innerHTML = `<strong>${role === 'user' ? '你' : 'Fake Neuro'}:</strong> ${content}`;
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // 处理弹幕消息
    async handleBarrageMessage(nickname, text) {
        try {
            if (!this) return;

            // 如果正在播放TTS，直接返回，不处理弹幕
            if (global.isPlayingTTS) {
                console.log('TTS正在播放，弹幕处理已延迟');
                return;
            }

            // 确保系统提示已增强
            enhanceSystemPrompt();

            // 将弹幕消息添加到主对话历史中，带标记
            this.messages.push({
                'role': 'user',
                'content': `[弹幕] ${nickname}: ${text}`
            });

            // 如果启用了上下文限制，需要裁剪消息
            if (this.enableContextLimit) {
                this.trimMessages();
            }

            // 重置TTS处理器
            this.ttsProcessor.reset();

            // 发送请求到LLM
            const response = await fetch(`${this.API_URL}/chat/completions`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.API_KEY}`
                },
                body: JSON.stringify({
                    model: this.MODEL,
                    messages: this.messages,
                    stream: true
                })
            });

            if (!response.ok) {
                // 根据HTTP状态码提供具体错误信息
                let errorMessage = "";
                switch(response.status) {
                    case 401:
                        errorMessage = "API密钥验证失败，请检查你的API密钥";
                        break;
                    case 403:
                        errorMessage = "API访问被禁止，你的账号可能被限制";
                        break;
                    case 404:
                        errorMessage = "API接口未找到，请检查API地址";
                        break;
                    case 429:
                        errorMessage = "请求过于频繁，超出API限制";
                        break;
                    case 500:
                    case 502:
                    case 503:
                    case 504:
                        errorMessage = "服务器错误，AI服务当前不可用";
                        break;
                    default:
                        errorMessage = `API错误: ${response.status} ${response.statusText}`;
                }
                throw new Error(errorMessage);
            }

            let fullResponse = "";
            const reader = response.body.getReader();
            const decoder = new TextDecoder("utf-8");

            while (true) {
                const { value, done } = await reader.read();
                if (done) {
                    this.ttsProcessor.finalizeStreamingText();
                    break;
                }

                const text = decoder.decode(value);
                const lines = text.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        if (line.includes('[DONE]')) continue;

                        try {
                            const data = JSON.parse(line.slice(6));
                            if (data.choices[0].delta.content) {
                                const newContent = data.choices[0].delta.content;
                                fullResponse += newContent;
                                this.ttsProcessor.addStreamingText(newContent);
                            }
                        } catch (e) {
                            console.error('解析响应错误:', e);
                        }
                    }
                }
            }

            if (fullResponse) {
                // 保存原始回复（包含情绪标签）到对话历史
                this.messages.push({'role': 'assistant', 'content': fullResponse});

                // 再次裁剪消息
                if (this.enableContextLimit) {
                    this.trimMessages();
                }

                // 构建要追加的弹幕对话内容 - 不包含时间戳和空行
                const newContent = `【弹幕】[${nickname}]: ${text}\n【Fake Neuro】: ${fullResponse}\n`;

                // 追加到对话记录文件
                try {
                    fs.appendFileSync(
                        path.join(__dirname, '..', '对话记录.txt'),
                        newContent,
                        'utf8'
                    );
                } catch (error) {
                    console.error('保存弹幕对话记录失败:', error);
                }
            }
        } catch (error) {
            console.error('处理弹幕消息出错:', error);

            // 检查错误类型，显示具体错误信息
            let errorMessage = "抱歉，处理弹幕出错";

            if (error.message.includes("API密钥验证失败")) {
                errorMessage = "API密钥错误，请检查配置";
            } else if (error.message.includes("API访问被禁止")) {
                errorMessage = "API访问受限，请联系支持";
            } else if (error.message.includes("API接口未找到")) {
                errorMessage = "无效的API地址，请检查配置";
            } else if (error.message.includes("请求过于频繁")) {
                errorMessage = "请求频率超限，请稍后再试";
            } else if (error.message.includes("服务器错误")) {
                errorMessage = "AI服务不可用，请稍后再试";
            } else if (error.name === "TypeError" && error.message.includes("fetch")) {
                errorMessage = "网络错误，请检查网络连接";
            } else if (error.name === "SyntaxError") {
                errorMessage = "解析API响应出错，请重试";
            }

            this.showSubtitle(errorMessage, 3000);
            // 出错时解锁ASR
            this.asrProcessor.resumeRecording();
        }
    }
}

module.exports = { VoiceChatInterface };