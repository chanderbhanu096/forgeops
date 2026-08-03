/**
 * API client — typed wrappers for ForgeOps REST endpoints.
 *
 * Browser requests stay on the web app origin and are forwarded by the
 * Next.js proxy route at /api/backend/[...path]. This avoids CORS and stale
 * NEXT_PUBLIC_API_URL values embedded in old browser bundles.
 */

const API = "/api/backend";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

import type { Approval, Mission, MemoryEntry, Skill } from "@/types";

// ── Missions ──────────────────────────────────────────────────────────────────

export function createMission(payload: {
  title: string;
  description: string;
  max_steps?: number;
  max_cost_usd?: number;
}): Promise<Mission> {
  return request("/api/v1/missions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listMissions(): Promise<Mission[]> {
  return request("/api/v1/missions");
}

export function getMission(id: string): Promise<Mission> {
  return request(`/api/v1/missions/${id}`);
}

export function pauseMission(id: string): Promise<{ status: string }> {
  return request(`/api/v1/missions/${id}/pause`, { method: "POST" });
}

export function resumeMission(id: string): Promise<{ status: string }> {
  return request(`/api/v1/missions/${id}/resume`, { method: "POST" });
}

// ── Approvals ─────────────────────────────────────────────────────────────────

export function listPendingApprovals(): Promise<Approval[]> {
  return request("/api/v1/approvals/pending");
}

export function decideApproval(
  id: string,
  decision: "approved" | "rejected",
  reviewer_id: string,
  notes?: string
): Promise<{ status: string }> {
  return request(`/api/v1/approvals/${id}/decide`, {
    method: "POST",
    body: JSON.stringify({ decision, reviewer_id, notes }),
  });
}

// ── Skills ────────────────────────────────────────────────────────────────────

export function listSkills(): Promise<Skill[]> {
  return request("/api/v1/skills");
}

// ── Memory ────────────────────────────────────────────────────────────────────

export function getMissionMemory(missionId: string): Promise<MemoryEntry[]> {
  return request(`/api/v1/memory/missions/${missionId}`);
}

export function getProceduralMemory(): Promise<MemoryEntry[]> {
  return request("/api/v1/memory/procedural");
}

export function recordFeedback(payload: {
  mission_id: string;
  feedback_type: string;
  outcome: "positive" | "negative";
  detail: string;
}): Promise<{ id: string; status: string }> {
  return request("/api/v1/memory/feedback", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
