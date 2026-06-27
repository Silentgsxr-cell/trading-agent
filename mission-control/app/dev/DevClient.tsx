"use client";

import { useState, useEffect } from "react";
import {
  Ticket,
  TicketDB,
  TicketPriority,
  TicketComplexity,
  COMPLEXITY_COLOR,
  PRIORITY_COLOR,
  PRIORITY_ORDER,
} from "@/lib/ticket-types";
import { SuggestionBoard } from "../suggestions/SuggestionBoard";

// ── Helpers ───────────────────────────────────────────────────────────────────

const STATUS_LABEL: Record<string, string> = {
  open:         "OPEN",
  in_progress:  "IN PROGRESS",
  done:         "DONE",
  failed:       "FAILED",
  needs_review: "NEEDS REVIEW",
};

const STATUS_COLOR: Record<string, string> = {
  open:         "rgba(0,230,118,0.15)",
  in_progress:  "rgba(33,150,243,0.15)",
  done:         "rgba(0,230,118,0.15)",
  failed:       "rgba(244,67,54,0.15)",
  needs_review: "rgba(255,193,7,0.15)",
};

const STATUS_TEXT: Record<string, string> = {
  open:         "#00e676",
  in_progress:  "#2196f3",
  done:         "#00e676",
  failed:       "#f44336",
  needs_review: "#ffc107",
};

function fmt(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
    });
  } catch { return iso; }
}

function elapsed(start: string | null | undefined, end: string | null | undefined): string {
  if (!start || !end) return "—";
  const ms = new Date(end).getTime() - new Date(start).getTime();
  if (ms < 0) return "—";
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m ${s % 60}s`;
  return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;
}

// ── Shared UI atoms ───────────────────────────────────────────────────────────

function Chip({
  label, bg, color,
}: { label: string; bg: string; color: string }) {
  return (
    <span
      style={{ background: bg, color, border: `1px solid ${color}30` }}
      className="inline-block rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest"
    >
      {label}
    </span>
  );
}

function CopyChip({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(value); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
      className="rounded bg-white/5 px-2 py-0.5 font-mono text-xs text-slate-300 transition hover:bg-white/10"
    >
      {copied ? "copied!" : value}
    </button>
  );
}

// ── Ticket queue card ─────────────────────────────────────────────────────────

function TicketCard({
  ticket,
  selected,
  onClick,
}: { ticket: Ticket; selected: boolean; onClick: () => void }) {
  const complexity = ticket.complexity as TicketComplexity;
  const borderColor = COMPLEXITY_COLOR[complexity] ?? "#64748b";
  const needsReview = ticket.status === "needs_review";

  return (
    <button
      onClick={onClick}
      className="w-full text-left"
    >
      <div
        style={{
          borderLeft: `3px solid ${borderColor}`,
          background: selected ? "rgba(255,255,255,0.05)" : "rgba(255,255,255,0.02)",
          boxShadow: needsReview ? `0 0 0 1px #ffc10770, 0 0 12px #ffc10720` : undefined,
          animation: needsReview ? "pulse-border 2s ease-in-out infinite" : undefined,
        }}
        className="relative rounded-r-lg border border-white/5 p-3 transition hover:bg-white/[0.04]"
      >
        {/* Done checkmark */}
        {ticket.status === "done" && (
          <span className="absolute right-3 top-2 text-base text-green-400">✓</span>
        )}

        {/* Top row */}
        <div className="flex flex-wrap items-center gap-1.5 pr-5">
          <span className="font-mono text-[11px] font-bold text-slate-400">
            {ticket.id}
          </span>
          <Chip
            label={ticket.priority}
            bg={`${PRIORITY_COLOR[ticket.priority as TicketPriority]}20`}
            color={PRIORITY_COLOR[ticket.priority as TicketPriority] ?? "#64748b"}
          />
          <Chip
            label={STATUS_LABEL[ticket.status] ?? ticket.status}
            bg={STATUS_COLOR[ticket.status]}
            color={STATUS_TEXT[ticket.status]}
          />
          <span
            style={{ color: borderColor }}
            className="text-[10px] uppercase tracking-widest"
          >
            {ticket.complexity}
          </span>
        </div>

        {/* Title */}
        <p className="mt-1.5 text-sm font-medium text-slate-200 leading-snug">
          {ticket.title}
        </p>

        {/* Description muted */}
        {ticket.description && (
          <p className="mt-1 text-[12px] text-slate-500 line-clamp-2 leading-snug">
            {ticket.description}
          </p>
        )}

        {/* Bottom row */}
        <div className="mt-2 flex items-center gap-3 text-[11px] text-slate-600">
          <span>{fmt(ticket.created_at)}</span>
          {ticket.status === "done" && (
            <span className="text-green-600">
              {(ticket.files_modified?.length ?? 0) + (ticket.files_created?.length ?? 0)} files changed
            </span>
          )}
          {needsReview && (
            <span className="text-amber-400 font-medium">Awaiting approval</span>
          )}
        </div>
      </div>
    </button>
  );
}

