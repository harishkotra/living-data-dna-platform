import { apiGetOptional } from "@/lib/api";

export default async function TimelinePage() {
  const graph = await apiGetOptional<{ nodes: Array<{ id: string; risk_score?: number }> }>("/graph");
  const selectedDataset = graph?.nodes?.slice().sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0))[0]?.id;
  const timeline = selectedDataset
      ? await apiGetOptional<{
        dataset: string;
        snapshots: Array<{
          captured_at: string;
          trust_score: number;
          mutation_type?: string | null;
          incident?: string | null;
          risk_score?: number;
          mutation_frequency_24h?: number;
          blast_radius?: number;
          severity_level?: string;
        }>;
        schema_diff: { added?: Array<{ name: string; type: string }>; removed?: Array<{ name: string; type: string }> };
        metrics: { risk_score: number; mutation_frequency_24h: number; blast_radius: number; severity_level: string };
        timeline_events: Array<{ captured_at?: string; at?: string; dataset: string; event_type: string; message: string }>;
      }>(`/timeline/${encodeURIComponent(selectedDataset)}`)
    : null;

  if (!timeline) {
    return (
      <div className="card">
        <h3 className="section-title">Timeline Unavailable</h3>
        <p className="section-kicker">No timeline records yet. Sync from OpenMetadata or enable demo seed mode.</p>
      </div>
    );
  }

  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="card">
        <h2 className="section-title">Time Machine</h2>
        <p className="mono" style={{ fontSize: 34, margin: "8px 0 0" }}>
          {timeline.dataset}
        </p>
        <p className="section-kicker">Replay the exact failure timeline from mutation trigger to downstream business impact.</p>
        <div className="question-chips">
          <span className={`data-pill ${timeline.metrics.severity_level === "critical" ? "bad" : timeline.metrics.severity_level === "high" ? "warn" : "good"}`}>
            Severity {timeline.metrics.severity_level}
          </span>
          <span className="data-pill warn">Risk {timeline.metrics.risk_score.toFixed(0)}</span>
          <span className="data-pill good">Blast {timeline.metrics.blast_radius}</span>
        </div>
      </div>

      <div className="card timeline">
        {timeline.snapshots.map((s, i) => (
          <div key={s.captured_at + i} className="timeline-item">
            <p style={{ margin: 0, fontWeight: 800, fontSize: 24 }}>{new Date(s.captured_at).toLocaleString()}</p>
            <p style={{ margin: "4px 0 9px" }}>Trust score: {s.trust_score}</p>
            {s.mutation_type ? <span className="data-pill bad">{s.mutation_type}</span> : <span className="data-pill good">stable</span>}
            {s.incident ? <p style={{ color: "var(--warn)", marginTop: 10 }}>{s.incident}</p> : null}
          </div>
        ))}
      </div>

      <div className="grid-3">
        <article className="card">
          <h3>Added Columns</h3>
          <p className="muted">{timeline.schema_diff.added?.map((x) => `${x.name}:${x.type}`).join(", ") || "None"}</p>
        </article>
        <article className="card">
          <h3>Removed Columns</h3>
          <p className="muted">{timeline.schema_diff.removed?.map((x) => `${x.name}:${x.type}`).join(", ") || "None"}</p>
        </article>
        <article className="card">
          <h3>Snapshot Count</h3>
          <p className="metric-value">{timeline.snapshots.length}</p>
        </article>
      </div>

      <div className="card">
        <h3>Failure Sequence</h3>
        <div className="timeline">
          {timeline.timeline_events.map((e, i) => (
            <div key={`${e.dataset}-${i}`} className="timeline-item">
              <p style={{ margin: 0, fontWeight: 700 }}>
                {new Date(e.at || e.captured_at || Date.now()).toLocaleString()} · {e.dataset}
              </p>
              <p style={{ marginTop: 6 }}>
                <span className={`data-pill ${e.event_type.includes("break") || e.event_type.includes("mutation") ? "bad" : "good"}`}>
                  {e.event_type}
                </span>
              </p>
              <p className="muted">{e.message}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
