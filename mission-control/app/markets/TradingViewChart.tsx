"use client";
import { useEffect, useRef, useState, useId } from "react";

declare global {
  interface Window {
    TradingView?: {
      widget: new (config: TvConfig) => void;
    };
  }
}

interface TvConfig {
  container_id:     string;
  width:            string | number;
  height:           number;
  symbol:           string;
  interval:         string;
  timezone:         string;
  theme:            "dark" | "light";
  style:            string;
  locale:           string;
  toolbar_bg:       string;
  enable_publishing: boolean;
  allow_symbol_change: boolean;
  hide_side_toolbar: boolean;
  save_image:       boolean;
  studies:          string[];
  overrides:        Record<string, string | number | boolean>;
  studies_overrides: Record<string, number | string | boolean>;
}

const TV_SCRIPT_SRC = "https://s3.tradingview.com/tv.js";

const INTERVALS = [
  { label: "2m",  value: "2"  },
  { label: "15m", value: "15" },
  { label: "1H",  value: "60" },
  { label: "1D",  value: "D"  },
] as const;

type Interval = typeof INTERVALS[number]["value"];

const OVERRIDES: TvConfig["overrides"] = {
  "paneProperties.background":              "#070b16",
  "paneProperties.backgroundType":          "solid",
  "paneProperties.vertGridProperties.color": "#1c2740",
  "paneProperties.horzGridProperties.color": "#1c2740",
  "scalesProperties.textColor":             "#5b6680",
  "scalesProperties.lineColor":             "#1c2740",
  "mainSeriesProperties.candleStyle.upColor":          "#3ddc97",
  "mainSeriesProperties.candleStyle.downColor":        "#c02a44",
  "mainSeriesProperties.candleStyle.borderUpColor":    "#3ddc97",
  "mainSeriesProperties.candleStyle.borderDownColor":  "#c02a44",
  "mainSeriesProperties.candleStyle.wickUpColor":      "#3ddc97",
  "mainSeriesProperties.candleStyle.wickDownColor":    "#c02a44",
  "mainSeriesProperties.candleStyle.drawBorder":       true,
};

const STUDIES_OVERRIDES: TvConfig["studies_overrides"] = {
  "moving average exp.length":            9,
  "moving average exp.plot.color":        "#f2b84b",
  "moving average exp.plot.linewidth":    1.5,
  "volume.volume.color.0":               "#c02a44cc",
  "volume.volume.color.1":               "#3ddc97cc",
  "volume.show ma":                      false,
};

export function TradingViewChart({
  watchlist,
  defaultSymbol = "TSLA",
}: {
  watchlist:     string[];
  defaultSymbol?: string;
}) {
  const uid              = useId().replace(/:/g, "");
  const containerId      = `tv_chart_${uid}`;
  const containerRef     = useRef<HTMLDivElement>(null);
  const scriptLoadedRef  = useRef(false);
  const widgetRef        = useRef<boolean>(false);

  const [symbol,   setSymbol]   = useState(defaultSymbol);
  const [interval, setInterval] = useState<Interval>("15");

  function buildWidget() {
    if (!window.TradingView || !document.getElementById(containerId)) return;
    // Clear any existing content
    const el = document.getElementById(containerId);
    if (el) el.innerHTML = "";
    widgetRef.current = true;

    new window.TradingView.widget({
      container_id:      containerId,
      width:             "100%",
      height:            560,
      symbol:            symbol,
      interval:          interval,
      timezone:          "America/New_York",
      theme:             "dark",
      style:             "1",
      locale:            "en",
      toolbar_bg:        "#0d1426",
      enable_publishing: false,
      allow_symbol_change: false,
      hide_side_toolbar: false,
      save_image:        false,
      studies:           [
        "Volume@tv-studioideas",
        "MAExp@tv-studioideas",
        "VWAP@tv-studioideas",
      ],
      overrides:         OVERRIDES,
      studies_overrides: STUDIES_OVERRIDES,
    });
  }

  useEffect(() => {
    if (typeof window === "undefined") return;

    if (window.TradingView) {
      buildWidget();
      return;
    }

    if (scriptLoadedRef.current) {
      // Script tag already added but TV not loaded yet — poll with recursive setTimeout
      let stopped = false;
      const poll = () => {
        if (stopped) return;
        if (window.TradingView) { buildWidget(); return; }
        setTimeout(poll, 100);
      };
      setTimeout(poll, 100);
      return () => { stopped = true; };
    }

    scriptLoadedRef.current = true;
    const script = document.createElement("script");
    script.src   = TV_SCRIPT_SRC;
    script.async = true;
    script.onload = buildWidget;
    document.head.appendChild(script);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol, interval]);

  return (
    <div className="flex h-full flex-col gap-3">

      {/* ── Controls ───────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3">

        {/* Symbol strip */}
        <div className="flex flex-wrap gap-1.5">
          {watchlist.map((sym) => (
            <button
              key={sym}
              onClick={() => setSymbol(sym)}
              className={`rounded px-2.5 py-1 font-mono text-[11px] font-semibold transition ${
                symbol === sym
                  ? "bg-maroon-600/80 text-white"
                  : "border border-edge bg-navy-800/60 text-slate-400 hover:text-slate-100"
              }`}
            >
              {sym}
            </button>
          ))}
        </div>

        {/* Divider */}
        <div className="h-5 w-px bg-edge" />

        {/* Interval strip */}
        <div className="flex gap-1">
          {INTERVALS.map((iv) => (
            <button
              key={iv.value}
              onClick={() => setInterval(iv.value)}
              className={`rounded px-2.5 py-1 text-[11px] font-semibold transition ${
                interval === iv.value
                  ? "bg-navy-600/80 text-slate-100"
                  : "border border-edge bg-navy-800/60 text-signal-dim hover:text-slate-300"
              }`}
            >
              {iv.label}
            </button>
          ))}
        </div>

        <div className="ml-auto flex items-center gap-2 text-[10px] text-signal-dim">
          <span className="font-mono">{symbol}</span>
          <span>·</span>
          <span>EMA 9 · VWAP · Volume</span>
          <span>·</span>
          <span>NYSE/ET</span>
        </div>
      </div>

      {/* ── Chart container ────────────────────────────────────────── */}
      <div
        className="flex-1 overflow-hidden rounded-xl border border-edge"
        style={{ minHeight: 560 }}
      >
        <div id={containerId} ref={containerRef} style={{ width: "100%", height: "100%" }} />
      </div>

      <p className="text-[9px] text-signal-dim/60">
        Chart data via TradingView. For reference only — not financial advice.
        Paper trading only.
      </p>
    </div>
  );
}
