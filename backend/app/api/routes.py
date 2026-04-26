from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Dataset, DnaSnapshot, LineageEdge
from app.schemas import AnalyzeRequest, AnalyzeResponse, GraphResponse, SimulateFixRequest, TimelineResponse
from app.services.agents.orchestrator import AgentOrchestrator
from app.services.demo_magic import current_metrics, run_magic_demo, severity_from_score
from app.services.ingestion import MetadataIngestionService
from app.services.temporal_engine import compute_lineage_diff, compute_schema_diff

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.get("/dna/{dataset}")
def get_dna(dataset: str, db: Session = Depends(get_db)):
    data = db.query(Dataset).filter(Dataset.name == dataset).first()
    if not data:
        raise HTTPException(status_code=404, detail="Dataset not found")

    snap = (
        db.query(DnaSnapshot)
        .filter(DnaSnapshot.dataset_id == data.id)
        .order_by(DnaSnapshot.captured_at.desc())
        .first()
    )
    if not snap:
        raise HTTPException(status_code=404, detail="DNA snapshot not found")

    edges = db.query(LineageEdge).all()
    metrics = current_metrics(db, data, edges, latest=snap)

    return {
        "dataset": data.name,
        "owner": data.owner,
        "description": data.description,
        "trust_score": snap.trust_score,
        "captured_at": snap.captured_at,
        "genes": snap.genes,
        "mutation_type": snap.mutation_type,
        "incident": snap.incident,
        "risk_score": metrics["risk_score"],
        "mutation_frequency_24h": metrics["mutation_frequency_24h"],
        "blast_radius": metrics["blast_radius"],
        "severity_level": metrics["severity_level"],
    }


@router.get("/timeline/{dataset}", response_model=TimelineResponse)
def get_timeline(dataset: str, db: Session = Depends(get_db)):
    data = db.query(Dataset).filter(Dataset.name == dataset).first()
    if not data:
        raise HTTPException(status_code=404, detail="Dataset not found")

    snaps = (
        db.query(DnaSnapshot)
        .filter(DnaSnapshot.dataset_id == data.id)
        .order_by(DnaSnapshot.captured_at.asc())
        .all()
    )

    schema_diff = {}
    lineage_diff = {}
    if len(snaps) >= 2:
        schema_diff = compute_schema_diff(snaps[-2].genes, snaps[-1].genes)
        lineage_diff = compute_lineage_diff(snaps[-2].genes, snaps[-1].genes)

    edges = db.query(LineageEdge).all()
    latest_metrics = current_metrics(db, data, edges, latest=snaps[-1] if snaps else None)
    timeline_events = [
        {
            "captured_at": s.captured_at,
            "dataset": dataset,
            "event_type": s.mutation_type or "stable_snapshot",
            "message": s.incident or "Snapshot captured",
        }
        for s in snaps
    ]

    return {
        "dataset": dataset,
        "snapshots": [
            {
                "captured_at": s.captured_at,
                "trust_score": s.trust_score,
                "mutation_type": s.mutation_type,
                "incident": s.incident,
                "genes": s.genes,
                "risk_score": (s.genes or {}).get("metrics", {}).get("risk_score"),
                "mutation_frequency_24h": (s.genes or {}).get("metrics", {}).get("mutation_frequency_24h"),
                "blast_radius": (s.genes or {}).get("metrics", {}).get("blast_radius"),
                "severity_level": (s.genes or {}).get("metrics", {}).get("severity_level"),
            }
            for s in snaps
        ],
        "schema_diff": schema_diff,
        "lineage_diff": lineage_diff,
        "timeline_events": timeline_events,
        "metrics": latest_metrics,
    }


