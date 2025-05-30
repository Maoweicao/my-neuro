// 导入所需模块
const { EnhancedTextProcessor } = require('./js/tts-processor.js');
const { ModelInteractionController } = require('./js/model-interaction.js');
const { VoiceChatInterface } = require('./js/voice-chat.js');
const { configLoader } = require('./js/config-loader.js');
const { LiveStreamModule } = require('./js/LiveStreamModule.js');
const { AutoChatModule } = require('./js/auto-chat.js');
const { EmotionMotionMapper } = require('./js/emotion-motion-mapper.js');
const { MCPClientModule } = require('./js/mcp-client-module.js');

// 设置全局变量，用于模块间共享状态
global.isPlayingTTS = false;
global.isProcessingBarrage = false;
global.isProcessingUserInput = false;

const { ipcRenderer } = require('electron');
const fs = require('fs');
const path = require('path');
const os = require('os');

// 监听中断信号
ipcRenderer.on('interrupt-tts', () => {
    console.log('接收到中断信号');
    logToTerminal('info', '接收到中断信号');
    if (ttsProcessor) {
        ttsProcessor.interrupt();
    }
    global.isPlayingTTS = false;
    global.isProcessingUserInput = false;
    global.isProcessingBarrage = false;
    if (voiceChat && voiceChat.asrProcessor) {
        setTimeout(() => {
            voiceChat.resumeRecording();
            console.log('ASR录音已恢复');
            logToTerminal('info', 'ASR录音已恢复');
        }, 200);
    }
    console.log('系统已复位，可以继续对话');
    logToTerminal('info', '系统已复位，可以继续对话');
});

// 添加终端日志记录函数
function logToTerminal(level, message) {
    // 将日志格式化，包含时间戳
    const timestamp = new Date().toISOString();
    const formattedMsg = `[${timestamp}] [${level.toUpperCase()}] ${message}\n`;

    // 直接写入到stderr（错误）或stdout（普通日志）
    if (level === 'error') {
        process.stderr.write(formattedMsg);
    } else {
        process.stdout.write(formattedMsg);
    }

    // 同时也记录到浏览器控制台（开发调试用）
    if (level === 'error') {
        console.error(message);
    } else if (level === 'warn') {
        console.warn(message);
    } else {
        console.log(message);
    }
}

// 加载配置文件
let config;
try {
    // 尝试加载配置
    config = configLoader.load();
    console.log('配置文件加载成功');
    logToTerminal('info', '配置文件加载成功');
} catch (error) {
    // 如果加载失败，显示错误消息
    console.error('配置加载失败:', error);
    logToTerminal('error', `配置加载失败: ${error.message}`);
    alert(`配置文件错误: ${error.message}\n请检查config.json格式是否正确。`);
    // 让用户看到错误信息后手动关闭程序
    throw error; // 抛出错误，终止程序执行
}

// 字幕管理
let subtitleTimeout = null;

// 更新鼠标穿透状态
function updateMouseIgnore() {
    // 如果鼠标不在可交互区域，则穿透
    const shouldIgnore = !this.model.containsPoint(this.app.renderer.plugins.interaction.mouse.global);

    ipcRenderer.send('set-ignore-mouse-events', {
        ignore: shouldIgnore,
        options: { forward: true } // 允许鼠标事件穿透
    });
}

// 监听鼠标移动
document.addEventListener('mousemove', updateMouseIgnore);

// 监听聊天框相关事件，强制禁用穿透
const chatInput = document.getElementById('chat-input');
if (chatInput) {
    // 鼠标进入聊天框时，禁用穿透
    document.getElementById('text-chat-container').addEventListener('mouseenter', () => {
        ipcRenderer.send('set-ignore-mouse-events', {
            ignore: false,
            options: { forward: false }
        });
    });

    // 鼠标离开聊天框时，恢复检测
    document.getElementById('text-chat-container').addEventListener('mouseleave', () => {
        ipcRenderer.send('set-ignore-mouse-events', {
            ignore: true,
            options: { forward: true }
        });
    });

    // 输入框聚焦时，强制禁用穿透（防止键盘输入失效）
    chatInput.addEventListener('focus', () => {
        ipcRenderer.send('set-ignore-mouse-events', {
            ignore: false,
            options: { forward: false }
        });
    });

    // 输入框失焦时，恢复检测
    chatInput.addEventListener('blur',() => {
        ipcRenderer.send('set-ignore-mouse-events', {
            ignore: true,
            options: { forward: true }
        });
    });
}

