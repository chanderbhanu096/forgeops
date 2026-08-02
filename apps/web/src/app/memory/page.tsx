/**
 * Memory viewer — browse agent operational memory.
 */
"use client";

import { useState, useEffect } from "react";
import { getProceduralMemory } from "@/lib/api";
import type { MemoryEntry } from "@/types";

const TYPE_STYLE: Record<string, React.CSSProperties> = {
  episodic:   { borderLeft: "3px solid var(--accent)", paddingLeft: 12 },
  semantic:   { borderLeft: "3px solid var(--purple)", paddingLeft: 12 },
  procedural: { borderLeft: "3px solid var(--green)",  paddingLeft: 12 },
  feedback:   { borderLeft: "3px solid var(--orange)", paddingLeft: 12 },
};

export default function MemoryPage() {
  const [entries, setEntries] = useState<MemoryEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getProceduralMemory()
      .then(setEntries)
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <div className="page-header">
        <h1>Agent Memory</h1>
        <p>Procedural strategies and semantic facts learned from completed missions.</p>
      </div>

      <div style={{ display: "flex", gap: 16, marginBottom: 20, flexWrap: "wrap" }}>
        {[
          { type: "episodic",   label: "Episodic",   desc: "Mission-specific events" },
          { type: "semantic",   label: "Semantic",   desc: "Durable environmental facts" },
          { type: "procedural", label: "Procedural", desc: "Proven strategies" },
          { type: "feedback",   label: "Feedback",   desc: "Human signals" },
        ].map(({ type, label, desc }) => (
          <div key={type} className="card" style={{ ...TYPE_STYLE[type], marginBottom: 0, flex: "1 1 180px" }}>
            <div style={{ fontWeight: 700, fontSize: 13 }}>{label}</div>
            <div style={{ fontSize: 12, color: "var(--muted)" }}>{desc}</div>
          </div>
        ))}
      </div>

      {loading ? (
        <p className="muted">Loading…</p>
      ) : entries.length === 0 ? (
        <div className="empty-state">
          <p>No memory entries yet.</p>
          <p style={{ fontSize: 12, marginTop: 6 }}>
            ForgeOps learns from completed missions. Procedural strategies will appear here.
          </p>
        </div>
      ) : (
        entries.map((entry) => (
          <div key={entry.id} className="card" style={{ ...TYPE_STYLE[entry.type], marginBottom: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
              <span className="badge" style={{ fontSize: 10, textTransform: "uppercase" }}>
                {entry.type}
              </span>
              <span className="muted" style={{ fontSize: 11 }}>
                usefulness: {entry.usefulness_score.toFixed(1)}
              </span>
            </div>
            <p style={{ fontSize: 13, marginBottom: 0 }}>{entry.content}</p>
            {Array.isArray(entry.extra.tags) && (
              <div style={{ display: "flex", gap: 4, marginTop: 8, flexWrap: "wrap" }}>
                {(entry.extra.tags as string[]).map((tag) => (
                  <code key={tag} style={{ fontSize: 11, background: "var(--surface)", border: "1px solid var(--border)", borderRadius: 3, padding: "1px 6px" }}>
                    {tag}
                  </code>
                ))}
              </div>
            )}
          </div>
        ))
      )}
    </>
  );
}
