// recordServer.js - 带原文的记录工具 (合并版)

const fs = require('fs');
const path = require('path');

// 文件路径 - 保存在上一级目录
const RECORDS_FILE = path.join(process.cwd(), '..', 'text_database.txt');

// 工具定义 - 重要信息记录
const NOTE_TOOL = {
    name: "record_note",
    description: "记录用户要求的信息到文件中，当用户要求记录某些内容时，使用此工具记录",
    parameters: {
        type: "object",
        properties: {
            content: {
                type: "string",
                description: "要记录的内容"
            }
        },
        required: ["content"]
    }
};

// 工具定义 - 情感关怀记录 (带原文)
const CARE_TOOL = {
    name: "record_emotional_insight",
    description: "记录用户情感状态的洞察和总结。当用户分享个人情感问题、心理困扰或成长挑战时使用。",
    parameters: {
        type: "object",
        properties: {
            user_message: {
                type: "string",
                description: "用户的原始消息内容"
            },
            summary: {
                type: "string",
                description: "对用户情感状态的总结，以及自己对用户吐露这些内容的想法。要用自己的性格来关怀用户并给出自己的点评和想法"
            }
        },
        required: ["user_message", "summary"]
    }
};

// 获取简化的日期 (只到天)
function getSimpleDate() {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth() + 1;
    const day = now.getDate();
    return `${year}年${month}月${day}日`;
}

// 保存重要信息到文件
async function saveNote(content) {
    try {
        // 获取简化日期
        const date = getSimpleDate();
        
        // 格式化笔记
        const note = `[${date}] 普通记录: ${content}\n\n`;
        
        // 检查文件是否存在，不存在则创建
        if (!fs.existsSync(RECORDS_FILE)) {
            fs.writeFileSync(RECORDS_FILE, '', 'utf8');
        }
        
        // 追加笔记到文件
        fs.appendFileSync(RECORDS_FILE, note, 'utf8');
        
        return {
            success: true,
            file: RECORDS_FILE
        };
    } catch (error) {
        console.error('保存笔记错误:', error);
        throw error;
    }
}

// 保存关怀记录到文件 (带原文)
async function saveCareRecord(userMessage, summary) {
    try {
        // 获取简化日期
        const date = getSimpleDate();
        
        // 格式化记录，包含用户原文
        const record = `[${date}] 情感记录:\n用户原文: "${userMessage}"\n总结: ${summary}\n\n`;
        
        // 检查文件是否存在，不存在则创建
        if (!fs.existsSync(RECORDS_FILE)) {
            fs.writeFileSync(RECORDS_FILE, '', 'utf8');
        }
        
        // 追加记录到文件
        fs.appendFileSync(RECORDS_FILE, record, 'utf8');
        
        return {
            success: true,
            file: RECORDS_FILE
        };
    } catch (error) {
        console.error('保存情感记录错误:', error);
        throw error;
    }
}

// 模块接口：获取工具定义
function getToolDefinitions() {
    return [NOTE_TOOL, CARE_TOOL];
}

// 模块接口：执行工具函数
async function executeFunction(name, parameters) {
    // 处理重要信息记录
    if (name === "record_note") {
        const content = parameters?.content;
        if (!content || content.trim() === '') {
            throw new Error("记录内容不能为空");
        }
        
        try {
            await saveNote(content);
            return `✅ 已记录到all_records.txt文件`;
        } catch (error) {
            return `⚠️ 记录失败: ${error.message}`;
        }
    }
    
    // 处理情感关怀记录
    else if (name === "record_emotional_insight") {
        const userMessage = parameters?.user_message;
        const summary = parameters?.summary;
        
        if (!userMessage || userMessage.trim() === '') {
            throw new Error("用户原文不能为空");
        }
        
        if (!summary || summary.trim() === '') {
            throw new Error("情感总结不能为空");
        }
        
        try {
            await saveCareRecord(userMessage, summary);
            // 这个工具应该是"静默"的，不直接告诉用户记录了什么
            return `✓ 记录已保存`; // 这个返回值通常不会直接展示给用户
        } catch (error) {
            return `⚠️ 情感记录失败: ${error.message}`;
        }
    }
    
    // 未知工具
    else {
        throw new Error(`此模块不支持工具: ${name}`);
    }
}

// 导出模块接口
module.exports = {
    getToolDefinitions,
    executeFunction
};