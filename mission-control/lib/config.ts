import path from "node:path";

// ── Real data sources ────────────────────────────────────────────────────────
// Mission Control lives at:  silent graph/trading-agent 2/mission-control
// So the trading project root is one level up, and the Obsidian vault two up.
// Everything is overridable via env so this isn't pinned to one machine.

const MC_DIR = process.cwd();

export const PROJECT_ROOT =
  process.env.CLAWOPS_PROJECT_ROOT || path.resolve(MC_DIR, "..");

export const VAULT_ROOT =
  process.env.CLAWOPS_VAULT_ROOT || path.resolve(MC_DIR, "..", "..");

export const PATHS = {
  projectRoot: PROJECT_ROOT,
  journalCsv: path.join(PROJECT_ROOT, "data", "journal.csv"),
  agentsV2Dir: path.join(PROJECT_ROOT, "agents"),
  legacyAgentDir: path.join(PROJECT_ROOT, "dashboard", "agent"),
  // v2 runtime state contract (written by the Python runner in Phase 2).
  // Read-if-present today so the cockpit goes live the moment it exists.
  stateDir: path.join(PROJECT_ROOT, "state"),
  sessionJson: path.join(PROJECT_ROOT, "state", "session.json"),
  signalsJsonl: path.join(PROJECT_ROOT, "state", "signals.jsonl"),
  decisionsJsonl: path.join(PROJECT_ROOT, "state", "decisions.jsonl"),
  agentStatusJson: path.join(PROJECT_ROOT, "state", "agent_status.json"),
  financeJson: path.join(PROJECT_ROOT, "data", "finance.json"),
  vaultRoot: VAULT_ROOT,
};

// Vault files that must NEVER surface in the Docs/Memory screens.
// Silent's vault mixes trading with finances, EIN, family, LLC — keep those out.
export const DOC_DENYLIST = [
  "finance",
  "ein",
  "family",
  "business & llc",
  "business plan",
  "network",
  "vault-setup",
  "mac tools",
];

// Only these vault notes/folders are considered "trading research".
// Deliberately excludes the personal root hub (SILENT.md) and any non-trading node.
export const DOC_ALLOW_HINTS = ["trading", "orb", "strategy", "handoff", "readme"];
