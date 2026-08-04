/**
 * Mission detail page — execution status plus a human-readable analysis report.
 */
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { BudgetMeter } from "@/components/BudgetMeter";
import { DiffViewer } from "@/components/DiffViewer";
import { ExecutionGraph } from "@/components/ExecutionGraph";
import { StatusBadge } from "@/components/StatusBadge";
import { getMission, pauseMission, resumeMission } from "@/lib/api";
import { useMissionStream } from "@/lib/useMissionStream";
import type { Mission, SSEEvent } from "@/types";
import { STATE_ORDER } from "@/types";

const PANEL_STATES = STATE_ORDER;
type RecordValue = Record<string, unknown>;

type HypothesisView = {
  description: string;
  confidence: number;
  evidence: string[];
};

type PlanStepView = {
  description: string;
  skillName?: string;
};

function asRecord(value: unknown): RecordValue {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as RecordValue)
    : {};
}

function displayValue(value: unknown): string {
  if (value == null) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function asStringList(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map(displayValue).map((item) => item.trim()).filter(Boolean);
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) return [];
    return trimmed.includes("\n")
      ? trimmed.split("\n").map((item) => item.replace(/^[-*•]\s*/, "").trim()).filter(Boolean)
      : [trimmed];
  }
  if (value && typeof value === "object") {
    return Object.entries(value as RecordValue).map(
      ([key, item]) => `${key.replace(/_/g, " ")}: ${displayValue(item)}`
    );
  }
  return value == null ? [] : [String(value)];
}

function normalizeHypotheses(value: unknown): HypothesisView[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => {
    const record = asRecord(item);
    return {
      description: displayValue(record.description || record.summary || "Hypothesis recorded"),
      confidence: Number(record.confidence) || 0,
      evidence: asStringList(record.evidence),
    };
  });
}

function normalizePlan(value: unknown): PlanStepView[] {
  if (!Array.isArray(value)) return [];
  return value.map((item) => {
    const record = asRecord(item);
    return {
      description: displayValue(record.description || record.title || "Investigation step"),
      skillName: displayValue(record.skill_name || record.skillName) || undefined,
    };
  });
}

function SectionList({ items }: { items: unknown }) {
  const safeItems = asStringList(items);
  if (safeItems.length === 0) return <p className="muted">No items recorded.</p>;
  return (
    <ul style={{ margin: "8px 0 0", paddingLeft: 20 }}>
      {safeItems.map((item, index) => (
        <li key={`${index}-${item.slice(0, 40)}`} style={{ marginBottom: 7, lineHeight: 1.5 }}>
          {item}
        </li>
      ))}
    </ul>
  );
}

