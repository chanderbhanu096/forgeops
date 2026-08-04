"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createMission, listMissions, listModelProviders } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import type { Mission, ModelProvider } from "@/types";

const DEMO_TITLE = "Analyze a simulated API deployment failure";
const DEMO_DESCRIPTION = `Treat this as a simulated, non-destructive incident. Do not access production systems or make external changes.

Known facts:
- The frontend and API health endpoint are reachable.
- A mission can still fail after the health check passes.
- The application uses FastAPI, Next.js, PostgreSQL, GitHub Actions and Azure Container Apps.

Produce a visible investigation report containing the environment, investigation plan, evidence, three hypotheses, the most likely root cause, a safe remediation, regression tests, risks and a confidence score. Stop before any destructive action.`;

export default function HomePage() {
  const router = useRouter();
  const [missions, setMissions] = useState<Mission[]>([]);
  const [providers, setProviders] = useState<ModelProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [llmProvider, setLlmProvider] = useState("demo");
  const [llmModel, setLlmModel] = useState("forgeops-demo");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    Promise.allSettled([listMissions(), listModelProviders()]).then(([missionResult, modelResult]) => {
      if (!active) return;
      if (missionResult.status === "fulfilled") setMissions(missionResult.value);
      else setError("The mission list could not be loaded. The service may be waking up; try again in a moment.");

      if (modelResult.status === "fulfilled") {
        const catalog = modelResult.value;
        setProviders(catalog.providers);
        const preferred = catalog.providers.find((p) => p.id === catalog.default_provider && p.configured)
          ?? catalog.providers.find((p) => p.configured);
        if (preferred) {
          setLlmProvider(preferred.id);
          setLlmModel(catalog.default_provider === preferred.id && catalog.default_model
            ? catalog.default_model
            : preferred.default_model || preferred.models[0] || "");
        }
      } else {
        setProviders([{ id: "demo", label: "Demo simulator", configured: true, models: ["forgeops-demo"], default_model: "forgeops-demo", supports_custom_model: false, configuration_hint: "No API key required." }]);
      }
      setLoading(false);
    });
    return () => { active = false; };
  }, []);

  const selectedProvider = useMemo(
    () => providers.find((provider) => provider.id === llmProvider),
    [providers, llmProvider]
  );

  function handleProviderChange(providerId: string) {
    const provider = providers.find((entry) => entry.id === providerId);
    setLlmProvider(providerId);
    setLlmModel(provider?.default_model || provider?.models[0] || "");
  }

  function useDemoTemplate() {
    setTitle(DEMO_TITLE);
    setDescription(DEMO_DESCRIPTION);
    if (providers.some((provider) => provider.id === "demo")) {
      setLlmProvider("demo");
      setLlmModel("forgeops-demo");
    }
    setShowForm(true);
    requestAnimationFrame(() => document.getElementById("title")?.focus());
  }

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const mission = await createMission({ title, description, llm_provider: llmProvider, llm_model: llmModel });
      router.push(`/missions/${mission.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create mission");
      setSubmitting(false);
    }
  }

  return (
    <>
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", gap: 20, alignItems: "flex-start" }}>
        <div>
          <h1>Missions</h1>
          <p>Give ForgeOps an engineering problem, watch the investigation and review the evidence before execution.</p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 14 }}>
            <button className="btn btn-primary" onClick={useDemoTemplate}>▶ Run the guided demo</button>
            <button className="btn" onClick={() => setShowForm(!showForm)}>{showForm ? "Close form" : "+ Create your own mission"}</button>
          </div>
        </div>
        <div className="card" style={{ maxWidth: 300, margin: 0 }}>
          <div className="card-title">First time here?</div>
          <p className="muted" style={{ fontSize: 13, marginBottom: 10 }}>The guided demo needs no API key and opens the result page automatically.</p>
          <a href="https://github.com/chanderbhanu096/forgeops#60-second-start" target="_blank" rel="noreferrer" className="btn">Setup guide ↗</a>
        </div>
      </div>

      {showForm && (
        <div className="card" style={{ marginBottom: 28 }}>
          <div className="card-title">1. Describe the mission</div>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="title">Mission title</label>
              <input id="title" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="e.g. Investigate revenue pipeline failure" required minLength={5} />
            </div>
            <div className="form-group">
              <label htmlFor="description">What should ForgeOps investigate?</label>
              <textarea id="description" value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Include symptoms, known facts, constraints and the output you expect." required minLength={10} style={{ minHeight: 190 }} />
            </div>

            <div className="card-title" style={{ marginTop: 20 }}>2. Choose the AI</div>
            <div style={{ display: "grid", gridTemplateColumns: "minmax(180px, .8fr) minmax(240px, 1.2fr)", gap: 14 }}>
              <div className="form-group">
                <label htmlFor="llm-provider">AI provider</label>
                <select id="llm-provider" value={llmProvider} onChange={(event) => handleProviderChange(event.target.value)} required>
                  {providers.map((provider) => (
                    <option key={provider.id} value={provider.id} disabled={!provider.configured}>
                      {provider.configured ? "✓ " : "○ "}{provider.label}{provider.configured ? "" : " — add API key first"}
                    </option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label htmlFor="llm-model">Model</label>
                <input id="llm-model" list="llm-model-options" value={llmModel} onChange={(event) => setLlmModel(event.target.value)} readOnly={selectedProvider?.supports_custom_model === false} required />
                <datalist id="llm-model-options">{(selectedProvider?.models ?? []).map((model) => <option key={model} value={model} />)}</datalist>
              </div>
            </div>

            {selectedProvider && <p className="muted" style={{ fontSize: 12 }}>{selectedProvider.configuration_hint}</p>}
            {error && <div className="card" style={{ borderColor: "var(--red)", color: "var(--red)", padding: 12 }}>{error}</div>}
            <button className="btn btn-primary" type="submit" disabled={submitting || !llmModel.trim()}>
              {submitting ? "Starting mission…" : "3. Launch and view progress →"}
            </button>
          </form>
        </div>
      )}

      {loading ? (
        <div className="card"><p className="muted">Connecting to ForgeOps… Azure may need a few seconds to wake up.</p></div>
      ) : missions.length === 0 ? (
        <div className="empty-state"><p>No missions yet.</p><button className="btn btn-primary" onClick={useDemoTemplate}>Run the guided demo</button></div>
      ) : (
        <table>
          <thead><tr><th>Mission</th><th>Model</th><th>Status</th><th>Steps</th><th>Cost</th><th>Created</th><th></th></tr></thead>
          <tbody>{missions.map((mission) => (
            <tr key={mission.id}>
              <td><span style={{ fontWeight: 600 }}>{mission.title}</span></td>
              <td className="mono muted" style={{ fontSize: 11 }}>{mission.llm_provider} / {mission.llm_model}</td>
              <td><StatusBadge status={mission.status} /></td>
              <td className="mono muted">{mission.steps_used}</td>
              <td className="mono muted">€{mission.cost_usd_used.toFixed(3)}</td>
              <td className="muted">{new Date(mission.created_at).toLocaleString()}</td>
              <td><Link href={`/missions/${mission.id}`} className="btn">View result →</Link></td>
            </tr>
          ))}</tbody>
        </table>
      )}
    </>
  );
}
