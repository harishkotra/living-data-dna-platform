from datetime import datetime

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    dataset: str = "sales.orders"
    question: str | None = None


class SimulateFixRequest(BaseModel):
    dataset: str = "sales.orders"
    issue_type: str


class IssueOut(BaseModel):
    issue_type: str
    severity: str
    details: dict


class AnalyzeResponse(BaseModel):
    dataset: str
    issues: list[IssueOut]
    analysis: list[dict]
    fixes: list[dict]
    narrative: str
    sections: dict[str, str]


class SnapshotOut(BaseModel):
    captured_at: datetime
    trust_score: float
    mutation_type: str | None = None
    incident: str | None = None
    genes: dict
    risk_score: float | None = None
    mutation_frequency_24h: int | None = None
    blast_radius: int | None = None
    severity_level: str | None = None


class TimelineResponse(BaseModel):
    dataset: str
    snapshots: list[SnapshotOut]
    schema_diff: dict = Field(default_factory=dict)
    lineage_diff: dict = Field(default_factory=dict)
    timeline_events: list[dict] = Field(default_factory=list)
    metrics: dict = Field(default_factory=dict)


class GraphResponse(BaseModel):
    nodes: list[dict]
    edges: list[dict]
    anomalies: list[dict]
    metrics: dict = Field(default_factory=dict)
