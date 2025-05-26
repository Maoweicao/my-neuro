// server.js - 主MCP服务器
// 自动加载所有子模块的版本

const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const app = express();
const PORT = 3000;

// 启用CORS和JSON解析
app.use(cors());
app.use(express.json());

// 存储SSE客户端连接
const sseClients = {};

// 存储所有加载的模块
let modules = [];
// 汇总所有工具定义
let allTools = [];

// 动态加载所有JavaScript文件作为模块
function loadModules() {
    modules = [];
    allTools = [];
    
    // 读取当前目录中所有文件
    const files = fs.readdirSync(__dirname);
    
    // 处理每个JavaScript文件
    files.forEach(file => {
        // 跳过主服务器文件和非JavaScript文件
        if (file === 'server.js' || !file.endsWith('.js')) {
            return;
        }
        
        try {
            const modulePath = path.join(__dirname, file);
            const module = require(modulePath);
            
            // 检查模块是否有必要的接口
            if (typeof module.getToolDefinitions === 'function' && 
                typeof module.executeFunction === 'function') {
                modules.push(module);
                
                // 获取并添加工具定义
                const tools = module.getToolDefinitions();
                if (Array.isArray(tools) && tools.length > 0) {
                    allTools = [...allTools, ...tools];
                    console.log(`已加载模块: ${file} (${tools.length}个工具)`);
                } else {
                    console.warn(`模块 ${file} 没有返回有效的工具定义`);
                }
            } else {
                console.warn(`跳过文件 ${file}: 不是有效的MCP模块(缺少必要的接口)`);
            }
        } catch (error) {
            console.error(`加载模块 ${file} 失败:`, error);
        }
    });
    
    console.log(`总共加载了 ${modules.length} 个模块, ${allTools.length} 个工具`);
}

// 查找工具对应的模块
function findModuleForTool(toolName) {
    return modules.find(module => 
        module.getToolDefinitions().some(tool => tool.name === toolName)
    );
}

// MCP发现端点 - 符合标准MCP规范
app.post('/mcp/v1/discover', (req, res) => {
    // MCP发现响应
    const serverInfo = {
        // MCP服务器信息
        server: {
            name: "自动加载MCP服务器",
            version: "1.0.0",
            vendor: "演示应用",
            description: "自动加载所有模块的MCP服务器"
        },
        // 可用工具（功能）列表
        functions: allTools
    };

    res.json(serverInfo);
});

// MCP调用端点 - 符合标准MCP规范
app.post('/mcp/v1/invoke', async (req, res) => {
    const { name, parameters } = req.body;

    if (!name) {
        return res.status(400).json({
            error: {
                message: "缺少函数名称",
                type: "InvalidRequest"
            }
        });
    }

    // 查找负责处理该工具的模块
    const module = findModuleForTool(name);
    if (!module) {
        return res.status(404).json({
            error: {
                message: `未知函数: ${name}`,
                type: "UnknownFunction"
            }
        });
    }

    try {
        // 委托给对应模块处理
        const result = await module.executeFunction(name, parameters);

        // 返回MCP标准格式的调用结果
        res.json({
            result: {
                content: result
            }
        });
    } catch (error) {
        res.status(500).json({
            error: {
                message: `函数执行失败: ${error.message}`,
                type: "ExecutionError"
            }
        });
    }
});

// 重新加载模块端点 - 允许在不重启服务器的情况下重新加载模块
app.post('/reload', (req, res) => {
    try {
        loadModules();
        res.json({
            success: true,
            modules: modules.length,
            tools: allTools.map(tool => tool.name)
        });
    } catch (error) {
        res.status(500).json({
            error: error.message
        });
    }
});

// 健康检查端点
app.get('/health', (req, res) => {
    res.json({ 
        status: 'ok',
        modules: modules.length,
        tools: allTools.map(tool => ({
            name: tool.name,
            description: tool.description
        }))
    });
});

// ===== SSE支持 =====

