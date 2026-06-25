import { getAgents, crewHealth } from "@/lib/agents";
import { getJournal } from "@/lib/journal";
import { getSession } from "@/lib/runtime";
import { ThreeRings } from "@/components/ThreeRings";
import { AgentCardView } from "@/components/AgentCard";
import { StatCard } from "@/components/StatCard";
import { usd, pct, pnlClass } from "@/lib/format";

export const dynamic = "force-dynamic"; // always read fresh from disk

export default async function Cockpit() {
  const [agents, { stats }, { online }] = await Promise.all([getAgents(), getJournal(), getSession()]);
  const health = crewHealth(agents);

  return (
    <div className="space-y-5">
      <PageTitle title="Cockpit" subtitle="Live system posture across the agent fleet, risk, and journaled edge." />

      {/* Top row: rings + crew readiness + journal stats */}
      <div className="grid grid-cols-12 gap-5">
        <section className="panel col-span-12 lg:col-span-5">
          <div className="panel-head">
            <h2 className="text-sm font-semibold text-slate-200">Agent Fleet · 3 Rings</h2>
            <span className="text-[11px] text-signal-dim">{health.readiness}% live</span>
          </div>
          <div className="p-4">
            <ThreeRings agents={agents} />
            <div className="mt-3 flex items-center justify-center gap-4 text-[11px]">
              <Legend color="#3ddc97" label={`${health.live} live`} />
              <Legend color="#f2b84b" label={`${health.stub} stub`} />
              <Legend color="#5b6680" label={`${health.missing} not built`} />
            </div>
          </div>
        </section>

        <section className="col-span-12 grid grid-cols-2 gap-4 lg:col-span-7 lg:grid-cols-3">
          <StatCard
            label="Engine"
            value={online ? "ONLINE" : "OFFLINE"}
            valueClass={online ? "text-signal-live" : "text-signal-dim"}
            accent={online ? "live" : "neutral"}
            sub={online ? "v2 runner reporting" : "runner not started"}
          />
          <StatCard label="Crew Readiness" value={`${health.readiness}%`} sub={`${health.live}/${health.total} agents live`} />
          <StatCard label="Journaled Net P&L" value={usd(stats.netPnl)} valueClass={pnlClass(stats.netPnl)} sub={`${stats.closed} closed`} accent={stats.netPnl < 0 ? "risk" : "neutral"} />
          <StatCard label="Win Rate" value={pct(stats.winRate)} sub={`${stats.wins}W / ${stats.losses}L`} />
          <StatCard label="Avg Discipline" value={stats.avgGrade ?? "—"} sub={stats.disciplineScore !== null ? `${stats.disciplineScore}/100 rule-following` : "no grades yet"} />
          <StatCard label="Open Positions" value={String(stats.open)} sub="from journal" />
        </section>
      </div>

      {/* Agent crew grid */}
      <section>
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-200">Agent Crew</h2>
          <span className="text-[11px] text-signal-dim">status derived live from <span className="font-mono">agent_v2/*.py</span></span>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {agents.map((a) => (
            <AgentCardView key={a.id} agent={a} />
          ))}
        </div>
      </section>
    </div>
  );
}

function PageTitle({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div>
      <h1 className="text-xl font-semibold text-slate-100">{title}</h1>
      <p className="text-[13px] text-signal-dim">{subtitle}</p>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1.5 text-signal-dim">
      <span className="h-2 w-2 rounded-full" style={{ background: color }} />
      {label}
    </span>
  );
}
