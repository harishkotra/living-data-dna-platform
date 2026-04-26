from __future__ import annotations

from urllib.parse import urlencode

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import TextContent

from app.core.config import get_settings


class BrightDataMCPClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _build_url(self) -> str:
        if not self.settings.brightdata_api_token:
            raise ValueError("BRIGHTDATA_API_TOKEN is required")

        params: dict[str, str] = {"token": self.settings.brightdata_api_token}
        if self.settings.brightdata_pro_mode:
            params["pro"] = "1"
        if self.settings.brightdata_groups:
            params["groups"] = self.settings.brightdata_groups
        if self.settings.brightdata_tools:
            params["tools"] = self.settings.brightdata_tools

        return f"{self.settings.brightdata_mcp_base_url}?{urlencode(params)}"

    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        url = self._build_url()

        async with streamablehttp_client(url) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)

        text_parts = []
        for block in result.content:
            if isinstance(block, TextContent):
                text_parts.append(block.text)

        return {
            "tool": tool_name,
            "structured": result.structuredContent,
            "text": "\n".join(text_parts).strip(),
            "is_error": bool(result.isError),
        }

    async def discover(self, query: str) -> dict:
        return await self.call_tool("discover", {"query": query})
