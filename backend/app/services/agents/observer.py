from __future__ import annotations

from app.models import DnaSnapshot, LineageEdge


class ObserverAgent:
    def detect_issues(self, dataset: str, latest: DnaSnapshot, previous: DnaSnapshot | None, edges: list[LineageEdge]) -> list[dict]:
        issues: list[dict] = []
        description = latest.genes.get("ownership_gene", {}).get("description", "")
        if not description:
            issues.append(
                {
                    "dataset": dataset,
                    "issue_type": "missing_description",
                    "severity": "low",
                    "details": {"message": "Dataset description is missing."},
                }
            )

        if previous:
            prev_schema = {(c["name"], c["type"]) for c in previous.genes.get("schema_gene", [])}
            curr_schema = {(c["name"], c["type"]) for c in latest.genes.get("schema_gene", [])}
            if prev_schema != curr_schema:
                issues.append(
                    {
                        "dataset": dataset,
                        "issue_type": "schema_drift",
                        "severity": "high",
                        "details": {
                            "added": [{"name": x[0], "type": x[1]} for x in curr_schema - prev_schema],
                            "removed": [{"name": x[0], "type": x[1]} for x in prev_schema - curr_schema],
                        },
                    }
                )

        broken = [e for e in edges if e.source == dataset and not e.is_active]
        for edge in broken:
            issues.append(
                {
                    "dataset": dataset,
                    "issue_type": "broken_lineage",
                    "severity": "critical",
                    "details": {
                        "target": edge.target,
                        "reason": edge.broken_reason or "No reason provided",
                    },
                }
            )

        return issues
