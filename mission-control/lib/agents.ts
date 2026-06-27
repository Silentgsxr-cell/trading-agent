import "server-only";
import { promises as fs } from "node:fs";
import path from "node:path";
import { PATHS } from "./config";

export type AgentStatus = "live" | "stub" | "missing";
export type Ring = "macro" | "news" | "execution" | "core";

export interface AgentCard {
  id: string;
  name: string;
  role: string;
  file: string;
  status: AgentStatus;
  ring: Ring;
  governor: boolean; // Risk Engine + Mission Control act as governors
  summary: string;
  blockers: string[]; // parsed TODO / pending lines
  lines: number;
}

// The v2 crew. `file` maps to agent_v2/<file>; status is DERIVED by reading the
// source (NotImplementedError => stub), never hardcoded.
const CREW: Omit<AgentCard, "status" | "blockers" | "lines">[] = [
  {
    id: "signal",
    name: "Signaos",
    role: "Multi-strategy signal framework",
    file: "signaos.py",
    ring: "core",
    governor: false,
    summary: "Runs all enabled strategies, scores and ranks signals (S/A/B/C), routes A+ to Risk Engine. Never sizes or orders.",
  },
  {
    id: "risk",
    name: "Risk Engine",
    role: "Deterministic veto · sizing · circuit breakers",
    file: "risk_engine.py",
    ring: "core",
    governor: true,
    summary: "Only agent with veto power. Sizing, daily loss breaker, cooldown, force-close.",
  },
  {
    id: "data",
    name: "DataOS",
    role: "Bars · VWAP · session levels · options chain",
    file: "dataos.py",
    ring: "macro",
    governor: false,
    summary: "Read-only data backbone. Aggregates 1-min bars into 2-min/15-min, computes VWAP, publishes session levels and options chain on demand.",
  },
  {
    id: "execution",
    name: "Execution Agent",
    role: "Order submission (paper-first)",
    file: "execution_agent.py",
    ring: "execution",
    governor: false,
    summary: "The only agent allowed to place/modify/cancel orders. Rejects un-approved trades.",
  },
  {
    id: "review",
    name: "Review Agent",
    role: "Journal · expectancy · edge-decay",
    file: "review_agent.py",
    ring: "news",
    governor: false,
    summary: "Daily feedback loop. Can get pickier, never braver — can't touch risk limits.",
  },
  {
    id: "strategist",
    name: "Strategist",
    role: "Strike selection",
    file: "strategist.py",
    ring: "execution",
    governor: false,
    summary: "Selects strikes/expirations from approved signals. Not yet specced.",
  },
];

function parseBlockers(src: string): string[] {
  const out: string[] = [];
  const lines = src.split("\n");
  for (const l of lines) {
    const t = l.trim();
    if (/not yet (built|implemented)/i.test(t) || /pending /i.test(t)) {
      const clean = t.replace(/^["'\s]+|["'\s]+$/g, "");
      if (clean && clean.length < 160) out.push(clean);
    }
  }
  return Array.from(new Set(out)).slice(0, 3);
}

export async function getAgents(): Promise<AgentCard[]> {
  return Promise.all(
    CREW.map(async (c) => {
      const full = path.join(PATHS.agentsV2Dir, c.file);
      try {
        const src = await fs.readFile(full, "utf8");
        const isStub = /raise\s+NotImplementedError/.test(src);
        return {
          ...c,
          status: (isStub ? "stub" : "live") as AgentStatus,
          blockers: isStub ? parseBlockers(src) : [],
          lines: src.split("\n").length,
        };
      } catch {
        return { ...c, status: "missing" as AgentStatus, blockers: ["Not yet created."], lines: 0 };
      }
    }),
  );
}

export interface CrewHealth {
  total: number;
  live: number;
  stub: number;
  missing: number;
  readiness: number; // % live
}

export function crewHealth(agents: AgentCard[]): CrewHealth {
  const live = agents.filter((a) => a.status === "live").length;
  const stub = agents.filter((a) => a.status === "stub").length;
  const missing = agents.filter((a) => a.status === "missing").length;
  return { total: agents.length, live, stub, missing, readiness: Math.round((live / agents.length) * 100) };
}