function showSubtitle(text, duration = null) {
    const container = document.getElementById('subtitle-container');
    const subtitleText = document.getElementById('subtitle-text');

    if (subtitleTimeout) {
        clearTimeout(subtitleTimeout);
        subtitleTimeout = null;
    }

    subtitleText.textContent = text;
    container.style.display = 'block';

    // 确保滚动到底部，显示最新内容
    container.scrollTop = container.scrollHeight;

    if (duration) {
        subtitleTimeout = setTimeout(() => {
            hideSubtitle();
        }, duration);
    }
}

function hideSubtitle() {
    const container = document.getElementById('subtitle-container');
    container.style.display = 'none';
    if (subtitleTimeout) {
        clearTimeout(subtitleTimeout);
        subtitleTimeout = null;
    }
}

// 创建模型交互控制器
const modelController = new ModelInteractionController();
let currentModel = null;
const INTRO_TEXT = config.ui.intro_text || "你好，我叫fake neuro。";
let voiceChat = null;
let liveStreamModule = null; // 直播模块实例
let autoChatModule = null;   // 自动对话模块实例
let emotionMapper = null;    // 情绪动作映射器实例
let mcpClientModule = null;  // MCP客户端模块实例

// 弹幕队列管理
let barrageQueue = [];
// 注意：isPlayingTTS 和 isProcessingBarrage 现在是全局变量

// 使用外部TTS处理器
const ttsProcessor = new EnhancedTextProcessor(
    config.tts.url,
    (value) => modelController.setMouthOpenY(value),  // 音频数据回调
    () => {
        // TTS开始播放回调
        global.isPlayingTTS = true;
        if (voiceChat) voiceChat.pauseRecording();
    },
    () => {
        // TTS结束播放回调
        global.isPlayingTTS = false;
        if (voiceChat) voiceChat.resumeRecording();
        // TTS播放结束后，更新自动对话最后交互时间
        if (global.autoChatModule) {
            global.autoChatModule.updateLastInteractionTime();
        }
        // TTS播放结束后，检查并处理队列中的弹幕
        processBarrageQueue();
    },
    config  // 传递配置对象
);

// 初始化时增强系统提示词
function enhanceSystemPrompt() {
    if (voiceChat && voiceChat.messages && voiceChat.messages.length > 0 && voiceChat.messages[0].role === 'system') {
        const originalPrompt = voiceChat.messages[0].content;

        // 检查是否已经添加了直播相关提示
        if (!originalPrompt.includes('你可能会收到直播弹幕')) {
            const enhancedPrompt = originalPrompt + "\n\n你可能会收到直播弹幕消息，这些消息会被标记为[弹幕]，表示这是来自直播间观众的消息，而不是主人直接对你说的话。当你看到[弹幕]标记时，你应该知道这是其他人发送的，但你仍然可以回应，就像在直播间与观众互动一样。";
            voiceChat.messages[0].content = enhancedPrompt;
            console.log('系统提示已增强，添加了直播弹幕相关说明');
            logToTerminal('info', '系统提示已增强，添加了直播弹幕相关说明');
        }
    }
}

// 将弹幕添加到队列
function addToBarrageQueue(nickname, text) {
    barrageQueue.push({ nickname, text });
    console.log(`弹幕已加入队列: ${nickname}: ${text}`);
    logToTerminal('info', `弹幕已加入队列: ${nickname}: ${text}`);

    // 如果当前没有TTS播放，尝试处理队列
    if (!global.isPlayingTTS && !global.isProcessingBarrage) {
        processBarrageQueue();
    }
}

// 处理弹幕队列
async function processBarrageQueue() {
    // 如果正在处理弹幕或正在播放TTS，则不处理
    if (global.isProcessingBarrage || global.isPlayingTTS || barrageQueue.length === 0) {
        return;
    }

    global.isProcessingBarrage = true;

    try {
        // 获取队列中的第一条弹幕
        const { nickname, text } = barrageQueue.shift();
        console.log(`处理队列中的弹幕: ${nickname}: ${text}`);
        logToTerminal('info', `处理队列中的弹幕: ${nickname}: ${text}`);

        // 处理弹幕消息
        await handleBarrageMessage(nickname, text);

        // 处理完成后，检查队列中是否还有其他弹幕
        global.isProcessingBarrage = false;

        // 更新自动对话最后交互时间
        if (global.autoChatModule) {
            global.autoChatModule.updateLastInteractionTime();
        }

        // 延迟一下再继续处理，避免连续处理过多弹幕
        setTimeout(() => {
            processBarrageQueue();
        }, 500);
    } catch (error) {
        console.error('处理弹幕队列出错:', error);
        logToTerminal('error', `处理弹幕队列出错: ${error.message}`);
        global.isProcessingBarrage = false;
    }
}

