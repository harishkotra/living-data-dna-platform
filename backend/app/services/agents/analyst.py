from __future__ import annotations

import json

from app.services.external_apis import ExternalContextService
from app.services.llm_gateway import LLMGateway
from app.services.prompts import ROOT_CAUSE_PROMPT


class AnalystAgent:
    def __init__(self) -> None:
        self.llm = LLMGateway()
        self.external_context = ExternalContextService()

    async def analyze_issue(self, issue: dict, lineage_context: list[dict], schema_context: dict) -> dict:
        tavily_context = await self.external_context.tavily_lookup(
            f"data pipeline root cause for {issue['issue_type']} in dataset {issue.get('dataset', '')}"
        )
        payload = {
            "issue": issue,
            "lineage_context": lineage_context,
            "schema_context": schema_context,
            "tavily_context": tavily_context,
        }
        result = await self.llm.complete(ROOT_CAUSE_PROMPT, payload)
        try:
            parsed = json.loads(result)
            parsed["issue_type"] = issue["issue_type"]
            return parsed
        except json.JSONDecodeError:
            return {
                "issue_type": issue["issue_type"],
                "root_cause": result,
                "impact": "Potential downstream reliability degradation",
                "confidence": 0.5,
            }