// ── Ticket detail view ────────────────────────────────────────────────────────

function TicketDetail({ ticket, onClose }: { ticket: Ticket; onClose: () => void }) {
  const [tab, setTab] = useState<"modified" | "created" | "read">("modified");
  const [showLog, setShowLog] = useState(false);

  const complexity = ticket.complexity as TicketComplexity;
  const borderColor = COMPLEXITY_COLOR[complexity] ?? "#64748b";
  const duration = elapsed(ticket.started_at, ticket.completed_at);
  const allFiles = {
    modified: ticket.files_modified ?? [],
    created:  ticket.files_created ?? [],
    read:     ticket.files_read ?? [],
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-xs text-slate-500">{ticket.id}</span>
            <Chip
              label={STATUS_LABEL[ticket.status] ?? ticket.status}
              bg={STATUS_COLOR[ticket.status]}
              color={STATUS_TEXT[ticket.status]}
            />
            <span style={{ color: borderColor }} className="text-[10px] uppercase tracking-widest">
              {ticket.complexity}
            </span>
          </div>
          <h2 className="mt-1 text-base font-semibold text-slate-100 leading-snug">{ticket.title}</h2>
        </div>
        <button onClick={onClose} className="mt-1 shrink-0 text-slate-500 hover:text-slate-300 text-sm">✕</button>
      </div>

      {/* Done: big checkmark + summary */}
      {ticket.status === "done" && (
        <div className="rounded-lg border border-green-500/20 bg-green-500/5 p-4 text-center">
          <div className="text-3xl text-green-400">✓</div>
          <p className="mt-2 text-sm text-slate-300 leading-relaxed">
            {ticket.agent_summary || "Ticket completed successfully."}
          </p>
        </div>
      )}

      {/* Failed: red box */}
      {ticket.status === "failed" && (
        <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 text-sm text-red-300">
          This ticket failed during execution. See the execution log for details.
        </div>
      )}

      {/* Needs review */}
      {ticket.status === "needs_review" && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3 text-sm text-amber-300">
          Complex ticket — awaiting your approval. Send <code className="bg-white/10 px-1 rounded">!approve {ticket.id}</code> in Discord.
        </div>
      )}

      {/* Stats row */}
      <div className="grid grid-cols-4 gap-2">
        {[
          { label: "Files read",     value: ticket.files_read?.length ?? 0 },
          { label: "Modified",       value: ticket.files_modified?.length ?? 0 },
          { label: "Created",        value: ticket.files_created?.length ?? 0 },
          { label: "Time",           value: duration },
        ].map(({ label, value }) => (
          <div key={label} className="rounded-md bg-white/[0.03] border border-white/5 p-2 text-center">
            <div className="text-lg font-bold text-slate-100">{value}</div>
            <div className="text-[10px] uppercase tracking-wide text-slate-500">{label}</div>
          </div>
        ))}
      </div>

      {/* Commit hash */}
      {ticket.git_commit_hash && (
        <div className="flex items-center gap-2">
          <span className="text-[11px] uppercase tracking-widest text-slate-600">Commit</span>
          <CopyChip value={ticket.git_commit_hash} />
        </div>
      )}

      {/* File tabs */}
      {(allFiles.modified.length + allFiles.created.length + allFiles.read.length) > 0 && (
        <div>
          <div className="flex border-b border-white/5 mb-3">
            {(["modified", "created", "read"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-3 py-1.5 text-xs uppercase tracking-wide transition ${
                  tab === t
                    ? "border-b-2 border-green-400 text-green-400"
                    : "text-slate-500 hover:text-slate-300"
                }`}
              >
                {t} ({allFiles[t].length})
              </button>
            ))}
          </div>
          <div className="space-y-1">
            {allFiles[tab].length === 0 ? (
              <p className="text-xs text-slate-600 italic">None</p>
            ) : (
              allFiles[tab].map((f) => (
                <div key={f} className="font-mono text-xs text-slate-400 bg-white/[0.02] rounded px-2 py-1">
                  {f}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Description / spec */}
      <div className="space-y-2 text-sm">
        {ticket.description && (
          <div>
            <p className="text-[10px] uppercase tracking-wide text-slate-600 mb-1">Description</p>
            <p className="text-slate-400 leading-relaxed">{ticket.description}</p>
          </div>
        )}
        {ticket.what_done_looks_like && (
          <div>
            <p className="text-[10px] uppercase tracking-wide text-slate-600 mb-1">Done when</p>
            <p className="text-slate-400 leading-relaxed">{ticket.what_done_looks_like}</p>
          </div>
        )}
      </div>

      {/* Execution log */}
      {(ticket.log?.length ?? 0) > 0 && (
        <div>
          <button
            onClick={() => setShowLog(!showLog)}
            className="text-[11px] text-slate-500 hover:text-slate-300 uppercase tracking-wide"
          >
            {showLog ? "▾" : "▸"} Execution Log ({ticket.log!.length} entries)
          </button>
          {showLog && (
            <div className="mt-2 max-h-48 overflow-y-auto rounded-md bg-black/30 p-3 font-mono text-[11px] text-slate-400 space-y-0.5">
              {ticket.log!.map((line, i) => (
                <div key={i} className="leading-snug">{line}</div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Revert button (done only) */}
      {ticket.status === "done" && ticket.git_commit_hash && (
        <div className="pt-1">
          <p className="text-[11px] text-slate-600">
            To revert: send <code className="bg-white/10 px-1 rounded">!revert {ticket.id}</code> in Discord
          </p>
        </div>
      )}
    </div>
  );
}

// ── New ticket form ───────────────────────────────────────────────────────────

const GLOBAL_BLOCKED = [
  "agents/", "config/", "tests/", ".env",
  "utils/watchdog.py", "utils/state_manager.py",
  "utils/journal_writer.py", "utils/event_log.py",
];
const DEFAULT_ALLOWED = [
  "dashboard/", "utils/", "mission-control/app/",
  "mission-control/components/", "mission-control/lib/",
];

function NewTicketForm({ onSubmit, onCancel }: {
  onSubmit: (t: Partial<Ticket>) => Promise<void>;
  onCancel: () => void;
}) {
  const [title, setTitle]                   = useState("");
  const [description, setDescription]       = useState("");
  const [whatToComplete, setWhatToComplete]  = useState("");
  const [whatDone, setWhatDone]             = useState("");
  const [connectors, setConnectors]         = useState("");
  const [restrictions, setRestrictions]    = useState("Do not modify agents/ or config/");
  const [priority, setPriority]            = useState<TicketPriority>("medium");
  const [complexity, setComplexity]        = useState<TicketComplexity>("simple");
  const [allowedPaths, setAllowedPaths]    = useState(DEFAULT_ALLOWED.join("\n"));
  const [submitting, setSubmitting]        = useState(false);
  const [error, setError] = useState("");

  const complexColors: Record<TicketComplexity, string> = {
    simple:   "#00e676",
    moderate: "#ffc107",
    complex:  "#f44336",
  };

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!title.trim()) { setError("Title is required."); return; }
    setError("");
    setSubmitting(true);
    try {
      await onSubmit({
        title:              title.trim(),
        description:        description.trim(),
        what_to_complete:   whatToComplete.trim(),
        what_done_looks_like: whatDone.trim(),
        connectors_needed:  connectors.split(",").map(s => s.trim()).filter(Boolean),
        restrictions:       restrictions.split("\n").map(s => s.trim()).filter(Boolean),
        priority,
        complexity,
        complexity_color:   complexColors[complexity],
        allowed_paths:      allowedPaths.split("\n").map(s => s.trim()).filter(Boolean),
        blocked_paths:      GLOBAL_BLOCKED,
        status:             "open",
        approval_gate:      "auto",
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create ticket.");
      setSubmitting(false);
    }
  }

  const inputCls = "w-full rounded-md border border-white/10 bg-white/[0.03] px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:border-white/20 focus:outline-none";
  const labelCls = "text-[10px] uppercase tracking-wide text-slate-500 mb-1 block";

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-slate-100">New Ticket</h2>
        <button type="button" onClick={onCancel} className="text-slate-500 hover:text-slate-300 text-sm">✕</button>
      </div>

      {error && (
        <div className="rounded-md bg-red-500/10 border border-red-500/20 px-3 py-2 text-sm text-red-300">
          {error}
        </div>
      )}

      <div>
        <label className={labelCls}>Ticket Title *</label>
        <input className={inputCls} value={title} onChange={e => setTitle(e.target.value)}
          placeholder="e.g. Add dark mode toggle to cockpit" />
      </div>

      <div>
        <label className={labelCls}>What is the task looking to complete?</label>
        <textarea rows={2} className={inputCls} value={whatToComplete}
          onChange={e => setWhatToComplete(e.target.value)}
          placeholder="Describe what needs to be built or changed" />
      </div>

      <div>
        <label className={labelCls}>What does done look like?</label>
        <textarea rows={2} className={inputCls} value={whatDone}
          onChange={e => setWhatDone(e.target.value)}
          placeholder="Describe the visible result when complete" />
      </div>

      <div>
        <label className={labelCls}>Description (optional, more context)</label>
        <textarea rows={2} className={inputCls} value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder="Additional background or motivation" />
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={labelCls}>Priority</label>
          <select className={inputCls} value={priority} onChange={e => setPriority(e.target.value as TicketPriority)}>
            {(["critical", "high", "medium", "low"] as TicketPriority[]).map(p => (
              <option key={p} value={p} style={{ color: PRIORITY_COLOR[p] }}>{p}</option>
            ))}
          </select>
        </div>
        <div>
          <label className={labelCls}>Complexity</label>
          <select className={inputCls} value={complexity}
            style={{ borderColor: `${complexColors[complexity]}50` }}
            onChange={e => setComplexity(e.target.value as TicketComplexity)}>
            <option value="simple" style={{ color: "#00e676" }}>simple</option>
            <option value="moderate" style={{ color: "#ffc107" }}>moderate</option>
            <option value="complex" style={{ color: "#f44336" }}>complex — requires approval</option>
          </select>
        </div>
      </div>

      <div>
        <label className={labelCls}>Allowed file paths (one per line)</label>
        <textarea rows={4} className={`${inputCls} font-mono text-xs`} value={allowedPaths}
          onChange={e => setAllowedPaths(e.target.value)} />
      </div>

      <div>
        <label className={labelCls}>Restrictions (one per line)</label>
        <textarea rows={2} className={inputCls} value={restrictions}
          onChange={e => setRestrictions(e.target.value)} />
      </div>

      <div>
        <label className={labelCls}>Connectors needed (comma-separated, optional)</label>
        <input className={inputCls} value={connectors} onChange={e => setConnectors(e.target.value)}
          placeholder="e.g. Discord webhook, yfinance" />
      </div>

      <div className="pt-1">
        <p className="text-[11px] text-slate-600 mb-3">
          Blocked paths (always enforced): {GLOBAL_BLOCKED.join(", ")}
        </p>
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-green-500/15 border border-green-500/30 py-2 text-sm font-medium text-green-400 transition hover:bg-green-500/20 disabled:opacity-50"
        >
          {submitting ? "Adding to queue…" : "Add to Queue"}
        </button>
      </div>
    </form>
  );
}

// ── Tab button ────────────────────────────────────────────────────────────────

function TabBtn({
  active, onClick, children,
}: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-4 py-2 text-[12px] font-medium uppercase tracking-wide border-b-2 transition ${
        active
          ? "border-maroon-400 text-white"
          : "border-transparent text-slate-500 hover:text-slate-300"
      }`}
    >
      {children}
    </button>
  );
}

// ── Main client component ─────────────────────────────────────────────────────

export function DevClient({ db }: { db: TicketDB }) {
  const [section, setSection] = useState<"tickets" | "suggestions">("tickets");
  const [unreviewedCount, setUnreviewedCount] = useState(0);
  const [selected, setSelected] = useState<Ticket | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [tickets, setTickets] = useState<Ticket[]>(db.tickets);
  const [paused, setPaused] = useState(db.paused);
  const [toast, setToast] = useState("");

  const FLASK = process.env.NEXT_PUBLIC_FLASK_URL ?? "http://localhost:5000";

  useEffect(() => {
    let mounted = true;
    async function poll() {
      try {
        const r = await fetch(`${FLASK}/api/suggestions/stats`);
        if (r.ok && mounted) {
          const d = await r.json();
          setUnreviewedCount(d.unreviewed ?? 0);
        }
      } catch { /* flask offline */ }
    }
    poll();
    const id = setInterval(poll, 30_000);
    return () => { mounted = false; clearInterval(id); };
  }, [FLASK]);

  const sorted = [...tickets].sort(
    (a, b) =>
      PRIORITY_ORDER[a.priority as TicketPriority] -
      PRIORITY_ORDER[b.priority as TicketPriority]
  );

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(""), 3000);
  }

  async function handleNewTicket(partial: Partial<Ticket>) {
    const res = await fetch(`${FLASK}/api/tickets`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(partial),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.error || `HTTP ${res.status}`);
    }
    const { ticket } = await res.json();
    setTickets(prev => [...prev, ticket]);
    setShowForm(false);
    setSelected(ticket);
    showToast(`${ticket.id} added to queue`);
  }

  return (
    <div className="space-y-0">
      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 z-50 rounded-lg bg-green-500/90 px-4 py-2 text-sm font-medium text-white shadow-lg">
          {toast}
        </div>
      )}

      {/* Section header + tab bar */}
      <div className="mb-4 flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Dev</h1>
          <p className="text-[13px] text-signal-dim">Tickets · SAGE Suggestions</p>
        </div>
      </div>

      <div className="flex border-b border-white/5 mb-4 -mt-2">
        <TabBtn active={section === "tickets"} onClick={() => setSection("tickets")}>
          Tickets
          <span className={`rounded-full px-1.5 py-0.5 text-[9px] font-bold ${
            section === "tickets" ? "bg-maroon-500/30 text-maroon-300" : "bg-white/5 text-slate-600"
          }`}>
            {tickets.length}
          </span>
        </TabBtn>
        <TabBtn active={section === "suggestions"} onClick={() => setSection("suggestions")}>
          Suggestions
          {unreviewedCount > 0 && (
            <span className="rounded-full bg-maroon-500 px-1.5 py-0.5 text-[9px] font-bold text-white">
              {unreviewedCount > 99 ? "99+" : unreviewedCount}
            </span>
          )}
        </TabBtn>
      </div>

      {/* Tickets panel */}
      {section === "tickets" && (
        <div className="flex h-[calc(100vh-180px)] gap-4">
          {/* Left column — ticket queue */}
          <div className="flex w-[340px] shrink-0 flex-col">
            <div className="mb-3 flex items-center justify-between">
              <p className="text-[11px] text-slate-500">
                {tickets.length} ticket{tickets.length !== 1 ? "s" : ""}
                {paused ? " · ⏸ paused" : ""}
              </p>
              <button
                onClick={() => { setShowForm(true); setSelected(null); }}
                className="rounded-md border border-white/10 bg-white/[0.03] px-3 py-1.5 text-xs text-slate-300 transition hover:bg-white/[0.06]"
              >
                + New Ticket
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2 pr-1">
              {sorted.length === 0 ? (
                <div className="pt-8 text-center text-sm text-slate-600">
                  No tickets yet. Click "+ New Ticket" to create one.
                </div>
              ) : (
                sorted.map(t => (
                  <TicketCard
                    key={t.id}
                    ticket={t}
                    selected={selected?.id === t.id}
                    onClick={() => { setSelected(t); setShowForm(false); }}
                  />
                ))
              )}
            </div>
          </div>

          {/* Right column — detail or form */}
          <div className="flex-1 overflow-y-auto rounded-lg border border-white/5 bg-white/[0.02] p-5">
            {showForm ? (
              <NewTicketForm
                onSubmit={handleNewTicket}
                onCancel={() => setShowForm(false)}
              />
            ) : selected ? (
              <TicketDetail
                ticket={selected}
                onClose={() => setSelected(null)}
              />
            ) : (
              <div className="flex h-full flex-col items-center justify-center text-center gap-3">
                <span className="text-4xl text-slate-700">⬡</span>
                <p className="text-sm text-slate-600">Select a ticket to view details,<br />or create a new one.</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Suggestions panel */}
      {section === "suggestions" && <SuggestionBoard />}
    </div>
  );
}