// 处理弹幕消息 - 按顺序执行流程
async function handleBarrageMessage(nickname, text) {
    try {
        if (!voiceChat) return;

        // 如果正在播放TTS，直接返回，不处理弹幕
        if (global.isPlayingTTS) {
            console.log('TTS正在播放，弹幕处理已延迟');
            logToTerminal('info', 'TTS正在播放，弹幕处理已延迟');
            return;
        }

        // 确保系统提示已增强
        enhanceSystemPrompt();

        // 1. 用户输入阶段 - 将弹幕消息添加到主对话历史中，带标记
        voiceChat.messages.push({
            'role': 'user',
            'content': `[弹幕] ${nickname}: ${text}`
        });

        // 如果启用了上下文限制，需要裁剪消息
        if (voiceChat.enableContextLimit) {
            voiceChat.trimMessages();
        }

        // 2. 准备API请求
        const requestBody = {
            model: voiceChat.MODEL,
            messages: voiceChat.messages,
            stream: false  // 改为非流式请求，确保完整分析
        };

        // 添加工具列表（如果可用）
        if (global.mcpClientModule && global.mcpClientModule.isConnected) {
            const tools = global.mcpClientModule.getToolsForLLM();
            if (tools && tools.length > 0) {
                requestBody.tools = tools;
            }
        }

        // 3. 分析阶段 - 发送请求到LLM进行分析
        const response = await fetch(`${voiceChat.API_URL}/chat/completions`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${voiceChat.API_KEY}`
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            // 尝试读取响应体获取详细错误信息
            let errorDetail = "";
            try {
                const errorBody = await response.text();
                try {
                    // 尝试解析JSON
                    const errorJson = JSON.parse(errorBody);
                    errorDetail = JSON.stringify(errorJson, null, 2);
                } catch (e) {
                    errorDetail = errorBody;
                }
            } catch (e) {
                errorDetail = "无法读取错误详情";
            }

            // 记录完整错误到终端
            logToTerminal('error', `API错误 (${response.status} ${response.statusText}):\n${errorDetail}`);

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
            throw new Error(`${errorMessage}\n详细信息: ${errorDetail}`);
        }

        // 解析LLM响应
        const responseData = await response.json();
        const result = responseData.choices[0].message;

        // 4. 工具调用阶段（如需）- 检查是否需要工具调用
        if (result.tool_calls && result.tool_calls.length > 0 && global.mcpClientModule) {
            console.log("检测到工具调用:", result.tool_calls);
            logToTerminal('info', `检测到工具调用: ${JSON.stringify(result.tool_calls)}`);

            // 将工具调用添加到消息历史
            voiceChat.messages.push({
                'role': 'assistant',
                'content': null,
                'tool_calls': result.tool_calls
            });

            // 执行工具调用
            const toolResult = await global.mcpClientModule.handleToolCalls(result.tool_calls);

            if (toolResult) {
                console.log("工具调用结果:", toolResult);
                logToTerminal('info', `工具调用结果: ${toolResult}`);

                // 将工具结果添加到消息历史
                voiceChat.messages.push({
                    'role': 'tool',
                    'content': toolResult,
                    'tool_call_id': result.tool_calls[0].id
                });

                // 再次调用LLM获取最终回复
                const finalRequestOptions = {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${voiceChat.API_KEY}`
                    },
                    body: JSON.stringify({
                        model: voiceChat.MODEL,
                        messages: voiceChat.messages,
                        stream: false
                    })
                };

                const finalResponse = await fetch(`${voiceChat.API_URL}/chat/completions`, finalRequestOptions);

                if (!finalResponse.ok) {
                    // 尝试读取错误详情
                    let errorDetail = "";
                    try {
                        const errorBody = await finalResponse.text();
                        try {
                            const errorJson = JSON.parse(errorBody);
                            errorDetail = JSON.stringify(errorJson, null, 2);
                        } catch (e) {
                            errorDetail = errorBody;
                        }
                    } catch (e) {
                        errorDetail = "无法读取错误详情";
                    }

                    // 记录完整错误
                    logToTerminal('error', `API错误 (${finalResponse.status} ${finalResponse.statusText}):\n${errorDetail}`);

                    // 根据HTTP状态码提供错误信息
                    let errorMessage = "";
                    switch(finalResponse.status) {
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
                            errorMessage = `API错误: ${finalResponse.status} ${finalResponse.statusText}`;
                    }
                    throw new Error(`${errorMessage}\n详细信息: ${errorDetail}`);
                }

                // 获取最终回复
                const finalResponseData = await finalResponse.json();
                const finalResult = finalResponseData.choices[0].message;

                // 保存最终回复
                if (finalResult.content) {
                    voiceChat.messages.push({'role': 'assistant', 'content': finalResult.content});

                    // 5. 语音输出阶段 - 播放最终回复
                    ttsProcessor.reset();
                    ttsProcessor.processTextToSpeech(finalResult.content);
                }
            } else {
                // 工具调用失败处理
                console.error("工具调用失败");
                logToTerminal('error', "工具调用失败");
                throw new Error("工具调用失败，无法完成功能扩展");
            }
        } else if (result.content) {
            // 不需要工具调用，直接处理LLM响应
            voiceChat.messages.push({'role': 'assistant', 'content': result.content});

            // 5. 语音输出阶段 - 播放回复
            ttsProcessor.reset();
            ttsProcessor.processTextToSpeech(result.content);
        }

        // 再次裁剪消息
        if (voiceChat.enableContextLimit) {
            voiceChat.trimMessages();
        }
    } catch (error) {
        // 详细错误记录到终端
        logToTerminal('error', `处理弹幕消息出错: ${error.message}`);
        if (error.stack) {
            logToTerminal('error', `错误堆栈: ${error.stack}`);
        }

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
        } else if (error.message.includes("工具调用失败")) {
            errorMessage = "功能扩展调用失败，请重试";
        } else if (error.name === "TypeError" && error.message.includes("fetch")) {
            errorMessage = "网络连接失败，请检查网络";
        } else if (error.name === "SyntaxError") {
            errorMessage = "解析API响应出错，请重试";
        } else {
            // 未识别错误，显示原始错误信息
            errorMessage = `弹幕处理错误: ${error.message}`;
        }

        // 用户显示的错误消息也记录到终端
        logToTerminal('error', `用户显示错误: ${errorMessage}`);

        showSubtitle(errorMessage, 3000);
        // 出错时解锁ASR
        voiceChat.asrProcessor.resumeRecording();
        // 延迟隐藏字幕
        setTimeout(() => hideSubtitle(), 3000);
    }
}

