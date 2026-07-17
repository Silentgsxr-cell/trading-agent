import "server-only";
import { promises as fs } from "node:fs";
import path from "node:path";
import { PATHS } from "./config";

export type AgentStatus = "live" | "stub" | "missing";
export type Ring = "macro" | "news" | "execution" | "core";
export type LiveState = "thinking" | "idle" | "error";

// Mirrors what AgentBrain.start_task/update_task/finish_task/error write to
// state/agent_status.json (utils/agent_brain.py). Real agents only — an
// agent with no entry here has simply never run since the file existed.
export interface AgentLiveStatus {
  state: LiveState;
  currentTask: string | null;
  progressPct: number | null;
  queueLen: number | null;
  confidence: number | null;
  waitingOn: string | null;
  lastAction: string | null;
  startedAt: string | null;
  lastCompletedAt: string | null;
  lastHeartbeat: string | null;
  nextScheduledAction: string | null;
}

export interface AgentCard {
  id: string;
  name: string;
  role: string;
  file: string;
  status: AgentStatus;
  ring: Ring;
  governor: boolean;
  summary: string;
  description: string;
  feedsInto: string;
  blockers: string[];
  lines: number;
  live: AgentLiveStatus | null;
}

type CrewEntry = Omit<AgentCard, "status" | "blockers" | "lines" | "live"> & {
  dir?: "utils"; // non-agents/ source files
};