// SSE连接端点
app.get('/sse', (req, res) => {
    // 设置SSE必要的头信息
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.setHeader('Access-Control-Allow-Origin', '*');

    // 客户端ID，使用session_id参数或生成新ID
    const clientId = req.query.session_id || `client-${Date.now()}`;

    // 发送初始连接消息
    res.write(`event: connected\ndata: {"message": "SSE连接已建立", "clientId": "${clientId}"}\n\n`);

    // 发送端点事件(MCP协议要求)
    res.write(`event: endpoint\ndata: ${JSON.stringify({
        endpoint: `/messages?session_id=${clientId}`
    })}\n\n`);

    // 保存连接
    sseClients[clientId] = res;
    console.log(`SSE客户端 ${clientId} 已连接`);

    // 设置连接关闭时的处理
    req.on('close', () => {
        delete sseClients[clientId];
        console.log(`SSE客户端 ${clientId} 已断开连接`);
    });

    // 发送定期保活消息
    const keepAliveInterval = setInterval(() => {
        if (sseClients[clientId]) {
            res.write(`:keepalive\n\n`);
        } else {
            clearInterval(keepAliveInterval);
        }
    }, 30000); // 每30秒发送一次
});

// SSE消息处理端点
app.post('/messages', express.json(), async (req, res) => {
    const sessionId = req.query.session_id;
    const messageId = req.body.id;
    const method = req.body.method;
    const params = req.body.params;

    // 验证会话ID
    if (!sessionId || !sseClients[sessionId]) {
        return res.status(404).json({
            jsonrpc: "2.0",
            id: messageId,
            error: {
                code: -32001,
                message: "无效的会话ID"
            }
        });
    }

    // 处理初始化请求
    if (method === "initialize") {
        return res.json({
            jsonrpc: "2.0",
            id: messageId,
            result: {
                capabilities: {
                    tools: true,
                    resources: false,
                    prompts: false
                }
            }
        });
    }

    // 处理工具列表请求
    if (method === "tools/list") {
        return res.json({
            jsonrpc: "2.0",
            id: messageId,
            result: {
                tools: allTools
            }
        });
    }

    // 处理功能列表请求
    if (method === "listOfferings") {
        return res.json({
            jsonrpc: "2.0",
            id: messageId,
            result: {
                resources: [],
                tools: allTools,
                prompts: []
            }
        });
    }

    // 处理工具调用
    if (method === "tools/call") {
        const toolName = params.name;
        const toolArgs = params.parameters || {};

        // 查找负责处理该工具的模块
        const module = findModuleForTool(toolName);
        if (!module) {
            return res.status(404).json({
                jsonrpc: "2.0",
                id: messageId,
                error: {
                    code: -32601,
                    message: `未知工具: ${toolName}`
                }
            });
        }

        try {
            // 委托给对应模块处理
            const result = await module.executeFunction(toolName, toolArgs);

            // 返回工具调用结果
            return res.json({
                jsonrpc: "2.0",
                id: messageId,
                result: {
                    content: result
                }
            });
        } catch (error) {
            console.error(`工具调用错误 ${toolName}:`, error);
            return res.status(500).json({
                jsonrpc: "2.0",
                id: messageId,
                error: {
                    code: -32603,
                    message: `工具执行失败: ${error.message}`
                }
            });
        }
    }

    // 处理其他未知请求
    return res.status(404).json({
        jsonrpc: "2.0",
        id: messageId,
        error: {
            code: -32601,
            message: `未知方法: ${method}`
        }
    });
});

// 在服务器启动前先加载所有模块
loadModules();

// 启动服务器
app.listen(PORT, () => {
    console.log(`MCP服务器启动成功，监听端口: ${PORT}`);
    console.log(`已加载的工具:`);
    allTools.forEach(tool => {
        console.log(`- ${tool.name}: ${tool.description}`);
    });
    console.log(`\n标准MCP端点:`);
    console.log(`- http://localhost:${PORT}/mcp/v1/discover (POST)`);
    console.log(`- http://localhost:${PORT}/mcp/v1/invoke (POST)`);
    console.log(`\n管理端点:`);
    console.log(`- http://localhost:${PORT}/health (GET) - 检查服务器状态`);
    console.log(`- http://localhost:${PORT}/reload (POST) - 重新加载模块`);
});