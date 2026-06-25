import "server-only";
import { promises as fs } from "node:fs";
import { PATHS } from "./config";

export interface JournalTrade {
  date: string;
  ticker: string;
  strategy: string;
  entry: number | null;
  stop: number | null;
  target: number | null;
  exit: number | null;
  pnl: number | null;
  tradeType: string;
  wasPlanned: boolean | null;
  chased: boolean | null;
  followedStop: boolean | null;
  lesson: string;
  grade: string;
}

export interface JournalStats {
  total: number;
  closed: number;
  open: number;
  wins: number;
  losses: number;
  winRate: number | null;
  netPnl: number;
  avgGrade: string | null;
  disciplineScore: number | null; // 0-100 from followedStop / chased / planned
}

// Tiny CSV parser — handles quoted fields with commas. No deps, no mocks.
function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  let field = "";
  let row: string[] = [];
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQuotes) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (c === '"') inQuotes = false;
      else field += c;
    } else if (c === '"') inQuotes = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n") { row.push(field); rows.push(row); row = []; field = ""; }
    else if (c === "\r") { /* skip */ }
    else field += c;
  }
  if (field.length > 0 || row.length > 0) { row.push(field); rows.push(row); }
  return rows.filter((r) => r.some((c) => c.trim() !== ""));
}

const num = (v: string): number | null => {
  const t = v?.trim();
  if (!t) return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
};
const yn = (v: string): boolean | null => {
  const t = v?.trim().toLowerCase();
  if (t === "yes") return true;
  if (t === "no") return false;
  return null;
};

const GRADE_VALUES: Record<string, number> = { A: 4, B: 3, C: 2, D: 1, F: 0 };
const GRADE_LABELS = ["F", "D", "C", "B", "A"];

export async function getJournal(): Promise<{ trades: JournalTrade[]; stats: JournalStats; exists: boolean }> {
  let text: string;
  try {
    text = await fs.readFile(PATHS.journalCsv, "utf8");
  } catch {
    return { trades: [], stats: emptyStats(), exists: false };
  }

  const rows = parseCsv(text);
  if (rows.length <= 1) return { trades: [], stats: emptyStats(), exists: true };

  const header = rows[0].map((h) => h.trim().toLowerCase());
  const idx = (name: string) => header.indexOf(name);
  const trades: JournalTrade[] = rows.slice(1).map((r) => ({
    date: r[idx("date")]?.trim() ?? "",
    ticker: r[idx("ticker")]?.trim() ?? "",
    strategy: r[idx("strategy")]?.trim() ?? "",
    entry: num(r[idx("entry")] ?? ""),
    stop: num(r[idx("stop")] ?? ""),
    target: num(r[idx("target")] ?? ""),
    exit: num(r[idx("exit")] ?? ""),
    pnl: num(r[idx("pnl")] ?? ""),
    tradeType: r[idx("trade_type")]?.trim() ?? "",
    wasPlanned: yn(r[idx("was_planned")] ?? ""),
    chased: yn(r[idx("chased")] ?? ""),
    followedStop: yn(r[idx("followed_stop")] ?? ""),
    lesson: r[idx("lesson")]?.trim() ?? "",
    grade: (r[idx("discipline_grade")]?.trim() ?? "").toUpperCase(),
  }));

  return { trades: trades.reverse(), stats: computeStats(trades), exists: true };
}

function computeStats(trades: JournalTrade[]): JournalStats {
  const closed = trades.filter((t) => t.pnl !== null);
  const wins = closed.filter((t) => (t.pnl ?? 0) > 0).length;
  const losses = closed.filter((t) => (t.pnl ?? 0) < 0).length;
  const netPnl = closed.reduce((s, t) => s + (t.pnl ?? 0), 0);

  const grades = trades.map((t) => GRADE_VALUES[t.grade]).filter((v) => v !== undefined);
  const avgGradeNum = grades.length ? grades.reduce((a, b) => a + b, 0) / grades.length : null;

  const disciplineFlags = trades.flatMap((t) => {
    const f: number[] = [];
    if (t.followedStop !== null) f.push(t.followedStop ? 1 : 0);
    if (t.chased !== null) f.push(t.chased ? 0 : 1);
    if (t.wasPlanned !== null) f.push(t.wasPlanned ? 1 : 0);
    return f;
  });
  const disciplineScore = disciplineFlags.length
    ? Math.round((disciplineFlags.reduce((a, b) => a + b, 0) / disciplineFlags.length) * 100)
    : null;

  return {
    total: trades.length,
    closed: closed.length,
    open: trades.length - closed.length,
    wins,
    losses,
    winRate: closed.length ? Math.round((wins / closed.length) * 100) : null,
    netPnl: Math.round(netPnl * 100) / 100,
    avgGrade: avgGradeNum === null ? null : GRADE_LABELS[Math.round(avgGradeNum)],
    disciplineScore,
  };
}

function emptyStats(): JournalStats {
  return { total: 0, closed: 0, open: 0, wins: 0, losses: 0, winRate: null, netPnl: 0, avgGrade: null, disciplineScore: null };
}
