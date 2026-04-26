"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const MAGIC_PAYLOAD_KEY = "dnaMagicDemoPayload";
const QUICK_QUESTIONS = [
  "Can I trust this dataset today?",
  "What changed recently and why?",
  "What is the blast radius if this fails?",
  "What is the safest rollback strategy?",
];

export function CopilotClient() {
  const [question, setQuestion] = useState("Why did this dataset break?");
  const [dataset, setDataset] = useState("sales.orders");
  const [answer, setAnswer] = useState<string>("");
  const [sections, setSections] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const loadDataset = async () => {
      try {
        const res = await fetch(`${API_BASE}/graph`);
        const data = await res.json();
        const firstDataset = data?.nodes?.[0]?.id;
        if (firstDataset) {
          setDataset(firstDataset);
        }
      } catch {
        // Keep default dataset value if graph fetch fails.
      }
    };
    loadDataset();

    try {
      const raw = localStorage.getItem(MAGIC_PAYLOAD_KEY);
      if (raw) {
        const payload = JSON.parse(raw) as { boardroom_brief?: Record<string, string>; incident?: { dataset?: string } };
        if (payload.boardroom_brief) {
          setSections(payload.boardroom_brief);
          setAnswer(Object.entries(payload.boardroom_brief).map(([k, v]) => `${k}: ${v}`).join("\n\n"));
        }
        if (payload.incident?.dataset) {
          setDataset(payload.incident.dataset);
        }
      }
    } catch {
      // No magic payload available.
    }
  }, []);

  const title = useMemo(() => {
    const short = dataset.split(".");
    return short.length > 2 ? `${short[short.length - 2]}.${short[short.length - 1]}` : dataset;
  }, [dataset]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setAnswer("");
    setSections({});
    try {
      const res = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dataset, question }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data?.detail || `Request failed (${res.status})`);
      }
      setSections(data.sections || {});
      setAnswer(data.narrative || "No narrative returned");
    } catch (err) {
      setAnswer(`Failed to call copilot: ${(err as Error).message}`);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="grid" style={{ gap: 16 }}>
      <section className="card">
        <h2 className="section-title">Copilot Console</h2>
        <p className="section-kicker">Generate a boardroom-ready incident brief with root cause, impact summary, and fix path.</p>
      </section>

      <section className="card">
        <h3>Live Assistant</h3>
        <div className="kv-row">
          <span>Dataset Scope</span>
          <span className="mono">{dataset}</span>
        </div>
        <div className="kv-row">
          <span>Display Name</span>
          <span>{title}</span>
        </div>

        <p className="muted" style={{ marginTop: 14 }}>
          Quick prompts:
        </p>
        <div className="question-chips" style={{ marginBottom: 14 }}>
          {QUICK_QUESTIONS.map((item) => (
            <button key={item} type="button" className="question-chip" onClick={() => setQuestion(item)}>
              {item}
            </button>
          ))}
        </div>

        <form onSubmit={onSubmit} className="grid" style={{ gap: 10 }}>
          <textarea className="textarea" rows={4} value={question} onChange={(e) => setQuestion(e.target.value)} />
          <button className="button" type="submit" disabled={loading}>
            {loading ? "Building Executive Brief..." : "Generate Executive Brief"}
          </button>
        </form>
      </section>

      <section className="card">
        <h3>Boardroom Brief</h3>
        {!answer ? <p className="muted">No response yet. Run the pipeline to generate findings.</p> : null}
        {Object.keys(sections).length > 0 ? (
          <div className="grid boardroom-grid">
            {Object.entries(sections).map(([title, text]) => (
              <article key={title} className="timeline-item">
                <p style={{ margin: 0, fontWeight: 800 }}>{title}</p>
                <p className="muted">{text}</p>
              </article>
            ))}
          </div>
        ) : null}
        {answer && Object.keys(sections).length === 0 ? (
          <pre
            style={{
              marginTop: 8,
              whiteSpace: "pre-wrap",
              background: "rgba(8, 15, 39, .82)",
              border: "1px solid var(--line)",
              borderRadius: 14,
              padding: 14,
              fontSize: 15,
              lineHeight: 1.45,
            }}
          >
            {answer}
          </pre>
        ) : null}
      </section>
    </div>
  );
}
