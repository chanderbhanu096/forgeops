"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  createMission,
  listMissions,
  listModelProviders,
} from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import type { Mission, ModelProvider } from "@/types";

export default function HomePage() {
  const [missions, setMissions] = useState<Mission[]>([]);
  const [providers, setProviders] = useState<ModelProvider[]>([]);
  const [loading, setLoading] = useState(true);
  const [modelsLoading, setModelsLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [llmProvider, setLlmProvider] = useState("demo");
  const [llmModel, setLlmModel] = useState("forgeops-demo");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listMissions()
      .then(setMissions)
      .catch(() => setError("Failed to load missions"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    listModelProviders()
      .then((catalog) => {
        setProviders(catalog.providers);
        const preferred =
          catalog.providers.find(
            (provider) =>
              provider.id === catalog.default_provider && provider.configured
          ) ?? catalog.providers.find((provider) => provider.configured);

        if (preferred) {
          setLlmProvider(preferred.id);
          setLlmModel(
            catalog.default_provider === preferred.id && catalog.default_model
              ? catalog.default_model
              : preferred.default_model || preferred.models[0] || ""
          );
        }
      })
      .catch(() => {
        setProviders([
          {
            id: "demo",
            label: "Demo simulator",
            configured: true,
            models: ["forgeops-demo"],
            default_model: "forgeops-demo",
            supports_custom_model: false,
            configuration_hint: "No API key required.",
          },
        ]);
      })
      .finally(() => setModelsLoading(false));
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

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const mission = await createMission({
        title,
        description,
        llm_provider: llmProvider,
        llm_model: llmModel,
      });
      setMissions((previous) => [mission, ...previous]);
      setTitle("");
      setDescription("");
      setShowForm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create mission");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <div
        className="page-header"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
        }}
      >
        <div>
          <h1>Missions</h1>
          <p>Active and historical autonomous agent missions.</p>
        </div>
        <button
          className="btn btn-primary"
          onClick={() => setShowForm(!showForm)}
        >
          {showForm ? "Cancel" : "+ New mission"}
        </button>
      </div>

      {showForm && (
        <div className="card" style={{ marginBottom: 28 }}>
          <div className="card-title">Define mission</div>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="title">Mission title</label>
              <input
                id="title"
                type="text"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="e.g. Investigate revenue pipeline failure"
                required
                minLength={5}
              />
            </div>

            <div className="form-group">
              <label htmlFor="description">Mission description</label>
              <textarea
                id="description"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Describe what the agent should investigate and resolve…"
                required
                minLength={10}
              />
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "minmax(180px, 0.8fr) minmax(240px, 1.2fr)",
                gap: 14,
              }}
            >
              <div className="form-group">
                <label htmlFor="llm-provider">AI provider</label>
                <select
                  id="llm-provider"
                  value={llmProvider}
                  onChange={(event) => handleProviderChange(event.target.value)}
                  disabled={modelsLoading}
                  required
                >
                  {providers.map((provider) => (
                    <option
                      key={provider.id}
                      value={provider.id}
                      disabled={!provider.configured}
                    >
                      {provider.label}
                      {provider.configured ? "" : " — not configured"}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="llm-model">Model ID</label>
                <input
                  id="llm-model"
                  type="text"
                  list="llm-model-options"
                  value={llmModel}
                  onChange={(event) => setLlmModel(event.target.value)}
                  placeholder="Enter the exact provider model ID"
                  readOnly={selectedProvider?.supports_custom_model === false}
                  required
                />
                <datalist id="llm-model-options">
                  {(selectedProvider?.models ?? []).map((model) => (
                    <option key={model} value={model} />
                  ))}
                </datalist>
              </div>
            </div>

            {selectedProvider && (
              <p className="muted" style={{ fontSize: 12, marginTop: -4 }}>
                {selectedProvider.configuration_hint}
                {selectedProvider.supports_custom_model
                  ? " You can choose a suggestion or type any valid model ID."
                  : ""}
              </p>
            )}

            {error && (
              <p style={{ color: "var(--red)", marginBottom: 12 }}>{error}</p>
            )}

            <button
              className="btn btn-primary"
              type="submit"
              disabled={submitting || modelsLoading || !llmModel.trim()}
            >
              {submitting ? "Launching…" : "Launch mission"}
            </button>
          </form>
        </div>
      )}

      {loading ? (
        <p className="muted">Loading missions…</p>
      ) : missions.length === 0 ? (
        <div className="empty-state">
          <p>No missions yet.</p>
          <p style={{ fontSize: 12, marginTop: 6 }}>
            Create a mission to start the autonomous agent.
          </p>
        </div>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Mission</th>
              <th>Model</th>
              <th>Status</th>
              <th>Steps</th>
              <th>Cost</th>
              <th>Created</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {missions.map((mission) => (
              <tr key={mission.id}>
                <td>
                  <span style={{ fontWeight: 600 }}>{mission.title}</span>
                </td>
                <td className="mono muted" style={{ fontSize: 11 }}>
                  {mission.llm_provider} / {mission.llm_model}
                </td>
                <td>
                  <StatusBadge status={mission.status} />
                </td>
                <td className="mono muted">{mission.steps_used}</td>
                <td className="mono muted">
                  €{mission.cost_usd_used.toFixed(3)}
                </td>
                <td className="muted">
                  {new Date(mission.created_at).toLocaleString()}
                </td>
                <td>
                  <Link href={`/missions/${mission.id}`} className="btn">
                    View →
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </>
  );
}
