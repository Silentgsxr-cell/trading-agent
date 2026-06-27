"use client";
import { useState, useEffect, useCallback, useRef } from "react";

const FLASK = process.env.NEXT_PUBLIC_FLASK_URL ?? "http://localhost:5000";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Suggestion {
  id: string;
  agent_id: string;
  agent_color: string;
  agent_avatar: string;
  title: string;
  reasoning: string;
  category: string;
  priority: number;
  flags: string[];
  flag_emojis: string;
  affected_files: string[];
  has_locked_files: boolean;
  status: "open" | "dev_queue" | "silent_queue" | "completed" | "discarded";
  queue: "dev" | "silent" | null;
  completed_by: "dev_agent" | "silent" | null;
  archive_reason: string;
  progress_pct: number;
  dev_ticket_id: string | null;
  user_edits: string;
  created_at: string;
  updated_at: string;
  archived_at: string | null;
  discord_posted: boolean;
  cycle_id: string;
}

// ── Constants ─────────────────────────────────────────────────────────────────

const CATEGORIES = ["All", "UI", "Trading", "Risk", "Life", "Agents", "Security"] as const;

const AGENT_IDS = ["VAULT", "HAWK", "DATAOS", "TRIGGER", "LEDGER", "WATCHDOG", "DEV_AGENT"];

const AGENT_COLORS: Record<string, string> = {
  VAULT:     "#c02a44",
  HAWK:      "#3ddc97",
  DATAOS:    "#4fc3f7",
  TRIGGER:   "#ff7043",
  LEDGER:    "#ab47bc",
  WATCHDOG:  "#f2b84b",
  DEV_AGENT: "#5c6bc0",
};

const AGENT_GLYPHS: Record<string, string> = {
  VAULT:     "🛡",
  HAWK:      "🦅",
  DATAOS:    "🗄",
  TRIGGER:   "⚡",
  LEDGER:    "📖",
  WATCHDOG:  "👁",
  DEV_AGENT: "⌬",
};

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// ── Sticky Note Card ──────────────────────────────────────────────────────────

