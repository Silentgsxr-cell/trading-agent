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
const AGENT_IDS  = ["VAULT", "HAWK", "DATAOS", "TRIGGER", "LEDGER", "WATCHDOG", "DEV_AGENT"];

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
  if (m < 1)  return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// ── Circular progress SVG ─────────────────────────────────────────────────────

function CircularProgress({ pct, color }: { pct: number; color: string }) {
  const r = 11;
  const circ  = 2 * Math.PI * r;
  const offset = circ - (Math.min(pct, 100) / 100) * circ;
  return (
    <svg width="28" height="28" viewBox="0 0 28 28" className="shrink-0">
      <circle cx="14" cy="14" r={r} fill="none" stroke="#1c2740" strokeWidth="2.5" />
      <circle
        cx="14" cy="14" r={r}
        fill="none"
        stroke={pct >= 100 ? "#3ddc97" : color}
        strokeWidth="2.5"
        strokeDasharray={circ}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform="rotate(-90 14 14)"
        style={{ transition: "stroke-dashoffset 0.4s ease" }}
      />
      <text x="14" y="17.5" textAnchor="middle" fontSize="6.5" fill="#c7d0e0" fontFamily="monospace">
        {pct}%
      </text>
    </svg>
  );
}

// ── Sticky Note Card (cork board) ─────────────────────────────────────────────

function StickyCard({
  sug, onDev, onSilent, onDiscard, onEdit,
}: {
  sug: Suggestion;
  onDev:     (id: string) => void;
  onSilent:  (id: string) => void;
  onDiscard: (id: string) => void;
  onEdit:    (id: string, field: "title" | "reasoning", val: string) => void;
}) {
  const [expanded,        setExpanded]        = useState(false);
  const [editingTitle,    setEditingTitle]    = useState(false);
  const [editingReasoning,setEditingReasoning]= useState(false);
  const [localTitle,      setLocalTitle]      = useState(sug.title);
  const [localReasoning,  setLocalReasoning]  = useState(sug.reasoning);

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
      {isCritical && (
        <div className="bg-red-600/90 px-3 py-1 text-[11px] font-semibold text-white tracking-wide">
          ⚠️ REQUIRES YOUR ATTENTION
        </div>
      )}

      {/* Agent header strip */}
      <div className="flex items-center justify-between px-3 py-2" style={{ backgroundColor: color }}>
        <div className="flex items-center gap-1.5">
          <span className="text-sm">{AGENT_GLYPHS[sug.agent_id] ?? "●"}</span>
          <span className="text-[11px] font-bold uppercase tracking-wider text-white/90">{sug.agent_id}</span>
        </div>
        <span className="rounded-full bg-black/25 px-1.5 py-0.5 text-[10px] font-bold text-white">P{sug.priority}</span>
      </div>

      <div className="flex flex-1 flex-col gap-2 p-3">
        {sug.flag_emojis && <div className="text-sm">{sug.flag_emojis}</div>}

        {/* Title */}
        {editingTitle ? (
          <textarea
            className="w-full rounded bg-navy-800/80 p-1 text-[12px] font-semibold text-slate-100 outline-none resize-none"
            value={localTitle} rows={2} autoFocus
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
            value={localReasoning} rows={3} autoFocus
            onChange={(e) => setLocalReasoning(e.target.value)}
            onBlur={() => { setEditingReasoning(false); onEdit(sug.id, "reasoning", localReasoning); }}
          />
        ) : (
          <p
            className={`text-[11px] leading-relaxed text-slate-400 cursor-pointer ${expanded ? "" : "line-clamp-3"}`}
            onClick={() => setExpanded((x) => !x)} title="Click to expand"
          >
            {localReasoning}
          </p>
        )}

        {sug.affected_files.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {sug.affected_files.map((f) => (
              <span key={f} className="rounded bg-navy-700/60 px-1.5 py-0.5 font-mono text-[9px] text-signal-dim">{f}</span>
            ))}
          </div>
        )}

        <div className="mt-auto flex items-center justify-between pt-1">
          <span className="chip border-edge bg-navy-700/60 text-signal-dim" style={{ fontSize: "9px" }}>{sug.category}</span>
          <span className="text-[9px] text-signal-dim">{relativeTime(sug.created_at)}</span>
        </div>

        {!isArchived && (
          <div className="flex gap-1.5 pt-1">
            <button onClick={() => onDev(sug.id)} className="flex-1 rounded py-1 text-[10px] font-semibold text-white transition hover:brightness-110" style={{ backgroundColor: "#2196f3" }}>Dev</button>
            <button onClick={() => onSilent(sug.id)} className="flex-1 rounded py-1 text-[10px] font-semibold text-white transition hover:brightness-110" style={{ backgroundColor: "#8B1A1A" }}>Silent</button>
            <button onClick={() => setEditingTitle(true)} className="flex-1 rounded bg-slate-600/60 py-1 text-[10px] font-semibold text-slate-200 transition hover:bg-slate-500/60">Edit</button>
            <button onClick={() => onDiscard(sug.id)} className="rounded bg-navy-700/60 px-2 py-1 text-[10px] text-signal-dim transition hover:text-red-400" title="Discard">✕</button>
          </div>
        )}

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

