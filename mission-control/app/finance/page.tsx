import { getFinance } from "@/lib/finance";
import { getJournal } from "@/lib/journal";
import { FinanceEditor } from "./FinanceEditor";
import { usd, pnlClass } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function FinancePage() {
  const [finance, { trades }] = await Promise.all([getFinance(), getJournal()]);

  const todayStr = new Date().toISOString().slice(0, 10);
  const weekAgoStr = new Date(Date.now() - 7 * 86400_000).toISOString().slice(0, 10);
  const monthStr = todayStr.slice(0, 7);

  const closed = trades.filter((t) => t.pnl !== null);
  const sum = (ts: typeof closed) => Math.round(ts.reduce((s, t) => s + (t.pnl ?? 0), 0) * 100) / 100;

  const todayTrades  = closed.filter((t) => t.date === todayStr);
  const weekTrades   = closed.filter((t) => t.date >= weekAgoStr);
  const monthTrades  = closed.filter((t) => t.date.startsWith(monthStr));

  const pnlRows = [
    { label: "Today",      value: sum(todayTrades),  sub: `${todayTrades.length} trade${todayTrades.length !== 1 ? "s" : ""}` },
    { label: "This Week",  value: sum(weekTrades),   sub: `${weekTrades.length} trade${weekTrades.length !== 1 ? "s" : ""}` },
    { label: "This Month", value: sum(monthTrades),  sub: `${monthTrades.length} trade${monthTrades.length !== 1 ? "s" : ""}` },
    { label: "All Time",   value: sum(closed),        sub: `${closed.length} closed` },
  ];

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Finance</h1>
        <p className="text-[13px] text-signal-dim">
          Net worth · accounts · debt · budget · trading P&amp;L
        </p>
      </div>

      <FinanceEditor initial={finance} />

      {/* Trading P&L — read-only, sourced from journal.csv */}
      <section className="panel">
        <div className="panel-head">
          <h2 className="text-sm font-semibold text-slate-200">Trading P&amp;L</h2>
          <span className="text-[11px] text-signal-dim">journal.csv · read-only</span>
        </div>
        <div className="grid grid-cols-2 gap-4 p-4 sm:grid-cols-4">
          {pnlRows.map(({ label, value, sub }) => (
            <div key={label} className="panel p-4">
              <div className="label">{label}</div>
              <div className={`mt-1 font-mono text-xl font-semibold ${pnlClass(value)}`}>
                {usd(value)}
              </div>
              <div className="mt-0.5 text-[11px] text-signal-dim">{sub}</div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