@router.get("/graph", response_model=GraphResponse)
def get_graph(db: Session = Depends(get_db)):
    datasets = db.query(Dataset).all()
    edges = db.query(LineageEdge).all()

    latest_snap_by_dataset = {}
    metrics_by_dataset = {}
    for dataset in datasets:
        snap = (
            db.query(DnaSnapshot)
            .filter(DnaSnapshot.dataset_id == dataset.id)
            .order_by(DnaSnapshot.captured_at.desc())
            .first()
        )
        if snap:
            latest_snap_by_dataset[dataset.name] = snap
        metrics_by_dataset[dataset.name] = current_metrics(db, dataset, edges, latest=snap)

    nodes = [
        {
            "id": d.name,
            "label": d.name,
            "trust_score": latest_snap_by_dataset[d.name].trust_score if d.name in latest_snap_by_dataset else 0,
            "mutation": latest_snap_by_dataset[d.name].mutation_type if d.name in latest_snap_by_dataset else None,
            "risk_score": metrics_by_dataset[d.name]["risk_score"],
            "mutation_frequency_24h": metrics_by_dataset[d.name]["mutation_frequency_24h"],
            "blast_radius": metrics_by_dataset[d.name]["blast_radius"],
            "severity_level": metrics_by_dataset[d.name]["severity_level"],
        }
        for d in datasets
    ]

    edge_payload = [
        {
            "id": f"{e.source}->{e.target}",
            "source": e.source,
            "target": e.target,
            "is_active": e.is_active,
            "reason": e.broken_reason,
            "severity_level": "critical" if not e.is_active else "low",
        }
        for e in edges
    ]

    anomalies = [
        {
            "dataset": e.source,
            "type": "broken_lineage",
            "target": e.target,
            "reason": e.broken_reason,
            "severity_level": "critical",
        }
        for e in edges
        if not e.is_active
    ]

    max_risk = max((node["risk_score"] for node in nodes), default=0)
    aggregate = {
        "risk_score": max_risk,
        "mutation_frequency_24h": sum(node["mutation_frequency_24h"] for node in nodes),
        "blast_radius": max((node["blast_radius"] for node in nodes), default=0),
        "severity_level": severity_from_score(max_risk),
    }
    return {"nodes": nodes, "edges": edge_payload, "anomalies": anomalies, "metrics": aggregate}


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(req: AnalyzeRequest, db: Session = Depends(get_db)):
    orchestrator = AgentOrchestrator()
    try:
        result = await orchestrator.run(db, req.dataset, req.question)
    except ValueError as exc:
        message = str(exc)
        status = 404 if message.startswith("Dataset not found") or message.startswith("No DNA snapshots") else 400
        raise HTTPException(status_code=status, detail=message) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return AnalyzeResponse(
        dataset=result["dataset"],
        issues=result["issues"],
        analysis=result["analysis"],
        fixes=result["fixes"],
        narrative=result["narrative"],
        sections=result["sections"],
    )


@router.post("/simulate-fix")
async def simulate_fix(req: SimulateFixRequest, db: Session = Depends(get_db)):
    orchestrator = AgentOrchestrator()
    try:
        result = await orchestrator.run(db, req.dataset)
    except ValueError as exc:
        message = str(exc)
        status = 404 if message.startswith("Dataset not found") or message.startswith("No DNA snapshots") else 400
        raise HTTPException(status_code=status, detail=message) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    match = next((f for f in result["fixes"] if f["issue_type"] == req.issue_type), None)
    if not match:
        raise HTTPException(status_code=404, detail="Issue type not found for dataset")

    return {
        "dataset": req.dataset,
        "issue_type": req.issue_type,
        "simulation": {
            "status": "simulated",
            "actions": match["suggested_actions"],
            "rollback_steps": match["rollback_steps"],
            "message": "No production metadata changed. This is a dry-run recommendation.",
        },
    }


@router.post("/refresh-openmetadata")
async def refresh_openmetadata(db: Session = Depends(get_db)):
    service = MetadataIngestionService()
    try:
        stats = await service.sync(db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code if exc.response is not None else 502
        detail = f"OpenMetadata request failed ({status_code}). Check OPENMETADATA_TOKEN and OPENMETADATA_URL."
        raise HTTPException(status_code=status_code, detail=detail) from exc
    return {"status": "ok", "synced": stats}


@router.post("/demo/magic-run")
async def demo_magic_run(db: Session = Depends(get_db)):
    return run_magic_demo(db)
