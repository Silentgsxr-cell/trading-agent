import "server-only";
import { promises as fs } from "node:fs";
import { PATHS } from "./config";

// Reads the v2 runtime state contract IF it exists. Phase 2's Python runner
// writes these; until then the cockpit shows an honest "engine offline" state
// instead of inventing live data.

export interface SessionState {
  date: string;
  startingBalance: number;
  currentBalance: number;
  dailyPnl: number;
  consecutiveLosses: number;
  halted: boolean;
  haltReason: string | null;
  openPositions: number;
  tradesToday: number;
}

export interface DecisionEvent {
  ts: string;
  kind: "signal" | "approved" | "rejected" | "halt" | "open" | "close" | "info";
  agent: string;
  message: string;
  meta?: Record<string, unknown>;
}

export async function getSession(): Promise<{ session: SessionState | null; online: boolean }> {
  try {
    const raw = await fs.readFile(PATHS.sessionJson, "utf8");
    return { session: JSON.parse(raw) as SessionState, online: true };
  } catch {
    return { session: null, online: false };
  }
}

async function readJsonl<T>(file: string, limit: number): Promise<T[]> {
  try {
    const raw = await fs.readFile(file, "utf8");
    const lines = raw.split("\n").map((l) => l.trim()).filter(Boolean);
    const out: T[] = [];
    for (const l of lines.slice(-limit)) {
      try { out.push(JSON.parse(l) as T); } catch { /* skip bad line */ }
    }
    return out.reverse();
  } catch {
    return [];
  }
}

export async function getDecisions(limit = 50): Promise<DecisionEvent[]> {
  return readJsonl<DecisionEvent>(PATHS.decisionsJsonl, limit);
}
