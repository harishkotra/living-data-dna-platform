"use client";

import "reactflow/dist/style.css";
import ReactFlow, { Background, Controls, MarkerType } from "reactflow";

type Props = {
  data: {
    nodes: Array<{
      id: string;
      label: string;
      trust_score: number;
      mutation?: string | null;
      risk_score: number;
      blast_radius: number;
      severity_level: "low" | "medium" | "high" | "critical";
    }>;
    edges: Array<{ id: string; source: string; target: string; is_active: boolean; severity_level?: string }>;
  };
};

function trustTone(score: number): string {
  if (score > 80) return "#d4d4d4";
  if (score > 65) return "#a3a3a3";
  return "#737373";
}

function severityTone(level: string): string {
  if (level === "critical") return "#525252";
  if (level === "high") return "#737373";
  if (level === "medium") return "#a3a3a3";
  return "#d4d4d4";
}

function compactLabel(input: string): string {
  const parts = input.split(".");
  if (parts.length <= 3) {
    return input;
  }
  return `${parts[0]}…${parts[parts.length - 2]}.${parts[parts.length - 1]}`;
}

export function GraphView({ data }: Props) {
  const nodes = data.nodes.map((n, idx) => {
    const severity = severityTone(n.severity_level);
    const tone = trustTone(n.trust_score);
    return {
      id: n.id,
      position: { x: 280 * (idx % 3), y: 190 * Math.floor(idx / 3) },
      data: {
        label: `${compactLabel(n.label)}\nTrust ${n.trust_score.toFixed(0)} • Risk ${n.risk_score.toFixed(0)}\nBlast ${n.blast_radius}`,
      },
      style: {
        border: `1px solid ${severity}`,
        background: "#111111",
        color: "#f5f5f5",
        borderRadius: 12,
        padding: 12,
        width: 250,
        fontSize: 13,
        fontWeight: 600,
        whiteSpace: "pre-wrap",
        textAlign: "center" as const,
        boxShadow: `0 0 0 1px ${tone}22`,
      },
    };
  });

  const edges = data.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    animated: !e.is_active,
    markerEnd: { type: MarkerType.ArrowClosed },
    style: {
      stroke: e.is_active ? "#a3a3a3" : severityTone(e.severity_level || "critical"),
      strokeWidth: e.is_active ? 2.5 : 3.4,
    },
  }));

  return (
    <div className="card graph-shell">
      <ReactFlow
        fitView
        proOptions={{ hideAttribution: true }}
        nodes={nodes}
        edges={edges}
        defaultViewport={{ x: 0, y: 0, zoom: 0.9 }}
      >
        <Controls />
        <Background color="#2a2a2a" gap={30} size={1} />
      </ReactFlow>
    </div>
  );
}
