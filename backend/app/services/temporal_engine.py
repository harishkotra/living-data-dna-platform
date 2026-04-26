from __future__ import annotations


def _schema_set(genes: dict) -> set[tuple[str, str]]:
    return {(col["name"], col["type"]) for col in genes.get("schema_gene", [])}


def compute_schema_diff(previous_genes: dict, current_genes: dict) -> dict:
    prev = _schema_set(previous_genes)
    curr = _schema_set(current_genes)
    return {
        "added": sorted([{"name": c[0], "type": c[1]} for c in curr - prev], key=lambda x: x["name"]),
        "removed": sorted([{"name": c[0], "type": c[1]} for c in prev - curr], key=lambda x: x["name"]),
    }


def compute_lineage_diff(previous_genes: dict, current_genes: dict) -> dict:
    prev = {(e["source"], e["target"], e.get("is_active", True)) for e in previous_genes.get("lineage_gene", [])}
    curr = {(e["source"], e["target"], e.get("is_active", True)) for e in current_genes.get("lineage_gene", [])}
    return {
        "activated": [{"source": e[0], "target": e[1]} for e in curr - prev if e[2]],
        "deactivated": [{"source": e[0], "target": e[1]} for e in curr - prev if not e[2]],
    }
