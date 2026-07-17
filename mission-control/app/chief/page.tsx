import Link from "next/link";
import { getChiefData, getFocusLine } from "@/lib/chief";
import { getAgents }                 from "@/lib/agents";
import { getJournal }                from "@/lib/journal";
import type { AgentCard }            from "@/lib/agents";
import type { Suggestion, MorningBrief, ChiefAssessment, ChiefHandoff } from "@/lib/chief";

export const dynamic = "force-dynamic";

// ── Helpers ───────────────────────────────────────────────────────────────────

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const m    = Math.floor(diff / 60_000);
  if (m < 1)  return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

// ── Agent tab links (for strip clicks) ───────────────────────────────────────
const AGENT_TABS: Record<string, string> = {
  signal:     "/signals",
  risk:       "/risk",
  data:       "/markets",
  intel:      "/memory",
  execution:  "/dev",
  review:     "/logs",
  watch:      "/system",
  sage:       "/dev",
  chief:      "/chief",
  strategist: "/signals",
};

// ── Question card ─────────────────────────────────────────────────────────────

function QuestionCard({
  question, accent, children, full = false,
}: {
  question: string;
  accent:   "amber" | "red" | "green" | "orange" | "blue";
  children: React.ReactNode;
  full?:    boolean;
}) {
  const colors = {
    amber:  { border: "border-signal-warn/30",  header: "text-signal-warn",  bg: "bg-signal-warn/5"  },
    red:    { border: "border-red-500/30",       header: "text-red-400",      bg: "bg-red-500/5"      },
    green:  { border: "border-signal-live/30",   header: "text-signal-live",  bg: "bg-signal-live/5"  },
    orange: { border: "border-orange-400/30",    header: "text-orange-400",   bg: "bg-orange-400/5"   },
    blue:   { border: "border-blue-400/30",      header: "text-blue-400",     bg: "bg-blue-400/5"     },
  }[accent];

  return (
    <div className={`panel flex flex-col gap-3 p-4 ${colors.border} ${colors.bg} ${full ? "col-span-2" : ""}`}>
      <div className={`text-[9px] font-bold uppercase tracking-[0.22em] ${colors.header}`}>
        {question}
      </div>
      <div className="flex-1 space-y-2 text-[12px] text-slate-300">
        {children}
      </div>
    </div>
  );
}

// ── Item row ──────────────────────────────────────────────────────────────────

function Item({ dot, label, sub }: { dot?: string; label: string; sub?: string }) {
  return (
    <div className="flex items-start gap-2">
      <span className="mt-1 shrink-0 text-[10px]">{dot ?? "▸"}</span>
      <div>
        <div className="leading-snug text-slate-200">{label}</div>
        {sub && <div className="text-[10px] text-signal-dim">{sub}</div>}
      </div>
    </div>
  );
}

// ── Agent status strip ────────────────────────────────────────────────────────

const STATUS_COLORS: Record<AgentCard["status"], string> = {
  live:    "#3ddc97",
  stub:    "#f2b84b",
  missing: "#5b6680",
};

const STATUS_LABELS: Record<AgentCard["status"], string> = {
  live:    "live",
  stub:    "stub",
  missing: "–",
};

function AgentStrip({ agents }: { agents: AgentCard[] }) {
  return (
    <div className="flex flex-wrap gap-2">
      {agents
        .filter((a) => a.id !== "strategist") // skip unspecced stub
        .map((a) => {
          const color = STATUS_COLORS[a.status];
          const dest  = AGENT_TABS[a.id] ?? "/chief";
          return (
            <Link
              key={a.id}
              href={dest}
              className="group flex items-center gap-2 rounded-md border border-edge bg-navy-800/60 px-3 py-1.5 transition hover:bg-navy-700/60"
            >
              <span
                className={`h-2 w-2 flex-shrink-0 rounded-full ${a.status === "live" ? "animate-pulseDot" : ""}`}
                style={{ backgroundColor: color }}
              />
              <span className="text-[11px] font-semibold text-slate-200 group-hover:text-white">{a.name}</span>
              <span className="text-[9px] text-signal-dim">{STATUS_LABELS[a.status]}</span>
            </Link>
          );
        })}
    </div>
  );
}

// ── CHIEF assessment panel ────────────────────────────────────────────────────