const CREW: CrewEntry[] = [
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
    name: "PULSE",
    role: "Market intelligence — bars · VWAP · levels · options",
    file: "dataos.py",
    ring: "macro",
    governor: false,
    summary: "Read-only market data backbone. Never thinks. Aggregates 1-min bars, computes VWAP, publishes session levels and options chain on demand.",
    description:
      "Read-only market intelligence backbone. Fetches 1-min and 2-min bars, computes VWAP from running cumulative(price × volume) / cumulative(volume), publishes session high/low/open, and serves options chain on demand. No opinions — just structured data. Everything HAWK processes flows through PULSE first. Currently a stub; Webull live-data integration is the next build milestone.",
    feedsInto: "HAWK → signal evaluation",
  },
  {
    id: "intel",
    name: "INTEL",
    role: "Daily intelligence brief · Discord",
    file: "daitaos.py",
    ring: "news",
    governor: false,
    summary: "Morning briefing officer. Sends daily Discord brief at 6:20 AM AZ — market status, TSLA bias, watchlist scan, rules, journal edge.",
    description:
      "Sends a 9-section morning brief to Discord at 6:20 AM AZ: market status, TSLA direction bias, watchlist scan, SPY bias, today's rules, agent status, journal edge summary, edge reminder, and dev agent overnight results. Also hosts the live Discord bot for real-time queries (!brief, !status, !pnl, !ticket). Routes to DISCORD_MORNING_BRIEF_WEBHOOK.",
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
    feedsInto: "INTEL → edge summary in daily brief",
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
  {
    id: "watch",
    name: "WATCH",
    role: "Security monitor · integrity checks",
    file: "watchdog.py",
    dir: "utils",
    ring: "core",
    governor: false,
    summary: "Background security monitor. Runs 7 checks every 60s — key exposure, session integrity, config tamper, heartbeat, .env git tracking, git author audit.",
    description:
      "Always-on security layer. Checks every 60s: API key exposure in source files, session.json invariants vs config thresholds, 5 critical file existence checks, risk_config/strategy_config mtime+size tampering, runner heartbeat staleness, .env git-tracking status, and hourly git commit author audit. Alerts fire to DISCORD_WATCHDOG_WEBHOOK. Alert dedup prevents spam. Log rotation at 10 MB.",
    feedsInto: "Discord → security alerts / SAGE → suggestion hooks",
  },
  {
    id: "sage",
    name: "SAGE",
    role: "Suggestion intelligence · system advisor",
    file: "suggestion_agent.py",
    dir: "utils",
    ring: "news",
    governor: false,
    summary: "Reads 9 data sources twice daily, makes one Claude API call, surfaces up to 3 actionable suggestions for the operator.",
    description:
      "Autonomous advisor that runs at 5:00 AM and 5:30 PM AZ. Reads journal.csv, session.json, decisions.jsonl, tickets.json, suggestions.json, finance.json, watchdog.log, tab_usage.json, and agents/ stub scan. One Claude API call (claude-sonnet-4-6) per cycle with a strict JSON-only output prompt. Posts suggestions via AgentBrain — priority ≥ 9 alerts also route to DISCORD_SUGGESTIONS_WEBHOOK.",
    feedsInto: "Suggestion Board → operator review / Dev Agent → ticket queue",
  },
  {
    id: "chief",
    name: "CHIEF",
    role: "Chief of Staff · orchestrator",
    file: "chief.py",
    ring: "core",
    governor: false,
    summary: "Runs 6:00 AM and 4:30 PM AZ. Reads state from every agent, makes one Claude API call, writes the assessment the /chief home page renders.",
    description:
      "The operator's primary interface. Twice daily, aggregates signal state, risk posture, suggestion queue, and agent health from across the crew, then makes one Claude API call to produce a structured assessment written to logs/chief_assessment.json. Mission Control's /chief page renders that assessment as the home screen. Does not trade, research, or override VAULT — pure coordination and summarization.",
    feedsInto: "Master Chief home page → operator",
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

const AGENTS_DIR = path.join(PATHS.projectRoot, "agents");
const UTILS_DIR  = path.join(PATHS.projectRoot, "utils");

// Some agents post status under a legacy AgentBrain id (see AGENT_AVATARS
// in utils/agent_brain.py). Check these before giving up on a lookup.
const STATUS_ID_ALIASES: Record<string, string[]> = {
  WATCH: ["WATCHDOG"],
  PULSE: ["DATAOS"],
  INTEL: ["DAITAOS"],
};

async function _readAgentStatusFile(): Promise<Record<string, any>> {
  try {
    const raw = await fs.readFile(PATHS.agentStatusJson, "utf8");
    const data = JSON.parse(raw);
    return typeof data === "object" && data !== null ? data : {};
  } catch {
    return {};
  }
}

function _toLiveStatus(raw: any): AgentLiveStatus | null {
  if (!raw || typeof raw !== "object") return null;
  const state: LiveState =
    raw.status === "thinking" || raw.status === "error" ? raw.status : "idle";
  return {
    state,
    currentTask:         raw.current_task ?? null,
    progressPct:          raw.progress_pct ?? null,
    queueLen:              raw.queue_len ?? null,
    confidence:            raw.confidence ?? null,
    waitingOn:             raw.waiting_on ?? null,
    lastAction:            raw.last_action ?? null,
    startedAt:             raw.started_at ?? null,
    lastCompletedAt:       raw.last_completed_at ?? null,
    lastHeartbeat:         raw.last_heartbeat ?? null,
    nextScheduledAction:   raw.next_scheduled_action ?? null,
  };
}

export async function getAgents(): Promise<AgentCard[]> {
  const statusFile = await _readAgentStatusFile();

  return Promise.all(
    CREW.map(async (c) => {
      const baseDir = c.dir === "utils" ? UTILS_DIR : AGENTS_DIR;
      const full    = path.join(baseDir, c.file);
      const { dir: _dir, ...card } = c;

      const candidates = [c.name, ...(STATUS_ID_ALIASES[c.name] ?? [])];
      const rawStatus = candidates.map((id) => statusFile[id]).find(Boolean) ?? null;
      const live = _toLiveStatus(rawStatus);

      try {
        const src = await fs.readFile(full, "utf8");
        // Anchored to line start so this doesn't false-positive on agents
        // (CHIEF, SAGE) whose own source code *contains the string*
        // "raise NotImplementedError" as part of scanning other agents'
        // stub status — that text lives inside a quoted string/condition,
        // never at the start of a line, so it no longer matches.
        const isStub = /^\s*raise\s+NotImplementedError/m.test(src);
        return {
          ...card,
          status: (isStub ? "stub" : "live") as AgentStatus,
          blockers: isStub ? parseBlockers(src) : [],
          lines: src.split("\n").length,
          live,
        };
      } catch {
        return { ...card, status: "missing" as AgentStatus, blockers: ["Not yet created."], lines: 0, live };
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
  thinking: number;
  errors: number;
  idle: number;
}

export function crewHealth(agents: AgentCard[]): CrewHealth {
  const live     = agents.filter((a) => a.status === "live").length;
  const stub     = agents.filter((a) => a.status === "stub").length;
  const missing  = agents.filter((a) => a.status === "missing").length;
  const thinking = agents.filter((a) => a.live?.state === "thinking").length;
  const errors   = agents.filter((a) => a.live?.state === "error").length;
  // "idle" here means built + has actually reported in at least once —
  // distinct from a live agent that has simply never run yet.
  const idle = agents.filter((a) => a.status === "live" && a.live?.state === "idle").length;
  return {
    total: agents.length, live, stub, missing,
    readiness: Math.round((live / agents.length) * 100),
    thinking, errors, idle,
  };
}
