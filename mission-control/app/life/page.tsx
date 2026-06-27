"use client";
import { useState, useEffect, useRef } from "react";

const FLASK = "";

// ═══════════════════════════════════════════════════════════════ TYPES ══════

interface Goal {
  id: string; title: string; category: string; progress: number;
  target_date: string; notes: string; status: "active" | "done";
  created_at: string; completed_at: string | null;
}
interface CalEvent {
  calendar: string; title: string; start: string; end: string; allDay: boolean;
}
interface Task {
  id: string; title: string; tag: string; due: string;
  completed: boolean; notes: string; created_at: string; completed_at: string | null;
}
interface FinanceData {
  accounts: { id: string; name: string; role: string; balance: number; updatedAt: string }[];
  debts:    { id: string; name: string; balance: number; original: number }[];
  total_assets: number; total_debt: number; net_worth: number;
}

// ═══════════════════════════════════════════════════════════ CONSTANTS ════════

const GOAL_CATS: Record<string, { label: string; color: string }> = {
  trading: { label: "Trading", color: "#3ddc97" },
  finance: { label: "Finance", color: "#4fc3f7" },
  health:  { label: "Health",  color: "#f2b84b" },
  life:    { label: "Life",    color: "#ab47bc" },
  dev:     { label: "Dev",     color: "#5c6bc0" },
  other:   { label: "Other",   color: "#5b6680" },
};

const TASK_TAGS: Record<string, { label: string; color: string }> = {
  urgent:  { label: "Urgent",  color: "#f44336" },
  trading: { label: "Trading", color: "#3ddc97" },
  dev:     { label: "Dev",     color: "#5c6bc0" },
  life:    { label: "Life",    color: "#ab47bc" },
  finance: { label: "Finance", color: "#4fc3f7" },
  other:   { label: "Other",   color: "#5b6680" },
};

const CAL_COLORS: Record<string, string> = {
  "Trading":               "#4fc3f7",
  "Work":                  "#f2b84b",
  "Scheduled Reminders":   "#ab47bc",
  "US Holidays":           "#5b6680",
  "Home":                  "#3ddc97",
  "Personal":              "#3ddc97",
  "Calendar":              "#4fc3f7",
};

