from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Dataset, DnaSnapshot, LineageEdge


SEVERITY_BANDS = (
    (24, "low"),
    (49, "medium"),
    (74, "high"),
    (100, "critical"),
)


def severity_from_score(risk_score: float) -> str:
    for cap, label in SEVERITY_BANDS:
        if risk_score <= cap:
            return label
    return "critical"


def compute_risk_score(schema_break: int, downstream_breaks: int, mutation_frequency_24h: int) -> float:
    return min(100.0, float(40 + 20 * schema_break + 15 * downstream_breaks + 5 * mutation_frequency_24h))


def _downstream_map(edges: list[LineageEdge]) -> dict[str, set[str]]:
    mapping: dict[str, set[str]] = {}
    for edge in edges:
        mapping.setdefault(edge.source, set()).add(edge.target)
    return mapping


def compute_blast_radius(edges: list[LineageEdge], root_dataset: str) -> int:
    mapping = _downstream_map(edges)
    visited: set[str] = set()
    stack = [root_dataset]
    while stack:
        source = stack.pop()
        for target in mapping.get(source, set()):
            if target in visited:
                continue
            visited.add(target)
            stack.append(target)
    return len(visited)


def mutation_frequency_24h(db: Session, dataset_id: int, now: datetime | None = None) -> int:
    current = now or datetime.utcnow()
    window_start = current - timedelta(hours=24)
    snaps = (
        db.query(DnaSnapshot)
        .filter(DnaSnapshot.dataset_id == dataset_id, DnaSnapshot.captured_at >= window_start, DnaSnapshot.mutation_type.is_not(None))
        .all()
    )
    return len(snaps)


def current_metrics(db: Session, dataset: Dataset, edges: list[LineageEdge], latest: DnaSnapshot | None = None) -> dict:
    latest_snap = latest or (
        db.query(DnaSnapshot)
        .filter(DnaSnapshot.dataset_id == dataset.id)
        .order_by(DnaSnapshot.captured_at.desc())
        .first()
    )
    if not latest_snap:
        return {
            "risk_score": 0.0,
            "mutation_frequency_24h": 0,
            "blast_radius": 0,
            "severity_level": "low",
        }

    freq = mutation_frequency_24h(db, dataset.id)
    schema_break = 1 if latest_snap.mutation_type == "schema_mutation" else 0
    downstream_breaks = len([e for e in edges if e.source == dataset.name and not e.is_active])
    blast_radius = compute_blast_radius(edges, dataset.name)
    risk_score = compute_risk_score(schema_break, downstream_breaks, freq)

    return {
        "risk_score": risk_score,
        "mutation_frequency_24h": freq,
        "blast_radius": blast_radius,
        "severity_level": severity_from_score(risk_score),
    }


def persist_metrics_in_genes(snapshot: DnaSnapshot, metrics: dict) -> None:
    genes = dict(snapshot.genes or {})
    genes["metrics"] = {
        "risk_score": metrics["risk_score"],
        "mutation_frequency_24h": metrics["mutation_frequency_24h"],
        "blast_radius": metrics["blast_radius"],
        "severity_level": metrics["severity_level"],
    }
    snapshot.genes = genes


def _ensure_dataset(db: Session, name: str, owner: str, description: str) -> Dataset:
    dataset = db.query(Dataset).filter(Dataset.name == name).first()
    if dataset:
        dataset.owner = owner
        dataset.description = description
        return dataset
    dataset = Dataset(name=name, owner=owner, description=description)
    db.add(dataset)
    db.flush()
    return dataset


def _upsert_lineage_edge(db: Session, source: str, target: str, is_active: bool, broken_reason: str | None = None) -> LineageEdge:
    edge = db.query(LineageEdge).filter(LineageEdge.source == source, LineageEdge.target == target).first()
    if edge:
        edge.is_active = is_active
        edge.broken_reason = broken_reason
        return edge
    edge = LineageEdge(source=source, target=target, is_active=is_active, broken_reason=broken_reason)
    db.add(edge)
    return edge


