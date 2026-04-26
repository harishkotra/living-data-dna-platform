from __future__ import annotations

import json

import httpx

from app.core.config import get_settings


class LLMGateway:
    def __init__(self) -> None:
        self.settings = get_settings()

    async def complete(self, prompt: str, payload: dict) -> str:
        if not self.settings.llm_api_key:
            raise ValueError("LLM_API_KEY is required")

        body = {
            "model": self.settings.llm_model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": json.dumps(payload)},
            ],
            "temperature": 0.2,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.llm_api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(f"{self.settings.llm_base_url.rstrip('/')}/chat/completions", headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
        return data["choices"][0]["message"]["content"]