function AgentStrip({ active, onToggle, counts }: {
  active: string | null;
  onToggle: (id: string) => void;
  counts: Record<string, number>;
}) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      {AGENT_IDS.map((id) => {
        const color    = AGENT_COLORS[id] ?? "#5b6680";
        const isActive = active === id;
        const count    = counts[id] ?? 0;
        return (
          <button key={id} onClick={() => onToggle(id)} title={id} className="relative flex flex-col items-center transition">
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
              <span className="absolute -right-1 -top-1 flex h-4 w-4 items-center justify-center rounded-full text-[8px] font-bold text-white" style={{ backgroundColor: color }}>
                {count > 9 ? "9+" : count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

// ── Discard Modal ─────────────────────────────────────────────────────────────

function DiscardModal({ id, onConfirm, onCancel }: {
  id: string;
  onConfirm: (reason: string) => void;
  onCancel:  () => void;
}) {
  const [reason, setReason] = useState("");
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="panel w-[380px] space-y-3 p-5">
        <div className="text-sm font-semibold text-slate-100">Discard {id}</div>
        <p className="text-[12px] text-slate-400">Provide a reason (required):</p>
        <textarea
          className="w-full rounded border border-edge bg-navy-800/80 p-2 text-[12px] text-slate-200 outline-none resize-none"
          rows={3} value={reason} onChange={(e) => setReason(e.target.value)}
          placeholder="e.g. Not relevant to current phase" autoFocus
        />
        <div className="flex gap-2">
          <button onClick={() => reason.trim() && onConfirm(reason.trim())} disabled={!reason.trim()} className="flex-1 rounded bg-maroon-600/80 py-1.5 text-[12px] font-semibold text-white disabled:opacity-40">Discard</button>
          <button onClick={onCancel} className="flex-1 rounded bg-navy-700/60 py-1.5 text-[12px] text-slate-300">Cancel</button>
        </div>
      </div>
    </div>
  );
}

// ── Queue flip-card sidebar ───────────────────────────────────────────────────

const lsGet = (key: string, fallback: string) =>
  typeof window !== "undefined" ? (localStorage.getItem(key) ?? fallback) : fallback;

function QueueFlipCard({ queue, active, archived, onProgressUpdate, onComplete }: {
  queue:            "dev" | "silent";
  active:           Suggestion[];
  archived:         Suggestion[];
  onProgressUpdate: (id: string, pct: number) => void;
  onComplete:       (id: string, note: string) => void;
}) {
  const isDev      = queue === "dev";
  const accent     = isDev ? "#2196f3" : "#8B1A1A";
  const accentSoft = isDev ? "#1565c080" : "#8B1A1A80";
  const label      = isDev ? "Dev Queue" : "Silent Queue";

  const [flipped,  setFlipped]  = useState(() => lsGet(`clawops-${queue}-flipped`, "false") === "true");
  const [subtab,   setSubtab]   = useState<"active" | "archive">(() => lsGet(`clawops-${queue}-subtab`, "active") as "active" | "archive");
  const [completing, setCompleting] = useState<string | null>(null);
  const [note,       setNote]       = useState("");

  useEffect(() => { localStorage.setItem(`clawops-${queue}-flipped`,  String(flipped)); },  [flipped,  queue]);
  useEffect(() => { localStorage.setItem(`clawops-${queue}-subtab`,   subtab);          },  [subtab,   queue]);

  const items = subtab === "active" ? active : archived;

  function handleSlider(id: string, val: number) {
    if (val >= 100) {
      setCompleting(id);
      setNote("");
    } else {
      onProgressUpdate(id, val);
    }
  }

  function confirmComplete() {
    if (!completing || !note.trim()) return;
    onComplete(completing, note.trim());
    setCompleting(null);
    setNote("");
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col" style={{ perspective: "900px" }}>
      <div
        className="relative flex-1 min-h-0"
        style={{
          transformStyle:  "preserve-3d",
          transition:      "transform 0.52s cubic-bezier(0.4,0,0.2,1)",
          transform:       flipped ? "rotateY(180deg)" : "rotateY(0deg)",
        }}
      >
        {/* ── FRONT ── */}
        <div
          className="absolute inset-0 flex cursor-pointer flex-col items-center justify-center gap-3 rounded-xl border border-edge bg-navy-850/80 p-4"
          style={{ backfaceVisibility: "hidden", WebkitBackfaceVisibility: "hidden" }}
          onClick={() => setFlipped(true)}
        >
          <div
            className="flex h-10 w-10 items-center justify-center rounded-full text-lg font-bold text-white"
            style={{ backgroundColor: accent }}
          >
            {isDev ? "⌬" : "◎"}
          </div>
          <div className="text-sm font-bold tracking-wide text-slate-100">{label}</div>
          <div
            className="rounded-full px-3 py-1 text-[11px] font-bold text-white"
            style={{ backgroundColor: accentSoft }}
          >
            {active.length} active
            {archived.length > 0 && ` · ${archived.length} archived`}
          </div>
          <div className="text-[9px] uppercase tracking-widest text-signal-dim/50">
            Click to view queue
          </div>
        </div>

        {/* ── BACK ── */}
        <div
          className="absolute inset-0 flex flex-col overflow-hidden rounded-xl border border-edge bg-navy-850/95"
          style={{
            backfaceVisibility:        "hidden",
            WebkitBackfaceVisibility:  "hidden",
            transform:                 "rotateY(180deg)",
          }}
        >
          {/* Back header */}
          <div
            className="flex items-center justify-between px-3 py-2 text-[11px] font-bold text-white"
            style={{ backgroundColor: accent }}
          >
            <span>{label}</span>
            <button
              onClick={(e) => { e.stopPropagation(); setFlipped(false); }}
              className="rounded px-1.5 py-0.5 bg-black/20 text-[10px] hover:bg-black/40 transition"
            >
              ← Back
            </button>
          </div>

          {/* Sub-tabs */}
          <div className="flex border-b border-edge/60">
            {(["active", "archive"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setSubtab(t)}
                className={`flex-1 py-1.5 text-[10px] uppercase tracking-widest transition ${
                  subtab === t ? "text-slate-100" : "text-signal-dim hover:text-slate-400"
                }`}
                style={{ borderBottom: subtab === t ? `2px solid ${accent}` : "2px solid transparent" }}
              >
                {t}
                {t === "active"  && active.length  > 0 && ` (${active.length})`}
                {t === "archive" && archived.length > 0 && ` (${archived.length})`}
              </button>
            ))}
          </div>

          {/* Item list */}
          <div className="flex-1 overflow-y-auto">
            {items.length === 0 ? (
              <div className="flex h-20 items-center justify-center text-[11px] text-signal-dim">
                Nothing here
              </div>
            ) : (
              <ul className="divide-y divide-edge/40">
                {items.map((s) => (
                  <li key={s.id} className="space-y-2 p-3">
                    {/* Title + avatar dot + progress ring */}
                    <div className="flex items-start gap-2">
                      <span
                        className="mt-0.5 h-2 w-2 flex-shrink-0 rounded-full"
                        style={{ backgroundColor: AGENT_COLORS[s.agent_id] ?? "#5b6680" }}
                      />
                      <span className="flex-1 text-[11px] leading-snug text-slate-200 line-clamp-2">{s.title}</span>
                      {subtab === "active" && (
                        <CircularProgress pct={s.progress_pct} color={accent} />
                      )}
                    </div>

                    {/* Silent: slider + completion prompt */}
                    {!isDev && subtab === "active" && (
                      <>
                        <input
                          type="range" min={0} max={100}
                          value={completing === s.id ? 100 : s.progress_pct}
                          onChange={(e) => handleSlider(s.id, Number(e.target.value))}
                          className="w-full accent-maroon-400"
                        />
                        {completing === s.id && (
                          <div className="space-y-1.5 rounded-lg border border-maroon-600/40 bg-navy-800/80 p-2">
                            <p className="text-[10px] text-slate-300">Add a completion note:</p>
                            <input
                              className="w-full rounded border border-edge bg-navy-700/60 px-2 py-1 text-[11px] text-slate-200 outline-none"
                              value={note}
                              onChange={(e) => setNote(e.target.value)}
                              placeholder="What did you do?"
                              autoFocus
                              onKeyDown={(e) => { if (e.key === "Enter") confirmComplete(); }}
                            />
                            <div className="flex gap-1.5">
                              <button onClick={confirmComplete} disabled={!note.trim()} className="flex-1 rounded bg-maroon-600/80 py-1 text-[10px] font-semibold text-white disabled:opacity-40">Complete</button>
                              <button onClick={() => { setCompleting(null); onProgressUpdate(s.id, 99); }} className="flex-1 rounded bg-navy-700/60 py-1 text-[10px] text-slate-300">Cancel</button>
                            </div>
                          </div>
                        )}
                      </>
                    )}

                    {/* Dev: ticket ID + status chip */}
                    {isDev && subtab === "active" && s.dev_ticket_id && (
                      <div className="flex items-center gap-2">
                        <span className="rounded bg-blue-900/40 px-1.5 py-0.5 font-mono text-[9px] text-blue-300">{s.dev_ticket_id}</span>
                      </div>
                    )}

                    {/* Archive info */}
                    {subtab === "archive" && (
                      <div className="space-y-1">
                        <span className={`chip text-[9px] ${
                          s.status === "completed"
                            ? "border-signal-live/40 bg-signal-live/10 text-signal-live"
                            : "border-edge bg-navy-700/40 text-signal-dim"
                        }`}>
                          {s.status === "completed" ? "COMPLETED" : "DISCARDED"}
                        </span>
                        {s.completed_by && (
                          <p className="text-[9px] text-signal-dim">
                            By: {s.completed_by === "dev_agent" ? "Dev Agent" : "Silent (you)"}
                          </p>
                        )}
                        {s.archive_reason && (
                          <p className="text-[10px] italic text-slate-400">{s.archive_reason}</p>
                        )}
                        {s.dev_ticket_id && (
                          <span className="rounded bg-blue-900/40 px-1.5 py-0.5 font-mono text-[9px] text-blue-300">{s.dev_ticket_id}</span>
                        )}
                        {s.archived_at && (
                          <p className="text-[9px] text-signal-dim">{relativeTime(s.archived_at)}</p>
                        )}
                      </div>
                    )}

                    {subtab === "active" && (
                      <div className="text-[9px] text-signal-dim">{relativeTime(s.created_at)}</div>
                    )}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Full flip-card sidebar ────────────────────────────────────────────────────

function QueueSidebar({ suggestions, onProgressUpdate, onComplete }: {
  suggestions:      Suggestion[];
  onProgressUpdate: (id: string, pct: number) => void;
  onComplete:       (id: string, note: string) => void;
}) {
  const devActive   = suggestions.filter((s) => s.status === "dev_queue");
  const devArchived = suggestions.filter((s) => s.queue === "dev" && (s.status === "completed" || s.status === "discarded"));
  const silActive   = suggestions.filter((s) => s.status === "silent_queue");
  const silArchived = suggestions.filter((s) => s.queue === "silent" && (s.status === "completed" || s.status === "discarded"));

  return (
    <div className="flex h-full flex-col gap-3 border-l border-edge bg-navy-900/70 p-3 backdrop-blur-sm">
      <div className="text-[9px] uppercase tracking-[0.2em] text-signal-dim/70">Queues</div>
      <QueueFlipCard
        queue="dev"
        active={devActive}
        archived={devArchived}
        onProgressUpdate={onProgressUpdate}
        onComplete={onComplete}
      />
      <QueueFlipCard
        queue="silent"
        active={silActive}
        archived={silArchived}
        onProgressUpdate={onProgressUpdate}
        onComplete={onComplete}
      />
    </div>
  );
}

// ── Main board ────────────────────────────────────────────────────────────────

export function SuggestionBoard() {
  const [suggestions,   setSuggestions]   = useState<Suggestion[]>([]);
  const [loading,       setLoading]       = useState(true);
  const [agentFilter,   setAgentFilter]   = useState<string | null>(null);
  const [catFilter,     setCatFilter]     = useState<string>("All");
  const [sortBy,        setSortBy]        = useState<"priority" | "newest">("priority");
  const [sidebarOpen,   setSidebarOpen]   = useState(() => lsGet("clawops-sidebar-open", "true") === "true");
  const [discardTarget, setDiscardTarget] = useState<string | null>(null);

  useEffect(() => { localStorage.setItem("clawops-sidebar-open", String(sidebarOpen)); }, [sidebarOpen]);

  const loadSuggestions = useCallback(async () => {
    try {
      const r = await fetch(`${FLASK}/api/suggestions`);
      if (r.ok) setSuggestions(await r.json());
    } catch { /* ignore */ }
    setLoading(false);
  }, []);

  useEffect(() => { loadSuggestions(); }, [loadSuggestions]);

  const visible = suggestions
    .filter((s) => !agentFilter || s.agent_id === agentFilter)
    .filter((s) => catFilter === "All" || s.category === catFilter)
    .sort((a, b) =>
      sortBy === "priority"
        ? b.priority - a.priority
        : new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
    );

  const openCounts = suggestions.reduce<Record<string, number>>((acc, s) => {
    if (s.status === "open") acc[s.agent_id] = (acc[s.agent_id] ?? 0) + 1;
    return acc;
  }, {});
  const totalUnreviewed = suggestions.filter((s) => s.status === "open").length;

  const patchSuggestion = useCallback(async (id: string, body: object) => {
    await fetch(`${FLASK}/api/suggestions/${id}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
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
      method: "POST", headers: { "Content-Type": "application/json" },
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
  }, [patchSuggestion]);

  const handleComplete = useCallback(async (id: string, note: string) => {
    await fetch(`${FLASK}/api/suggestions/${id}/discard`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ archive_reason: note }),
    });
    // Re-fetch and mark as completed
    await fetch(`${FLASK}/api/suggestions/${id}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ progress_pct: 100 }),
    });
    await fetch(`${FLASK}/api/suggestions/${id}/approve-silent`, { method: "POST" });
    loadSuggestions();
  }, [loadSuggestions]);

  return (
    <div className="flex h-full min-h-[calc(100vh-6rem)] flex-col">

      {/* ── Header ─────────────────────────────────────────────────── */}
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-3">
          <h1 className="font-mono text-lg font-bold tracking-wide text-slate-100">📌 Suggestion Board</h1>
          {totalUnreviewed > 0 && (
            <span className="rounded-full bg-maroon-500 px-2.5 py-0.5 text-[11px] font-bold text-white">{totalUnreviewed}</span>
          )}
        </div>

        <AgentStrip
          active={agentFilter}
          onToggle={(id) => setAgentFilter((prev) => (prev === id ? null : id))}
          counts={openCounts}
        />

        <div className="ml-auto flex flex-wrap items-center gap-2">
          <div className="flex gap-1 flex-wrap">
            {CATEGORIES.map((c) => (
              <button
                key={c} onClick={() => setCatFilter(c)}
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
          <button onClick={() => setSortBy((s) => (s === "priority" ? "newest" : "priority"))} className="chip border-edge bg-navy-700/40 text-signal-dim hover:text-slate-200">
            {sortBy === "priority" ? "↓ Priority" : "⏱ Newest"}
          </button>
          <button onClick={loadSuggestions} className="chip border-edge bg-navy-700/40 text-signal-dim hover:text-slate-200">↺</button>
        </div>
      </div>

      {/* ── Cork board + sidebar ────────────────────────────────────── */}
      <div className="relative flex flex-1 min-h-0 overflow-hidden rounded-xl">

        {/* Cork board */}
        <div
          className="flex-1 min-h-0 overflow-y-auto p-5 transition-all"
          style={{
            backgroundColor: "#8B6914",
            backgroundImage: `
              repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(0,0,0,0.04) 3px,rgba(0,0,0,0.04) 4px),
              repeating-linear-gradient(90deg,transparent,transparent 3px,rgba(0,0,0,0.03) 3px,rgba(0,0,0,0.03) 4px),
              radial-gradient(ellipse at 20% 50%,rgba(139,105,20,0.3) 0%,transparent 60%),
              radial-gradient(ellipse at 80% 20%,rgba(160,120,30,0.2) 0%,transparent 50%)
            `,
          }}
        >
          {loading ? (
            <div className="flex h-40 items-center justify-center text-[13px] text-amber-200/60">Loading suggestions…</div>
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
                  key={s.id} sug={s}
                  onDev={handleDev}
                  onSilent={handleSilent}
                  onDiscard={(id) => setDiscardTarget(id)}
                  onEdit={handleEdit}
                />
              ))}
            </div>
          )}
        </div>

        {/* Sidebar toggle tab */}
        <button
          onClick={() => setSidebarOpen((x) => !x)}
          className="absolute top-1/2 z-10 flex h-12 w-5 -translate-y-1/2 items-center justify-center rounded-l-md border border-edge bg-navy-800/90 text-[11px] text-signal-dim transition hover:text-slate-100"
          style={{ right: sidebarOpen ? "30%" : 0 }}
          title={sidebarOpen ? "Collapse queue sidebar" : "Expand queue sidebar"}
        >
          {sidebarOpen ? "›" : "‹"}
        </button>

        {/* Right sidebar */}
        <div
          className={`shrink-0 overflow-hidden transition-all duration-300 ${sidebarOpen ? "w-[30%]" : "w-0"}`}
        >
          {sidebarOpen && (
            <QueueSidebar
              suggestions={suggestions}
              onProgressUpdate={handleProgressUpdate}
              onComplete={handleComplete}
            />
          )}
        </div>
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