def _snapshot(
    dataset_id: int,
    captured_at: datetime,
    trust_score: float,
    schema_gene: list[dict],
    lineage_gene: list[dict],
    usage_gene: dict,
    owner: str,
    description: str,
    mutation_type: str | None = None,
    incident: str | None = None,
) -> DnaSnapshot:
    return DnaSnapshot(
        dataset_id=dataset_id,
        captured_at=captured_at,
        trust_score=trust_score,
        mutation_type=mutation_type,
        incident=incident,
        genes={
            "schema_gene": schema_gene,
            "lineage_gene": lineage_gene,
            "usage_gene": usage_gene,
            "ownership_gene": {"owner": owner, "description": description},
            "computed_at": captured_at.isoformat(),
        },
    )


def run_magic_demo(db: Session) -> dict:
    now = datetime.utcnow()
    baseline_time = now - timedelta(minutes=1)
    event_time = now

    orders = _ensure_dataset(db, "sales.orders", "revenue-platform", "Canonical order records from checkout pipeline")
    daily_revenue = _ensure_dataset(
        db,
        "analytics.daily_revenue",
        "finance-analytics",
        "Daily aggregate revenue model for financial reporting",
    )
    kpi_board = _ensure_dataset(
        db,
        "exec.kpi_board",
        "executive-analytics",
        "Executive KPI board dataset consumed by leadership dashboards",
    )

    db.query(DnaSnapshot).filter(DnaSnapshot.dataset_id.in_([orders.id, daily_revenue.id, kpi_board.id])).delete(
        synchronize_session=False
    )
    db.query(LineageEdge).filter(
        (LineageEdge.source.in_([orders.name, daily_revenue.name])) | (LineageEdge.target.in_([daily_revenue.name, kpi_board.name]))
    ).delete(synchronize_session=False)
    db.flush()

    _upsert_lineage_edge(db, orders.name, daily_revenue.name, True, None)
    _upsert_lineage_edge(db, daily_revenue.name, kpi_board.name, True, None)
    db.flush()

    orders_base_schema = [
        {"name": "order_id", "type": "string", "nullable": False},
        {"name": "customer_id", "type": "string", "nullable": False},
        {"name": "status", "type": "string", "nullable": False},
        {"name": "order_total", "type": "double", "nullable": False},
        {"name": "created_at", "type": "timestamp", "nullable": False},
    ]
    orders_mutated_schema = [
        {"name": "order_id", "type": "string", "nullable": False},
        {"name": "customer_id", "type": "string", "nullable": False},
        {"name": "order_state", "type": "string", "nullable": False},
        {"name": "order_total", "type": "double", "nullable": False},
        {"name": "created_at", "type": "timestamp", "nullable": False},
    ]

    revenue_schema = [
        {"name": "order_date", "type": "date", "nullable": False},
        {"name": "status", "type": "string", "nullable": False},
        {"name": "gross_revenue", "type": "double", "nullable": False},
    ]
    kpi_schema = [
        {"name": "metric_date", "type": "date", "nullable": False},
        {"name": "daily_revenue", "type": "double", "nullable": False},
        {"name": "run_health", "type": "string", "nullable": False},
    ]

    snapshots = [
        _snapshot(
            dataset_id=orders.id,
            captured_at=baseline_time,
            trust_score=91.0,
            schema_gene=orders_base_schema,
            lineage_gene=[{"source": orders.name, "target": daily_revenue.name, "is_active": True}],
            usage_gene={"weekly_queries": 2200, "consumers": 19, "last_accessed": baseline_time.isoformat()},
            owner=orders.owner,
            description=orders.description,
        ),
        _snapshot(
            dataset_id=orders.id,
            captured_at=event_time,
            trust_score=62.0,
            schema_gene=orders_mutated_schema,
            lineage_gene=[{"source": orders.name, "target": daily_revenue.name, "is_active": False}],
            usage_gene={"weekly_queries": 2050, "consumers": 19, "last_accessed": event_time.isoformat()},
            owner=orders.owner,
            description=orders.description,
            mutation_type="schema_mutation",
            incident="Column status renamed to order_state; downstream model expects status.",
        ),
        _snapshot(
            dataset_id=daily_revenue.id,
            captured_at=event_time,
            trust_score=54.0,
            schema_gene=revenue_schema,
            lineage_gene=[{"source": daily_revenue.name, "target": kpi_board.name, "is_active": False}],
            usage_gene={"weekly_queries": 1300, "consumers": 11, "last_accessed": event_time.isoformat()},
            owner=daily_revenue.owner,
            description=daily_revenue.description,
            mutation_type="downstream_break",
            incident="Model failed: missing required upstream column status from sales.orders.",
        ),
        _snapshot(
            dataset_id=kpi_board.id,
            captured_at=event_time,
            trust_score=47.0,
            schema_gene=kpi_schema,
            lineage_gene=[],
            usage_gene={"weekly_queries": 680, "consumers": 7, "last_accessed": event_time.isoformat()},
            owner=kpi_board.owner,
            description=kpi_board.description,
            mutation_type="propagated_risk",
            incident="Executive KPI board shows stale revenue due to failed upstream refresh.",
        ),
    ]
    db.add_all(snapshots)
    _upsert_lineage_edge(
        db,
        orders.name,
        daily_revenue.name,
        False,
        "Schema drift: status column renamed to order_state in upstream dataset",
    )
    _upsert_lineage_edge(
        db,
        daily_revenue.name,
        kpi_board.name,
        False,
        "Refresh dependency blocked by failed analytics.daily_revenue model",
    )
    db.flush()

    edges = db.query(LineageEdge).all()
    latest_by_dataset: dict[str, DnaSnapshot] = {}
    for ds in [orders, daily_revenue, kpi_board]:
        latest_by_dataset[ds.name] = (
            db.query(DnaSnapshot).filter(DnaSnapshot.dataset_id == ds.id).order_by(DnaSnapshot.captured_at.desc()).first()
        )

    metrics_by_dataset = {}
    for ds in [orders, daily_revenue, kpi_board]:
        latest = latest_by_dataset[ds.name]
        metrics = current_metrics(db, ds, edges, latest=latest)
        persist_metrics_in_genes(latest, metrics)
        metrics_by_dataset[ds.name] = metrics

    db.commit()

    incident = {
        "dataset": orders.name,
        "type": "schema_mutation",
        "started_at": event_time.isoformat(),
        "downstream_failed": daily_revenue.name,
        "propagated_to": kpi_board.name,
        "status": "active",
    }
    timeline_events = [
        {
            "at": baseline_time.isoformat(),
            "dataset": orders.name,
            "event_type": "baseline_snapshot",
            "message": "Baseline schema includes status column.",
        },
        {
            "at": event_time.isoformat(),
            "dataset": orders.name,
            "event_type": "schema_mutation",
            "message": "status renamed to order_state",
        },
        {
            "at": event_time.isoformat(),
            "dataset": daily_revenue.name,
            "event_type": "downstream_break",
            "message": "daily_revenue failed due to missing status column",
        },
        {
            "at": event_time.isoformat(),
            "dataset": kpi_board.name,
            "event_type": "propagated_risk",
            "message": "KPI board stale after upstream break",
        },
    ]

    root_metrics = metrics_by_dataset[orders.name]
    boardroom_brief = {
        "Executive Summary": "A schema mutation in sales.orders broke a critical downstream model and degraded executive KPI freshness.",
        "Root Cause": "The upstream field status was renamed to order_state without synchronized downstream contract updates.",
        "Business Impact": (
            f"Blast radius is {root_metrics['blast_radius']} datasets. Risk score is {root_metrics['risk_score']:.0f} "
            f"({root_metrics['severity_level']}). Executive revenue KPIs may be stale."
        ),
        "Recommended Fix (Now/Next)": (
            "Now: restore compatibility by reintroducing status alias or update downstream model mapping. "
            "Next: add schema contract checks and pre-deploy lineage validation."
        ),
        "Confidence + Evidence": (
            "High confidence based on temporal mutation event, broken lineage edges, and incident snapshots across dependent datasets."
        ),
    }

    return {
        "datasets": [orders.name, daily_revenue.name, kpi_board.name],
        "lineage": [
            {"source": orders.name, "target": daily_revenue.name, "is_active": False},
            {"source": daily_revenue.name, "target": kpi_board.name, "is_active": False},
        ],
        "incident": incident,
        "metrics": root_metrics,
        "boardroom_brief": boardroom_brief,
        "timeline_events": timeline_events,
    }
