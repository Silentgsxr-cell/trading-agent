import Link from "next/link";

const NAV = [
  { href: "/", label: "Cockpit", glyph: "◎" },
  { href: "/logs", label: "Decision Feed", glyph: "≣" },
  { href: "/memory", label: "Intelligence", glyph: "✦" },
  { href: "/docs", label: "Research", glyph: "❡" },
  { href: "/finance", label: "Finance", glyph: "$" },
];

export function Sidebar() {
  return (
    <aside className="sticky top-0 flex h-screen w-[200px] flex-col border-r border-edge bg-navy-900/80">
      <div className="px-4 py-4">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-maroon-500 text-sm font-bold text-white shadow-risk">
            C
          </span>
          <div className="leading-tight">
            <div className="text-sm font-semibold text-slate-100">ClawOps</div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-signal-dim">Control Center</div>
          </div>
        </div>
      </div>

      <nav className="mt-2 flex flex-col gap-0.5 px-2">
        {NAV.map((n) => (
          <Link
            key={n.href}
            href={n.href}
            className="group flex items-center gap-3 rounded-md px-3 py-2 text-sm text-slate-300 transition hover:bg-navy-700/60 hover:text-white"
          >
            <span className="w-4 text-center text-signal-dim group-hover:text-maroon-300">{n.glyph}</span>
            {n.label}
          </Link>
        ))}
      </nav>

      <div className="mt-auto space-y-2 px-4 py-4">
        <div className="rounded-md border border-maroon-600/40 bg-maroon-600/10 px-3 py-2">
          <div className="label text-maroon-300">Mode</div>
          <div className="text-sm font-semibold text-slate-100">Paper · Read-only</div>
        </div>
        <div className="text-[10px] leading-relaxed text-signal-dim">
          File-system driven. No live orders. Localhost only.
        </div>
      </div>
    </aside>
  );
}