function StickyCard({
  sug,
  onDev,
  onSilent,
  onDiscard,
  onEdit,
}: {
  sug: Suggestion;
  onDev: (id: string) => void;
  onSilent: (id: string) => void;
  onDiscard: (id: string) => void;
  onEdit: (id: string, field: "title" | "reasoning", val: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [editingTitle, setEditingTitle] = useState(false);
  const [editingReasoning, setEditingReasoning] = useState(false);
  const [localTitle, setLocalTitle] = useState(sug.title);
  const [localReasoning, setLocalReasoning] = useState(sug.reasoning);

  const isCritical = sug.priority >= 9;
  const isArchived = sug.status === "discarded" || sug.status === "completed";
  const color      = AGENT_COLORS[sug.agent_id] ?? "#5b6680";

  return (
    <div
      className={`relative flex flex-col rounded-lg border overflow-hidden transition-all ${
        isCritical ? "animate-riskPulse border-red-500/60" : "border-edge"
      }`}
      style={{ backgroundColor: `${color}18` }}
    >
      {/* CRITICAL banner */}
      {isCritical && (
        <div className="bg-red-600/90 px-3 py-1 text-[11px] font-semibold text-white tracking-wide">
          ⚠️ REQUIRES YOUR ATTENTION
        </div>
      )}

      {/* Agent header strip */}
      <div
        className="flex items-center justify-between px-3 py-2"
        style={{ backgroundColor: color }}
      >
        <div className="flex items-center gap-2">
          <span className="text-base">{AGENT_GLYPHS[sug.agent_id] ?? "●"}</span>
          <span className="text-[11px] font-bold uppercase tracking-wider text-white/90">
            {sug.agent_id}
          </span>
        </div>
        <span className="rounded-full bg-black/25 px-2 py-0.5 text-[10px] font-bold text-white">
          P{sug.priority}
        </span>
      </div>

      {/* Body */}
      <div className="flex flex-1 flex-col gap-2 p-3">
        {/* Flag emojis */}
        {sug.flag_emojis && (
          <div className="text-sm">{sug.flag_emojis}</div>
        )}

        {/* Title */}
        {editingTitle ? (
          <textarea
            className="w-full rounded bg-navy-800/80 p-1 text-[12px] font-semibold text-slate-100 outline-none resize-none"
            value={localTitle}
            rows={2}
            autoFocus
            onChange={(e) => setLocalTitle(e.target.value)}
            onBlur={() => { setEditingTitle(false); onEdit(sug.id, "title", localTitle); }}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); setEditingTitle(false); onEdit(sug.id, "title", localTitle); } }}
          />
        ) : (
          <p className="text-[12px] font-semibold leading-snug text-slate-100">{localTitle}</p>
        )}

        {/* Reasoning */}
        {editingReasoning ? (
          <textarea
            className="w-full rounded bg-navy-800/80 p-1 text-[11px] text-slate-300 outline-none resize-none"
            value={localReasoning}
            rows={3}
            autoFocus
            onChange={(e) => setLocalReasoning(e.target.value)}
            onBlur={() => { setEditingReasoning(false); onEdit(sug.id, "reasoning", localReasoning); }}
          />
        ) : (
          <p
            className={`text-[11px] leading-relaxed text-slate-400 cursor-pointer ${
              expanded ? "" : "line-clamp-3"
            }`}
            onClick={() => setExpanded((x) => !x)}
            title="Click to expand"
          >
            {localReasoning}
          </p>
        )}

        {/* Affected files */}
        {sug.affected_files.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {sug.affected_files.map((f) => (
              <span key={f} className="rounded bg-navy-700/60 px-1.5 py-0.5 font-mono text-[9px] text-signal-dim">
                {f}
              </span>
            ))}
          </div>
        )}

        {/* Footer row */}
        <div className="mt-auto flex items-center justify-between pt-1">
          <span
            className="chip border-edge bg-navy-700/60 text-signal-dim"
            style={{ fontSize: "9px" }}
          >
            {sug.category}
          </span>
          <span className="text-[9px] text-signal-dim">{relativeTime(sug.created_at)}</span>
        </div>

        {/* Action buttons (not shown for archived) */}
        {!isArchived && (
          <div className="flex gap-1.5 pt-1">
            <button
              onClick={() => onDev(sug.id)}
              className="flex-1 rounded py-1 text-[10px] font-semibold text-white transition hover:brightness-110"
              style={{ backgroundColor: "#2196f3" }}
            >
              Dev
            </button>
            <button
              onClick={() => onSilent(sug.id)}
              className="flex-1 rounded py-1 text-[10px] font-semibold text-white transition hover:brightness-110"
              style={{ backgroundColor: "#8B1A1A" }}
            >
              Silent
            </button>
            <button
              onClick={() => { setEditingTitle(true); }}
              className="flex-1 rounded bg-slate-600/60 py-1 text-[10px] font-semibold text-slate-200 transition hover:bg-slate-500/60"
            >
              Edit
            </button>
            <button
              onClick={() => onDiscard(sug.id)}
              className="rounded bg-navy-700/60 px-2 py-1 text-[10px] text-signal-dim transition hover:text-red-400"
              title="Discard"
            >
              ✕
            </button>
          </div>
        )}

        {/* Status chip for queued / archived */}
        {sug.status !== "open" && (
          <div className={`rounded px-2 py-1 text-center text-[10px] font-semibold uppercase ${
            sug.status === "dev_queue"    ? "bg-blue-600/30 text-blue-300" :
            sug.status === "silent_queue" ? "bg-maroon-600/30 text-maroon-300" :
            sug.status === "completed"    ? "bg-signal-live/20 text-signal-live" :
                                            "bg-navy-700/60 text-signal-dim"
          }`}>
            {sug.status.replace("_", " ")}
            {sug.dev_ticket_id && ` · ${sug.dev_ticket_id}`}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Agent Avatar Strip ────────────────────────────────────────────────────────

function AgentStrip({
  active,
  onToggle,
  counts,
}: {
  active: string | null;
  onToggle: (id: string) => void;
  counts: Record<string, number>;
}) {
  return (
    <div className="flex items-center gap-2">
      {AGENT_IDS.map((id) => {
        const color   = AGENT_COLORS[id] ?? "#5b6680";
        const isActive = active === id;
        const count   = counts[id] ?? 0;
        return (
          <button
            key={id}
            onClick={() => onToggle(id)}
            title={id}
            className="relative flex flex-col items-center gap-0.5 transition"
          >
            <div
              className="flex h-8 w-8 items-center justify-center rounded-full border-2 text-sm transition"
              style={{
                borderColor:     color,
                backgroundColor: isActive ? color : `${color}22`,
                boxShadow:       isActive ? `0 0 10px ${color}66` : undefined,
              }}
            >
              {AGENT_GLYPHS[id]}
            </div>
            {count > 0 && (
              <span
                className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full text-[8px] font-bold text-white"
                style={{ backgroundColor: color }}
              >
                {count > 9 ? "9+" : count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

// ── Discard modal ─────────────────────────────────────────────────────────────

function DiscardModal({
  id,
  onConfirm,
  onCancel,
}: {
  id: string;
  onConfirm: (reason: string) => void;
  onCancel: () => void;
}) {
  const [reason, setReason] = useState("");
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="panel w-[380px] space-y-3 p-5">
        <div className="text-sm font-semibold text-slate-100">Discard {id}</div>
        <p className="text-[12px] text-slate-400">Provide a reason (required):</p>
        <textarea
          className="w-full rounded border border-edge bg-navy-800/80 p-2 text-[12px] text-slate-200 outline-none resize-none"
          rows={3}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. Not relevant to current phase"
          autoFocus
        />
        <div className="flex gap-2">
          <button
            onClick={() => reason.trim() && onConfirm(reason.trim())}
            disabled={!reason.trim()}
            className="flex-1 rounded bg-maroon-600/80 py-1.5 text-[12px] font-semibold text-white disabled:opacity-40"
          >
            Discard
          </button>
          <button
            onClick={onCancel}
            className="flex-1 rounded bg-navy-700/60 py-1.5 text-[12px] text-slate-300"
          >
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Sidebar queue ─────────────────────────────────────────────────────────────

function QueueSidebar({
  suggestions,
  onProgressUpdate,
}: {
  suggestions: Suggestion[];
  onProgressUpdate: (id: string, pct: number) => void;
}) {
  const [activeTab, setActiveTab] = useState<"dev" | "silent">("dev");
  const [subtab, setSubtab] = useState<"active" | "archive">("active");

  const devActive  = suggestions.filter((s) => s.status === "dev_queue");
  const devArchive = suggestions.filter((s) => s.queue === "dev" && (s.status === "completed" || s.status === "discarded"));
  const silActive  = suggestions.filter((s) => s.status === "silent_queue");
  const silArchive = suggestions.filter((s) => s.queue === "silent" && (s.status === "completed" || s.status === "discarded"));

  const items  = activeTab === "dev"
    ? (subtab === "active" ? devActive : devArchive)
    : (subtab === "active" ? silActive : silArchive);

  return (
    <div className="flex h-full flex-col border-l border-edge bg-navy-900/60 backdrop-blur-sm">
      {/* Queue selector */}
      <div className="flex border-b border-edge">
        {(["dev", "silent"] as const).map((q) => {
          const count = q === "dev" ? devActive.length : silActive.length;
          return (
            <button
              key={q}
              onClick={() => { setActiveTab(q); setSubtab("active"); }}
              className={`flex flex-1 items-center justify-center gap-1.5 py-2.5 text-[11px] font-semibold uppercase tracking-wide transition ${
                activeTab === q ? "border-b-2 text-slate-100" : "text-signal-dim hover:text-slate-300"
              }`}
              style={{ borderColor: activeTab === q ? (q === "dev" ? "#2196f3" : "#8B1A1A") : undefined }}
            >
              {q === "dev" ? "Dev" : "Silent"}
              {count > 0 && (
                <span
                  className="rounded-full px-1.5 py-0.5 text-[9px] font-bold text-white"
                  style={{ backgroundColor: q === "dev" ? "#2196f3" : "#8B1A1A" }}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Sub-tab */}
      <div className="flex border-b border-edge/50">
        {(["active", "archive"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setSubtab(t)}
            className={`flex-1 py-1.5 text-[10px] uppercase tracking-widest transition ${
              subtab === t ? "text-slate-100" : "text-signal-dim hover:text-slate-400"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto">
        {items.length === 0 ? (
          <div className="flex h-24 items-center justify-center text-[11px] text-signal-dim">
            Nothing here
          </div>
        ) : (
          <ul className="divide-y divide-edge/40">
            {items.map((s) => (
              <li key={s.id} className="p-3 space-y-2">
                <div className="flex items-start gap-2">
                  <span
                    className="mt-0.5 h-2 w-2 flex-shrink-0 rounded-full"
                    style={{ backgroundColor: AGENT_COLORS[s.agent_id] ?? "#5b6680" }}
                  />
                  <span className="text-[11px] leading-snug text-slate-200 line-clamp-2">
                    {s.title}
                  </span>
                </div>

                {/* Progress for silent queue */}
                {s.status === "silent_queue" && subtab === "active" && (
                  <div className="space-y-1">
                    <div className="flex justify-between text-[9px] text-signal-dim">
                      <span>Progress</span>
                      <span>{s.progress_pct}%</span>
                    </div>
                    <input
                      type="range"
                      min={0}
                      max={100}
                      value={s.progress_pct}
                      onChange={(e) => onProgressUpdate(s.id, Number(e.target.value))}
                      className="w-full accent-maroon-400"
                    />
                  </div>
                )}

                {/* Dev queue ticket link */}
                {s.status === "dev_queue" && s.dev_ticket_id && (
                  <div className="text-[9px] text-blue-400 font-mono">{s.dev_ticket_id}</div>
                )}

                {/* Archive info */}
                {(s.status === "completed" || s.status === "discarded") && (
                  <div className="space-y-0.5">
                    <span className={`chip text-[9px] ${
                      s.status === "completed"
                        ? "border-signal-live/40 bg-signal-live/10 text-signal-live"
                        : "border-edge bg-navy-700/40 text-signal-dim"
                    }`}>
                      {s.status}
                    </span>
                    {s.archive_reason && (
                      <p className="text-[10px] text-slate-400 italic">{s.archive_reason}</p>
                    )}
                  </div>
                )}

                <div className="text-[9px] text-signal-dim">{relativeTime(s.created_at)}</div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

// ── Main board ────────────────────────────────────────────────────────────────

export function SuggestionBoard() {
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [loading,     setLoading]     = useState(true);
  const [agentFilter, setAgentFilter] = useState<string | null>(null);
  const [catFilter,   setCatFilter]   = useState<string>("All");
  const [sortBy,      setSortBy]      = useState<"priority" | "newest">("priority");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [discardTarget, setDiscardTarget] = useState<string | null>(null);

  const loadSuggestions = useCallback(async () => {
    try {
      const r = await fetch(`${FLASK}/api/suggestions`);
      if (r.ok) setSuggestions(await r.json());
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { loadSuggestions(); }, [loadSuggestions]);

  // Filtered + sorted list
  const visible = suggestions
    .filter((s) => !agentFilter || s.agent_id === agentFilter)
    .filter((s) => catFilter === "All" || s.category === catFilter)
    .sort((a, b) =>
      sortBy === "priority"
        ? b.priority - a.priority
        : new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );

  // Badge counts (open only)
  const openCounts = suggestions.reduce<Record<string, number>>((acc, s) => {
    if (s.status === "open") acc[s.agent_id] = (acc[s.agent_id] ?? 0) + 1;
    return acc;
  }, {});
  const totalUnreviewed = suggestions.filter((s) => s.status === "open").length;

  // Actions
  const patchSuggestion = useCallback(async (id: string, body: object) => {
    await fetch(`${FLASK}/api/suggestions/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    loadSuggestions();
  }, [loadSuggestions]);

  const handleDev = useCallback(async (id: string) => {
    await fetch(`${FLASK}/api/suggestions/${id}/approve-dev`, { method: "POST" });
    loadSuggestions();
  }, [loadSuggestions]);

  const handleSilent = useCallback(async (id: string) => {
    await fetch(`${FLASK}/api/suggestions/${id}/approve-silent`, { method: "POST" });
    loadSuggestions();
  }, [loadSuggestions]);

  const handleDiscard = useCallback(async (id: string, reason: string) => {
    await fetch(`${FLASK}/api/suggestions/${id}/discard`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ archive_reason: reason }),
    });
    setDiscardTarget(null);
    loadSuggestions();
  }, [loadSuggestions]);

  const handleEdit = useCallback(async (id: string, field: "title" | "reasoning", val: string) => {
    await patchSuggestion(id, { [field]: val });
  }, [patchSuggestion]);

  const handleProgressUpdate = useCallback(async (id: string, pct: number) => {
    await patchSuggestion(id, { progress_pct: pct });
    if (pct >= 100) {
      // Auto-complete at 100%
      await fetch(`${FLASK}/api/suggestions/${id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "completed", completed_by: "silent", archive_reason: "Completed manually" }),
      });
      loadSuggestions();
    }
  }, [patchSuggestion, loadSuggestions]);

  return (
    <div className="flex h-full min-h-[calc(100vh-6rem)] flex-col">

      {/* ── Header bar ─────────────────────────────────────────────── */}
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <h1 className="font-mono text-lg font-bold tracking-wide text-slate-100">
            Suggestion Board
          </h1>
          {totalUnreviewed > 0 && (
            <span className="rounded-full bg-maroon-500 px-2.5 py-0.5 text-[11px] font-bold text-white">
              {totalUnreviewed}
            </span>
          )}
        </div>

        {/* Agent avatar strip */}
        <AgentStrip
          active={agentFilter}
          onToggle={(id) => setAgentFilter((prev) => (prev === id ? null : id))}
          counts={openCounts}
        />

        {/* Controls */}
        <div className="flex items-center gap-2">
          {/* Category filter */}
          <div className="flex gap-1">
            {CATEGORIES.map((c) => (
              <button
                key={c}
                onClick={() => setCatFilter(c)}
                className={`chip transition ${
                  catFilter === c
                    ? "border-maroon-400/60 bg-maroon-600/20 text-maroon-300"
                    : "border-edge bg-navy-700/40 text-signal-dim hover:text-slate-300"
                }`}
              >
                {c}
              </button>
            ))}
          </div>

          {/* Sort */}
          <button
            onClick={() => setSortBy((s) => (s === "priority" ? "newest" : "priority"))}
            className="chip border-edge bg-navy-700/40 text-signal-dim hover:text-slate-200"
          >
            {sortBy === "priority" ? "↓ Priority" : "⏱ Newest"}
          </button>

          {/* Refresh */}
          <button
            onClick={loadSuggestions}
            className="chip border-edge bg-navy-700/40 text-signal-dim hover:text-slate-200"
          >
            ↺
          </button>
        </div>
      </div>

      {/* ── Cork board + sidebar ────────────────────────────────────── */}
      <div className="relative flex flex-1 overflow-hidden rounded-xl">

        {/* Cork board */}
        <div
          className="flex-1 overflow-y-auto p-5 transition-all"
          style={{
            backgroundColor: "#8B6914",
            backgroundImage: `
              repeating-linear-gradient(
                0deg,
                transparent,
                transparent 3px,
                rgba(0,0,0,0.04) 3px,
                rgba(0,0,0,0.04) 4px
              ),
              repeating-linear-gradient(
                90deg,
                transparent,
                transparent 3px,
                rgba(0,0,0,0.03) 3px,
                rgba(0,0,0,0.03) 4px
              ),
              radial-gradient(
                ellipse at 20% 50%,
                rgba(139,105,20,0.3) 0%,
                transparent 60%
              ),
              radial-gradient(
                ellipse at 80% 20%,
                rgba(160,120,30,0.2) 0%,
                transparent 50%
              )
            `,
          }}
        >
          {loading ? (
            <div className="flex h-40 items-center justify-center text-[13px] text-amber-200/60">
              Loading suggestions…
            </div>
          ) : visible.length === 0 ? (
            <div className="flex h-40 flex-col items-center justify-center gap-2">
              <div className="text-4xl opacity-30">📌</div>
              <div className="text-[13px] text-amber-200/60">
                {suggestions.length === 0
                  ? "No suggestions yet — run the suggestion agent to populate the board."
                  : "No suggestions match the current filter."}
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
              {visible.map((s) => (
                <StickyCard
                  key={s.id}
                  sug={s}
                  onDev={handleDev}
                  onSilent={handleSilent}
                  onDiscard={(id) => setDiscardTarget(id)}
                  onEdit={handleEdit}
                />
              ))}
            </div>
          )}
        </div>

        {/* Sidebar toggle */}
        <button
          onClick={() => setSidebarOpen((x) => !x)}
          className="absolute right-0 top-1/2 z-10 -translate-y-1/2 translate-x-0 flex h-10 w-5 items-center justify-center rounded-l-md border border-edge bg-navy-800/90 text-[10px] text-signal-dim hover:text-slate-200 transition"
          style={{ right: sidebarOpen ? "30%" : 0 }}
        >
          {sidebarOpen ? "›" : "‹"}
        </button>

        {/* Right sidebar */}
        {sidebarOpen && (
          <div className="w-[30%] shrink-0 overflow-hidden">
            <QueueSidebar
              suggestions={suggestions}
              onProgressUpdate={handleProgressUpdate}
            />
          </div>
        )}
      </div>

      {/* Discard modal */}
      {discardTarget && (
        <DiscardModal
          id={discardTarget}
          onConfirm={(reason) => handleDiscard(discardTarget, reason)}
          onCancel={() => setDiscardTarget(null)}
        />
      )}
    </div>
  );
}
