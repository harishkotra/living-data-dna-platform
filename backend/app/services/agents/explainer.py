from __future__ import annotations

import json

from app.services.llm_gateway import LLMGateway
from app.services.prompts import EXPLANATION_PROMPT


class ExplainerAgent:
    def __init__(self) -> None:
        self.llm = LLMGateway()

    async def explain(
        self, dataset: str, issues: list[dict], analyses: list[dict], fixes: list[dict], user_question: str | None = None
    ) -> tuple[str, dict[str, str]]:
        payload = {
            "dataset": dataset,
            "issues": issues,
            "analyses": analyses,
            "fixes": fixes,
            "user_question": user_question,
        }
        text = await self.llm.complete(EXPLANATION_PROMPT, payload)
        try:
            parsed = json.loads(text)
            sections = {
                "Executive Summary": parsed.get("executive_summary", "").strip(),
                "Root Cause": parsed.get("root_cause", "").strip(),
                "Business Impact": parsed.get("business_impact", "").strip(),
                "Recommended Fix (Now/Next)": parsed.get("recommended_fix_now_next", "").strip(),
                "Confidence + Evidence": parsed.get("confidence_and_evidence", "").strip(),
            }
        except json.JSONDecodeError:
            sections = {
                "Executive Summary": text.strip() or "No explanation returned.",
                "Root Cause": "Unable to parse structured root cause from model output.",
                "Business Impact": "Potential reliability degradation in downstream consumers.",
                "Recommended Fix (Now/Next)": "Review lineage dependencies and restore schema compatibility.",
                "Confidence + Evidence": "Medium confidence from agent-derived signals.",
            }

        narrative = "\n\n".join(f"{k}: {v}" for k, v in sections.items())
        return narrative, sections
