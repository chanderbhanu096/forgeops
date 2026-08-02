/**
 * Mission detail page — command-centre layout with aligned vertical divider.
 *
 * Layout matches the brief's ASCII wireframe:
 *
 *   ┌─────────────────────────────────────────────────────────┐
 *   │ Mission title                    status  progress bar   │
 *   ├──────────────────────────┬──────────────────────────────┤
 *   │  Execution graph         │  Current activity            │
 *   │  (left column)           │  (right column)              │
 *   ├──────────────────────────┴──────────────────────────────┤
 *   │  Budgets / error / PR / review summary / diff           │
 *   └─────────────────────────────────────────────────────────┘
 *
 * The vertical bar between the two columns is a real CSS border on the
 * right edge of the left column — not a grid gap — so it stretches the
 * full height of the panel regardless of content length.
 */
"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { use } from "react";
import { getMission, pauseMission, resumeMission } from "@/lib/api";
import { ExecutionGraph } from "@/components/ExecutionGraph";
import { StatusBadge } from "@/components/StatusBadge";
import { BudgetMeter } from "@/components/BudgetMeter";
import { DiffViewer } from "@/components/DiffViewer";
import { useMissionStream } from "@/lib/useMissionStream";
import type { Mission, SSEEvent } from "@/types";
import { STATE_ORDER } from "@/types";

const PANEL_STATES = STATE_ORDER;

