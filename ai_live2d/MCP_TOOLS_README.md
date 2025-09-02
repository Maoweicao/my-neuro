# MCP工具支持说明

## 概述

本项目现在支持使用UV和Bun作为MCP服务器的运行时环境。这允许您使用这些现代工具包管理器来运行MCP服务器。

## 支持的传输类型

### 1. stdio (推荐 - 包括UV和Bun)
- **transport**: `"stdio"`
- **配置参数**:
  - `command`: 命令名 (`"uv"`, `"bun"`, `"npx"`, `"python"` 等)
  - `package`: 要运行的包名 (对于UV/Bun包管理器)
  - `script`: 要运行的脚本文件路径
  - `args`: 传递给命令的额外参数
  - `env`: 环境变量

### 2. python (Python模块)
- **transport**: `"python"`
- **配置参数**:
  - `module`: Python模块路径
  - `args`: 传递给模块的参数

### 3. sse (用于HTTP流)
- **transport**: `"sse"`
- **配置参数**:
  - `url`: SSE端点URL
  - `headers`: 请求头

## 配置示例

在 `config.json` 中的 `mcp.mcpServers` 下添加服务器配置：

```json
{
  "uv_server": {
    "transport": "stdio",
    "command": "uv",
    "package": "@modelcontextprotocol/server-everything",
    "args": ["--port", "3000"],
    "enabled": true,
    "description": "使用UV运行的MCP服务器"
  },
  "bun_server": {
    "transport": "stdio",
    "command": "bun",
    "package": "@modelcontextprotocol/server-everything",
    "args": ["--host", "localhost"],
    "enabled": true,
    "description": "使用Bun运行的MCP服务器"
  },
  "npx_server": {
    "transport": "stdio",
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-everything"],
    "enabled": true,
    "description": "使用npx运行的MCP服务器"
  }
}
```

## 自动工具下载

如果您的系统上没有安装UV或Bun，可以运行自动下载脚本：

### Windows
```batch
download_mcp_tools.bat
```

### 手动运行
```bash
python utils\mcp_tool_downloader.py
```

## 功能特性

1. **自动检测**: 脚本会自动检测已安装的工具，跳过已存在的安装
2. **跨平台支持**: 支持Windows、Linux和macOS
3. **PATH更新**: 安装完成后会提示如何更新PATH环境变量
4. **错误处理**: 提供详细的错误信息和故障排除指导

## 故障排除

### 工具未找到错误
如果遇到"command not found"错误，请确保：
1. 工具已正确安装
2. PATH环境变量包含工具的安装路径
3. 重新启动应用程序或终端会话

### 下载失败
- 检查网络连接
- 验证GitHub是否可访问
- 尝试手动下载并安装工具

### 权限问题
在Unix-like系统上，如果遇到权限问题，请确保安装目录有写入权限，或使用sudo运行安装脚本。

## 技术细节

- **stdio传输**: 统一的命令行工具支持，包括UV、Bun、npx等
- **智能检测**: 自动检测可用的工具并选择合适的运行方式
- **PATH管理**: 自动查找和添加工具路径
- **跨平台兼容**: 支持Windows、Linux、macOS
- **向后兼容**: 保持对现有配置的兼容性
- **安装位置**: UV和Bun安装到 `%LOCALAPPDATA%\MCPTools` (Windows) 或 `~/.local/bin` (Unix)

## 示例MCP服务器

您可以使用以下示例MCP服务器进行测试：

- `@modelcontextprotocol/server-everything`: 功能完整的示例服务器
- `@modelcontextprotocol/server-filesystem`: 文件系统操作服务器
- `@modelcontextprotocol/server-git`: Git操作服务器

## 更新日志

- ✅ **重构传输类型**: 将UV和Bun集成到stdio传输类型中，更符合MCP设计理念
- ✅ **智能命令检测**: stdio传输现在可以自动检测和使用uv/bun命令
- ✅ **统一配置格式**: 所有命令行工具现在使用相同的配置结构
- ✅ **保持兼容性**: 现有配置继续有效，无需修改
- ✅ **改进错误处理**: 更好的错误信息和故障排除指导
- ✅ **跨平台兼容**: 支持Windows、Linux、macOS
- ✅ **自动工具下载**: 自动下载和安装UV和Bun工具包管理器
