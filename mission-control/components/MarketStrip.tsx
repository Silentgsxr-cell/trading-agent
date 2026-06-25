import { getSession } from "@/lib/runtime";
import { usd, pnlClass } from "@/lib/format";

// Top "Market Intelligence Strip". Shows real engine state when the v2 runner
// is online; otherwise an honest offline banner (no invented prices).
export async function MarketStrip() {
  const { session, online } = await getSession();

  return (
    <header className="sticky top-0 z-10 flex items-center justify-between border-b border-edge bg-navy-900/85 px-5 py-2.5 backdrop-blur">
      <div className="flex items-center gap-5 text-xs">
        <span className="flex items-center gap-2">
          <span
            className={`h-2 w-2 rounded-full ${online ? "bg-signal-live animate-pulseDot" : "bg-signal-dim"}`}
          />
          <span className="font-medium text-slate-200">Engine</span>
          <span className={online ? "text-signal-live" : "text-signal-dim"}>
            {online ? "ONLINE" : "OFFLINE"}
          </span>
        </span>

        {session ? (
          <>
            <Stat label="Balance" value={usd(session.currentBalance)} />
            <Stat label="Day P&L" value={usd(session.dailyPnl)} cls={pnlClass(session.dailyPnl)} />
            <Stat label="Open" value={String(session.openPositions)} />
            <Stat label="Trades" value={String(session.tradesToday)} />
            {session.halted && (
              <span className="chip border-maroon-400 bg-maroon-600/20 text-maroon-300 animate-riskPulse">
                ◼ HALTED — {session.haltReason}
              </span>
            )}
          </>
        ) : (
          <span className="text-signal-dim">
            v2 runner not running — showing journal + research from disk
          </span>
        )}
      </div>

      <div className="flex items-center gap-3 text-[11px] text-signal-dim">
        <span>15-min ORB · TSLA / QQQ / MSFT / AMZN</span>
        <span className="text-edge">|</span>
        <span>Arizona MST</span>
      </div>
    </header>
  );
}

function Stat({ label, value, cls }: { label: string; value: string; cls?: string }) {
  return (
    <span className="flex items-center gap-1.5">
      <span className="label">{label}</span>
      <span className={`font-mono text-sm ${cls ?? "text-slate-100"}`}>{value}</span>
    </span>
  );
}
