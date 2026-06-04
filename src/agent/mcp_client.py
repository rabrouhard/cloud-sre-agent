from __future__ import annotations
from typing import Any
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

class AgentMcpClient:
    def __init__(self, url: str):
        self.url = url

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        async with streamablehttp_client(self.url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments)
                if not result.content:
                    return None
                first = result.content[0]
                if hasattr(first, "text"):
                    import json
                    try: return json.loads(first.text)
                    except Exception: return first.text
                return first
