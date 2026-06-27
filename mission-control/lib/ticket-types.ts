// Shared types and constants — safe to import from both server and client components.
// No Node.js imports (no fs, no path).

export type TicketStatus =
  | "open"
  | "in_progress"
  | "done"
  | "failed"
  | "needs_review";

export type TicketPriority = "critical" | "high" | "medium" | "low";
export type TicketComplexity = "simple" | "moderate" | "complex";

export interface Ticket {
  id: string;
  title: string;
  description: string;
  what_to_complete: string;
  what_done_looks_like: string;
  connectors_needed: string[];
  restrictions: string[];
  allowed_paths: string[];
  blocked_paths: string[];
  priority: TicketPriority;
  complexity: TicketComplexity;
  complexity_color: string;
  status: TicketStatus;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  files_read: string[];
  files_modified: string[];
  files_created: string[];
  git_branch: string;
  git_commit_hash: string;
  agent_summary: string;
  approval_gate: string;
  smoke_test_passed: boolean | null;
  log: string[];
}

export interface TicketDB {
  paused: boolean;
  tickets: Ticket[];
}

export const COMPLEXITY_COLOR: Record<TicketComplexity, string> = {
  simple:   "#00e676",
  moderate: "#ffc107",
  complex:  "#f44336",
};

export const PRIORITY_COLOR: Record<TicketPriority, string> = {
  critical: "#9c27b0",
  high:     "#f44336",
  medium:   "#ffc107",
  low:      "#64748b",
};

export const PRIORITY_ORDER: Record<TicketPriority, number> = {
  critical: 0,
  high:     1,
  medium:   2,
  low:      3,
};
