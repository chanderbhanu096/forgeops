/**
 * Home page — mission list with new-mission form.
 */
"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { listMissions, createMission } from "@/lib/api";
import { StatusBadge } from "@/components/StatusBadge";
import type { Mission } from "@/types";

export default function HomePage() {
  const [missions, setMissions] = useState<Mission[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listMissions()
      .then(setMissions)
      .catch(() => setError("Failed to load missions"))
      .finally(() => setLoading(false));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const mission = await createMission({ title, description });
      setMissions((prev) => [mission, ...prev]);
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
      <div className="page-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1>Missions</h1>
          <p>Active and historical autonomous agent missions.</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowForm(!showForm)}>
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
                onChange={(e) => setTitle(e.target.value)}
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
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe what the agent should investigate and resolve…"
                required
                minLength={10}
              />
            </div>
            {error && (
              <p style={{ color: "var(--red)", marginBottom: 12 }}>{error}</p>
            )}
            <button className="btn btn-primary" type="submit" disabled={submitting}>
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
              <th>Status</th>
              <th>Steps</th>
              <th>Cost</th>
              <th>Created</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {missions.map((m) => (
              <tr key={m.id}>
                <td>
                  <span style={{ fontWeight: 600 }}>{m.title}</span>
                </td>
                <td>
                  <StatusBadge status={m.status} />
                </td>
                <td className="mono muted">{m.steps_used}</td>
                <td className="mono muted">€{m.cost_usd_used.toFixed(3)}</td>
                <td className="muted">
                  {new Date(m.created_at).toLocaleString()}
                </td>
                <td>
                  <Link href={`/missions/${m.id}`} className="btn">
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
