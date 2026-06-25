import type { AgentCard as Agent } from "@/lib/agents";

const STATUS_META: Record<Agent["status"], { label: string; chip: string; dot: string }> = {
  live: { label: "Live", chip: "border-signal-live/40 bg-signal-live/10 text-signal-live", dot: "bg-signal-live animate-pulseDot" },
  stub: { label: "Stub", chip: "border-signal-warn/40 bg-signal-warn/10 text-signal-warn", dot: "bg-signal-warn" },
  missing: { label: "Not built", chip: "border-signal-dim/40 bg-navy-700/40 text-signal-dim", dot: "bg-signal-dim" },
};

export function AgentCardView({ agent }: { agent: Agent }) {
  const meta = STATUS_META[agent.status];
  const isGov = agent.governor;
  return (
    <div
      className={`panel flex flex-col gap-2 p-4 transition ${
        agent.status === "live" ? "hover:shadow-glow" : ""
      } ${isGov ? "border-maroon-600/40" : ""}`}
    >
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className={`h-2 w-2 rounded-full ${meta.dot}`} />
            <span className="text-sm font-semibold text-slate-100">{agent.name}</span>
            {isGov && <span className="chip border-maroon-400/50 bg-maroon-600/15 text-maroon-300">Governor</span>}
          </div>
          <div className="mt-0.5 text-[11px] text-signal-dim">{agent.role}</div>
        </div>
        <span className={`chip ${meta.chip}`}>{meta.label}</span>
      </div>

      <p className="text-[12px] leading-relaxed text-slate-400">{agent.summary}</p>

      {agent.blockers.length > 0 && (
        <ul className="mt-1 space-y-1 border-t border-edge pt-2">
          {agent.blockers.map((b, i) => (
            <li key={i} className="flex gap-1.5 text-[11px] text-signal-warn/90">
              <span>▸</span>
              <span className="text-slate-400">{b}</span>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-auto flex items-center justify-between pt-1 text-[10px] text-signal-dim">
        <span className="font-mono">agent_v2/{agent.file}</span>
        <span>{agent.lines > 0 ? `${agent.lines} lines` : "—"}</span>
      </div>
    </div>
  );
}
