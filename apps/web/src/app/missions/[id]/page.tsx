/**
 * Mission detail page — execution status plus a human-readable analysis report.
 */
"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { getMission, pauseMission, resumeMission } from "@/lib/api";
import { ExecutionGraph } from "@/components/ExecutionGraph";
import { StatusBadge } from "@/components/StatusBadge";
import { BudgetMeter } from "@/components/BudgetMeter";
import { DiffViewer } from "@/components/DiffViewer";
import { useMissionStream } from "@/lib/useMissionStream";
import type { Mission, SSEEvent } from "@/types";
import { STATE_ORDER } from "@/types";

const PANEL_STATES = STATE_ORDER;

type RecordValue = Record<string, unknown>;
type HypothesisView = {
  id?: string;
  description?: string;
  confidence?: number;
  evidence?: string[];
};
type PlanStepView = {
  step_id?: string;
  description?: string;
  skill_name?: string;
};

function asRecord(value: unknown): RecordValue {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as RecordValue)
    : {};
}

function asStringList(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String).filter(Boolean) : [];
}

function SectionList({ items }: { items: string[] }) {
  if (items.length === 0) return <p className="muted">No items recorded.</p>;
  return (
    <ul style={{ margin: "8px 0 0", paddingLeft: 20 }}>
      {items.map((item, index) => (
        <li key={`${item}-${index}`} style={{ marginBottom: 7, lineHeight: 1.5 }}>
          {item}
        </li>
      ))}
    </ul>
  );
}

