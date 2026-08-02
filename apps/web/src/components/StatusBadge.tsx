/**
 * Status badge component.
 */
import type { MissionStatus } from "@/types";

const CLASS_MAP: Record<string, string> = {
  pending: "badge badge-pending",
  running: "badge badge-running",
  paused: "badge badge-paused",
  awaiting_approval: "badge badge-approval",
  approved: "badge badge-approval",
  completed: "badge badge-completed",
  failed: "badge badge-failed",
  rejected: "badge badge-failed",
  rolled_back: "badge badge-failed",
};

const LABEL_MAP: Record<string, string> = {
  pending: "Pending",
  running: "Running",
  paused: "Paused",
  awaiting_approval: "Awaiting approval",
  approved: "Approved",
  completed: "Completed",
  failed: "Failed",
  rejected: "Rejected",
  rolled_back: "Rolled back",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={CLASS_MAP[status] ?? "badge"}>
      {LABEL_MAP[status] ?? status}
    </span>
  );
}
