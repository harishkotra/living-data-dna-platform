from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import Dataset, DnaSnapshot, Issue, LineageEdge
from app.services.agents.analyst import AnalystAgent
from app.services.agents.explainer import ExplainerAgent
from app.services.agents.fixer import FixerAgent
from app.services.agents.observer import ObserverAgent
from app.services.external_apis import ExternalContextService


class AgentOrchestrator:
    def __init__(self) -> None:
        self.observer = ObserverAgent()
        self.analyst = AnalystAgent()
        self.fixer = FixerAgent()
        self.explainer = ExplainerAgent()
        self.external_context = ExternalContextService()

    async def run(self, db: Session, dataset_name: str, user_question: str | None = None) -> dict:
        dataset = db.query(Dataset).filter(Dataset.name == dataset_name).first()
        if not dataset:
            raise ValueError(f"Dataset not found: {dataset_name}")

        snaps = (
            db.query(DnaSnapshot)
            .filter(DnaSnapshot.dataset_id == dataset.id)
            .order_by(DnaSnapshot.captured_at.desc())
            .limit(2)
            .all()
        )
        latest = snaps[0] if snaps else None
        previous = snaps[1] if len(snaps) > 1 else None
        if not latest:
            raise ValueError(f"No DNA snapshots for dataset: {dataset_name}")

        edges = db.query(LineageEdge).all()
        issues = self.observer.detect_issues(dataset_name, latest, previous, edges)
        brightdata_validation = await self.external_context.brightdata_validate(dataset_name)

        for issue in issues:
            issue["details"]["external_validation"] = brightdata_validation
            db_issue = Issue(
                dataset=dataset_name,
                issue_type=issue["issue_type"],
                severity=issue["severity"],
                details=issue["details"],
            )
            db.add(db_issue)
        db.commit()

        analyses = []
        fixes = []
        for issue in issues:
            analysis = await self.analyst.analyze_issue(
                issue,
                lineage_context=[{"source": e.source, "target": e.target, "is_active": e.is_active} for e in edges],
                schema_context={
                    "latest": latest.genes.get("schema_gene", []),
                    "previous": previous.genes.get("schema_gene", []) if previous else [],
                },
            )
            analyses.append(analysis)
            fixes.append(self.fixer.suggest_fix(issue, analysis))

        narrative, sections = await self.explainer.explain(dataset_name, issues, analyses, fixes, user_question)
        return {
            "dataset": dataset_name,
            "issues": issues,
            "analysis": analyses,
            "fixes": fixes,
            "narrative": narrative,
            "sections": sections,
        }
