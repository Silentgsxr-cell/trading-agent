export const usd = (n: number | null | undefined): string => {
  if (n === null || n === undefined) return "—";
  const sign = n < 0 ? "-" : "";
  return `${sign}$${Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

export const pct = (n: number | null | undefined): string =>
  n === null || n === undefined ? "—" : `${n}%`;

export const ago = (ms: number): string => {
  const diff = Date.now() - ms;
  const m = Math.floor(diff / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
};

export const pnlClass = (n: number | null | undefined): string =>
  n === null || n === undefined ? "text-signal-dim" : n > 0 ? "text-signal-live" : n < 0 ? "text-maroon-300" : "text-slate-400";
