export function StatCard({
  label,
  value,
  sub,
  valueClass,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  valueClass?: string;
  accent?: "live" | "risk" | "neutral";
}) {
  const ring =
    accent === "risk" ? "border-maroon-600/40" : accent === "live" ? "border-signal-live/30" : "border-edge";
  return (
    <div className={`panel ${ring} p-4`}>
      <div className="label">{label}</div>
      <div className={`mt-1 font-mono text-2xl font-semibold ${valueClass ?? "text-slate-100"}`}>{value}</div>
      {sub && <div className="mt-0.5 text-[11px] text-signal-dim">{sub}</div>}
    </div>
  );
}
