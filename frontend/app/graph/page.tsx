import { GraphView } from "@/components/GraphView";
import { apiGet } from "@/lib/api";

export default async function GraphPage() {
  const graph = await apiGet<{
    nodes: any[];
    edges: any[];
    anomalies: any[];
    metrics: { risk_score: number; mutation_frequency_24h: number; blast_radius: number; severity_level: string };
  }>("/graph");
  const hasData = graph.nodes.length > 0;

  return (
    <div className="grid" style={{ gap: 16 }}>
      <div className="card">
        <h2 className="section-title">Data DNA Graph</h2>
        <p className="section-kicker">See the blast radius instantly. Hotter edges and nodes indicate mutation impact and incident pressure.</p>
      </div>

      <section className="grid-3">
        <article className="card">
          <h3>Blast Radius</h3>
          <p className="metric-value">{graph.metrics.blast_radius}</p>
        </article>
        <article className="card">
          <h3>Risk Score</h3>
          <p className="metric-value">{graph.metrics.risk_score.toFixed(0)}</p>
          <span className={`data-pill ${graph.metrics.severity_level === "critical" ? "bad" : graph.metrics.severity_level === "high" ? "warn" : "good"}`}>
            {graph.metrics.severity_level}
          </span>
        </article>
        <article className="card">
          <h3>Mutation / 24h</h3>
          <p className="metric-value">{graph.metrics.mutation_frequency_24h}</p>
        </article>
      </section>

      <section className="grid-3">
        <article className="card">
          <h3>Total Nodes</h3>
          <p className="metric-value">{graph.nodes.length}</p>
        </article>
        <article className="card">
          <h3>Total Edges</h3>
          <p className="metric-value">{graph.edges.length}</p>
        </article>
        <article className="card">
          <h3>Anomalies</h3>
          <p className="metric-value">{graph.anomalies.length}</p>
          <span className={`data-pill ${graph.anomalies.length > 0 ? "bad" : "good"}`}>
            {graph.anomalies.length > 0 ? "incident path detected" : "all clear"}
          </span>
        </article>
      </section>

      {hasData ? (
        <GraphView data={graph} />
      ) : (
        <div className="card">
          <p className="section-kicker">No graph data yet. Run metadata sync first.</p>
        </div>
      )}

      <div className="card">
        <h3>Incident Feed</h3>
        {graph.anomalies.length === 0 ? (
          <p className="muted">No incident edges detected</p>
        ) : (
          graph.anomalies.map((a, i) => (
            <div key={`${a.dataset}-${i}`} className="timeline-item" style={{ marginBottom: 10 }}>
              <p style={{ margin: 0 }}>
                <span className="data-pill bad">{a.type}</span>
              </p>
              <p className="mono" style={{ marginTop: 10 }}>
                {a.dataset} → {a.target}
              </p>
              <p className="muted" style={{ marginTop: 6 }}>
                {a.reason}
              </p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
