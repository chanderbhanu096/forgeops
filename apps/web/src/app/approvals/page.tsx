/**
 * Approval Centre — human-in-the-loop decision page.
 */
"use client";

import { useState, useEffect } from "react";
import { listPendingApprovals, decideApproval } from "@/lib/api";
import { DiffViewer } from "@/components/DiffViewer";
import type { Approval } from "@/types";

const RISK_CLASS: Record<string, string> = {
  low: "badge badge-completed",
  medium: "badge badge-pending",
  high: "badge badge-paused",
  critical: "badge badge-failed",
};

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<Approval[]>([]);
  const [loading, setLoading] = useState(true);
  const [deciding, setDeciding] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [notes, setNotes] = useState("");

  function reload() {
    listPendingApprovals()
      .then(setApprovals)
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    reload();
    const interval = setInterval(reload, 10_000);
    return () => clearInterval(interval);
  }, []);

  async function decide(id: string, decision: "approved" | "rejected") {
    setDeciding(id);
    try {
      await decideApproval(id, decision, "human-operator", notes || undefined);
      setApprovals((prev) => prev.filter((a) => a.id !== id));
      setNotes("");
      setExpanded(null);
    } finally {
      setDeciding(null);
    }
  }

  return (
    <>
      <div className="page-header">
        <h1>Approval Centre</h1>
        <p>Review and approve agent-generated changes before production deployment.</p>
      </div>

      {loading ? (
        <p className="muted">Loading…</p>
      ) : approvals.length === 0 ? (
        <div className="empty-state">
          <p>No pending approvals.</p>
          <p style={{ fontSize: 12, marginTop: 6 }}>
            ForgeOps will request approval here before executing any changes.
          </p>
        </div>
      ) : (
        approvals.map((a) => (
          <div key={a.id} className="card">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
              <div>
                <h3 style={{ marginBottom: 4 }}>{a.summary}</h3>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  <span className={RISK_CLASS[a.risk_level] ?? "badge"}>
                    {a.risk_level} risk
                  </span>
                  <span className="muted" style={{ fontSize: 12 }}>
                    Requested {new Date(a.created_at).toLocaleString()}
                  </span>
                </div>
              </div>
              <button
                className="btn"
                onClick={() => setExpanded(expanded === a.id ? null : a.id)}
              >
                {expanded === a.id ? "Hide diff" : "View diff"}
              </button>
            </div>

            {expanded === a.id && a.diff && (
              <div style={{ marginBottom: 12 }}>
                <DiffViewer patch={a.diff} />
              </div>
            )}

            <div className="form-group">
              <label htmlFor={`notes-${a.id}`}>Review notes (optional)</label>
              <textarea
                id={`notes-${a.id}`}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Add notes for the audit trail…"
                style={{ minHeight: 60 }}
              />
            </div>

            <div style={{ display: "flex", gap: 10 }}>
              <button
                className="btn btn-success"
                disabled={deciding === a.id}
                onClick={() => decide(a.id, "approved")}
              >
                {deciding === a.id ? "Processing…" : "Approve"}
              </button>
              <button
                className="btn btn-danger"
                disabled={deciding === a.id}
                onClick={() => decide(a.id, "rejected")}
              >
                Reject
              </button>
            </div>
          </div>
        ))
      )}
    </>
  );
}