(async function main() {
    try {
        // 创建语音聊天接口
        voiceChat = new VoiceChatInterface(
            config.asr.vad_url,
            config.asr.asr_url,
            ttsProcessor,
            showSubtitle,
            hideSubtitle,
            config  // 传递整个配置对象给VoiceChatInterface
        );
        global.voiceChat = voiceChat;

        // 创建PIXI应用
        const app = new PIXI.Application({
            view: document.getElementById("canvas"),
            autoStart: true,
            transparent: true,
            width: window.innerWidth * 2,
            height: window.innerHeight * 2
        });

        app.stage.position.set(window.innerWidth / 2, window.innerHeight / 2);
        app.stage.pivot.set(window.innerWidth / 2, window.innerHeight / 2);

        // 加载Live2D模型
        const model = await PIXI.live2d.Live2DModel.from("2D/Hiyori.model3.json");
        currentModel = model;
        app.stage.addChild(model);

        // 初始化模型交互控制器
        modelController.init(model, app);
        modelController.setupInitialModelProperties(config.ui.model_scale || 2.3);

        // 创建情绪动作映射器
        emotionMapper = new EmotionMotionMapper(model);

        // 将情绪映射器传递给TTS处理器，实现同步
        ttsProcessor.setEmotionMapper(emotionMapper);

        // 设置模型和情绪映射器
        voiceChat.setModel(model);
        voiceChat.setEmotionMapper = emotionMapper; // 设置情绪映射器引用

        // 初始化时增强系统提示
        enhanceSystemPrompt();

        // 初始化MCP客户端模块（如果在配置中启用）
        if (config.mcp && config.mcp.enabled) {
            mcpClientModule = new MCPClientModule(config, ttsProcessor, emotionMapper);

            // 异步初始化MCP模块
            mcpClientModule.initialize().then(success => {
                if (success) {
                    console.log('MCP客户端模块初始化成功');
                    logToTerminal('info', 'MCP客户端模块初始化成功');
                    global.mcpClientModule = mcpClientModule;

                    // 修改VoiceChat的sendToLLM方法，添加工具调用支持，遵循线性流程
                    voiceChat.sendToLLM = async function(prompt) {
                        try {
                            // 标记正在处理用户输入
                            global.isProcessingUserInput = true;

                            // 1. 用户输入阶段 - 保存用户消息到上下文
                            this.messages.push({'role': 'user', 'content': prompt});

                            // 裁剪消息历史
                            if (this.enableContextLimit) {
                                this.trimMessages();
                            }

                            // 准备API请求参数 - 处理多模态输入(如截图)
                            let messagesForAPI = JSON.parse(JSON.stringify(this.messages));
                            const needScreenshot = await this.shouldTakeScreenshot(prompt);

                            if (needScreenshot) {
                                try {
                                    console.log("需要截图");
                                    logToTerminal('info', "需要截图");
                                    const screenshotPath = await this.takeScreenshot();
                                    const base64Image = await this.imageToBase64(screenshotPath);

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
                                    logToTerminal('error', `截图处理失败: ${error.message}`);
                                    throw new Error("截图功能出错，无法处理视觉内容");
                                }
                            }

                            // 准备API请求
                            const requestBody = {
                                model: this.MODEL,
                                messages: messagesForAPI,
                                stream: false  // 改为非流式请求，确保完整分析
                            };

                            // 添加工具列表（如果可用）
                            if (global.mcpClientModule && global.mcpClientModule.isConnected) {
                                const tools = global.mcpClientModule.getToolsForLLM();
                                if (tools && tools.length > 0) {
                                    requestBody.tools = tools;
                                }
                            }

                            // 2. 分析阶段 - 发送请求到LLM进行分析
                            logToTerminal('info', `开始发送请求到LLM API: ${this.API_URL}/chat/completions`);
                            const response = await fetch(`${this.API_URL}/chat/completions`, {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'Authorization': `Bearer ${this.API_KEY}`
                                },
                                body: JSON.stringify(requestBody)
                            });

                            if (!response.ok) {
                                // 尝试读取响应体获取详细错误信息
                                let errorDetail = "";
                                try {
                                    const errorBody = await response.text();
                                    try {
                                        // 尝试解析JSON
                                        const errorJson = JSON.parse(errorBody);
                                        errorDetail = JSON.stringify(errorJson, null, 2);
                                    } catch (e) {
                                        errorDetail = errorBody;
                                    }
                                } catch (e) {
                                    errorDetail = "无法读取错误详情";
                                }

                                // 记录完整错误到终端
                                logToTerminal('error', `API错误 (${response.status} ${response.statusText}):\n${errorDetail}`);

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
                                throw new Error(`${errorMessage}\n详细信息: ${errorDetail}`);
                            }

                            // 解析LLM响应
                            const responseData = await response.json();
                            const result = responseData.choices[0].message;
                            logToTerminal('info', `收到LLM API响应`);

                            // 3. 工具调用阶段（如需）- 检查是否需要工具调用
                            if (result.tool_calls && result.tool_calls.length > 0 && global.mcpClientModule) {
                                console.log("检测到工具调用:", result.tool_calls);
                                logToTerminal('info', `检测到工具调用: ${JSON.stringify(result.tool_calls)}`);

                                // 将工具调用添加到消息历史
                                this.messages.push({
                                    'role': 'assistant',
                                    'content': null,
                                    'tool_calls': result.tool_calls
                                });

                                // 执行工具调用
                                logToTerminal('info', `开始执行工具调用`);
                                const toolResult = await global.mcpClientModule.handleToolCalls(result.tool_calls);

                                if (toolResult) {
                                    console.log("工具调用结果:", toolResult);
                                    logToTerminal('info', `工具调用结果: ${toolResult}`);

                                    // 将工具结果添加到消息历史
                                    this.messages.push({
                                        'role': 'tool',
                                        'content': toolResult,
                                        'tool_call_id': result.tool_calls[0].id
                                    });

                                    // 再次调用LLM获取最终回复
                                    logToTerminal('info', `发送工具结果到LLM获取最终回复`);
                                    const finalRequestOptions = {
                                        method: 'POST',
                                        headers: {
                                            'Content-Type': 'application/json',
                                            'Authorization': `Bearer ${this.API_KEY}`
                                        },
                                        body: JSON.stringify({
                                            model: this.MODEL,
                                            messages: this.messages,
                                            stream: false
                                        })
                                    };

                                    const finalResponse = await fetch(`${this.API_URL}/chat/completions`, finalRequestOptions);

                                    if (!finalResponse.ok) {
                                        // 尝试读取错误详情
                                        let errorDetail = "";
                                        try {
                                            const errorBody = await finalResponse.text();
                                            try {
                                                const errorJson = JSON.parse(errorBody);
                                                errorDetail = JSON.stringify(errorJson, null, 2);
                                            } catch (e) {
                                                errorDetail = errorBody;
                                            }
                                        } catch (e) {
                                            errorDetail = "无法读取错误详情";
                                        }

                                        // 记录完整错误
                                        logToTerminal('error', `API错误 (${finalResponse.status} ${finalResponse.statusText}):\n${errorDetail}`);

                                        // 根据HTTP状态码提供错误信息
                                        let errorMessage = "";
                                        switch(finalResponse.status) {
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
                                                errorMessage = `API错误: ${finalResponse.status} ${finalResponse.statusText}`;
                                        }
                                        throw new Error(`${errorMessage}\n详细信息: ${errorDetail}`);
                                    }

                                    // 获取最终回复
                                    const finalResponseData = await finalResponse.json();
                                    const finalResult = finalResponseData.choices[0].message;
                                    logToTerminal('info', `获得最终LLM回复，开始语音输出`);

                                    // 保存最终回复
                                    if (finalResult.content) {
                                        this.messages.push({'role': 'assistant', 'content': finalResult.content});

                                        // 4. 语音输出阶段 - 播放最终回复
                                        this.ttsProcessor.reset();
                                        this.ttsProcessor.processTextToSpeech(finalResult.content);
                                    }
                                } else {
                                    // 工具调用失败处理
                                    console.error("工具调用失败");
                                    logToTerminal('error', "工具调用失败");
                                    throw new Error("工具调用失败，无法完成功能扩展");
                                }
                            } else if (result.content) {
                                // 不需要工具调用，直接处理LLM响应
                                this.messages.push({'role': 'assistant', 'content': result.content});
                                logToTerminal('info', `LLM直接返回回复，开始语音输出`);

                                // 4. 语音输出阶段 - 播放回复
                                this.ttsProcessor.reset();
                                this.ttsProcessor.processTextToSpeech(result.content);
                            }

                            // 再次裁剪消息历史
                            if (this.enableContextLimit) {
                                this.trimMessages();
                            }
                        } catch (error) {
                            // 详细错误记录到终端
                            logToTerminal('error', `LLM处理错误: ${error.message}`);
                            if (error.stack) {
                                logToTerminal('error', `错误堆栈: ${error.stack}`);
                            }

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
                            } else if (error.message.includes("截图功能出错")) {
                                errorMessage = "截图失败，无法处理视觉内容";
                            } else if (error.message.includes("工具调用失败")) {
                                errorMessage = "功能扩展调用失败，请重试";
                            } else if (error.name === "TypeError" && error.message.includes("fetch")) {
                                errorMessage = "网络连接失败，请检查网络和API地址";
                            } else if (error.name === "SyntaxError") {
                                errorMessage = "解析API响应出错，请重试";
                            } else {
                                // 显示原始错误信息，但截断过长的消息
                                const shortErrorMsg = error.message.substring(0, 100) +
                                                   (error.message.length > 100 ? "..." : "");
                                errorMessage = `未知错误: ${shortErrorMsg}`;
                            }

                            // 用户显示的错误消息也记录到终端
                            logToTerminal('error', `用户显示错误: ${errorMessage}`);

                            this.showSubtitle(errorMessage, 3000);
                            // 出错时也要解锁ASR
                            this.asrProcessor.resumeRecording();
                            // 出错时也要隐藏字幕
                            setTimeout(() => this.hideSubtitle(), 3000);
                        } finally {
                            // 确保解除处理用户输入的锁定状态
                            global.isProcessingUserInput = false;
                        }
                    };
                } else {
                    console.log('MCP客户端模块初始化失败');
                    logToTerminal('error', 'MCP客户端模块初始化失败');
                }
            });
        }

        // 初始化直播模块（如果在配置中启用）
        if (config.bilibili && config.bilibili.enabled) {
            liveStreamModule = new LiveStreamModule({
                roomId: config.bilibili.roomId || '30230160',
                checkInterval: config.bilibili.checkInterval || 5000,
                maxMessages: config.bilibili.maxMessages || 50,
                apiUrl: config.bilibili.apiUrl || 'http://api.live.bilibili.com/ajax/msg',

                // 处理新弹幕消息
                onNewMessage: (message) => {
                    console.log(`收到弹幕: ${message.nickname}: ${message.text}`);
                    logToTerminal('info', `收到弹幕: ${message.nickname}: ${message.text}`);

                    // 将弹幕添加到处理队列
                    addToBarrageQueue(message.nickname, message.text);
                }
            });

            // 启动直播模块
            liveStreamModule.start();
            console.log('直播模块已启动，监听房间:', liveStreamModule.roomId);
            logToTerminal('info', `直播模块已启动，监听房间: ${liveStreamModule.roomId}`);
        }

        // 播放欢迎语
        setTimeout(() => {
            ttsProcessor.processTextToSpeech(INTRO_TEXT);
        }, 1000);

        // 开始录音
        setTimeout(() => {
            voiceChat.startRecording();
        }, 3000);

        // 初始化并启动自动对话模块（延迟启动，避免与欢迎语冲突）
        setTimeout(() => {
            // 创建自动对话模块实例
            autoChatModule = new AutoChatModule(config, ttsProcessor);

            // 添加到全局对象，便于其他模块访问
            global.autoChatModule = autoChatModule;

            // 启动自动对话模块
            autoChatModule.start();
            console.log('自动对话模块初始化完成');
            logToTerminal('info', '自动对话模块初始化完成');
        }, 8000); // 8秒后初始化自动对话

        // 在main函数中添加（放在voiceChat初始化之后）
        const chatInput = document.getElementById('chat-input');
        const chatSendBtn = document.getElementById('chat-send-btn');
        const textChatContainer = document.getElementById('text-chat-container');

        // 根据配置设置对话框初始显示状态
        if (config.ui && config.ui.hasOwnProperty('show_chat_box')) {
            textChatContainer.style.display = config.ui.show_chat_box ? 'block' : 'none';
        } else {
            // 如果配置中没有这个选项，默认隐藏
            textChatContainer.style.display = 'none';
        }

        // 切换文本框显示/隐藏的快捷键
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Alt') {
                e.preventDefault(); // 防止 Alt 键触发浏览器菜单
                const chatContainer = document.getElementById('text-chat-container');
                chatContainer.style.display = chatContainer.style.display === 'none' ? 'block' : 'none';
            }
        });

        // 按Enter键发送消息
        chatInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const message = chatInput.value.trim();
                if (message) {
                    voiceChat.handleTextMessage(message);
                    chatInput.value = '';
                }
            }
        });

        // 在模型初始化部分添加：
        model.hitTest = function(x, y) {
            return x >= interactionX &&
                x <= interactionX + interactionWidth &&
                y >= interactionY &&
                y <= interactionY + interactionHeight;
        };

        logToTerminal('info', '应用初始化完成');
    } catch (error) {
        console.error("加载模型错误:", error);
        console.error("错误详情:", error.message);
        logToTerminal('error', `加载模型错误: ${error.message}`);
        if (error.stack) {
            logToTerminal('error', `错误堆栈: ${error.stack}`);
        }
    }
})();

// 清理资源
window.onbeforeunload = () => {
    if (voiceChat) {
        voiceChat.stopRecording();
    }

    // 停止直播模块
    if (liveStreamModule && liveStreamModule.isRunning) {
        liveStreamModule.stop();
    }

    // 停止自动对话模块
    if (autoChatModule && autoChatModule.isRunning) {
        autoChatModule.stop();
    }

    // 停止MCP客户端模块
    if (mcpClientModule) {
        mcpClientModule.stop();
    }

    logToTerminal('info', '应用已关闭，资源已清理');
};