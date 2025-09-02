@echo off
REM MCP功能快速测试脚本
REM 测试UV和Bun MCP服务器连接

echo MCP功能测试
echo ============
echo.
echo 此脚本将测试UV和Bun MCP服务器的连接...
echo.

REM 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误：未找到Python
    pause
    exit /b 1
)

echo 正在测试MCP服务器连接...
echo.

REM 创建测试脚本
echo import asyncio > temp_test_mcp.py
echo import sys >> temp_test_mcp.py
echo sys.path.append('.') >> temp_test_mcp.py
echo. >> temp_test_mcp.py
echo from ai.mcp_client import MCPClient >> temp_test_mcp.py
echo. >> temp_test_mcp.py
echo async def test_mcp(): >> temp_test_mcp.py
echo     try: >> temp_test_mcp.py
echo         import json >> temp_test_mcp.py
echo         with open('config.json', 'r', encoding='utf-8') as f: >> temp_test_mcp.py
echo             config = json.load(f) >> temp_test_mcp.py
echo. >> temp_test_mcp.py
echo         client = MCPClient(config) >> temp_test_mcp.py
echo         await client.start() >> temp_test_mcp.py
echo. >> temp_test_mcp.py
echo         print("MCP服务器连接测试完成！") >> temp_test_mcp.py
echo         print(f"连接的服务器数量: {len(client.sessions)}") >> temp_test_mcp.py
echo         print(f"可用的工具数量: {len(client.all_available_tools_for_llm)}") >> temp_test_mcp.py
echo. >> temp_test_mcp.py
echo         await client.cleanup() >> temp_test_mcp.py
echo. >> temp_test_mcp.py
echo     except Exception as e: >> temp_test_mcp.py
echo         print(f"测试失败: {e}") >> temp_test_mcp.py
echo         import traceback >> temp_test_mcp.py
echo         traceback.print_exc() >> temp_test_mcp.py
echo. >> temp_test_mcp.py
echo if __name__ == "__main__": >> temp_test_mcp.py
echo     asyncio.run(test_mcp()) >> temp_test_mcp.py

REM 运行测试
python temp_test_mcp.py

REM 清理临时文件
del temp_test_mcp.py

echo.
echo 测试完成！
echo.
pause
