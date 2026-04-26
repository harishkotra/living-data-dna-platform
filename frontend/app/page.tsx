import { apiGet, apiGetOptional } from "@/lib/api";

type DNA = {
  dataset: string;
  owner: string;
  description: string;
  trust_score: number;
  risk_score: number;
  mutation_frequency_24h: number;
  blast_radius: number;
  severity_level: "low" | "medium" | "high" | "critical";
  mutation_type?: string;
  incident?: string;
  captured_at?: string;
};

export default async function DashboardPage() {
  const graph = await apiGet<{
    nodes: Array<{ id: string; trust_score: number; risk_score: number }>;
    anomalies: Array<{ type: string }>;
    metrics: { risk_score: number; mutation_frequency_24h: number; blast_radius: number; severity_level: string };
  }>("/graph");
  const selectedDataset = [...graph.nodes].sort((a, b) => b.risk_score - a.risk_score)[0]?.id;
  const dna = selectedDataset ? await apiGetOptional<DNA>(`/dna/${encodeURIComponent(selectedDataset)}`) : null;
  const timeline = selectedDataset
    ? await apiGetOptional<{ snapshots: Array<{ trust_score: number; captured_at: string }> }>(`/timeline/${encodeURIComponent(selectedDataset)}`)
    : null;

  if (!dna) {
    return (
      <section className="card">
        <h3 className="section-title">No Dataset Snapshots Yet</h3>
        <p className="section-kicker">
          Sync OpenMetadata via <code>POST /refresh-openmetadata</code> or set <code>DEMO_SEED_ENABLED=true</code> to preload demo data.
        </p>
      </section>
    );
  }

  const scoreTone = dna.trust_score > 80 ? "good" : dna.trust_score > 65 ? "warn" : "bad";
  const anomalyCount = graph.anomalies.length;
  const prevTrust = timeline?.snapshots?.at(-2)?.trust_score ?? dna.trust_score;
  const trustDelta = dna.trust_score - prevTrust;
  const trend = trustDelta === 0 ? "→" : trustDelta > 0 ? "↑" : "↓";

  return (
    <div className="grid" style={{ gap: 18 }}>
      <section className="kpi-strip">
        <article className="card kpi-mini">
          <h4>Risk Score</h4>
          <p>
            {dna.risk_score.toFixed(0)} <span>{dna.severity_level}</span>
          </p>
        </article>
        <article className="card kpi-mini">
          <h4>Mutation Frequency</h4>
          <p>
            {dna.mutation_frequency_24h} <span>24h</span>
          </p>
        </article>
        <article className="card kpi-mini">
          <h4>Blast Radius</h4>
          <p>
            {dna.blast_radius} <span>datasets</span>
          </p>
        </article>
        <article className="card kpi-mini">
          <h4>Trust Trend</h4>
          <p>
            {trend} {Math.abs(trustDelta).toFixed(0)} <span>vs prev</span>
          </p>
        </article>
      </section>

      <section className="card">
        <h2 className="section-title">Command Center</h2>
        <p className="section-kicker">Fastest narrative readout: what broke, how far it spread, and how risky the current state is.</p>
      </section>

      <section className="metrics">
        <article className="card">
          <h3>Dataset</h3>
          <p className="mono dataset-name" title={dna.dataset}>
            {dna.dataset}
          </p>
          <div className="kv-row">
            <span>Owner</span>
            <span>{dna.owner || "unknown"}</span>
          </div>
          <div className="kv-row">
            <span>Last Snapshot</span>
            <span>{dna.captured_at ? new Date(dna.captured_at).toLocaleString() : "N/A"}</span>
          </div>
        </article>

        <article className="card pulse">
          <h3>Trust Score</h3>
          <p className="metric-value">{dna.trust_score.toFixed(0)}</p>
          <span className={`data-pill ${scoreTone}`}>{scoreTone === "good" ? "high confidence" : scoreTone === "warn" ? "watchlist" : "high risk"}</span>
          <p className="muted" style={{ marginTop: 14 }}>
            Calculated from schema completeness, lineage health, metadata quality, and usage signal.
          </p>
        </article>

        <article className="card">
          <h3>Active Incidents</h3>
          <p className="metric-value">{anomalyCount}</p>
          <span className={`data-pill ${anomalyCount > 0 ? "bad" : "good"}`}>{anomalyCount > 0 ? "action needed" : "no active anomalies"}</span>
          <p className="muted" style={{ marginTop: 14 }}>
            {anomalyCount > 0 ? "Downstream reliability is degraded and needs immediate action." : "No downstream incident is currently flagged."}
          </p>
        </article>
      </section>

      <section className="card">
        <h3>Latest Mutation Story</h3>
        <div className="kv-row">
          <span>Mutation Type</span>
          <span>{dna.mutation_type || "none"}</span>
        </div>
        <div className="kv-row">
          <span>Dataset</span>
          <span className="mono">{dna.dataset}</span>
        </div>
        <div className="kv-row">
          <span>Incident</span>
          <span>{dna.incident || "No incident"}</span>
        </div>
        <div className="kv-row">
          <span>Risk / Severity</span>
          <span>
            {dna.risk_score.toFixed(0)} / {dna.severity_level}
          </span>
        </div>
      </section>
    </div>
  );
}