export default function MissionDetailPage({ params }: { params: { id: string } }) {
  const { id } = params;
  const [mission, setMission] = useState<Mission | null>(null);
  const [loading, setLoading] = useState(true);
  const [activity, setActivity] = useState("Initialising…");
  const [testsPassed, setTestsPassed] = useState<number | null>(null);
  const [testsFailed, setTestsFailed] = useState<number | null>(null);
  const [testsRunning, setTestsRunning] = useState<number | null>(null);
  const [testsTotal, setTestsTotal] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const startRef = useRef(Date.now());
  const [elapsed, setElapsed] = useState(0);

  const refresh = useCallback(async () => {
    try {
      const loadedMission = await getMission(id);
      setMission(loadedMission);
      setError(null);
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
    if (mission?.status !== "running") return;
    const timer = window.setInterval(() => setElapsed(Date.now() - startRef.current), 1000);
    return () => window.clearInterval(timer);
  }, [mission?.status]);

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
    if (event.data.tests_total != null) {
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

  if (loading) return <p className="muted">Loading mission result…</p>;
  if (error) return <div className="card"><p style={{ color: "var(--red)" }}>{error}</p><button className="btn" onClick={() => void refresh()}>Try again</button></div>;
  if (!mission) return <p style={{ color: "var(--red)" }}>Mission not found.</p>;

  const checkpoint = asRecord((mission as unknown as { checkpoint?: unknown }).checkpoint);
  const scratchpad = asRecord(checkpoint.scratchpad);
  const agentPipeline = asRecord(scratchpad.agent_pipeline);
  const verification = asRecord(scratchpad.verification);
  const monitoring = asRecord(scratchpad.monitoring);
  const hypotheses = normalizeHypotheses(checkpoint.hypotheses);
  const topHypothesis = hypotheses[0];
  const plan = normalizePlan(checkpoint.plan);
  const changedFiles = asStringList(checkpoint.changed_files);
  const citations = asStringList(scratchpad.retrieval_citations);
  const reviewerComments = asStringList(agentPipeline.reviewer_comments);
  const verificationFindings = asStringList(verification.findings);
  const securityFindings = Array.isArray(checkpoint.security_findings)
    ? checkpoint.security_findings.map((item) => {
        const finding = asRecord(item);
        return `${displayValue(finding.severity || "info").toUpperCase()}: ${displayValue(
          finding.description || finding.detail || "Finding recorded"
        )}`;
      })
    : asStringList(checkpoint.security_findings);
  const patch = typeof checkpoint.proposed_patch === "string" ? checkpoint.proposed_patch : "";
  const environmentSummary = displayValue(checkpoint.environment_summary);
  const retrievalSummary = displayValue(scratchpad.retrieval_summary);
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
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
          <div>
            <h1>{mission.title}</h1>
            <div style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 6 }}>
              <StatusBadge status={mission.status} />
              <span className="muted" style={{ fontSize: 12 }}>{activity}</span>
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {isActive && <button className="btn" onClick={handlePause}>Pause</button>}
            {mission.status === "paused" && <button className="btn btn-primary" onClick={handleResume}>Resume</button>}
            {mission.pull_request_url && <a href={mission.pull_request_url} target="_blank" rel="noreferrer" className="btn btn-success">View PR ↗</a>}
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
            <div className="cmd-stat"><span className="cmd-stat-label">Cost</span><span className="cmd-stat-value mono">€{mission.cost_usd_used.toFixed(3)}</span></div>
            <div className="cmd-stat"><span className="cmd-stat-label">Steps</span><span className="cmd-stat-value mono">{mission.steps_used} / {mission.max_steps}</span></div>
            <div className="cmd-stat"><span className="cmd-stat-label">Model calls</span><span className="cmd-stat-value mono">{Number(checkpoint.total_model_calls ?? 0)}</span></div>
            {isActive && <div className="cmd-stat"><span className="cmd-stat-label">Elapsed</span><span className="cmd-stat-value mono">{elapsedStr}</span></div>}
          </div>
          <div style={{ marginTop: 20 }}><BudgetMeter stepsUsed={mission.steps_used} maxSteps={mission.max_steps} costUsed={mission.cost_usd_used} maxCost={mission.max_cost_usd} /></div>
        </div>
      </div>

      <div style={{ marginTop: 16 }}>
        <div className="card"><div className="card-title">Mission brief</div><p style={{ marginBottom: 0 }}>{mission.description}</p></div>

        {mission.status === "failed" && (
          <div className="card" style={{ borderColor: "var(--red)" }}>
            <div className="card-title" style={{ color: "var(--red)" }}>Error</div>
            <pre className="mono" style={{ whiteSpace: "pre-wrap", marginBottom: 0 }}>{mission.error || "The mission failed before returning an error message."}</pre>
          </div>
        )}

        <div className="card" style={{ borderColor: analysisAvailable ? "var(--accent)" : undefined }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "flex-start" }}>
            <div><div className="card-title">AI analysis report</div><p className="muted">Visible investigation output and evidence.</p></div>
            {confidence > 0 && <span className="badge badge-completed">{confidence}% confidence</span>}
          </div>

          {!analysisAvailable ? <p className="muted">The report will appear as the mission collects evidence.</p> : (
            <div style={{ display: "grid", gap: 16 }}>
              <section><strong>Environment analyzed</strong><p>{environmentSummary || "No environment summary recorded."}</p></section>
              <section><strong>Investigation plan</strong><SectionList items={plan.map((step) => `${step.description}${step.skillName ? ` — ${step.skillName}` : ""}`)} /></section>
              <section><strong>Evidence and retrieval</strong><p>{retrievalSummary || "No retrieval summary recorded."}</p>{citations.length > 0 && <SectionList items={citations} />}</section>
              <section><strong>Most likely root cause</strong><p>{topHypothesis?.description || "No root-cause hypothesis generated yet."}</p>{topHypothesis && <SectionList items={topHypothesis.evidence} />}</section>
              {hypotheses.length > 1 && <section><strong>Alternative hypotheses</strong><SectionList items={hypotheses.slice(1).map((item) => `${item.description} (${Math.round(item.confidence * 100)}%)`)} /></section>}
              <section><strong>Verification result</strong><p>{checkpoint.test_passed === true ? "The proposed change passed the recorded verification gates." : checkpoint.test_passed === false ? "The proposed change has not passed every verification gate." : "Verification is still in progress."}</p>{verificationFindings.length > 0 && <SectionList items={verificationFindings} />}{reviewerComments.length > 0 && <SectionList items={reviewerComments} />}</section>
              <section><strong>Proposed outcome</strong><p>{displayValue(agentPipeline.judge_summary) || "A solution summary will appear after review."}</p><SectionList items={changedFiles.map((file) => `Change proposed in ${file}`)} /></section>
              {securityFindings.length > 0 && <section><strong>Risk and security findings</strong><SectionList items={securityFindings} /></section>}
              {Object.keys(monitoring).length > 0 && <section><strong>Post-action monitoring</strong><p>Status: {displayValue(monitoring.status) || "unknown"}</p><SectionList items={monitoring.observations} /></section>}
            </div>
          )}
        </div>

        {mission.status === "awaiting_approval" && (
          <div className="card" style={{ borderColor: "var(--accent)" }}>
            <div className="card-title">Human decision required</div>
            <p>You are reviewing and approving:</p>
            <SectionList items={[
              topHypothesis?.description ? `Root-cause conclusion: ${topHypothesis.description}` : "The recorded root-cause conclusion",
              changedFiles.length ? `Proposed changes to ${changedFiles.join(", ")}` : "The proposed remediation plan",
              checkpoint.test_passed === true ? "A solution that passed the recorded verification gates" : "The next controlled execution step",
            ]} />
            <a href="/approvals" className="btn btn-primary" style={{ marginTop: 12 }}>Review in Approval Centre →</a>
          </div>
        )}

        {patch && (
          <details className="card">
            <summary className="card-title" style={{ cursor: "pointer" }}>Generated patch — click to expand</summary>
            <div style={{ marginTop: 14 }}><DiffViewer patch={patch} /></div>
          </details>
        )}
      </div>
    </>
  );
}