const MONTHS_LONG  = ["January","February","March","April","May","June","July","August","September","October","November","December"];
const WDAYS        = ["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
const TASK_FILTERS = ["all","urgent","trading","dev","life","finance"] as const;

// ═══════════════════════════════════════════════════════════ HELPERS ══════════

function isoDay(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
}

function daysLeft(target: string): number {
  if (!target) return 0;
  const t = new Date(target + "T12:00:00");
  const n = new Date(); n.setHours(12,0,0,0);
  return Math.ceil((t.getTime() - n.getTime()) / 86_400_000);
}

function parseAppleDate(s: string): Date | null {
  if (!s) return null;
  const c = s.replace(/^[A-Za-z]+,\s*/,"").replace(" at "," ");
  const d = new Date(c);
  return isNaN(d.getTime()) ? null : d;
}

function calEventDay(start: string): string | null {
  const d = parseAppleDate(start);
  return d ? isoDay(d) : null;
}

function fmtTime(s: string): string {
  const d = parseAppleDate(s);
  if (!d) return "";
  const h = d.getHours(), m = String(d.getMinutes()).padStart(2,"0");
  return `${h%12||12}:${m} ${h>=12?"PM":"AM"}`;
}

function calColor(cal: string): string {
  return CAL_COLORS[cal] ?? "#5b6680";
}

function usd(n: number) {
  return new Intl.NumberFormat("en-US",{style:"currency",currency:"USD",maximumFractionDigits:0}).format(n);
}

function monthCells(year: number, month: number): (number|null)[] {
  const first = new Date(year, month, 1).getDay();
  const last  = new Date(year, month+1, 0).getDate();
  const cells: (number|null)[] = Array(first).fill(null);
  for (let d=1; d<=last; d++) cells.push(d);
  while (cells.length%7) cells.push(null);
  return cells;
}

// ═══════════════════════════════════════════════════════ GOALS STRIP ══════════

function GoalsStrip({ goals, onAdd, onUpdate, onDelete }: {
  goals: Goal[];
  onAdd(g: Partial<Goal>): Promise<void>;
  onUpdate(id: string, p: Partial<Goal>): Promise<void>;
  onDelete(id: string): Promise<void>;
}) {
  const [expanded, setExpanded] = useState<string|null>(null);
  const [showAdd,  setShowAdd]  = useState(false);
  const [form, setForm] = useState({ title:"", category:"life", target_date:"", progress:0 });
  const [saving, setSaving] = useState(false);

  const active = goals.filter(g => g.status === "active");
  const exp    = active.find(g => g.id === expanded) ?? null;
  const expCat = exp ? (GOAL_CATS[exp.category] ?? GOAL_CATS.other) : null;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.title.trim()) return;
    setSaving(true);
    await onAdd({ ...form, title: form.title.trim() });
    setForm({ title:"", category:"life", target_date:"", progress:0 });
    setShowAdd(false); setSaving(false);
  }

  const inp = "rounded border border-white/10 bg-white/[0.03] px-2 py-1 text-[12px] text-slate-200 placeholder-slate-600 focus:outline-none";

  return (
    <div className="panel p-3">
      {/* Chip row */}
      <div className="flex items-center gap-2 overflow-x-auto pb-0.5">
        <span className="shrink-0 text-[9px] font-bold uppercase tracking-[0.2em] text-slate-500 pr-1">
          GOALS
        </span>

        {active.length === 0 && !showAdd && (
          <span className="text-[12px] text-slate-700 italic">No active goals — add one →</span>
        )}

        {active.map(g => {
          const cat  = GOAL_CATS[g.category] ?? GOAL_CATS.other;
          const days = daysLeft(g.target_date);
          const isEx = expanded === g.id;
          return (
            <button
              key={g.id}
              onClick={() => { setExpanded(isEx ? null : g.id); setShowAdd(false); }}
              className={`shrink-0 flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[12px] transition ${
                isEx ? "border-white/20 bg-white/[0.06] text-white"
                     : "border-white/10 bg-white/[0.02] text-slate-300 hover:bg-white/[0.05]"
              }`}
            >
              <span style={{ backgroundColor: cat.color }} className="h-2 w-2 shrink-0 rounded-full" />
              <span className="max-w-[120px] truncate whitespace-nowrap">{g.title}</span>
              <span style={{ color: cat.color }} className="shrink-0 font-mono text-[10px]">
                {g.progress ?? 0}%
              </span>
              {g.target_date && (
                <span className={`shrink-0 text-[10px] ${days < 7 ? "text-red-400" : "text-slate-600"}`}>
                  {days > 0 ? `${days}d` : "due"}
                </span>
              )}
            </button>
          );
        })}

        <button
          onClick={() => { setShowAdd(s => !s); setExpanded(null); }}
          className="shrink-0 rounded-full border border-dashed border-white/10 px-2.5 py-1 text-[11px] text-slate-500 hover:border-white/20 hover:text-slate-300 transition"
        >
          + goal
        </button>
      </div>

      {/* Expanded editor */}
      {exp && expCat && (
        <div className="mt-2 flex flex-wrap items-center gap-3 border-t border-white/5 pt-2">
          <span style={{ color: expCat.color }} className="text-[12px] font-medium">{exp.title}</span>
          <div className="flex min-w-[180px] flex-1 items-center gap-2">
            <input
              type="range" min={0} max={100} value={exp.progress ?? 0}
              onChange={e => onUpdate(exp.id, { progress: +e.target.value })}
              style={{ accentColor: expCat.color }}
              className="flex-1"
            />
            <span className="w-8 text-[11px] text-slate-400">{exp.progress ?? 0}%</span>
          </div>
          {exp.target_date && (
            <span className="text-[10px] text-slate-500">Due {exp.target_date}</span>
          )}
          <button
            onClick={() => { onUpdate(exp.id, { status:"done", completed_at: new Date().toISOString() }); setExpanded(null); }}
            className="rounded border border-signal-live/20 bg-signal-live/5 px-2 py-0.5 text-[11px] text-signal-live hover:bg-signal-live/10 transition"
          >
            ✓ Done
          </button>
          <button onClick={() => onDelete(exp.id)} className="text-[11px] text-slate-600 hover:text-red-400 transition">
            remove
          </button>
          <button onClick={() => setExpanded(null)} className="text-[11px] text-slate-600 hover:text-slate-400 transition">✕</button>
        </div>
      )}

      {/* Add form */}
      {showAdd && (
        <form onSubmit={submit} className="mt-2 flex flex-wrap items-center gap-2 border-t border-white/5 pt-2">
          <input
            className={`${inp} w-36`} placeholder="Goal name *"
            value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} autoFocus
          />
          <select
            className={`${inp} bg-navy-900`} value={form.category}
            onChange={e => setForm(f => ({ ...f, category: e.target.value }))}
          >
            {Object.entries(GOAL_CATS).map(([k,v]) => <option key={k} value={k}>{v.label}</option>)}
          </select>
          <input type="date" className={inp} value={form.target_date}
            onChange={e => setForm(f => ({ ...f, target_date: e.target.value }))} />
          <button type="submit" disabled={saving || !form.title.trim()}
            className="rounded border border-signal-live/20 bg-signal-live/5 px-3 py-1 text-[12px] text-signal-live disabled:opacity-40 hover:bg-signal-live/10 transition"
          >
            {saving ? "…" : "Add"}
          </button>
          <button type="button" onClick={() => setShowAdd(false)}
            className="text-[11px] text-slate-600 hover:text-slate-400 transition">Cancel</button>
        </form>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════ MONTH CALENDAR ═══════════

function MonthCalendar({ year, month, events, onPrev, onNext, onDayClick, onAddClick }: {
  year: number; month: number; events: CalEvent[];
  onPrev(): void; onNext(): void;
  onDayClick(iso: string): void;
  onAddClick(): void;
}) {
  const cells = monthCells(year, month);
  const today = isoDay(new Date());

  const byDay = new Map<string, CalEvent[]>();
  for (const ev of events) {
    const d = calEventDay(ev.start);
    if (!d) continue;
    if (!byDay.has(d)) byDay.set(d, []);
    byDay.get(d)!.push(ev);
  }

  function cellIso(day: number) {
    return `${year}-${String(month+1).padStart(2,"0")}-${String(day).padStart(2,"0")}`;
  }

  return (
    <div className="panel flex flex-col p-4">
      {/* Header */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-1">
          <button onClick={onPrev}
            className="rounded p-1.5 text-slate-400 hover:bg-white/5 hover:text-white transition text-lg leading-none">
            ‹
          </button>
          <h2 className="min-w-[140px] text-center text-[13px] font-semibold text-slate-100">
            {MONTHS_LONG[month]} {year}
          </h2>
          <button onClick={onNext}
            className="rounded p-1.5 text-slate-400 hover:bg-white/5 hover:text-white transition text-lg leading-none">
            ›
          </button>
        </div>
        <button onClick={onAddClick}
          className="rounded-md border border-white/10 bg-white/[0.02] px-2 py-1 text-[11px] text-slate-400 hover:bg-white/[0.05] transition">
          + event
        </button>
      </div>

      {/* Weekday headers */}
      <div className="mb-1 grid grid-cols-7">
        {WDAYS.map(d => (
          <div key={d} className="py-1 text-center text-[10px] font-bold uppercase tracking-wide text-slate-600">{d}</div>
        ))}
      </div>

      {/* Day cells */}
      <div className="grid flex-1 grid-cols-7 gap-px overflow-hidden rounded-lg bg-white/[0.04]">
        {cells.map((day, i) => {
          if (day === null) {
            return <div key={i} className="min-h-[76px] bg-navy-900/50" />;
          }
          const iso       = cellIso(day);
          const isToday   = iso === today;
          const isPast    = iso < today;
          const dayEvents = byDay.get(iso) ?? [];

          return (
            <button
              key={i}
              onClick={() => onDayClick(iso)}
              className={`group relative flex min-h-[76px] flex-col p-1.5 text-left transition ${
                isToday  ? "bg-maroon-600/20 ring-1 ring-inset ring-maroon-500/40"
                : isPast ? "bg-navy-900/40 hover:bg-navy-800/50"
                         : "bg-navy-900/60 hover:bg-navy-800/60"
              }`}
            >
              <span className={`text-[11px] font-semibold leading-none ${
                isToday ? "text-maroon-300" : isPast ? "text-slate-600" : "text-slate-300"
              }`}>
                {day}
              </span>

              <div className="mt-1 min-w-0 flex-1 space-y-0.5 overflow-hidden">
                {dayEvents.slice(0,3).map((ev, j) => (
                  <div
                    key={j}
                    style={{
                      backgroundColor: calColor(ev.calendar) + "18",
                      borderLeftColor: calColor(ev.calendar),
                    }}
                    className="truncate rounded-sm border-l-2 py-0.5 pl-1 pr-0.5 text-[9px] leading-tight text-slate-300"
                  >
                    {ev.title}
                  </div>
                ))}
                {dayEvents.length > 3 && (
                  <div className="text-[9px] text-slate-600">+{dayEvents.length-3}</div>
                )}
              </div>

              <span className="absolute right-1 top-1 text-[10px] text-slate-700 opacity-0 transition group-hover:opacity-100">+</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════ DAY MODAL ════════════

function DayModal({ iso, events, onClose, onAddEvent }: {
  iso: string; events: CalEvent[];
  onClose(): void;
  onAddEvent(d: { type: string; title: string; time: string; endTime: string; date: string }): Promise<void>;
}) {
  const [tab,    setTab]   = useState<"event"|"reminder">("event");
  const [form,   setForm]  = useState({ title:"", time:"09:00", endTime:"10:00" });
  const [saving, setSaving] = useState(false);
  const [err,    setErr]   = useState("");
  const [done,   setDone]  = useState(false);

  const [y, m, d] = iso.split("-").map(Number);
  const dt = new Date(y, m-1, d);
  const label = `${WDAYS[dt.getDay()]}, ${MONTHS_LONG[m-1]} ${d}, ${y}`;

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.title.trim()) return;
    setSaving(true); setErr("");
    try {
      await onAddEvent({ type: tab, title: form.title.trim(), time: form.time, endTime: form.endTime, date: iso });
      setDone(true);
      setForm({ title:"", time:"09:00", endTime:"10:00" });
      setTimeout(() => setDone(false), 2000);
    } catch (ex: unknown) {
      setErr(ex instanceof Error ? ex.message : "Failed");
    }
    setSaving(false);
  }

  const inp = "w-full rounded border border-white/10 bg-white/[0.03] px-2 py-1.5 text-[12px] text-slate-200 placeholder-slate-600 focus:outline-none";

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center" onClick={onClose}>
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
      <div
        className="relative z-50 w-[420px] max-h-[85vh] overflow-y-auto rounded-xl border border-white/10 bg-navy-900 p-5 shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="mb-4 flex items-start justify-between">
          <div>
            <p className="text-[9px] font-bold uppercase tracking-[0.18em] text-signal-dim">Calendar</p>
            <h2 className="text-base font-semibold text-slate-100">{label}</h2>
          </div>
          <button onClick={onClose} className="mt-0.5 text-slate-500 hover:text-white transition">✕</button>
        </div>

        {/* Events */}
        {events.length > 0 ? (
          <div className="mb-4 space-y-1">
            {events.map((ev, i) => (
              <div key={i} className="flex items-center gap-2 rounded-md bg-white/[0.03] px-3 py-2">
                <span style={{ backgroundColor: calColor(ev.calendar) }} className="h-2 w-2 shrink-0 rounded-full" />
                <span className="flex-1 text-[12px] text-slate-200">{ev.title}</span>
                <span className="shrink-0 text-[10px] text-slate-500">
                  {ev.allDay ? "All day" : fmtTime(ev.start)}
                </span>
              </div>
            ))}
          </div>
        ) : (
          <p className="mb-4 text-[12px] italic text-slate-600">No events this day.</p>
        )}

        {/* Add form */}
        <div className="border-t border-white/5 pt-4">
          <div className="mb-3 flex gap-0.5">
            {(["event","reminder"] as const).map(t => (
              <button
                key={t} onClick={() => setTab(t)}
                className={`rounded px-3 py-1 text-[11px] uppercase tracking-wide transition ${
                  tab===t ? "bg-maroon-600/30 text-maroon-300" : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {t === "event" ? "Add Event" : "Add Reminder"}
              </button>
            ))}
          </div>

          <form onSubmit={submit} className="space-y-2">
            <input
              className={inp}
              placeholder={tab === "event" ? "Event title *" : "Reminder title *"}
              value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))}
              autoFocus
            />
            <div className="flex gap-2">
              <div className="flex-1">
                <p className="mb-1 text-[10px] text-slate-600">{tab === "event" ? "Start" : "Time"}</p>
                <input type="time" className={inp} value={form.time}
                  onChange={e => setForm(f => ({ ...f, time: e.target.value }))} />
              </div>
              {tab === "event" && (
                <div className="flex-1">
                  <p className="mb-1 text-[10px] text-slate-600">End</p>
                  <input type="time" className={inp} value={form.endTime}
                    onChange={e => setForm(f => ({ ...f, endTime: e.target.value }))} />
                </div>
              )}
            </div>
            {err  && <p className="text-[11px] text-red-400">{err}</p>}
            {done && <p className="text-[11px] text-signal-live">Created ✓</p>}
            <button
              type="submit" disabled={saving || !form.title.trim()}
              className="w-full rounded-md border border-maroon-500/30 bg-maroon-600/20 py-2 text-[12px] text-maroon-300 transition hover:bg-maroon-600/30 disabled:opacity-40"
            >
              {saving ? "Creating…" : tab === "event" ? "Create Event in Calendar" : "Create Reminder"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════ TASKS PANEL ══════════

function TasksPanel({ tasks, onAdd, onUpdate, onDelete }: {
  tasks: Task[];
  onAdd(t: Partial<Task>): Promise<void>;
  onUpdate(id: string, p: Partial<Task>): Promise<void>;
  onDelete(id: string): Promise<void>;
}) {
  const [filter,   setFilter]   = useState<string>("all");
  const [expanded, setExpanded] = useState<string|null>(null);
  const [showDone, setShowDone] = useState(false);
  const [addTitle, setAddTitle] = useState("");
  const [addTag,   setAddTag]   = useState("other");
  const [addDue,   setAddDue]   = useState("");
  const [saving,   setSaving]   = useState(false);

  const today  = isoDay(new Date());
  const active = tasks.filter(t => !t.completed);
  const done   = tasks.filter(t =>  t.completed);
  const shown  = filter === "all" ? active : active.filter(t => t.tag === filter);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!addTitle.trim()) return;
    setSaving(true);
    await onAdd({ title: addTitle.trim(), tag: addTag, due: addDue });
    setAddTitle(""); setAddTag("other"); setAddDue("");
    setSaving(false);
  }

  const inp = "rounded border border-white/10 bg-white/[0.03] px-2 py-1 text-[12px] text-slate-200 placeholder-slate-600 focus:outline-none";

  return (
    <div className="panel flex flex-col p-4">
      <div className="mb-2 flex items-center justify-between">
        <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-300">Tasks</div>
        <span className="text-[10px] text-slate-600">{active.length} open</span>
      </div>

      {/* Filter tabs */}
      <div className="mb-2 flex flex-wrap gap-0.5">
        {TASK_FILTERS.map(f => {
          const meta = TASK_TAGS[f as keyof typeof TASK_TAGS];
          const isActive = filter === f;
          return (
            <button key={f} onClick={() => setFilter(f)}
              className={`rounded px-2 py-0.5 text-[10px] uppercase tracking-wide transition font-medium ${
                isActive ? "bg-white/10" : "text-slate-600 hover:text-slate-300"
              }`}
              style={isActive && meta ? { color: meta.color } : undefined}
            >
              {f}
            </button>
          );
        })}
      </div>

      {/* Task list */}
      <div className="max-h-[200px] min-h-0 flex-1 space-y-0.5 overflow-y-auto pr-1">
        {shown.length === 0 ? (
          <p className="pt-2 text-[12px] italic text-slate-700">
            {filter === "all" ? "No tasks — add one below." : `No ${filter} tasks.`}
          </p>
        ) : (
          shown.map(t => {
            const tag  = TASK_TAGS[t.tag] ?? TASK_TAGS.other;
            const isEx = expanded === t.id;
            const over = t.due && t.due < today;
            return (
              <div key={t.id}>
                <div
                  className={`flex cursor-pointer items-center gap-2 rounded-md px-2 py-1.5 transition ${
                    isEx ? "bg-white/[0.05]" : "hover:bg-white/[0.03]"
                  }`}
                  onClick={() => setExpanded(isEx ? null : t.id)}
                >
                  <button
                    onClick={e => {
                      e.stopPropagation();
                      onUpdate(t.id, { completed: true, completed_at: new Date().toISOString() });
                    }}
                    className="h-4 w-4 shrink-0 rounded-full border border-slate-600 transition hover:border-signal-live"
                  />
                  <span className="flex-1 truncate text-[12px] text-slate-200">{t.title}</span>
                  <span
                    style={{ backgroundColor: tag.color+"22", color: tag.color, borderColor: tag.color+"44" }}
                    className="shrink-0 rounded-full border px-1.5 text-[9px] font-bold uppercase tracking-wide"
                  >
                    {tag.label}
                  </span>
                  {t.due && (
                    <span className={`shrink-0 text-[10px] ${over ? "text-red-400" : "text-slate-600"}`}>
                      {t.due}
                    </span>
                  )}
                </div>
                {isEx && (
                  <div className="mb-1 ml-6 flex items-center gap-3 text-[11px]">
                    {t.notes && <span className="text-slate-500">{t.notes}</span>}
                    <button onClick={() => onDelete(t.id)}
                      className="text-slate-700 transition hover:text-red-400">remove</button>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Completed section */}
      {done.length > 0 && (
        <div className="mt-1 border-t border-white/5 pt-1">
          <button onClick={() => setShowDone(s => !s)}
            className="text-[10px] text-slate-700 hover:text-slate-500 transition">
            {showDone ? "▾" : "▸"} {done.length} completed
          </button>
          {showDone && (
            <div className="mt-1 space-y-0.5">
              {done.slice(0,5).map(t => (
                <div key={t.id} className="flex items-center gap-2 px-2 py-1 opacity-50">
                  <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-signal-live/40 text-[9px] text-signal-live">✓</span>
                  <span className="text-[11px] line-through text-slate-500">{t.title}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Add task */}
      <form onSubmit={handleAdd} className="mt-3 flex flex-wrap gap-1.5 border-t border-white/5 pt-3">
        <input className={`${inp} min-w-0 flex-1`} placeholder="New task…"
          value={addTitle} onChange={e => setAddTitle(e.target.value)} />
        <select className={`${inp} w-20 bg-navy-900`} value={addTag}
          onChange={e => setAddTag(e.target.value)}>
          {Object.entries(TASK_TAGS).map(([k,v]) => <option key={k} value={k}>{v.label}</option>)}
        </select>
        <input type="date" className={`${inp} w-28`} value={addDue}
          onChange={e => setAddDue(e.target.value)} />
        <button type="submit" disabled={saving || !addTitle.trim()}
          className="rounded border border-white/10 bg-white/[0.03] px-2 py-1 text-[11px] text-slate-300 transition hover:bg-white/[0.06] disabled:opacity-40">
          {saving ? "…" : "Add"}
        </button>
      </form>
    </div>
  );
}

// ═══════════════════════════════════════════════════ FINANCE SNAPSHOT ═════════

function EditField({ value, onSave }: { value: number; onSave(v: number): void }) {
  const [editing, setEditing] = useState(false);
  const [val,     setVal]     = useState(String(value));
  const ref = useRef<HTMLInputElement>(null);

  useEffect(() => { if (editing) ref.current?.select(); }, [editing]);
  useEffect(() => { if (!editing) setVal(String(value)); }, [value, editing]);

  function save() {
    const n = parseFloat(val);
    if (!isNaN(n) && n !== value) onSave(n);
    setEditing(false);
  }

  if (editing) {
    return (
      <input
        ref={ref}
        className="w-24 rounded border border-maroon-500/40 bg-maroon-600/10 px-1 py-0.5 text-right text-[12px] text-slate-100 focus:outline-none"
        value={val}
        onChange={e => setVal(e.target.value)}
        onBlur={save}
        onKeyDown={e => { if (e.key==="Enter") save(); if (e.key==="Escape") setEditing(false); }}
      />
    );
  }
  return (
    <button
      onClick={() => { setVal(String(value)); setEditing(true); }}
      className="group flex items-center gap-1 rounded px-1 py-0.5 transition hover:bg-white/[0.04]"
    >
      <span className="text-[12px] font-semibold text-slate-200">{usd(value)}</span>
      <span className="text-[9px] text-slate-700 opacity-0 transition group-hover:opacity-100">✎</span>
    </button>
  );
}

function FinanceSnapshot({ finance, onUpdateAccount, onUpdateDebt }: {
  finance: FinanceData | null;
  onUpdateAccount(id: string, balance: number): void;
  onUpdateDebt(id: string, balance: number): void;
}) {
  if (!finance) {
    return (
      <div className="panel p-4">
        <div className="mb-2 text-[11px] font-bold uppercase tracking-[0.18em] text-slate-300">Finance</div>
        <p className="text-[12px] text-slate-600">Flask offline</p>
      </div>
    );
  }

  const nwColor = finance.net_worth >= 0 ? "#3ddc97" : "#f44336";

  return (
    <div className="panel flex flex-col gap-3 p-4">
      <div className="flex items-center justify-between">
        <div className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-300">Finance</div>
        <a href="/finance" className="text-[10px] text-slate-600 transition hover:text-slate-400">
          View full →
        </a>
      </div>

      {/* Net worth */}
      <div className="rounded-lg border border-white/5 bg-white/[0.02] p-3">
        <div className="mb-0.5 text-[10px] uppercase tracking-wide text-slate-600">Net Worth</div>
        <div style={{ color: nwColor }} className="text-lg font-bold">{usd(finance.net_worth)}</div>
        <div className="mt-1 flex gap-3 text-[10px] text-slate-500">
          <span>Assets {usd(finance.total_assets)}</span>
          <span>·</span>
          <span>Debt {usd(finance.total_debt)}</span>
        </div>
      </div>

      {/* Accounts */}
      {finance.accounts.length > 0 && (
        <div>
          <div className="mb-1 text-[10px] font-bold uppercase tracking-wide text-slate-600">Accounts</div>
          <div className="space-y-0.5">
            {finance.accounts.map(a => (
              <div key={a.id}
                className="flex items-center gap-2 rounded px-2 py-1 transition hover:bg-white/[0.02]">
                <span className="flex-1 text-[11px] text-slate-400">{a.name}</span>
                <span className="text-[10px] text-slate-600">{a.role}</span>
                <EditField value={a.balance} onSave={v => onUpdateAccount(a.id, v)} />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Debts */}
      {finance.debts.filter(d => d.balance > 0).length > 0 && (
        <div>
          <div className="mb-1 text-[10px] font-bold uppercase tracking-wide text-slate-600">Debts</div>
          <div className="space-y-1.5">
            {finance.debts.filter(d => d.balance > 0).map(d => {
              const pct = d.original > 0
                ? Math.round(((d.original - d.balance) / d.original) * 100)
                : 0;
              return (
                <div key={d.id} className="rounded-md border border-white/5 bg-white/[0.02] px-2 py-1.5">
                  <div className="mb-1 flex items-center justify-between">
                    <span className="text-[11px] text-slate-400">{d.name}</span>
                    <EditField value={d.balance} onSave={v => onUpdateDebt(d.id, v)} />
                  </div>
                  <div className="h-1 rounded-full bg-white/5">
                    <div style={{ width:`${pct}%`, backgroundColor:"#3ddc97" }} className="h-full rounded-full" />
                  </div>
                  <div className="mt-0.5 text-[9px] text-slate-700">{pct}% paid off</div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// ═══════════════════════════════════════════════════════════ LIFE PAGE ════════

export default function LifePage() {
  const now = new Date();
  const [year,  setYear]  = useState(now.getFullYear());
  const [month, setMonth] = useState(now.getMonth());

  const [goals,   setGoals]   = useState<Goal[]>([]);
  const [events,  setEvents]  = useState<CalEvent[]>([]);
  const [tasks,   setTasks]   = useState<Task[]>([]);
  const [finance, setFinance] = useState<FinanceData|null>(null);
  const [selDay,  setSelDay]  = useState<string|null>(null);

  useEffect(() => {
    let ok = true;
    (async () => {
      const [g, e, t, f] = await Promise.allSettled([
        fetch(`${FLASK}/api/life/goals`).then(r => r.json()),
        fetch(`${FLASK}/api/life/calendar`).then(r => r.json()),
        fetch(`${FLASK}/api/life/tasks`).then(r => r.json()),
        fetch(`${FLASK}/api/life/finance`).then(r => r.json()),
      ]);
      if (!ok) return;
      if (g.status==="fulfilled") setGoals(Array.isArray(g.value) ? g.value : []);
      if (e.status==="fulfilled") setEvents(e.value?.events ?? []);
      if (t.status==="fulfilled") setTasks(Array.isArray(t.value) ? t.value : []);
      if (f.status==="fulfilled") setFinance(f.value);
    })();
    return () => { ok = false; };
  }, []);

  // ── Goals
  async function addGoal(g: Partial<Goal>) {
    const r = await fetch(`${FLASK}/api/life/goals`, {
      method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(g),
    });
    const d = await r.json();
    if (d.success) setGoals(p => [...p, d.goal]);
  }
  async function updateGoal(id: string, patch: Partial<Goal>) {
    setGoals(p => p.map(g => g.id===id ? {...g,...patch} : g));
    await fetch(`${FLASK}/api/life/goals/${id}`, {
      method:"PATCH", headers:{"Content-Type":"application/json"}, body:JSON.stringify(patch),
    });
  }
  async function deleteGoal(id: string) {
    setGoals(p => p.filter(g => g.id!==id));
    await fetch(`${FLASK}/api/life/goals/${id}`, { method:"DELETE" });
  }

  // ── Tasks
  async function addTask(t: Partial<Task>) {
    const r = await fetch(`${FLASK}/api/life/tasks`, {
      method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(t),
    });
    const d = await r.json();
    if (d.success) setTasks(p => [...p, d.task]);
  }
  async function updateTask(id: string, patch: Partial<Task>) {
    setTasks(p => p.map(t => t.id===id ? {...t,...patch} : t));
    await fetch(`${FLASK}/api/life/tasks/${encodeURIComponent(id)}`, {
      method:"PATCH", headers:{"Content-Type":"application/json"}, body:JSON.stringify(patch),
    });
  }
  async function deleteTask(id: string) {
    setTasks(p => p.filter(t => t.id!==id));
    await fetch(`${FLASK}/api/life/tasks/${encodeURIComponent(id)}`, { method:"DELETE" });
  }

  // ── Calendar
  async function addCalEvent(data: { type:string; title:string; time:string; endTime:string; date:string }) {
    const r = await fetch(`${FLASK}/api/life/calendar/event`, {
      method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(data),
    });
    const d = await r.json();
    if (!d.success) throw new Error(d.error || "Failed");
    const fresh = await fetch(`${FLASK}/api/life/calendar`).then(r => r.json());
    setEvents(fresh.events ?? []);
  }

  // ── Finance
  async function updateAccount(id: string, balance: number) {
    await fetch(`${FLASK}/api/finance/accounts/${id}`, {
      method:"PATCH", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ balance }),
    });
    const fin = await fetch(`${FLASK}/api/life/finance`).then(r => r.json());
    setFinance(fin);
  }
  async function updateDebt(id: string, balance: number) {
    await fetch(`${FLASK}/api/finance/debts/${id}`, {
      method:"PATCH", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ balance }),
    });
    const fin = await fetch(`${FLASK}/api/life/finance`).then(r => r.json());
    setFinance(fin);
  }

  function prevMonth() { month===0 ? (setYear(y=>y-1),setMonth(11)) : setMonth(m=>m-1); }
  function nextMonth() { month===11 ? (setYear(y=>y+1),setMonth(0)) : setMonth(m=>m+1); }

  const dayEvents = selDay ? events.filter(ev => calEventDay(ev.start) === selDay) : [];

  return (
    <div className="flex flex-col gap-4" suppressHydrationWarning>
      {/* Goals strip — full width */}
      <GoalsStrip goals={goals} onAdd={addGoal} onUpdate={updateGoal} onDelete={deleteGoal} />

      {/* 2-col grid: calendar left, tasks+finance right */}
      <div className="grid grid-cols-[1fr_320px] gap-4 items-start">
        <MonthCalendar
          year={year} month={month} events={events}
          onPrev={prevMonth} onNext={nextMonth}
          onDayClick={setSelDay}
          onAddClick={() => setSelDay(isoDay(new Date()))}
        />

        <div className="flex flex-col gap-4">
          <TasksPanel tasks={tasks} onAdd={addTask} onUpdate={updateTask} onDelete={deleteTask} />
          <FinanceSnapshot finance={finance} onUpdateAccount={updateAccount} onUpdateDebt={updateDebt} />
        </div>
      </div>

      {/* Day modal */}
      {selDay && (
        <DayModal
          iso={selDay}
          events={dayEvents}
          onClose={() => setSelDay(null)}
          onAddEvent={addCalEvent}
        />
      )}
    </div>
  );
}
