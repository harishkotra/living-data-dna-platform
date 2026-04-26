from __future__ import annotations

from datetime import datetime


def calculate_trust_score(metadata: dict) -> float:
    schema = metadata.get("schema", [])
    lineage = metadata.get("lineage", [])
    usage = metadata.get("usage", {})
    description = metadata.get("description", "")

    schema_score = 1.0 if schema else 0.4
    description_score = 1.0 if description and len(description) > 12 else 0.5
    lineage_score = 1.0
    if lineage:
        inactive = sum(1 for edge in lineage if not edge.get("is_active", True))
        lineage_score = max(0.2, 1.0 - inactive / len(lineage))

    usage_score = min(1.0, usage.get("weekly_queries", 0) / 1000)

    trust = (0.35 * schema_score) + (0.2 * description_score) + (0.3 * lineage_score) + (0.15 * usage_score)
    return round(trust * 100, 2)


def build_dna(metadata: dict) -> dict:
    trust_score = calculate_trust_score(metadata)
    genes = {
        "schema_gene": metadata.get("schema", []),
        "lineage_gene": metadata.get("lineage", []),
        "usage_gene": metadata.get("usage", {}),
        "ownership_gene": {
            "owner": metadata.get("owner", "unknown"),
            "description": metadata.get("description", ""),
        },
        "computed_at": datetime.utcnow().isoformat(),
    }
    return {"dataset": metadata["dataset"], "trust_score": trust_score, "genes": genes}
