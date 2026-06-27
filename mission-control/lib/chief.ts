import "server-only";
import { promises as fs } from "node:fs";
import path from "node:path";
import { PATHS, PROJECT_ROOT } from "./config";
import { getSession, getDecisions } from "./runtime";
import type { SessionState, DecisionEvent } from "./runtime";

export type MarketStatus = "OPEN" | "PRE-MARKET" | "AFTER-HOURS" | "CLOSED";

export interface Suggestion {
  id: string;
  agent_id: string;
  agent_color: string;
  title: string;
  reasoning: string;
  category: string;
  priority: number;
  status: "open" | "dev_queue" | "silent_queue" | "completed" | "discarded";
  created_at: string;
  flags: string[];
  flag_emojis: string;
}

export interface MorningBrief {
  sent_at: string;
  sections: {
    date_status?: string;
    tsla?:        string;
    watchlist?:   string[];
    spy?:         string;
    catalysts?:   string;
    dev_overnight?: string;
  };
}

export interface ChiefData {
  session:       SessionState | null;
  online:        boolean;
  decisions:     DecisionEvent[];
  todayDecisions: DecisionEvent[];
  suggestions:   Suggestion[];
  watchdogAlerts: string[];
  morningBrief:  MorningBrief | null;
  marketStatus:  MarketStatus;
  marketChip:    string;
  greeting:      string;
  todayLabel:    string;
}

// ── Market status ──────────────────────────────────────────────────────────────

export function getMarketStatus(): { status: MarketStatus; chip: string } {
  const now     = new Date();
  const etParts = new Intl.DateTimeFormat("en-US", {
    timeZone:  "America/New_York",
    weekday:   "short",
    hour:      "numeric",
    minute:    "numeric",
    hour12:    false,
  }).formatToParts(now);

  const weekday = etParts.find((p) => p.type === "weekday")?.value ?? "";
  const hour    = parseInt(etParts.find((p) => p.type === "hour")?.value    ?? "0", 10);
  const minute  = parseInt(etParts.find((p) => p.type === "minute")?.value ?? "0", 10);
  const mins    = hour * 60 + minute;

  const isWeekend = weekday === "Sat" || weekday === "Sun";

  if (isWeekend || mins < 4 * 60 || mins >= 20 * 60) {
    return { status: "CLOSED",      chip: "border-slate-600/60 bg-slate-700/30 text-slate-400" };
  }
  if (mins >= 9 * 60 + 30 && mins < 16 * 60) {
    return { status: "OPEN",        chip: "border-signal-live/40 bg-signal-live/10 text-signal-live" };
  }
  if (mins >= 4 * 60 && mins < 9 * 60 + 30) {
    return { status: "PRE-MARKET",  chip: "border-signal-warn/40 bg-signal-warn/10 text-signal-warn" };
  }
  return { status: "AFTER-HOURS",   chip: "border-blue-400/40 bg-blue-400/10 text-blue-300" };
}

export function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 5)  return "Good night";
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

export function getTodayLabel(): string {
  return new Date().toLocaleDateString("en-US", {
    weekday: "long", month: "long", day: "numeric", year: "numeric",
  });
}

// ── Suggestions ───────────────────────────────────────────────────────────────

async function loadSuggestions(): Promise<Suggestion[]> {
  try {
    const raw = await fs.readFile(path.join(PROJECT_ROOT, "data", "suggestions.json"), "utf8");
    const data = JSON.parse(raw);
    return Array.isArray(data) ? data : [];
  } catch {
    return [];
  }
}

// ── Watchdog alerts ───────────────────────────────────────────────────────────

async function loadWatchdogAlerts(): Promise<string[]> {
  try {
    const raw   = await fs.readFile(path.join(PROJECT_ROOT, "logs", "watchdog.log"), "utf8");
    const lines = raw.split("\n").filter(Boolean).slice(-30);
    return lines
      .filter((l) => /WARNING|CRITICAL|ERROR/i.test(l))
      .slice(-10)
      .reverse();
  } catch {
    return [];
  }
}

// ── Morning brief ─────────────────────────────────────────────────────────────

async function loadMorningBrief(): Promise<MorningBrief | null> {
  try {
    const raw = await fs.readFile(
      path.join(PROJECT_ROOT, "logs", "morning_brief_log.json"), "utf8"
    );
    return JSON.parse(raw) as MorningBrief;
  } catch {
    return null;
  }
}

// ── Focus rule ────────────────────────────────────────────────────────────────

export function getFocusLine(
  session:      SessionState | null,
  marketStatus: MarketStatus,
  hasSignalToday: boolean,
): string {
  if (marketStatus === "CLOSED") {
    return "Review yesterday's trades in Journal before the next open.";
  }
  if (session?.halted) {
    return "Circuit breaker active — review your rules before the next session.";
  }
  if (hasSignalToday) {
    return "HAWK has a setup — check the Signals tab before the window closes.";
  }
  if (marketStatus === "OPEN") {
    return "Watchlist monitoring — ORB window 9:30–10:00 ET.";
  }
  if (marketStatus === "PRE-MARKET") {
    return "Pre-market. Review the brief, check levels, be ready for 9:30.";
  }
  return "Stay disciplined. $10/trade. 3 trades max. Let the setup come to you.";
}

// ── Main loader ───────────────────────────────────────────────────────────────

export async function getChiefData(): Promise<ChiefData> {
  const today = new Date().toISOString().slice(0, 10);

  const [{ session, online }, decisions, suggestions, watchdogAlerts, morningBrief] =
    await Promise.all([
      getSession(),
      getDecisions(100),
      loadSuggestions(),
      loadWatchdogAlerts(),
      loadMorningBrief(),
    ]);

  const todayDecisions = decisions.filter((d) => d.ts.startsWith(today));
  const { status: marketStatus, chip: marketChip } = getMarketStatus();

  return {
    session,
    online,
    decisions,
    todayDecisions,
    suggestions,
    watchdogAlerts,
    morningBrief,
    marketStatus,
    marketChip,
    greeting:   getGreeting(),
    todayLabel: getTodayLabel(),
  };
}