export default function MissionDetailPage({
  params,
}: {
  params: { id: string };
}) {
  const { id } = params;
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

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const loadedMission = await getMission(id);
      setMission(loadedMission);
      if (loadedMission.status === "failed") setActivity("Mission failed");
      else if (loadedMission.status === "completed") setActivity("Mission completed");
      else if (loadedMission.status === "awaiting_approval") setActivity("Waiting for approval");
    } catch (loadError) {
      const message = loadError instanceof Error ? loadError.message : "Unknown error";
      setError(`Failed to load mission: ${message}`);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    const timer = setInterval(() => setElapsed(Date.now() - startRef.current), 1000);
    return () => clearInterval(timer);
  }, []);

  useMissionStream(id, (event: SSEEvent) => {
    if (event.type === "state_starting" && event.data.state) {
      setActivity(`Running: ${String(event.data.state).replace(/_/g, " ")}`);
    }
    if (event.type === "state_starting" && event.data.state === "test_and_review") {
      setTestsPassed(null);
      setTestsFailed(null);
      setTestsRunning(null);
      setTestsTotal(null);
    }
    if (event.type === "state_starting" && event.data.tests_total != null) {
      setTestsTotal(Number(event.data.tests_total));
      setTestsPassed(Number(event.data.tests_passed ?? 0));
      setTestsFailed(Number(event.data.tests_failed ?? 0));
      setTestsRunning(Number(event.data.tests_running ?? 0));
    }
    if (["state_changed", "completed", "failed", "awaiting_approval"].includes(event.type)) {
      void refresh();
    }
  });

  async function handlePause() {
    if (!mission) return;
    await pauseMission(mission.id);
    await refresh();
  }

  async function handleResume() {
    if (!mission) return;
    await resumeMission(mission.id);
    await refresh();
  }

  if (loading) return <p className="muted">Loading…</p>;
  if (error) return <p style={{ color: "var(--red)" }}>{error}</p>;
  if (!mission) return <p style={{ color: "var(--red)" }}>Mission not found.</p>;

  const checkpoint = asRecord((mission as unknown as { checkpoint?: unknown }).checkpoint);
  const scratchpad = asRecord(checkpoint.scratchpad);
  const agentPipeline = asRecord(scratchpad.agent_pipeline);
  const verification = asRecord(scratchpad.verification);
  const monitoring = asRecord(scratchpad.monitoring);
  const hypotheses = (Array.isArray(checkpoint.hypotheses)
    ? checkpoint.hypotheses
    : []) as HypothesisView[];
  const topHypothesis = hypotheses[0];
  const plan = (Array.isArray(checkpoint.plan) ? checkpoint.plan : []) as PlanStepView[];
  const changedFiles = asStringList(checkpoint.changed_files);
  const citations = asStringList(scratchpad.retrieval_citations);
  const reviewerComments = asStringList(agentPipeline.reviewer_comments);
  const securityFindings = Array.isArray(checkpoint.security_findings)
    ? checkpoint.security_findings.map((item) => {
        const finding = asRecord(item);
        return `${String(finding.severity ?? "info").toUpperCase()}: ${String(
          finding.description ?? "Finding recorded"
        )}`;
      })
    : [];
  const patch = typeof checkpoint.proposed_patch === "string" ? checkpoint.proposed_patch : undefined;
  const environmentSummary = String(checkpoint.environment_summary ?? "");
  const retrievalSummary = String(scratchpad.retrieval_summary ?? "");
  const verificationFindings = asStringList(verification.findings);
  const confidence = Math.round(
    (Number(agentPipeline.confidence ?? topHypothesis?.confidence ?? verification.confidence) || 0) * 100
  );
  const analysisAvailable = Boolean(
    environmentSummary || retrievalSummary || hypotheses.length || patch || plan.length
  );

  const stateIndex = mission.current_state ? PANEL_STATES.indexOf(mission.current_state) : -1;
  const progressPct = stateIndex >= 0 ? Math.round(((stateIndex + 1) / PANEL_STATES.length) * 100) : 0;
  const elapsedMin = Math.floor(elapsed / 60000);
  const elapsedSec = Math.floor((elapsed % 60000) / 1000);
  const elapsedStr = `${elapsedMin}m ${String(elapsedSec).padStart(2, "0")}s`;
  const isActive = mission.status === "running";

  return (
    <>
      <div className="page-header">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h1>{mission.title}</h1>
            <div style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 6 }}>
              <StatusBadge status={mission.status} />
              <span className="muted" style={{ fontSize: 12 }}>{activity}</span>
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {isActive && <button className="btn" onClick={handlePause}>Pause</button>}
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

        {isActive && (
          <div style={{ marginTop: 12 }}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "var(--muted)", marginBottom: 4 }}>
              <span>{mission.current_state ? mission.current_state.replace(/_/g, " ").toUpperCase() : "STARTING"}</span>
              <span>{progressPct}% complete</span>
            </div>
            <div className="progress-bar"><div className="progress-fill" style={{ width: `${progressPct}%` }} /></div>
          </div>
        )}
      </div>

      <div className="cmd-panel">
        <div className="cmd-left">
          <div className="cmd-col-title">Execution graph</div>
          <ExecutionGraph currentState={mission.current_state} missionStatus={mission.status} />
        </div>
        <div className="cmd-right">
          <div className="cmd-col-title">Current activity</div>
          <div className="cmd-activity-label">{activity}</div>
          {testsTotal != null && (
            <div className="cmd-tests">
              <div className="cmd-test-row pass"><span className="cmd-test-count">{testsPassed ?? 0}</span><span>passed</span></div>
              <div className="cmd-test-row fail"><span className="cmd-test-count">{testsFailed ?? 0}</span><span>failed</span></div>
              <div className="cmd-test-row running"><span className="cmd-test-count">{testsRunning ?? 0}</span><span>still running</span></div>
            </div>
          )}
          <div className="cmd-stats">
            <div className="cmd-stat"><span className="cmd-stat-label">Cost so far</span><span className="cmd-stat-value mono">€{mission.cost_usd_used.toFixed(3)}</span></div>
            <div className="cmd-stat"><span className="cmd-stat-label">Steps</span><span className="cmd-stat-value mono">{mission.steps_used} / {mission.max_steps}</span></div>
            <div className="cmd-stat"><span className="cmd-stat-label">Model calls</span><span className="cmd-stat-value mono">{Number(checkpoint.total_model_calls ?? 0)}</span></div>
            {isActive && <div className="cmd-stat"><span className="cmd-stat-label">Elapsed</span><span className="cmd-stat-value mono">{elapsedStr}</span></div>}
          </div>
          <div style={{ marginTop: 20 }}>
            <BudgetMeter stepsUsed={mission.steps_used} maxSteps={mission.max_steps} costUsed={mission.cost_usd_used} maxCost={mission.max_cost_usd} />
          </div>
        </div>
      </div>

      <div style={{ marginTop: 16 }}>
        <div className="card">
          <div className="card-title">Mission brief</div>
          <p style={{ color: "var(--text)", marginBottom: 0 }}>{mission.description}</p>
        </div>

        {mission.status === "failed" && (
          <div className="card" style={{ borderColor: "var(--red)" }}>
            <div className="card-title" style={{ color: "var(--red)" }}>Error</div>
            <pre className="mono" style={{ whiteSpace: "pre-wrap", marginBottom: 0 }}>{mission.error || "The mission failed before the runtime returned an error message."}</pre>
          </div>
        )}

        <div className="card" style={{ borderColor: analysisAvailable ? "var(--accent)" : undefined }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
            <div>
              <div className="card-title">AI analysis report</div>
              <p className="muted" style={{ marginBottom: 0 }}>
                This is the visible outcome of the investigation—not only the state-machine progress.
              </p>
            </div>
            {confidence > 0 && <span className="badge badge-completed">{confidence}% confidence</span>}
          </div>

          {!analysisAvailable ? (
            <p className="muted" style={{ marginTop: 16 }}>The report will fill in as the investigation reaches evidence collection and hypothesis verification.</p>
          ) : (
            <div style={{ display: "grid", gap: 14, marginTop: 16 }}>
              <div>
                <strong>Environment analyzed</strong>
                <p style={{ marginTop: 6 }}>{environmentSummary || "The agent has not produced an environment summary yet."}</p>
              </div>

              <div>
                <strong>Investigation plan</strong>
                <SectionList items={plan.map((step) => `${step.description || "Investigation step"}${step.skill_name ? ` — ${step.skill_name}` : ""}`)} />
              </div>

              <div>
                <strong>Evidence and retrieval</strong>
                <p style={{ marginTop: 6 }}>{retrievalSummary || "No retrieval summary was recorded."}</p>
                {citations.length > 0 && <SectionList items={citations} />}
              </div>

              <div>
                <strong>Most likely root cause</strong>
                <p style={{ marginTop: 6 }}>{topHypothesis?.description || "No root-cause hypothesis has been generated yet."}</p>
                {topHypothesis?.evidence && topHypothesis.evidence.length > 0 && <SectionList items={topHypothesis.evidence} />}
              </div>

              {hypotheses.length > 1 && (
                <div>
                  <strong>Alternative hypotheses considered</strong>
                  <SectionList items={hypotheses.slice(1).map((item) => `${item.description || "Alternative hypothesis"} (${Math.round((Number(item.confidence) || 0) * 100)}%)`)} />
                </div>
              )}

              <div>
                <strong>Verification result</strong>
                <p style={{ marginTop: 6 }}>
                  {checkpoint.test_passed === true
                    ? "The proposed change passed the deterministic and agent review gates."
                    : checkpoint.test_passed === false
                      ? "The proposed change has not passed every verification gate."
                      : "Verification is still in progress."}
                </p>
                {verificationFindings.length > 0 && <SectionList items={verificationFindings} />}
                {reviewerComments.length > 0 && <SectionList items={reviewerComments} />}
              </div>

              <div>
                <strong>Proposed outcome</strong>
                <p style={{ marginTop: 6 }}>{String(agentPipeline.judge_summary ?? "A solution summary will appear after review.")}</p>
                <SectionList items={changedFiles.map((file) => `Change proposed in ${file}`)} />
              </div>

              {securityFindings.length > 0 && (
                <div>
                  <strong>Risk and security findings</strong>
                  <SectionList items={securityFindings} />
                </div>
              )}

              {Object.keys(monitoring).length > 0 && (
                <div>
                  <strong>Post-action monitoring</strong>
                  <p style={{ marginTop: 6 }}>Status: {String(monitoring.status ?? "unknown")}</p>
                  <SectionList items={asStringList(monitoring.observations)} />
                </div>
              )}
            </div>
          )}
        </div>

        {mission.status === "awaiting_approval" && (
          <div className="card" style={{ borderColor: "var(--accent)" }}>
            <div className="card-title">Human decision required</div>
            <p>You are not approving a vague status change. You are reviewing and approving:</p>
            <SectionList items={[
              topHypothesis?.description ? `Root-cause conclusion: ${topHypothesis.description}` : "The recorded root-cause conclusion",
              changedFiles.length ? `The proposed changes to ${changedFiles.join(", ")}` : "The proposed remediation plan",
              checkpoint.test_passed === true ? "A solution that passed the recorded verification gates" : "The next controlled execution step",
            ]} />
            <a href="/approvals" className="btn btn-primary" style={{ marginTop: 12 }}>Review in Approval Centre →</a>
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