export default function MissionDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const [mission, setMission] = useState<Mission | null>(null);
  const [loading, setLoading] = useState(true);
  const [activity, setActivity] = useState<string>("Initialising…");
  const [testsPassed, setTestsPassed] = useState<number | null>(null);
  const [testsFailed, setTestsFailed] = useState<number | null>(null);
  const [testsRunning, setTestsRunning] = useState<number | null>(null);
  const [testsTotal, setTestsTotal] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const startRef = useRef<number>(Date.now());
  const [elapsed, setElapsed] = useState(0);

  const refresh = useCallback(() => {
    getMission(id)
      .then(setMission)
      .catch(() => setError("Failed to load mission"));
  }, [id]);

  useEffect(() => {
    refresh();
    setLoading(false);
  }, [refresh]);

  // Tick elapsed timer every second while running
  useEffect(() => {
    const t = setInterval(() => setElapsed(Date.now() - startRef.current), 1000);
    return () => clearInterval(t);
  }, []);

  // Live SSE updates
  useMissionStream(id, (event: SSEEvent) => {
    if (event.type === "state_starting" && event.data.state) {
      setActivity(`Running: ${String(event.data.state).replace(/_/g, " ")}`);
    }
    if (event.type === "state_starting" && event.data.state === "test_and_review") {
      // Reset test counters when test phase starts
      setTestsPassed(null); setTestsFailed(null);
      setTestsRunning(null); setTestsTotal(null);
    }
    // The API can emit a progress sub-event with test counts
    if (event.type === "state_starting" && event.data.tests_total != null) {
      setTestsTotal(Number(event.data.tests_total));
      setTestsPassed(Number(event.data.tests_passed ?? 0));
      setTestsFailed(Number(event.data.tests_failed ?? 0));
      setTestsRunning(Number(event.data.tests_running ?? 0));
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
    ? (checkpoint.scratchpad as Record<string, unknown>).agent_pipeline as
        | Record<string, unknown>
        | undefined
    : undefined;

  const stateIndex = mission.current_state
    ? PANEL_STATES.indexOf(mission.current_state)
    : -1;
  const progressPct =
    stateIndex >= 0 ? Math.round(((stateIndex + 1) / PANEL_STATES.length) * 100) : 0;

  const elapsedMin = Math.floor(elapsed / 60000);
  const elapsedSec = Math.floor((elapsed % 60000) / 1000);
  const elapsedStr = `${elapsedMin}m ${String(elapsedSec).padStart(2, "0")}s`;

  const isActive = mission.status === "running";

  return (
    <>
      {/* ── Page header ───────────────────────────────────────────────── */}
      <div className="page-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h1>{mission.title}</h1>
            <div style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 6 }}>
              <StatusBadge status={mission.status} />
              {isActive && (
                <span className="muted" style={{ fontSize: 12 }}>{activity}</span>
              )}
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {isActive && (
              <button className="btn" onClick={handlePause}>Pause</button>
            )}
            {mission.status === "paused" && (
              <button className="btn btn-primary" onClick={handleResume}>Resume</button>
            )}
            {mission.pull_request_url && (
              <a
                href={mission.pull_request_url}
                target="_blank"
                rel="noreferrer"
                className="btn btn-success"
              >
                View PR ↗
              </a>
            )}
          </div>
        </div>

        {/* Progress bar — always visible while running */}
        {isActive && (
          <div style={{ marginTop: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "var(--muted)", marginBottom: 4 }}>
              <span>
                {mission.current_state
                  ? mission.current_state.replace(/_/g, " ").toUpperCase()
                  : "STARTING"}
              </span>
              <span>{progressPct}% complete</span>
            </div>
            <div className="progress-bar">
              <div className="progress-fill" style={{ width: `${progressPct}%` }} />
            </div>
          </div>
        )}
      </div>

      {/* ── Command-centre panel ──────────────────────────────────────── */}
      {/*
        One outer bordered box. The left column has border-right which acts
        as the vertical divider — it stretches the full height of the row
        regardless of which side is taller, because both cells are in the
        same CSS grid with align-items: stretch (the default).
      */}
      <div className="cmd-panel">
        {/* Left — execution graph */}
        <div className="cmd-left">
          <div className="cmd-col-title">Execution graph</div>
          <ExecutionGraph
            currentState={mission.current_state}
            missionStatus={mission.status}
          />
        </div>

        {/* Right — current activity */}
        <div className="cmd-right">
          <div className="cmd-col-title">Current activity</div>

          <div className="cmd-activity-label">{activity}</div>

          {/* Test progress — only shown during test_and_review phase */}
          {testsTotal != null && (
            <div className="cmd-tests">
              <div className="cmd-test-row pass">
                <span className="cmd-test-count">{testsPassed ?? 0}</span>
                <span>passed</span>
              </div>
              <div className="cmd-test-row fail">
                <span className="cmd-test-count">{testsFailed ?? 0}</span>
                <span>failed</span>
              </div>
              <div className="cmd-test-row running">
                <span className="cmd-test-count">{testsRunning ?? 0}</span>
                <span>still running</span>
              </div>
            </div>
          )}

          {/* Stats row */}
          <div className="cmd-stats">
            <div className="cmd-stat">
              <span className="cmd-stat-label">Cost so far</span>
              <span className="cmd-stat-value mono">€{mission.cost_usd_used.toFixed(3)}</span>
            </div>
            <div className="cmd-stat">
              <span className="cmd-stat-label">Steps</span>
              <span className="cmd-stat-value mono">{mission.steps_used} / {mission.max_steps}</span>
            </div>
            {isActive && (
              <div className="cmd-stat">
                <span className="cmd-stat-label">Elapsed</span>
                <span className="cmd-stat-value mono">{elapsedStr}</span>
              </div>
            )}
          </div>

          {/* Budget meters inside the right panel */}
          <div style={{ marginTop: 20 }}>
            <BudgetMeter
              stepsUsed={mission.steps_used}
              maxSteps={mission.max_steps}
              costUsed={mission.cost_usd_used}
              maxCost={mission.max_cost_usd}
            />
          </div>
        </div>
      </div>

      {/* ── Below-the-fold cards ──────────────────────────────────────── */}
      <div style={{ marginTop: 16 }}>
        <div className="card">
          <div className="card-title">Mission brief</div>
          <p style={{ color: "var(--text)", marginBottom: 0 }}>{mission.description}</p>
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
            <p>
              The agent has completed its review and is waiting for approval before
              executing changes.
            </p>
            <a href="/approvals" className="btn btn-primary" style={{ marginTop: 10 }}>
              Go to Approval Centre →
            </a>
          </div>
        )}

        {agentPipeline && (
          <div className="card">
            <div className="card-title">Agent review summary</div>
            <p>{String(agentPipeline.judge_summary ?? "Review complete.")}</p>
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
    </>
  );
}
