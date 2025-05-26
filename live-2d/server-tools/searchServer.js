// searchServer.js - 只返回内容的搜索工具
const axios = require('axios');

// Tavily API配置
const TAVILY_API_KEY = "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";

// 工具定义
const SEARCH_TOOL = {
    name: "web_search",
    description: "使用搜索网络引擎，并返回内容",
    parameters: {
        type: "object",
        properties: {
            query: {
                type: "string",
                description: "搜索关键词"
            },
            max_results: {
                type: "number",
                description: "最大返回结果数量",
                default: 1
            },
            max_chars: {
                type: "number",
                description: "每个结果最大提取的字符数",
                default: 5000
            }
        },
        required: ["query"]
    }
};

// 搜索功能实现 - 只返回内容
async function searchWebContentOnly(query, maxResults = 1, maxChars = 5000) {
    try {
        console.log(`正在搜索: ${query}`);
        
        // 搜索获取URL
        const searchResponse = await axios.post("https://api.tavily.com/search", {
            query: query,
            max_results: maxResults,
            api_key: TAVILY_API_KEY
        });
        
        const urls = searchResponse.data.results.map(result => result.url);
        
        if (urls.length === 0) {
            return `未找到关于 "${query}" 的搜索结果`;
        }
        
        console.log(`找到 ${urls.length} 个结果，正在提取内容...`);
        
        // 提取内容
        const extractResponse = await axios.post("https://api.tavily.com/extract", {
            urls: urls,
            api_key: TAVILY_API_KEY
        });
        
        // 只提取内容，不包括链接和其他元数据
        let allContent = "";
        
        extractResponse.data.results.forEach(item => {
            const content = item.raw_content || '';
            
            // 只保留maxChars长度的内容
            if (content.length > maxChars) {
                allContent += content.substring(0, maxChars) + "\n\n";
            } else {
                allContent += content + "\n\n";
            }
        });
        
        return allContent.trim();
    } catch (error) {
        console.error("搜索错误:", error.message);
        if (error.response) {
            console.error(`状态码: ${error.response.status}`);
        }
        return `搜索失败: ${error.message}`;
    }
}

// MCP模块接口
module.exports = {
    // 获取工具定义
    getToolDefinitions: function() {
        return [SEARCH_TOOL];
    },
    
    // 执行工具函数
    executeFunction: async function(name, parameters) {
        if (name !== "web_search") {
            throw new Error(`不支持的函数: ${name}`);
        }
        
        const query = parameters.query;
        if (!query) {
            throw new Error("缺少搜索关键词");
        }
        
        const maxResults = parameters.max_results || 1;
        const maxChars = parameters.max_chars || 5000;
        
        return await searchWebContentOnly(query, maxResults, maxChars);
    }
};