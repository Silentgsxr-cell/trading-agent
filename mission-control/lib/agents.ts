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
  governor: boolean;
  summary: string;
  description: string; // back-face: architecture, flow, constraints
  feedsInto: string;   // output destination shown on card back
  blockers: string[];
  lines: number;
}

const CREW: Omit<AgentCard, "status" | "blockers" | "lines">[] = [
  {
    id: "signal",
    name: "HAWK",
    role: "Multi-strategy signal framework",
    file: "signaos.py",
    ring: "core",
    governor: false,
    summary: "Runs all enabled strategies, scores and ranks signals (S/A/B/C), routes A+ to VAULT. Never sizes or orders.",
    description:
      "Runs 6 pluggable strategies in parallel. ORB is live — 2-min bar opening-range breakout with volume ratio filter. Each signal is scored across four components: Technical 40%, News 15%, Macro 25%, Risk 20%. Only S and A tier signals are forwarded for sizing approval. HAWK has no knowledge of position size or account balance.",
    feedsInto: "VAULT → sizing decision",
  },
  {
    id: "risk",
    name: "VAULT",
    role: "Deterministic veto · sizing · circuit breakers",
    file: "risk_engine.py",
    ring: "core",
    governor: true,
    summary: "Only agent with veto power. Sizing, daily loss breaker, cooldown, force-close.",
    description:
      "The only agent with absolute veto. Enforces 3% daily loss limit, max 3 trades/day, and consecutive-loss cooldown. Sizes every position at 1% risk per trade using ATR-derived stop distance. A signal VAULT rejects never reaches TRIGGER — no bypass, no override. Circuit-breaker fires → session halts immediately.",
    feedsInto: "TRIGGER → order submission",
  },
  {
    id: "data",
    name: "DataOS",
    role: "Source of truth — bars · VWAP · levels · options",
    file: "dataos.py",
    ring: "macro",
    governor: false,
    summary: "Read-only data backbone. Never thinks. Aggregates 1-min bars, computes VWAP, publishes session levels and options chain on demand.",
    description:
      "Read-only data backbone. Fetches 1-min and 2-min bars, computes VWAP, publishes session high/low/open, and serves options chain on demand. No opinions — just structured data. Everything HAWK processes flows through DataOS first. Currently a stub; Webull live-data integration is the next build milestone.",
    feedsInto: "HAWK → signal evaluation",
  },
  {
    id: "daitaos",
    name: "DaiTaos",
    role: "Daily intelligence brief · Discord",
    file: "daitaos.py",
    ring: "news",
    governor: false,
    summary: "Morning briefing officer. Sends daily Discord brief at 6:20 AM AZ — market status, TSLA bias, watchlist scan, rules, journal edge.",
    description:
      "Sends a 9-section morning brief to Discord at 6:20 AM AZ: market status, TSLA direction bias, watchlist scan, SPY bias, today's rules, agent status, journal edge summary, edge reminder, and dev agent overnight results. Also hosts the live Discord bot for real-time queries (!brief, !status, !pnl, !ticket).",
    feedsInto: "Discord → daily context for the trader",
  },
  {
    id: "execution",
    name: "TRIGGER",
    role: "Order submission (paper-first)",
    file: "execution_agent.py",
    ring: "execution",
    governor: false,
    summary: "The only agent allowed to place/modify/cancel orders. Rejects trades not approved by VAULT.",
    description:
      "The only agent allowed to place, modify, or cancel orders. Any trade not stamped by VAULT is immediately rejected — no workarounds. Currently paper-mode only: simulates fills and writes results directly to the trade journal. Will go live only after paper profitability is established over a meaningful sample.",
    feedsInto: "Journal → fill record / LEDGER review",
  },
  {
    id: "review",
    name: "LEDGER",
    role: "Journal · expectancy · edge-decay",
    file: "review_agent.py",
    ring: "news",
    governor: false,
    summary: "Daily feedback loop. Can get pickier, never braver — can't touch risk limits.",
    description:
      "Reads completed trades daily, computes expectancy by strategy, and tracks discipline score over time. Can propose tightening setup filters when edge decays but cannot modify risk limits or position sizing. Acts as the system's own auditor. Currently a stub — wired in after TRIGGER paper fills are live.",
    feedsInto: "DaiTaos → edge summary in daily brief",
  },
  {
    id: "strategist",
    name: "Strategist",
    role: "Strike selection",
    file: "strategist.py",
    ring: "execution",
    governor: false,
    summary: "Selects strikes/expirations from approved signals. Not yet specced.",
    description:
      "Will select option strikes and expirations from VAULT-approved signals. Determines delta target, DTE range, and spread structure based on conviction tier and IV rank. Sits between VAULT approval and TRIGGER submission. Not yet specced or built — this is the last execution-layer piece needed before live options trading.",
    feedsInto: "TRIGGER → order parameters",
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
  readiness: number;
}

export function crewHealth(agents: AgentCard[]): CrewHealth {
  const live = agents.filter((a) => a.status === "live").length;
  const stub = agents.filter((a) => a.status === "stub").length;
  const missing = agents.filter((a) => a.status === "missing").length;
  return { total: agents.length, live, stub, missing, readiness: Math.round((live / agents.length) * 100) };
}
