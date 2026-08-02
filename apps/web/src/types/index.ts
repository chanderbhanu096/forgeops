/**
 * Shared TypeScript types for the ForgeOps Mission Control UI.
 */

export type MissionStatus =
  | "pending"
  | "running"
  | "paused"
  | "awaiting_approval"
  | "approved"
  | "rejected"
  | "completed"
  | "failed"
  | "rolled_back";

export type AgentState =
  | "mission_received"
  | "environment_discovery"
  | "plan_generation"
  | "evidence_collection"
  | "hypothesis_creation"
  | "hypothesis_verification"
  | "solution_generation"
  | "sandbox_execution"
  | "test_and_review"
  | "human_approval"
  | "execution"
  | "post_action_monitoring"
  | "completed"
  | "failed";

export interface Mission {
  id: string;
  title: string;
  description: string;
  status: MissionStatus;
  current_state: AgentState | null;
  steps_used: number;
  max_steps: number;
  cost_usd_used: number;
  max_cost_usd: number;
  pull_request_url: string | null;
  error: string | null;
  created_at: string;
}

export interface Approval {
  id: string;
  mission_id: string;
  summary: string;
  diff: string | null;
  risk_level: "low" | "medium" | "high" | "critical";
  decision: "pending" | "approved" | "rejected" | "auto_approved";
  created_at: string;
}

export interface Skill {
  name: string;
  version: string;
  description: string;
  required_tools: string[];
}

export interface MemoryEntry {
  id: string;
  type: string;
  content: string;
  extra: Record<string, unknown>;
  usefulness_score: number;
  created_at: string;
}

export interface SSEEvent {
  type:
    | "state_changed"
    | "state_starting"
    | "paused"
    | "awaiting_approval"
    | "completed"
    | "failed"
    | "timeout";
  data: Record<string, unknown>;
}

// Ordered display states for the execution graph
export const STATE_ORDER: AgentState[] = [
  "mission_received",
  "environment_discovery",
  "plan_generation",
  "evidence_collection",
  "hypothesis_creation",
  "hypothesis_verification",
  "solution_generation",
  "sandbox_execution",
  "test_and_review",
  "human_approval",
  "execution",
  "post_action_monitoring",
];

export const STATE_LABELS: Record<AgentState, string> = {
  mission_received: "Mission received",
  environment_discovery: "Discover environment",
  plan_generation: "Generate plan",
  evidence_collection: "Collect evidence",
  hypothesis_creation: "Create hypotheses",
  hypothesis_verification: "Verify hypotheses",
  solution_generation: "Generate fix",
  sandbox_execution: "Run in sandbox",
  test_and_review: "Test & review",
  human_approval: "Await approval",
  execution: "Execute",
  post_action_monitoring: "Monitor",
  completed: "Completed",
  failed: "Failed",
};
