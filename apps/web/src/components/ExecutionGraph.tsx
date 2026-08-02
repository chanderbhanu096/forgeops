/**
 * Execution graph — shows agent state machine progress.
 */
"use client";

import type { AgentState } from "@/types";
import { STATE_ORDER, STATE_LABELS } from "@/types";

interface Props {
  currentState: AgentState | null;
  missionStatus: string;
}

function stateClass(
  state: AgentState,
  currentState: AgentState | null,
  missionStatus: string
): "done" | "active" | "failed" | "pending" {
  if (missionStatus === "failed" && state === currentState) return "failed";
  if (state === currentState) return "active";

  const currentIndex = currentState ? STATE_ORDER.indexOf(currentState) : -1;
  const stateIndex = STATE_ORDER.indexOf(state);

  if (currentIndex > stateIndex) return "done";
  return "pending";
}

export function ExecutionGraph({ currentState, missionStatus }: Props) {
  return (
    <div className="exec-graph">
      {STATE_ORDER.map((state) => {
        const cls = stateClass(state, currentState, missionStatus);
        return (
          <div key={state} className="exec-node">
            <div className={`exec-indicator ${cls}`} />
            <span className={`exec-label ${cls === "active" ? "active" : cls === "pending" ? "muted" : ""}`}>
              {STATE_LABELS[state]}
            </span>
          </div>
        );
      })}
    </div>
  );
}
