import { getDecisions } from "@/lib/runtime";
import { getJournal, type JournalTrade } from "@/lib/journal";
import { usd, pnlClass, ago } from "@/lib/format";

export const dynamic = "force-dynamic";

// Decision Feed = the truth layer. Live engine events when online; always the
// journaled round-trips from the real CSV. No interpretation, just reality.
export default async function LogsPage() {
  const [decisions, { trades, exists }] = await Promise.all([getDecisions(80), getJournal()]);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Decision Feed</h1>
        <p className="text-[13px] text-signal-dim">Every signal, veto, and fill — the system's audit trail.</p>
      </div>

      <div className="grid grid-cols-12 gap-5">
        {/* Live engine events */}
        <section className="panel col-span-12 lg:col-span-5">
          <div className="panel-head">
            <h2 className="text-sm font-semibold text-slate-200">Live Engine Events</h2>
            <span className="text-[11px] text-signal-dim">{decisions.length ? `${decisions.length}` : "0"} events</span>
          </div>
          <div className="max-h-[560px] overflow-y-auto p-2">
            {decisions.length === 0 ? (
              <EmptyState
                title="Engine offline"
                body="No state/decisions.jsonl yet. The Phase 2 runner streams signal→risk→execution events here in real time."
              />
            ) : (
              <ul className="space-y-1">
                {decisions.map((d, i) => (
                  <li key={i} className="flex gap-2 rounded-md border border-edge/60 bg-navy-900/40 px-3 py-2 text-[12px]">
                    <KindTag kind={d.kind} />
                    <div className="min-w-0 flex-1">
                      <div className="text-slate-300">{d.message}</div>
                      <div className="mt-0.5 text-[10px] text-signal-dim">{d.agent} · {d.ts}</div>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>

        {/* Journaled trades */}
        <section className="panel col-span-12 lg:col-span-7">
          <div className="panel-head">
            <h2 className="text-sm font-semibold text-slate-200">Journaled Round-Trips</h2>
            <span className="text-[11px] text-signal-dim font-mono">data/journal.csv</span>
          </div>
          <div className="overflow-x-auto">
            {!exists ? (
              <EmptyState title="No journal yet" body="data/journal.csv not found." />
            ) : trades.length === 0 ? (
              <EmptyState title="Journal empty" body="No trades logged yet." />
            ) : (
              <table className="w-full text-left text-[12px]">
                <thead>
                  <tr className="border-b border-edge text-[10px] uppercase tracking-wide text-signal-dim">
                    <th className="px-3 py-2">Date</th>
                    <th className="px-3 py-2">Ticker</th>
                    <th className="px-3 py-2">Strategy</th>
                    <th className="px-3 py-2 text-right">Entry</th>
                    <th className="px-3 py-2 text-right">Exit</th>
                    <th className="px-3 py-2 text-right">P&L</th>
                    <th className="px-3 py-2 text-center">Disc.</th>
                    <th className="px-3 py-2 text-center">Grade</th>
                  </tr>
                </thead>
                <tbody>
                  {trades.map((t, i) => (
                    <TradeRow key={i} t={t} />
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function TradeRow({ t }: { t: JournalTrade }) {
  const flags: string[] = [];
  if (t.wasPlanned === false) flags.push("unplanned");
  if (t.chased) flags.push("chased");
  if (t.followedStop === false) flags.push("broke stop");
  return (
    <tr className="border-b border-edge/40 hover:bg-navy-800/40">
      <td className="px-3 py-2 font-mono text-slate-400">{t.date}</td>
      <td className="px-3 py-2 font-semibold text-slate-200">{t.ticker}</td>
      <td className="px-3 py-2 text-slate-400">{t.strategy}</td>
      <td className="px-3 py-2 text-right font-mono text-slate-300">{t.entry ?? "—"}</td>
      <td className="px-3 py-2 text-right font-mono text-slate-300">{t.exit ?? "—"}</td>
      <td className={`px-3 py-2 text-right font-mono ${pnlClass(t.pnl)}`}>{t.pnl === null ? "open" : usd(t.pnl)}</td>
      <td className="px-3 py-2 text-center">
        {flags.length ? (
          <span className="chip border-maroon-400/40 bg-maroon-600/15 text-maroon-300">{flags[0]}</span>
        ) : (
          <span className="text-signal-live">✓</span>
        )}
      </td>
      <td className="px-3 py-2 text-center">
        <GradePill grade={t.grade} />
      </td>
    </tr>
  );
}

function GradePill({ grade }: { grade: string }) {
  if (!grade) return <span className="text-signal-dim">—</span>;
  const tone =
    grade === "A" ? "border-signal-live/40 text-signal-live" :
    grade === "B" ? "border-signal-live/25 text-slate-200" :
    grade === "C" ? "border-signal-warn/40 text-signal-warn" :
    "border-maroon-400/40 text-maroon-300";
  return <span className={`chip ${tone}`}>{grade}</span>;
}

function KindTag({ kind }: { kind: string }) {
  const map: Record<string, string> = {
    approved: "border-signal-live/40 text-signal-live",
    open: "border-signal-live/40 text-signal-live",
    rejected: "border-maroon-400/40 text-maroon-300",
    halt: "border-maroon-400/50 text-maroon-300",
    signal: "border-signal-warn/40 text-signal-warn",
    close: "border-edge text-slate-300",
    info: "border-edge text-signal-dim",
  };
  return <span className={`chip h-fit ${map[kind] ?? map.info}`}>{kind}</span>;
}

function EmptyState({ title, body }: { title: string; body: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 px-4 py-12 text-center">
      <div className="text-sm font-medium text-slate-300">{title}</div>
      <div className="max-w-sm text-[12px] text-signal-dim">{body}</div>
    </div>
  );
}
