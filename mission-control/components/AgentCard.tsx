import type { AgentCard as Agent } from "@/lib/agents";

const STATUS_META: Record<Agent["status"], { label: string; chip: string; dot: string }> = {
  live:    { label: "Live",      chip: "border-signal-live/40 bg-signal-live/10 text-signal-live", dot: "bg-signal-live animate-pulseDot" },
  stub:    { label: "Stub",      chip: "border-signal-warn/40 bg-signal-warn/10 text-signal-warn", dot: "bg-signal-warn" },
  missing: { label: "Not built", chip: "border-signal-dim/40 bg-navy-700/40 text-signal-dim",      dot: "bg-signal-dim" },
};

const RING_LABEL: Record<Agent["ring"], string> = {
  core:      "Core",
  macro:     "Macro",
  news:      "News",
  execution: "Execution",
};

const RING_COLOR: Record<Agent["ring"], string> = {
  core:      "border-signal-live/30 bg-signal-live/10 text-signal-live",
  macro:     "border-blue-400/30 bg-blue-400/10 text-blue-300",
  news:      "border-signal-warn/30 bg-signal-warn/10 text-signal-warn",
  execution: "border-maroon-400/30 bg-maroon-400/10 text-maroon-300",
};

export function AgentCardView({ agent }: { agent: Agent }) {
  const meta  = STATUS_META[agent.status];
  const isGov = agent.governor;

  return (
    <div className="flip-card">
      <div className="flip-card-inner">

        {/* ── FRONT ─────────────────────────────────────────── */}
        <div
          className={`flip-card-front panel flex flex-col gap-2 p-4 ${
            agent.status === "live" ? "shadow-glow/0 hover:shadow-glow" : ""
          } ${isGov ? "border-maroon-600/40" : ""}`}
        >
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span className={`h-2 w-2 flex-shrink-0 rounded-full ${meta.dot}`} />
                <span className="text-sm font-semibold text-slate-100">{agent.name}</span>
                {isGov && (
                  <span className="chip border-maroon-400/50 bg-maroon-600/15 text-maroon-300">
                    Governor
                  </span>
                )}
              </div>
              <div className="mt-0.5 text-[11px] text-signal-dim">{agent.role}</div>
            </div>
            <span className={`chip ${meta.chip}`}>{meta.label}</span>
          </div>

          <p className="text-[12px] leading-relaxed text-slate-400">{agent.summary}</p>

          {agent.blockers.length > 0 && (
            <ul className="mt-1 space-y-1 border-t border-edge pt-2">
              {agent.blockers.map((b, i) => (
                <li key={i} className="flex gap-1.5 text-[11px]">
                  <span className="text-signal-warn/80">▸</span>
                  <span className="text-slate-400">{b}</span>
                </li>
              ))}
            </ul>
          )}

          <div className="mt-auto flex items-center justify-between pt-2 text-[10px] text-signal-dim">
            <span className="font-mono">{agent.file}</span>
            <span>{agent.lines > 0 ? `${agent.lines} lines` : "—"}</span>
          </div>

          <div className="absolute bottom-2 right-3 select-none text-[9px] uppercase tracking-widest text-signal-dim/35">
            hover to flip
          </div>
        </div>

        {/* ── BACK ──────────────────────────────────────────── */}
        <div
          className={`flip-card-back panel flex flex-col gap-3 p-4 ${
            isGov ? "border-maroon-600/40" : ""
          }`}
        >
          <div className="flex items-start justify-between">
            <div>
              <div className="text-xl font-bold tracking-wide text-slate-100">{agent.name}</div>
              <div className="mt-0.5 text-[11px] text-signal-dim">{agent.role}</div>
            </div>
            <div className="flex flex-col items-end gap-1.5">
              <span className={`chip ${RING_COLOR[agent.ring]}`}>
                {RING_LABEL[agent.ring]} Ring
              </span>
              {isGov && (
                <span className="chip border-maroon-400/50 bg-maroon-600/15 text-maroon-300">
                  Governor
                </span>
              )}
            </div>
          </div>

          <p className="flex-1 text-[11.5px] leading-relaxed text-slate-300">
            {agent.description}
          </p>

          <div className="mt-auto border-t border-edge pt-2">
            <div className="flex items-start gap-2 text-[10.5px]">
              <span className="shrink-0 uppercase tracking-wide text-signal-dim">Output →</span>
              <span className="text-slate-400">{agent.feedsInto}</span>
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}
