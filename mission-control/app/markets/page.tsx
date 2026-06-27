import { promises as fs } from "node:fs";
import path from "node:path";
import { PROJECT_ROOT } from "@/lib/config";
import { TradingViewChart } from "./TradingViewChart";

export const dynamic = "force-dynamic";

async function getWatchlist(): Promise<string[]> {
  try {
    const raw    = await fs.readFile(path.join(PROJECT_ROOT, "data", "daitaos_config.json"), "utf8");
    const config = JSON.parse(raw) as { watchlist?: string[] };
    return config.watchlist ?? ["TSLA", "QQQ", "SPY", "NVDA", "AAPL"];
  } catch {
    return ["TSLA", "QQQ", "SPY", "NVDA", "AAPL"];
  }
}

export default async function MarketsPage() {
  const watchlist = await getWatchlist();

  return (
    <div className="flex h-full flex-col gap-3">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">MARKETS</h1>
        <p className="text-[13px] text-signal-dim">
          Live chart — TSLA default · EMA 9 · VWAP · Volume · NYSE/ET timezone
        </p>
      </div>
      <TradingViewChart watchlist={watchlist} defaultSymbol="TSLA" />
    </div>
  );
}
