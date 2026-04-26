from __future__ import annotations


class FixerAgent:
    def suggest_fix(self, issue: dict, analysis: dict) -> dict:
        issue_type = issue["issue_type"]
        if issue_type == "schema_drift":
            return {
                "issue_type": issue_type,
                "suggested_actions": [
                    "Create backward-compatible view with legacy columns.",
                    "Version contract in OpenMetadata and notify consumers.",
                    "Replay failed downstream DAG runs after compatibility patch.",
                ],
                "rollback_steps": [
                    "Re-deploy previous schema in ingestion job.",
                    "Restore lineage edge state and validate BI model.",
                ],
                "confidence": analysis.get("confidence", 0.7),
            }

        if issue_type == "broken_lineage":
            return {
                "issue_type": issue_type,
                "suggested_actions": [
                    "Recreate missing transformation node.",
                    "Patch lineage metadata to reflect current pipeline.",
                    "Run quality check for target dataset completeness.",
                ],
                "rollback_steps": ["Point consumers to previous stable table version."],
                "confidence": analysis.get("confidence", 0.72),
            }

        return {
            "issue_type": issue_type,
            "suggested_actions": ["Add missing metadata documentation."],
            "rollback_steps": ["No rollback required."],
            "confidence": analysis.get("confidence", 0.9),
        }
