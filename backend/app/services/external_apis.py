from __future__ import annotations

import httpx

from app.core.config import get_settings
from app.services.brightdata_mcp_client import BrightDataMCPClient


class ExternalContextService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.brightdata = BrightDataMCPClient()

    async def tavily_lookup(self, query: str) -> list[dict]:
        if not self.settings.tavily_api_key:
            raise ValueError("TAVILY_API_KEY is required")

        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.settings.tavily_api_key,
            "query": query,
            "search_depth": "advanced",
            "max_results": 5,
            "include_raw_content": False,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data.get("results", [])

    async def brightdata_validate(self, dataset: str) -> dict:
        query = (
            f"Find recent incident patterns and best practices for data pipeline breakage involving dataset {dataset}. "
            "Return concise reliability checks."
        )
        return await self.brightdata.discover(query)
