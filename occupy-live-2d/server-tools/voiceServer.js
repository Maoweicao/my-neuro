// modules/voiceModule.js - 声线切换工具模块

const axios = require('axios');

// TTS 声线切换 API 配置
const TTS_SERVER_BASE = "http://127.0.0.1:5000";
const VOICE_MAP = {
    "肥牛": 0,
    "邪牛": 1
};

// 工具定义
const VOICE_TOOL = {
    name: "change_voice",
    description: "切换TTS语音合成的声线。",
    parameters: {
        type: "object",
        properties: {
            voice_name: {
                type: "string",
                description: "声线名称，可选值为：肥牛、邪牛"
            }
        },
        required: ["voice_name"]
    }
};

// 切换TTS声线
async function changeVoice(voiceName) {
    if (!VOICE_MAP.hasOwnProperty(voiceName)) {
        return `⚠️ 未知声线: ${voiceName}，可用声线: ${Object.keys(VOICE_MAP).join(", ")}`;
    }

    const voiceId = VOICE_MAP[voiceName];
    const url = `${TTS_SERVER_BASE}/select_voice/${voiceId}`;

    try {
        const response = await axios.get(url, { timeout: 5000 });

        if (response.status >= 200 && response.status < 300) {
            return `✅ 已成功切换到${voiceName}的声线`;
        } else {
            return `⚠️ 声线切换失败，HTTP状态码: ${response.status}`;
        }
    } catch (error) {
        console.error("声线切换错误:", error);

        if (error.response) {
            return `⚠️ 声线切换失败，HTTP状态码: ${error.response.status}`;
        } else if (error.request) {
            return "⚠️ 声线切换请求超时，TTS服务器可能未运行。";
        } else {
            return `⚠️ 声线切换请求失败: ${error.message}`;
        }
    }
}

// 模块接口：获取工具定义
function getToolDefinitions() {
    return [VOICE_TOOL];
}

// 模块接口：执行工具函数
async function executeFunction(name, parameters) {
    if (name !== "change_voice") {
        throw new Error(`此模块不支持工具: ${name}`);
    }

    const voiceName = parameters?.voice_name;
    if (!voiceName) {
        throw new Error("缺少声线名称参数");
    }

    return await changeVoice(voiceName);
}

// 导出模块接口
module.exports = {
    getToolDefinitions,
    executeFunction
};