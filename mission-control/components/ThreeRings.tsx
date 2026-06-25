import type { AgentCard } from "@/lib/agents";

// "Financial 3 Rings": Macro (outer) · News (middle) · Execution (inner),
// with the deterministic Core (Signal + Risk) at the center. Each agent is a
// dot on its ring, colored by real build status.
const RING_DEFS = [
  { key: "macro", label: "MACRO", r: 132 },
  { key: "news", label: "NEWS", r: 96 },
  { key: "execution", label: "EXECUTION", r: 60 },
] as const;

const statusColor = (s: AgentCard["status"]) =>
  s === "live" ? "#3ddc97" : s === "stub" ? "#f2b84b" : "#5b6680";

export function ThreeRings({ agents }: { agents: AgentCard[] }) {
  const size = 300;
  const c = size / 2;
  const core = agents.filter((a) => a.ring === "core");

  return (
    <div className="relative flex items-center justify-center">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {RING_DEFS.map((ring) => {
          const ringAgents = agents.filter((a) => a.ring === ring.key);
          return (
            <g key={ring.key}>
              <circle cx={c} cy={c} r={ring.r} fill="none" stroke="#1c2740" strokeWidth={1.5} />
              <text
                x={c}
                y={c - ring.r - 4}
                textAnchor="middle"
                className="fill-signal-dim"
                style={{ fontSize: 8, letterSpacing: 1.5 }}
              >
                {ring.label}
              </text>
              {ringAgents.map((a, i) => {
                const angle = (-90 + (360 / Math.max(ringAgents.length, 1)) * i) * (Math.PI / 180);
                const x = c + ring.r * Math.cos(angle);
                const y = c + ring.r * Math.sin(angle);
                const col = statusColor(a.status);
                return (
                  <g key={a.id}>
                    {a.status === "live" && (
                      <circle cx={x} cy={y} r={9} fill={col} opacity={0.18}>
                        <animate attributeName="r" values="6;11;6" dur="2s" repeatCount="indefinite" />
                      </circle>
                    )}
                    <circle cx={x} cy={y} r={5} fill={col} stroke="#070b16" strokeWidth={1.5} />
                    <text x={x} y={y + 16} textAnchor="middle" className="fill-slate-300" style={{ fontSize: 8 }}>
                      {a.name.split(" ")[0]}
                    </text>
                  </g>
                );
              })}
            </g>
          );
        })}

        {/* Core */}
        <circle cx={c} cy={c} r={30} fill="#0d1426" stroke="#7f1d2e" strokeWidth={1.5} />
        <text x={c} y={c - 2} textAnchor="middle" className="fill-slate-100" style={{ fontSize: 10, fontWeight: 700 }}>
          CORE
        </text>
        <text x={c} y={c + 10} textAnchor="middle" className="fill-signal-dim" style={{ fontSize: 7 }}>
          {core.filter((a) => a.status === "live").length}/{core.length} live
        </text>
      </svg>
    </div>
  );
}
