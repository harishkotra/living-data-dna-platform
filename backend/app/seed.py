from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Dataset, DnaSnapshot, LineageEdge


def seed_demo_data(db: Session) -> None:
    if db.query(Dataset).count() > 0:
        return

    sales_orders = Dataset(name="sales.orders", owner="data-platform", description="Order facts from checkout events")
    sales_items = Dataset(name="sales.order_items", owner="analytics", description="Line item details")
    rev_dash = Dataset(name="finance.revenue_dashboard", owner="finance-bi", description="Revenue reporting mart")
    db.add_all([sales_orders, sales_items, rev_dash])
    db.flush()

    t0 = datetime.utcnow() - timedelta(hours=4)
    t1 = datetime.utcnow() - timedelta(hours=1)

    baseline_genes = {
        "schema_gene": [
            {"name": "order_id", "type": "string", "nullable": False},
            {"name": "status", "type": "string", "nullable": False},
            {"name": "total_amount", "type": "double", "nullable": False},
            {"name": "created_at", "type": "timestamp", "nullable": False},
        ],
        "lineage_gene": [
            {"source": "sales.orders", "target": "finance.revenue_dashboard", "is_active": True},
        ],
        "usage_gene": {"weekly_queries": 1200, "consumers": 14, "last_accessed": t0.isoformat()},
        "ownership_gene": {"owner": "data-platform", "description": "Order facts from checkout events"},
        "computed_at": t0.isoformat(),
    }

    mutated_genes = {
        "schema_gene": [
            {"name": "order_id", "type": "string", "nullable": False},
            {"name": "order_status", "type": "string", "nullable": False},
            {"name": "total_amount", "type": "double", "nullable": False},
            {"name": "created_at", "type": "timestamp", "nullable": False},
        ],
        "lineage_gene": [
            {"source": "sales.orders", "target": "finance.revenue_dashboard", "is_active": False},
        ],
        "usage_gene": {"weekly_queries": 980, "consumers": 14, "last_accessed": t1.isoformat()},
        "ownership_gene": {"owner": "data-platform", "description": "Order facts from checkout events"},
        "computed_at": t1.isoformat(),
    }

    db.add_all(
        [
            DnaSnapshot(dataset_id=sales_orders.id, captured_at=t0, trust_score=89.4, genes=baseline_genes, mutation_type=None, incident=None),
            DnaSnapshot(
                dataset_id=sales_orders.id,
                captured_at=t1,
                trust_score=63.1,
                genes=mutated_genes,
                mutation_type="schema_change",
                incident="Downstream finance.revenue_dashboard failed due to missing status column",
            ),
            DnaSnapshot(
                dataset_id=sales_items.id,
                captured_at=t1,
                trust_score=92.0,
                genes={
                    "schema_gene": [
                        {"name": "order_id", "type": "string", "nullable": False},
                        {"name": "sku", "type": "string", "nullable": False},
                        {"name": "quantity", "type": "int", "nullable": False},
                    ],
                    "lineage_gene": [
                        {"source": "sales.order_items", "target": "finance.revenue_dashboard", "is_active": True},
                    ],
                    "usage_gene": {"weekly_queries": 840, "consumers": 8, "last_accessed": t1.isoformat()},
                    "ownership_gene": {"owner": "analytics", "description": "Line item details"},
                    "computed_at": t1.isoformat(),
                },
                mutation_type=None,
                incident=None,
            ),
            DnaSnapshot(
                dataset_id=rev_dash.id,
                captured_at=t1,
                trust_score=71.2,
                genes={
                    "schema_gene": [
                        {"name": "order_id", "type": "string", "nullable": False},
                        {"name": "status", "type": "string", "nullable": True},
                        {"name": "revenue", "type": "double", "nullable": True},
                    ],
                    "lineage_gene": [],
                    "usage_gene": {"weekly_queries": 430, "consumers": 5, "last_accessed": t1.isoformat()},
                    "ownership_gene": {"owner": "finance-bi", "description": "Revenue reporting mart"},
                    "computed_at": t1.isoformat(),
                },
                mutation_type="incident",
                incident="Stale values due to upstream schema mismatch",
            ),
        ]
    )

    db.add_all(
        [
            LineageEdge(source="sales.orders", target="finance.revenue_dashboard", is_active=False, broken_reason="Column status renamed to order_status"),
            LineageEdge(source="sales.order_items", target="finance.revenue_dashboard", is_active=True, broken_reason=None),
        ]
    )

    db.commit()
