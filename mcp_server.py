#!/usr/bin/env python3
"""
🎴 TaijiOS MCP Server · 让 Trae / Cursor / Claude Desktop 零配置接入

装一次:
    pip install mcp>=1.0.0

在你的 AI IDE 的 MCP config 里加:
    {
      "mcpServers": {
        "taijios-zhuge": {
          "command": "python",
          "args": ["<ABS_PATH>/mcp_server.py"]
        }
      }
    }

ABS_PATH 就是本文件绝对路径 (解包后 bundle 目录 + /mcp_server.py).

Trae: Settings → MCP → Add Server → 粘贴上面 JSON
Cursor: .cursor/mcp.json (工作区级) 或 ~/.cursor/mcp.json (全局)
Claude Desktop: ~/Library/Application Support/Claude/claude_desktop_config.json (Mac) /
                %APPDATA%/Claude/claude_desktop_config.json (Windows)

两个 tool 暴露出来:
  - predict(match): 诸葛亮足球推演 · 6 爻 + 64 卦 + 孔明亲笔
  - sync_crystals(): 拉公共晶体池 (HTTP 只读)
"""
import asyncio, sys, subprocess, re, os, pathlib

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    import mcp.types as types
except ImportError:
    print("错误: mcp 未装. 跑: pip install mcp>=1.0.0", file=sys.stderr)
    sys.exit(1)

ROOT = pathlib.Path(__file__).resolve().parent
ZHUGE = ROOT / "zhuge-skill"
ANSI = re.compile(r"\x1b\[[0-9;]*m")

server = Server("taijios-zhuge")


@server.list_tools()
async def list_tools():
    return [
        types.Tool(
            name="predict",
            description=(
                "诸葛亮足球推演 (TaijiOS). 输入对阵 (e.g. 'Inter vs Cagliari'), "
                "返回 6 维爻位 + 64 卦 + 1X2/大小球推荐 + 孔明亲笔古文评 (如果 LLM 配好)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "match": {
                        "type": "string",
                        "description": "对阵字符串, 格式 'HomeTeam vs AwayTeam'",
                    }
                },
                "required": ["match"],
            },
        ),
        types.Tool(
            name="sync_crystals",
            description=(
                "拉取公共决策晶体池 (TaijiOS zhuge-crystals). "
                "HTTP 只读 · 单向 pull · 不上传任何本地数据 · 架构级隐私合约."
            ),
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    if name == "predict":
        match = arguments.get("match", "").strip()
        if not match:
            return [types.TextContent(type="text", text="error: 缺 match 参数")]
        r = subprocess.run(
            [sys.executable, str(ZHUGE / "scripts" / "predict.py"), match],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            cwd=str(ZHUGE),
            env=env,
        )
        text = ANSI.sub("", (r.stdout or "") + (r.stderr or ""))
        return [types.TextContent(type="text", text=text or "(empty output)")]

    elif name == "sync_crystals":
        r = subprocess.run(
            [sys.executable, str(ZHUGE / "scripts" / "sync.py"), "pull"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            cwd=str(ZHUGE),
            env=env,
        )
        return [
            types.TextContent(
                type="text", text=ANSI.sub("", (r.stdout or "") + (r.stderr or ""))
            )
        ]

    return [types.TextContent(type="text", text=f"unknown tool: {name}")]


async def run():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(run())
