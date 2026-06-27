"use client";
import { useState, useEffect } from "react";

const FLASK = process.env.NEXT_PUBLIC_FLASK_URL ?? "http://localhost:5000";

// ── Types ─────────────────────────────────────────────────────────────────────

interface CalEvent {
  calendar: string;
  title: string;
  start: string;
  end: string;
  allDay: boolean;
}

interface ReminderTask {
  list: string;
  title: string;
  due: string;
}

interface Goal {
  id: string;
  title: string;
  notes: string;
  target_date: string;
  status: "active" | "done";
  created_at: string;
  completed_at: string | null;
}

interface FinanceSnapshot {
  accounts: { id: string; name: string; role: string; balance: number }[];
  debts:    { id: string; name: string; balance: number; original: number }[];
  total_assets: number;
  total_debt:   number;
  net_worth:    number;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function usd(n: number) {
  return new Intl.NumberFormat("en-US", {
    style: "currency", currency: "USD", maximumFractionDigits: 0,
  }).format(n);
}

function parseAppleDate(s: string): Date | null {
  if (!s) return null;
  // "Friday, June 27, 2026 at 9:30:00 AM" → "June 27, 2026 9:30:00 AM"
  const cleaned = s.replace(/^[A-Za-z]+,\s*/, "").replace(" at ", " ");
  const d = new Date(cleaned);
  return isNaN(d.getTime()) ? null : d;
}

const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const WEEKDAYS = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];

