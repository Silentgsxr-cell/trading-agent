import { getJournal } from "@/lib/journal";
import { getDocs } from "@/lib/vault";
import { usd, pnlClass, ago } from "@/lib/format";

export const dynamic = "force-dynamic";

// Intelligence = the morning-briefing terminal. A chronological feed distilled
// from real journal lessons/grades + recently-touched research notes.
export default async function MemoryPage() {
  const [{ trades, stats }, docs] = await Promise.all([getJournal(), getDocs()]);

  const lessons = trades.filter((t) => t.lesson && t.lesson.trim() !== "");
  const recentDocs = docs.slice(0, 5);

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Daily Intelligence</h1>
        <p className="text-[13px] text-signal-dim">What the system has learned — distilled from real trades and research.</p>
      </div>

      {/* What matters today */}
      <section className="panel">
        <div className="panel-head">
          <h2 className="text-sm font-semibold text-slate-200">What Matters Today</h2>
        </div>
        <div className="grid grid-cols-1 gap-3 p-4 sm:grid-cols-3">
          <Brief label="Edge so far" value={usd(stats.netPnl)} cls={pnlClass(stats.netPnl)} note={`${stats.winRate ?? "—"}% win rate over ${stats.closed} closed`} />
          <Brief label="Discipline" value={stats.avgGrade ?? "—"} note={stats.disciplineScore !== null ? `${stats.disciplineScore}/100 rule adherence` : "grade your trades to populate"} />
          <Brief label="Focus" value="15-min ORB" note="TSLA primary · QQQ / MSFT / AMZN" />
        </div>
      </section>

      <div className="grid grid-cols-12 gap-5">
        {/* Lessons feed */}
        <section className="panel col-span-12 lg:col-span-7">
          <div className="panel-head">
            <h2 className="text-sm font-semibold text-slate-200">Lessons & Notes from the Tape</h2>
            <span className="text-[11px] text-signal-dim">{lessons.length} logged</span>
          </div>
          <div className="p-2">
            {lessons.length === 0 ? (
              <p className="px-3 py-10 text-center text-[12px] text-signal-dim">
                No lessons logged in the journal yet. The Review Agent (Phase 2) will auto-summarize each session here.
              </p>
            ) : (
              <ul className="space-y-2">
                {lessons.map((t, i) => (
                  <li key={i} className="rounded-md border border-edge/60 bg-navy-900/40 px-3 py-2">
                    <div className="flex items-center justify-between text-[11px] text-signal-dim">
                      <span>{t.date} · {t.ticker} {t.strategy}</span>
                      <span className={`font-mono ${pnlClass(t.pnl)}`}>{t.pnl === null ? "open" : usd(t.pnl)}</span>
                    </div>
                    <p className="mt-1 text-[13px] text-slate-300">{t.lesson}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>

        {/* Recent research touches */}
        <section className="panel col-span-12 lg:col-span-5">
          <div className="panel-head">
            <h2 className="text-sm font-semibold text-slate-200">Recently Touched Research</h2>
          </div>
          <div className="p-2">
            {recentDocs.length === 0 ? (
              <p className="px-3 py-10 text-center text-[12px] text-signal-dim">No research notes found.</p>
            ) : (
              <ul className="space-y-1">
                {recentDocs.map((d) => (
                  <li key={d.relPath} className="flex items-center justify-between rounded-md px-3 py-2 hover:bg-navy-800/40">
                    <span className="text-[13px] text-slate-300">{d.title}</span>
                    <span className="text-[10px] text-signal-dim">{ago(d.modified)}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function Brief({ label, value, note, cls }: { label: string; value: string; note: string; cls?: string }) {
  return (
    <div className="rounded-md border border-edge bg-navy-900/40 p-3">
      <div className="label">{label}</div>
      <div className={`mt-1 font-mono text-lg font-semibold ${cls ?? "text-slate-100"}`}>{value}</div>
      <div className="mt-0.5 text-[11px] text-signal-dim">{note}</div>
    </div>
  );
}