const HEALTH_STYLES = {
  nominal:  { border: "border-signal-live/30",  bg: "bg-signal-live/5",  badge: "border-signal-live/40 bg-signal-live/10 text-signal-live" },
  degraded: { border: "border-signal-warn/30",  bg: "bg-signal-warn/5",  badge: "border-signal-warn/40 bg-signal-warn/10 text-signal-warn" },
  critical: { border: "border-red-500/30",       bg: "bg-red-500/5",      badge: "border-red-500/40 bg-red-500/10 text-red-400" },
};

function ChiefAssessmentPanel({ assessment }: { assessment: ChiefAssessment | null }) {
  if (!assessment) {
    return (
      <div className="panel flex items-center justify-between gap-4 px-4 py-3 border-dashed border-slate-700/60">
        <div className="text-[11px] text-signal-dim">
          CHIEF not yet run — <code className="text-slate-400 text-[10px]">python3 agents/chief.py --dry-run</code>
        </div>
        <span className="chip border-slate-600/40 bg-slate-700/30 text-slate-500 shrink-0">CHIEF OFFLINE</span>
      </div>
    );
  }

  const health  = assessment.system_health ?? "nominal";
  const styles  = HEALTH_STYLES[health] ?? HEALTH_STYLES.nominal;
  const age     = relativeTime(assessment.generated_at);
  const handoffs: ChiefHandoff[] = assessment.handoffs ?? [];

  return (
    <div className={`panel flex flex-col gap-3 p-4 ${styles.border} ${styles.bg}`}>
      {/* Header row */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="text-[9px] font-bold uppercase tracking-[0.22em] text-signal-dim">CHIEF Assessment</div>
          <span className={`chip text-[9px] ${styles.badge}`}>{health.toUpperCase()}</span>
          <span className="chip border-slate-600/40 bg-navy-700/30 text-slate-400 text-[9px]">
            {assessment.readiness_pct}% ready
          </span>
        </div>
        <div className="text-[9px] text-signal-dim">Updated {age}</div>
      </div>

      {/* Directive */}
      <div className="rounded-md border border-edge bg-navy-800/60 px-3 py-2">
        <div className="text-[9px] font-semibold uppercase tracking-widest text-signal-dim mb-1">Directive</div>
        <p className="text-[12px] font-medium text-slate-100 leading-snug">{assessment.directive}</p>
      </div>

      {/* Assessment + blocker side-by-side on wider screens */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <div className="label mb-1">Assessment</div>
          <p className="text-[11px] text-slate-300 leading-relaxed">{assessment.assessment}</p>
        </div>
        {assessment.key_blocker && (
          <div>
            <div className="label mb-1 text-signal-warn">Key Blocker</div>
            <p className="text-[11px] text-slate-300 leading-relaxed">{assessment.key_blocker}</p>
          </div>
        )}
        {assessment.next_session_prep && (
          <div className={assessment.key_blocker ? "sm:col-span-2" : ""}>
            <div className="label mb-1">Next Session</div>
            <p className="text-[11px] text-slate-300 leading-relaxed">{assessment.next_session_prep}</p>
          </div>
        )}
      </div>

      {/* Handoffs */}
      {handoffs.length > 0 && (
        <div>
          <div className="label mb-1">Handoffs</div>
          <div className="flex flex-col gap-1.5">
            {handoffs.map((h, i) => (
              <div key={i} className="flex items-start gap-2 text-[11px] text-slate-300">
                <span className="text-signal-dim shrink-0">
                  {h.from_agent} → {h.to_agent}
                </span>
                <span className="text-slate-400">·</span>
                <span>{h.note}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Morning brief panel ───────────────────────────────────────────────────────

function BriefPanel({ brief }: { brief: MorningBrief | null }) {
  if (!brief) {
    return (
      <div className="panel flex h-24 items-center justify-center text-[12px] text-signal-dim">
        Brief arrives at 6:20 AM — check back then.
      </div>
    );
  }

  const { sections, sent_at } = brief;

  return (
    <div className="panel space-y-3 p-4">
      <div className="flex items-center justify-between">
        <div className="text-[9px] font-bold uppercase tracking-[0.22em] text-signal-dim">
          Daily Brief · INTEL
        </div>
        <div className="text-[9px] text-signal-dim">
          Last updated: {relativeTime(sent_at)}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        {sections.date_status && (
          <div>
            <div className="label mb-1">Date & Status</div>
            <p className="text-[11px] text-slate-300">{sections.date_status}</p>
          </div>
        )}
        {sections.tsla && (
          <div>
            <div className="label mb-1">TSLA</div>
            <p className="text-[11px] text-slate-300">{sections.tsla}</p>
          </div>
        )}
        {sections.spy && (
          <div>
            <div className="label mb-1">SPY Bias</div>
            <p className="text-[11px] text-slate-300">{sections.spy}</p>
          </div>
        )}
        {sections.watchlist && sections.watchlist.length > 0 && (
          <div className="col-span-2 sm:col-span-3">
            <div className="label mb-1">Watchlist Snapshot</div>
            <div className="flex flex-wrap gap-2">
              {sections.watchlist.map((item, i) => (
                <span key={i} className="chip border-edge bg-navy-700/60 text-slate-300">{item}</span>
              ))}
            </div>
          </div>
        )}
        {sections.catalysts && (
          <div className="col-span-2 sm:col-span-3">
            <div className="label mb-1">Catalysts</div>
            <p className="text-[11px] text-slate-400">{sections.catalysts}</p>
          </div>
        )}
        {sections.dev_overnight && (
          <div className="col-span-2 sm:col-span-3">
            <div className="label mb-1">Dev Agent Overnight</div>
            <p className="text-[11px] text-slate-400">{sections.dev_overnight}</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default async function ChiefPage() {
  const [data, agents, { stats }] = await Promise.all([
    getChiefData(),
    getAgents(),
    getJournal(),
  ]);

  const {
    session, online, todayDecisions, suggestions, watchdogAlerts,
    morningBrief, chiefAssessment, marketStatus, marketChip, greeting, todayLabel,
  } = data;

  const today = new Date().toISOString().slice(0, 10);

  // Derived flags
  const openSuggestions  = suggestions.filter((s) => s.status === "open");
  const criticalSugs     = openSuggestions.filter((s) => s.priority >= 9);
  const highPriSugs      = openSuggestions.filter((s) => s.priority >= 7);
  const tradingSugs      = openSuggestions.filter((s) => ["Trading"].includes(s.category) && s.status === "open");
  const riskSugs         = openSuggestions.filter((s) => ["Risk", "Security"].includes(s.category) && s.status === "open");
  const approvedToday    = todayDecisions.filter((d) => d.kind === "approved");
  const hasSignalToday   = approvedToday.length > 0;

  // ── Card 1: What Matters Today
  const mattersItems: { label: string; sub?: string }[] = [];
  if (session?.halted) {
    mattersItems.push({ label: "Circuit breaker active", sub: session.haltReason ?? "Session halted by VAULT" });
  }
  if (criticalSugs.length > 0) {
    criticalSugs.slice(0, 2).forEach((s) =>
      mattersItems.push({ label: s.title, sub: `${s.agent_id} · priority ${s.priority}` })
    );
  }
  if (hasSignalToday && !session?.halted) {
    approvedToday.slice(0, 2).forEach((d) =>
      mattersItems.push({ label: "HAWK found a setup", sub: d.message })
    );
  }
  if (mattersItems.length === 0) {
    mattersItems.push({ label: "No critical items — standard session" });
  }

  // ── Card 2: What Needs Attention
  const attentionItems: { label: string; sub?: string }[] = [];
  if (session?.halted && session.haltReason) {
    attentionItems.push({ label: "Session halted", sub: session.haltReason });
  }
  watchdogAlerts.slice(0, 2).forEach((line) => {
    const clean = line.replace(/^\d{4}-\d{2}-\d{2}T[\d:.]+\s*/, "").trim();
    if (clean.length > 10) attentionItems.push({ label: clean.slice(0, 120) });
  });
  highPriSugs.slice(0, 3 - attentionItems.length).forEach((s) =>
    attentionItems.push({ label: s.title, sub: `${s.agent_id} · P${s.priority}` })
  );
  if (attentionItems.length === 0) {
    attentionItems.push({ label: "Nothing flagged — system nominal" });
  }

  // ── Card 3: Opportunities
  const oppItems: { label: string; sub?: string }[] = [];
  approvedToday.slice(0, 2).forEach((d) =>
    oppItems.push({ label: d.message, sub: `${d.agent} · approved today` })
  );
  tradingSugs.slice(0, 3 - oppItems.length).forEach((s) =>
    oppItems.push({ label: s.title, sub: `${s.agent_id} suggestion` })
  );
  if ((stats.winRate ?? 0) > 0.5 && stats.wins > 0) {
    oppItems.push({ label: `Win rate ${Math.round((stats.winRate ?? 0) * 100)}%`, sub: `${stats.wins}W/${stats.losses}L from journal` });
  }
  if (oppItems.length === 0) {
    oppItems.push({ label: "No approved signals today — monitoring watchlist" });
  }

  // ── Card 4: Risks
  const riskItems: { label: string; sub?: string }[] = [];
  if ((session?.consecutiveLosses ?? 0) >= 1) {
    riskItems.push({
      label: `${session!.consecutiveLosses} consecutive ${session!.consecutiveLosses === 1 ? "loss" : "losses"}`,
      sub:   session!.consecutiveLosses >= 2 ? "Cooldown may engage" : "Monitor closely",
    });
  }
  if ((session?.dailyPnl ?? 0) < 0) {
    riskItems.push({ label: `Daily P&L: $${session!.dailyPnl.toFixed(2)}`, sub: "3% loss limit triggers circuit breaker" });
  }
  riskSugs.slice(0, 3 - riskItems.length).forEach((s) =>
    riskItems.push({ label: s.title, sub: `${s.agent_id} · P${s.priority}` })
  );
  if (riskItems.length === 0) {
    riskItems.push({ label: "Risk posture nominal", sub: "No losses, no alerts" });
  }

  // ── Card 5: Focus Today
  const focusLine = getFocusLine(session, marketStatus, hasSignalToday);

  const hasAttention = attentionItems[0]?.label !== "Nothing flagged — system nominal";

  return (
    <div className="space-y-5">

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">
            {greeting}, Silent.
          </h1>
          <p className="text-[13px] text-signal-dim">{todayLabel}</p>
        </div>
        <div className="flex items-center gap-2">
          <span className={`chip ${marketChip}`}>{marketStatus}</span>
          {online ? (
            <span className="chip border-signal-live/40 bg-signal-live/10 text-signal-live">Engine Online</span>
          ) : (
            <span className="chip border-signal-dim/40 bg-navy-700/40 text-signal-dim">Engine Offline</span>
          )}
        </div>
      </div>

      {/* ── CHIEF assessment ────────────────────────────────────────────── */}
      <ChiefAssessmentPanel assessment={chiefAssessment} />

      {/* ── 2×2 question cards ─────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-4">
        {/* Card 1 */}
        <QuestionCard question="What matters today" accent="amber">
          {mattersItems.map((item, i) => (
            <Item key={i} dot={session?.halted ? "🛑" : criticalSugs.length > 0 ? "⚠️" : "▸"} label={item.label} sub={item.sub} />
          ))}
        </QuestionCard>

        {/* Card 2 */}
        <QuestionCard question="What needs attention" accent={hasAttention ? "red" : "amber"}>
          {attentionItems.slice(0, 3).map((item, i) => (
            <Item key={i} dot={hasAttention ? "⚑" : "✓"} label={item.label} sub={item.sub} />
          ))}
        </QuestionCard>

        {/* Card 3 */}
        <QuestionCard question="Opportunities" accent="green">
          {oppItems.slice(0, 3).map((item, i) => (
            <Item key={i} dot="→" label={item.label} sub={item.sub} />
          ))}
        </QuestionCard>

        {/* Card 4 */}
        <QuestionCard question="Risks" accent="orange">
          {riskItems.slice(0, 3).map((item, i) => (
            <Item key={i} dot="▲" label={item.label} sub={item.sub} />
          ))}
        </QuestionCard>

        {/* Card 5 — full width */}
        <QuestionCard question="Focus today" accent="blue" full>
          <p className="text-[13px] font-medium leading-relaxed text-slate-200">
            {focusLine}
          </p>
          <div className="flex gap-3 pt-1 text-[10px] text-signal-dim">
            <span>{stats.closed} trades journaled</span>
            <span>·</span>
            <span>Trades today: {session?.tradesToday ?? 0}/3</span>
            {(session?.openPositions ?? 0) > 0 && (
              <>
                <span>·</span>
                <span className="text-signal-warn">{session!.openPositions} open position</span>
              </>
            )}
          </div>
        </QuestionCard>
      </div>

      {/* ── Morning brief ───────────────────────────────────────────────── */}
      <section>
        <BriefPanel brief={morningBrief} />
      </section>

      {/* ── Agent status strip ──────────────────────────────────────────── */}
      <section>
        <div className="mb-2 text-[9px] font-bold uppercase tracking-[0.2em] text-signal-dim">
          Agent Fleet
        </div>
        <AgentStrip agents={agents} />
      </section>

    </div>
  );
}