function isoDay(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function dayLabel(iso: string): string {
  const [y, mo, da] = iso.split("-").map(Number);
  const d = new Date(y, mo - 1, da);
  return `${WEEKDAYS[d.getDay()]}, ${MONTHS[mo - 1]} ${da}`;
}

function fmtTime(s: string): string {
  const d = parseAppleDate(s);
  if (!d) return s;
  const h = d.getHours();
  const min = String(d.getMinutes()).padStart(2, "0");
  const ampm = h >= 12 ? "PM" : "AM";
  const h12 = h % 12 || 12;
  return `${h12}:${min} ${ampm}`;
}

function groupByDay(events: CalEvent[]): Map<string, CalEvent[]> {
  const map = new Map<string, CalEvent[]>();
  for (const evt of events) {
    const d = parseAppleDate(evt.start);
    if (!d) continue;
    const key = isoDay(d);
    if (!map.has(key)) map.set(key, []);
    map.get(key)!.push(evt);
  }
  return map;
}

// ── Shared atoms ──────────────────────────────────────────────────────────────

function SectionHeader({ glyph, label, sub }: { glyph: string; label: string; sub?: string }) {
  return (
    <div className="mb-3 flex items-center gap-2">
      <span className="text-[15px] text-slate-400">{glyph}</span>
      <div>
        <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-300">{label}</div>
        {sub && <div className="text-[10px] text-signal-dim">{sub}</div>}
      </div>
    </div>
  );
}

// ── Calendar section ──────────────────────────────────────────────────────────

const CAL_PALETTE: string[] = [
  "#3ddc97", "#4fc3f7", "#ab47bc", "#ff7043", "#f2b84b",
  "#5c6bc0", "#26a69a", "#ec407a",
];
const calColorCache: Record<string, string> = {};
let calColorIdx = 0;
function calColor(name: string): string {
  if (!calColorCache[name]) {
    calColorCache[name] = CAL_PALETTE[calColorIdx % CAL_PALETTE.length];
    calColorIdx++;
  }
  return calColorCache[name];
}

function CalendarSection() {
  const [events, setEvents] = useState<CalEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const r = await fetch(`${FLASK}/api/life/calendar`);
        const d = await r.json();
        if (mounted) { setEvents(d.events ?? []); setError(d.error ?? ""); }
      } catch (e) { if (mounted) setError(String(e)); }
      finally { if (mounted) setLoading(false); }
    })();
    return () => { mounted = false; };
  }, []);

  const today = new Date();
  const dayKeys: string[] = Array.from({ length: 7 }, (_, i) =>
    isoDay(new Date(today.getTime() + i * 86_400_000))
  );
  const todayKey = isoDay(today);
  const grouped = groupByDay(events);

  return (
    <div className="panel p-4">
      <SectionHeader glyph="◈" label="Calendar" sub="Next 7 days · macOS Calendar" />
      {error && <p className="mb-2 text-[11px] text-amber-400">AppleScript: {error}</p>}
      {loading ? (
        <p className="text-[12px] text-signal-dim">Fetching events…</p>
      ) : (
        <div className="space-y-4">
          {dayKeys.map(day => {
            const dayEvents = grouped.get(day) ?? [];
            const isToday = day === todayKey;
            return (
              <div key={day}>
                <div className={`mb-1.5 text-[10px] font-bold uppercase tracking-[0.14em] ${
                  isToday ? "text-signal-live" : "text-slate-600"
                }`}>
                  {isToday ? "Today · " : ""}{dayLabel(day)}
                </div>
                {dayEvents.length === 0 ? (
                  <p className="text-[11px] text-slate-700 italic">—</p>
                ) : (
                  <div className="space-y-1">
                    {dayEvents.map((evt, i) => (
                      <div
                        key={i}
                        className="flex items-center gap-2 rounded-md bg-white/[0.02] border border-white/5 px-3 py-1.5"
                      >
                        <span
                          style={{ backgroundColor: calColor(evt.calendar) }}
                          className="h-1.5 w-1.5 shrink-0 rounded-full"
                        />
                        <span className="flex-1 text-[12px] text-slate-200 truncate">{evt.title}</span>
                        <span className="shrink-0 text-[10px] text-slate-500">
                          {evt.allDay ? "All day" : fmtTime(evt.start)}
                        </span>
                        <span className="shrink-0 text-[10px] text-slate-600">{evt.calendar}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Goals section ─────────────────────────────────────────────────────────────

function GoalRow({
  goal, onToggle, onDelete,
}: { goal: Goal; onToggle: (g: Goal) => void; onDelete: (g: Goal) => void }) {
  const done = goal.status === "done";
  return (
    <div className={`group flex items-center gap-2.5 rounded-md px-3 py-2 border transition ${
      done
        ? "border-signal-live/10 bg-signal-live/5"
        : "border-white/5 bg-white/[0.02] hover:bg-white/[0.04]"
    }`}>
      <button
        onClick={() => onToggle(goal)}
        className={`shrink-0 h-4 w-4 rounded-full border-2 flex items-center justify-center transition ${
          done
            ? "border-signal-live bg-signal-live/20"
            : "border-slate-600 hover:border-signal-live"
        }`}
      >
        {done && <span className="text-[9px] text-signal-live">✓</span>}
      </button>
      <div className="flex-1 min-w-0">
        <p className={`text-[12px] leading-snug ${done ? "line-through text-slate-500" : "text-slate-200"}`}>
          {goal.title}
        </p>
        {goal.notes && (
          <p className="text-[10px] text-slate-600 truncate">{goal.notes}</p>
        )}
      </div>
      {goal.target_date && (
        <span className="shrink-0 text-[10px] text-slate-500">{goal.target_date}</span>
      )}
      <button
        onClick={() => onDelete(goal)}
        className="shrink-0 text-[10px] text-slate-700 hover:text-red-400 opacity-0 group-hover:opacity-100 transition"
      >
        ✕
      </button>
    </div>
  );
}

function GoalsSection() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [addTitle, setAddTitle] = useState("");
  const [addNotes, setAddNotes] = useState("");
  const [addDate, setAddDate] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [toast, setToast] = useState("");

  function showToast(m: string) {
    setToast(m);
    setTimeout(() => setToast(""), 2500);
  }

  async function loadGoals() {
    try {
      const r = await fetch(`${FLASK}/api/life/goals`);
      if (r.ok) setGoals(await r.json());
    } catch { /* flask offline */ }
    setLoading(false);
  }

  useEffect(() => { loadGoals(); }, []);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!addTitle.trim()) return;
    setSubmitting(true);
    try {
      const r = await fetch(`${FLASK}/api/life/goals`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: addTitle.trim(), notes: addNotes.trim(), target_date: addDate }),
      });
      const d = await r.json();
      if (d.success) {
        setGoals(prev => [...prev, d.goal]);
        setAddTitle(""); setAddNotes(""); setAddDate("");
        setShowAdd(false);
        showToast("Goal added");
      }
    } finally { setSubmitting(false); }
  }

  async function toggleGoal(g: Goal) {
    const newStatus = g.status === "done" ? "active" : "done";
    const r = await fetch(`${FLASK}/api/life/goals/${g.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: newStatus }),
    });
    const d = await r.json();
    if (d.success) {
      setGoals(prev => prev.map(x => x.id === g.id ? d.goal : x));
      showToast(newStatus === "done" ? "Goal completed!" : "Goal reopened");
    }
  }

  async function deleteGoal(g: Goal) {
    await fetch(`${FLASK}/api/life/goals/${g.id}`, { method: "DELETE" });
    setGoals(prev => prev.filter(x => x.id !== g.id));
    showToast("Goal removed");
  }

  const active = goals.filter(g => g.status === "active");
  const done   = goals.filter(g => g.status === "done");

  const inputCls =
    "rounded-md border border-white/10 bg-white/[0.03] px-2 py-1.5 text-[12px] text-slate-200 placeholder-slate-600 focus:border-white/20 focus:outline-none";

  return (
    <div className="panel p-4">
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 rounded-lg bg-signal-live/90 px-4 py-2 text-sm font-medium text-black shadow-lg">
          {toast}
        </div>
      )}
      <div className="mb-3 flex items-center justify-between">
        <SectionHeader
          glyph="◉"
          label="Goals"
          sub={`${active.length} active · ${done.length} done`}
        />
        <button
          onClick={() => setShowAdd(s => !s)}
          className="rounded-md border border-white/10 bg-white/[0.03] px-2 py-1 text-[11px] text-slate-400 hover:bg-white/[0.06] transition"
        >
          {showAdd ? "✕ Cancel" : "+ Add"}
        </button>
      </div>

      {showAdd && (
        <form onSubmit={handleAdd} className="mb-3 space-y-2 rounded-lg border border-white/10 bg-white/[0.02] p-3">
          <input
            className={`${inputCls} w-full`}
            placeholder="Goal title *"
            value={addTitle}
            onChange={e => setAddTitle(e.target.value)}
          />
          <input
            className={`${inputCls} w-full`}
            placeholder="Notes (optional)"
            value={addNotes}
            onChange={e => setAddNotes(e.target.value)}
          />
          <input
            type="date"
            className={`${inputCls} w-full`}
            value={addDate}
            onChange={e => setAddDate(e.target.value)}
          />
          <button
            type="submit"
            disabled={submitting || !addTitle.trim()}
            className="w-full rounded-md bg-signal-live/10 border border-signal-live/20 py-1.5 text-[12px] text-signal-live hover:bg-signal-live/15 transition disabled:opacity-40"
          >
            {submitting ? "Adding…" : "Add Goal"}
          </button>
        </form>
      )}

      {loading ? (
        <p className="text-[12px] text-signal-dim">Loading goals…</p>
      ) : goals.length === 0 ? (
        <p className="text-[12px] text-slate-600 italic">No goals yet — add your first one.</p>
      ) : (
        <div className="space-y-1.5">
          {active.map(g => (
            <GoalRow key={g.id} goal={g} onToggle={toggleGoal} onDelete={deleteGoal} />
          ))}
          {done.length > 0 && active.length > 0 && (
            <div className="my-2 border-t border-white/5" />
          )}
          {done.map(g => (
            <GoalRow key={g.id} goal={g} onToggle={toggleGoal} onDelete={deleteGoal} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Tasks section ─────────────────────────────────────────────────────────────

function TasksSection() {
  const [tasks, setTasks] = useState<ReminderTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const r = await fetch(`${FLASK}/api/life/tasks`);
        const d = await r.json();
        if (mounted) { setTasks(d.tasks ?? []); setError(d.error ?? ""); }
      } catch (e) { if (mounted) setError(String(e)); }
      finally { if (mounted) setLoading(false); }
    })();
    return () => { mounted = false; };
  }, []);

  const byList = new Map<string, ReminderTask[]>();
  for (const t of tasks) {
    if (!byList.has(t.list)) byList.set(t.list, []);
    byList.get(t.list)!.push(t);
  }

  return (
    <div className="panel p-4">
      <SectionHeader glyph="□" label="Tasks" sub="macOS Reminders · incomplete" />
      {error && <p className="mb-2 text-[11px] text-amber-400">AppleScript: {error}</p>}
      {loading ? (
        <p className="text-[12px] text-signal-dim">Fetching reminders…</p>
      ) : tasks.length === 0 ? (
        <p className="text-[12px] text-slate-600 italic">No incomplete reminders found.</p>
      ) : (
        <div className="space-y-3">
          {Array.from(byList.entries()).map(([list, items]) => (
            <div key={list}>
              <div className="mb-1 text-[10px] font-bold uppercase tracking-wide text-slate-600">
                {list}
              </div>
              <div className="space-y-1">
                {items.map((t, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-2 rounded-md bg-white/[0.02] border border-white/5 px-3 py-1.5"
                  >
                    <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-slate-600" />
                    <span className="flex-1 text-[12px] text-slate-300 truncate">{t.title}</span>
                    {t.due && (
                      <span className="shrink-0 text-[10px] text-slate-500">{t.due}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Finance snapshot ──────────────────────────────────────────────────────────

function FinanceSection() {
  const [fin, setFin] = useState<FinanceSnapshot | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const r = await fetch(`${FLASK}/api/life/finance`);
        if (r.ok && mounted) setFin(await r.json());
      } catch { /* flask offline */ }
      finally { if (mounted) setLoading(false); }
    })();
    return () => { mounted = false; };
  }, []);

  return (
    <div className="panel p-4">
      <SectionHeader glyph="$" label="Finance" sub="Snapshot from finance.json" />
      {loading ? (
        <p className="text-[12px] text-signal-dim">Loading…</p>
      ) : !fin ? (
        <p className="text-[12px] text-slate-600">Flask offline — start with python3 dashboard/app.py</p>
      ) : (
        <div className="space-y-4">
          {/* Net worth trio */}
          <div className="grid grid-cols-3 gap-2">
            {[
              { label: "Net Worth", value: fin.net_worth,    color: fin.net_worth >= 0 ? "#3ddc97" : "#f44336" },
              { label: "Assets",    value: fin.total_assets, color: "#4fc3f7" },
              { label: "Debt",      value: fin.total_debt,   color: "#f44336" },
            ].map(({ label, value, color }) => (
              <div key={label} className="rounded-lg border border-white/5 bg-white/[0.03] p-3 text-center">
                <div style={{ color }} className="text-sm font-bold">{usd(value)}</div>
                <div className="text-[10px] uppercase tracking-wide text-slate-600 mt-0.5">{label}</div>
              </div>
            ))}
          </div>

          {/* Accounts */}
          {fin.accounts.length > 0 && (
            <div>
              <div className="mb-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-600">Accounts</div>
              <div className="space-y-1">
                {fin.accounts.map(a => (
                  <div
                    key={a.id}
                    className="flex items-center gap-2 rounded-md bg-white/[0.02] border border-white/5 px-3 py-1.5"
                  >
                    <span className="flex-1 text-[12px] text-slate-300">{a.name}</span>
                    <span className="text-[10px] text-slate-500">{a.role}</span>
                    <span className="text-[12px] font-semibold text-slate-200">{usd(a.balance)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Debts with payoff bars */}
          {fin.debts.filter(d => d.balance > 0).length > 0 && (
            <div>
              <div className="mb-1.5 text-[10px] font-bold uppercase tracking-wide text-slate-600">Debts</div>
              <div className="space-y-1.5">
                {fin.debts.filter(d => d.balance > 0).map(d => {
                  const pct = d.original > 0
                    ? Math.round(((d.original - d.balance) / d.original) * 100)
                    : 0;
                  return (
                    <div key={d.id} className="rounded-md bg-white/[0.02] border border-white/5 px-3 py-2">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[12px] text-slate-300">{d.name}</span>
                        <span className="text-[12px] font-semibold text-red-400">{usd(d.balance)}</span>
                      </div>
                      <div className="h-1 rounded-full bg-white/5">
                        <div
                          style={{ width: `${pct}%`, backgroundColor: "#3ddc97" }}
                          className="h-full rounded-full transition-all"
                        />
                      </div>
                      <div className="mt-0.5 text-[9px] text-slate-600">{pct}% paid off</div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function LifePage() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Life</h1>
        <p className="text-[13px] text-signal-dim">Calendar · Goals · Tasks · Finance</p>
      </div>

      <div className="grid grid-cols-2 gap-5">
        {/* Left: Calendar + Tasks */}
        <div className="space-y-5">
          <CalendarSection />
          <TasksSection />
        </div>

        {/* Right: Goals + Finance */}
        <div className="space-y-5">
          <GoalsSection />
          <FinanceSection />
        </div>
      </div>
    </div>
  );
}
