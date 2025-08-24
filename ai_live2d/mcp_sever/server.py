from mcp.server.fastmcp import FastMCP
import aiohttp

# 创建一个MCP服务器
mcp = FastMCP("本地演示服务器")

# 添加一个加法工具
@mcp.tool()
def add(a: int, b: int) -> int:
    """将两个数字相加"""
    return a + b

# 添加一个乘法工具
@mcp.tool()
def multiply(a: int, b: int) -> int:
    """将两个数字相乘"""
    return a * b

# 添加一个动态问候资源
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """获取个性化问候"""
    return f"你好，{name}！欢迎使用本地MCP服务器。"

# 添加一个简单的提示模板
@mcp.prompt()
def calculate_prompt(operation: str, a: int, b: int) -> str:
    """创建一个计算提示"""
    return f"请执行以下{operation}运算: {a} 和 {b}"

# 异步天气查询工具
@mcp.tool()
async def get_current_weather(city: str) -> str:  # 添加 async 关键字
    print(f"[debug-server] get_current_weather({city})")
    endpoint = "https://wttr.in"
    
    async with aiohttp.ClientSession() as session:  # 创建异步会话
        async with session.get(f"{endpoint}/{city}") as response:
            return await response.text()  # 异步获取响应文本

# 直接运行服务器
if __name__ == "__main__":
    mcp.run("stdio")