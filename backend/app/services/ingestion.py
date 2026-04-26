from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Dataset, DnaSnapshot, LineageEdge
from app.services.dna_builder import build_dna
from app.services.openmetadata_client import OpenMetadataClient


class MetadataIngestionService:
    def __init__(self) -> None:
        self.client = OpenMetadataClient()

    async def sync(self, db: Session) -> dict:
        normalized = await self.client.fetch_normalized_metadata()

        edge_count = 0
        snapshot_count = 0
        for item in normalized:
            dataset = db.query(Dataset).filter(Dataset.name == item["dataset"]).first()
            if not dataset:
                dataset = Dataset(name=item["dataset"], owner=item.get("owner", "unknown"), description=item.get("description", ""))
                db.add(dataset)
                db.flush()
            else:
                dataset.owner = item.get("owner", dataset.owner)
                dataset.description = item.get("description", dataset.description)

            dna = build_dna(item)
            snapshot = DnaSnapshot(dataset_id=dataset.id, trust_score=dna["trust_score"], genes=dna["genes"])
            db.add(snapshot)
            snapshot_count += 1

            for edge in item.get("lineage", []):
                existing = (
                    db.query(LineageEdge)
                    .filter(LineageEdge.source == edge["source"], LineageEdge.target == edge["target"])
                    .first()
                )
                if existing:
                    existing.is_active = edge.get("is_active", True)
                    existing.broken_reason = edge.get("broken_reason")
                else:
                    db.add(
                        LineageEdge(
                            source=edge["source"],
                            target=edge["target"],
                            is_active=edge.get("is_active", True),
                            broken_reason=edge.get("broken_reason"),
                        )
                    )
                edge_count += 1

        db.commit()
        return {"datasets": len(normalized), "snapshots": snapshot_count, "lineage_edges": edge_count}
