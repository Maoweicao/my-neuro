// MCP客户端模块 - 集成到AI桌宠系统
class MCPClientModule {
    constructor(config, ttsProcessor, emotionMapper) {
        // 保存配置和依赖项
        this.config = config.mcp || {};
        this.ttsProcessor = ttsProcessor;
        this.emotionMapper = emotionMapper;
        this.isEnabled = this.config.enabled || false;
        this.serverUrl = this.config.server_url || 'http://localhost:3000';
        
        // 状态标志
        this.isConnected = false;
        this.availableTools = [];
        this.sessionId = this.generateSessionId();
        
        console.log(`MCP客户端模块已创建，启用状态: ${this.isEnabled}`);
    }
    
    // 初始化模块
    async initialize() {
        if (!this.isEnabled) {
            console.log('MCP功能已禁用，不进行初始化');
            return false;
        }
        
        console.log('正在初始化MCP客户端模块...');
        return await this.discoverMCPTools();
    }
    
    // 发现可用的MCP工具
    async discoverMCPTools() {
        try {
            console.log(`尝试连接MCP服务器: ${this.serverUrl}/mcp/v1/discover`);
            
            const response = await fetch(`${this.serverUrl}/mcp/v1/discover`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP错误: ${response.status}`);
            }
            
            const data = await response.json();
            
            // 保存可用工具列表
            this.availableTools = data.functions || [];
            this.serverInfo = data.server || { name: "未知MCP服务器" };
            this.isConnected = true;
            
            console.log(`已连接到MCP服务器: ${this.serverInfo.name}`);
            console.log(`可用工具(${this.availableTools.length}): ${this.availableTools.map(t => t.name).join(', ')}`);
            
            return true;
        } catch (error) {
            console.error('MCP服务器连接失败:', error);
            this.isConnected = false;
            return false;
        }
    }
    
    // 获取工具列表，用于传递给LLM
    getToolsForLLM() {
        if (!this.isEnabled || !this.isConnected || this.availableTools.length === 0) {
            return [];
        }
        
        return this.availableTools.map(tool => ({
            type: "function",
            function: {
                name: tool.name,
                description: tool.description,
                parameters: tool.parameters
            }
        }));
    }
    
    // 处理LLM返回的工具调用
    async handleToolCalls(toolCalls) {
        if (!this.isEnabled || !this.isConnected || !toolCalls || toolCalls.length === 0) {
            return null;
        }
        
        const toolCall = toolCalls[0]; // 处理第一个工具调用
        const functionName = toolCall.function.name;
        
        // 解析参数
        let parameters;
        try {
            parameters = typeof toolCall.function.arguments === 'string'
                ? JSON.parse(toolCall.function.arguments)
                : toolCall.function.arguments;
        } catch (error) {
            console.error('解析工具参数错误:', error);
            parameters = {};
        }
        
        // 调用MCP工具
        return await this.invokeFunction(functionName, parameters);
    }
    
    // 调用MCP工具
    async invokeFunction(functionName, parameters) {
        if (!this.isEnabled || !this.isConnected) {
            console.error('MCP功能未启用或未连接到服务器');
            return null;
        }
        
        // 查找工具是否存在
        const tool = this.availableTools.find(t => t.name === functionName);
        if (!tool) {
            console.error(`未找到MCP工具: ${functionName}`);
            return null;
        }
        
        try {
            console.log(`调用MCP工具: ${functionName}，参数:`, parameters);
            
            const response = await fetch(`${this.serverUrl}/mcp/v1/invoke`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    name: functionName,
                    parameters: parameters
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP错误: ${response.status}`);
            }
            
            const data = await response.json();
            console.log(`MCP工具(${functionName})返回:`, data);
            
            // 处理返回结果
            return data.result?.content || JSON.stringify(data.result);
        } catch (error) {
            console.error(`MCP工具调用失败(${functionName}):`, error);
            return null;
        }
    }
    
    // 生成唯一会话ID
    generateSessionId() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }
    
    // 停止MCP客户端
    stop() {
        this.isConnected = false;
        console.log('MCP客户端已停止');
    }
}

// 导出模块
module.exports = { MCPClientModule };