"use client";

import { useEffect, useMemo, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
const MAGIC_STATE_KEY = "dnaMagicDemoState";
const MAGIC_PAYLOAD_KEY = "dnaMagicDemoPayload";

type MagicStep = "dashboard" | "graph" | "timeline" | "copilot";

type MagicState = {
  active: boolean;
  startedAt: string;
  currentStep: MagicStep;
  stepTimes: Partial<Record<MagicStep, string>>;
};

const STEPS: Array<{ key: MagicStep; label: string; path: string }> = [
  { key: "dashboard", label: "Dashboard", path: "/" },
  { key: "graph", label: "Graph", path: "/graph" },
  { key: "timeline", label: "Timeline", path: "/timeline" },
  { key: "copilot", label: "Copilot", path: "/copilot" },
];

function stepFromPath(pathname: string): MagicStep {
  if (pathname.startsWith("/graph")) return "graph";
  if (pathname.startsWith("/timeline")) return "timeline";
  if (pathname.startsWith("/copilot")) return "copilot";
  return "dashboard";
}

function nextStep(step: MagicStep): MagicStep | null {
  const idx = STEPS.findIndex((x) => x.key === step);
  if (idx < 0 || idx === STEPS.length - 1) return null;
  return STEPS[idx + 1].key;
}

export function MagicPath() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [loading, setLoading] = useState(false);
  const [state, setState] = useState<MagicState | null>(null);

  const isMagicMode = searchParams.get("magic") === "1";
  const routeStep = useMemo(() => stepFromPath(pathname), [pathname]);

  useEffect(() => {
    const raw = localStorage.getItem(MAGIC_STATE_KEY);
    if (!raw) return;
    try {
      const parsed = JSON.parse(raw) as MagicState;
      setState(parsed);
    } catch {
      localStorage.removeItem(MAGIC_STATE_KEY);
    }
  }, []);

  useEffect(() => {
    if (!state?.active || !isMagicMode) return;

    const merged = {
      ...state,
      currentStep: routeStep,
      stepTimes: {
        ...state.stepTimes,
        [routeStep]: state.stepTimes[routeStep] || new Date().toISOString(),
      },
    };
    setState(merged);
    localStorage.setItem(MAGIC_STATE_KEY, JSON.stringify(merged));

    const upcoming = nextStep(routeStep);
    if (!upcoming) return;

    const timer = setTimeout(() => {
      const path = STEPS.find((x) => x.key === upcoming)?.path || "/";
      router.push(`${path}?magic=1`);
    }, 9000);
    return () => clearTimeout(timer);
  }, [isMagicMode, routeStep, router, state]);

  async function runMagicDemo() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/demo/magic-run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (!res.ok) {
        throw new Error(`Magic demo failed (${res.status})`);
      }
      const payload = await res.json();
      localStorage.setItem(MAGIC_PAYLOAD_KEY, JSON.stringify(payload));
      const nextState: MagicState = {
        active: true,
        startedAt: new Date().toISOString(),
        currentStep: "dashboard",
        stepTimes: { dashboard: new Date().toISOString() },
      };
      localStorage.setItem(MAGIC_STATE_KEY, JSON.stringify(nextState));
      setState(nextState);
      router.push("/?magic=1");
      router.refresh();
    } catch (err) {
      // eslint-disable-next-line no-alert
      alert((err as Error).message);
    } finally {
      setLoading(false);
    }
  }

  function stopMagic() {
    localStorage.removeItem(MAGIC_STATE_KEY);
    setState({
      active: false,
      startedAt: new Date().toISOString(),
      currentStep: routeStep,
      stepTimes: {},
    });
    const path = STEPS.find((s) => s.key === routeStep)?.path || "/";
    router.push(path);
  }

  return (
    <div className="magic-wrap">
      <button className="button magic-button" onClick={runMagicDemo} disabled={loading}>
        {loading ? "Booting Incident Replay..." : "Run 1-Minute Magic Path"}
      </button>

      {state?.active ? (
        <section className="magic-rail card">
          <div className="magic-rail-head">
            <strong>Live Incident Replay</strong>
            <span className="mono">{new Date(state.startedAt).toLocaleTimeString()}</span>
          </div>
          <div className="magic-steps">
            {STEPS.map((step) => {
              const visited = Boolean(state.stepTimes[step.key]);
              const current = routeStep === step.key;
              return (
                <div key={step.key} className={`magic-step ${visited ? "visited" : ""} ${current ? "current" : ""}`}>
                  <span>{step.label}</span>
                  <small>{state.stepTimes[step.key] ? new Date(state.stepTimes[step.key] as string).toLocaleTimeString() : "--:--:--"}</small>
                </div>
              );
            })}
          </div>
          <div className="magic-actions">
            <button
              type="button"
              className="question-chip"
              onClick={() => {
                const upcoming = nextStep(routeStep);
                if (!upcoming) return;
                const path = STEPS.find((x) => x.key === upcoming)?.path || "/";
                router.push(`${path}?magic=1`);
              }}
            >
              Jump to Next Scene
            </button>
            <button type="button" className="question-chip" onClick={stopMagic}>
              Exit Replay
            </button>
          </div>
        </section>
      ) : null}
    </div>
  );
}
