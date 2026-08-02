/**
 * Mission detail page — execution graph, live status, diff viewer, memory.
 */
"use client";

import { useState, useEffect, useCallback } from "react";
import { use } from "react";
import { getMission, pauseMission, resumeMission } from "@/lib/api";
import { ExecutionGraph } from "@/components/ExecutionGraph";
import { StatusBadge } from "@/components/StatusBadge";
import { BudgetMeter } from "@/components/BudgetMeter";
import { DiffViewer } from "@/components/DiffViewer";
import { useMissionStream } from "@/lib/useMissionStream";
import type { Mission, SSEEvent } from "@/types";

export default function MissionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [mission, setMission] = useState<Mission | null>(null);
  const [loading, setLoading] = useState(true);
  const [activity, setActivity] = useState<string>("Initialising…");
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    getMission(id)
      .then(setMission)
      .catch(() => setError("Failed to load mission"));
  }, [id]);

  useEffect(() => {
    refresh();
    setLoading(false);
  }, [refresh]);

  // Live SSE updates
  useMissionStream(id, (event: SSEEvent) => {
    if (event.type === "state_starting" && event.data.state) {
      setActivity(`Running: ${String(event.data.state).replace(/_/g, " ")}`);
    }
    if (
      event.type === "state_changed" ||
      event.type === "completed" ||
      event.type === "failed" ||
      event.type === "awaiting_approval"
    ) {
      refresh();
    }
  });

  async function handlePause() {
    if (!mission) return;
    await pauseMission(mission.id);
    refresh();
  }

  async function handleResume() {
    if (!mission) return;
    await resumeMission(mission.id);
    refresh();
  }

  if (loading || !mission) {
    return <p className="muted">Loading…</p>;
  }

  if (error) {
    return <p style={{ color: "var(--red)" }}>{error}</p>;
  }

  const checkpoint = (mission as unknown as { checkpoint?: Record<string, unknown> }).checkpoint;
  const patch = checkpoint?.proposed_patch as string | undefined;
  const agentPipeline = checkpoint?.scratchpad
    ? (checkpoint.scratchpad as Record<string, unknown>).agent_pipeline as Record<string, unknown> | undefined
    : undefined;

  const progressPct = mission.current_state
    ? Math.round(
        (["mission_received","environment_discovery","plan_generation","evidence_collection",
          "hypothesis_creation","hypothesis_verification","solution_generation",
          "sandbox_execution","test_and_review","human_approval","execution",
          "post_action_monitoring"].indexOf(mission.current_state) /
          12) *
          100
      )
    : 0;

  return (
    <>
      <div className="page-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h1>{mission.title}</h1>
            <div style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 6 }}>
              <StatusBadge status={mission.status} />
              {mission.status === "running" && (
                <span className="muted" style={{ fontSize: 12 }}>{activity}</span>
              )}
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {mission.status === "running" && (
              <button className="btn" onClick={handlePause}>Pause</button>
            )}
            {mission.status === "paused" && (
              <button className="btn btn-primary" onClick={handleResume}>Resume</button>
            )}
            {mission.pull_request_url && (
              <a href={mission.pull_request_url} target="_blank" rel="noreferrer" className="btn btn-success">
                View PR ↗
              </a>
            )}
          </div>
        </div>

        {mission.status === "running" && (
          <div style={{ marginTop: 12 }}>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${progressPct}%` }} />
            </div>
            <span className="muted" style={{ fontSize: 11, marginTop: 4, display: "block" }}>
              {progressPct}% complete
            </span>
          </div>
        )}
      </div>

      <div className="two-col">
        {/* Left column — execution graph */}
        <div>
          <div className="card">
            <div className="card-title">Execution graph</div>
            <ExecutionGraph
              currentState={mission.current_state}
              missionStatus={mission.status}
            />
          </div>

          <div className="card">
            <div className="card-title">Budgets</div>
            <BudgetMeter
              stepsUsed={mission.steps_used}
              maxSteps={mission.max_steps}
              costUsed={mission.cost_usd_used}
              maxCost={mission.max_cost_usd}
            />
          </div>
        </div>

        {/* Right column — details */}
        <div>
          <div className="card">
            <div className="card-title">Mission</div>
            <p style={{ color: "var(--text)" }}>{mission.description}</p>
          </div>

          {mission.status === "failed" && mission.error && (
            <div className="card" style={{ borderColor: "var(--red)" }}>
              <div className="card-title" style={{ color: "var(--red)" }}>Error</div>
              <pre className="mono" style={{ whiteSpace: "pre-wrap" }}>{mission.error}</pre>
            </div>
          )}

          {mission.status === "awaiting_approval" && (
            <div className="card" style={{ borderColor: "var(--accent)" }}>
              <div className="card-title">Awaiting human approval</div>
              <p>The agent has completed its review and is waiting for approval before executing.</p>
              <a href="/approvals" className="btn btn-primary" style={{ marginTop: 10 }}>
                Go to Approval Centre →
              </a>
            </div>
          )}

          {agentPipeline && (
            <div className="card">
              <div className="card-title">Agent review summary</div>
              <p>{String(agentPipeline.judge_summary || "Review complete.")}</p>
              <div style={{ marginTop: 8, fontSize: 12, color: "var(--muted)" }}>
                Revision cycles: {String(agentPipeline.revision_cycles ?? 0)} ·
                Confidence: {((Number(agentPipeline.confidence) || 0) * 100).toFixed(0)}%
              </div>
            </div>
          )}

          {patch && (
            <div className="card">
              <div className="card-title">Generated patch</div>
              <DiffViewer patch={patch} />
            </div>
          )}
        </div>
      </div>
    </>
  );
}
