"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const FLASK = process.env.NEXT_PUBLIC_FLASK_URL ?? "http://localhost:5000";

const NAV = [
  { href: "/chief",   label: "CHIEF",        glyph: "⌘"  },
  { href: "/markets", label: "MARKETS",       glyph: "◈"  },
  { href: "/signals", label: "SIGNALS",       glyph: "⊕"  },
  { href: "/risk",    label: "RISK",          glyph: "⛊"  },
  { href: "/logs",    label: "JOURNAL",       glyph: "≡"  },
  { href: "/memory",  label: "INTELLIGENCE",  glyph: "✦"  },
  { href: "/life",    label: "LIFE",          glyph: "♡"  },
  { href: "/dev",     label: "DEV",           glyph: "⌬",  badge: true },
  { href: "/system",  label: "SYSTEM",        glyph: "⚙"  },
] as const;

export function Sidebar() {
  const pathname = usePathname();
  const [badge, setBadge] = useState(0);

  useEffect(() => {
    let mounted = true;
    async function poll() {
      try {
        const r = await fetch(`${FLASK}/api/suggestions/stats`);
        if (r.ok && mounted) {
          const d = await r.json();
          setBadge(d.unreviewed ?? 0);
        }
      } catch { /* flask offline */ }
    }
    poll();
    const id = setInterval(poll, 30_000);
    return () => { mounted = false; clearInterval(id); };
  }, []);

  return (
    <aside className="sticky top-0 flex h-screen w-[190px] flex-col border-r border-edge bg-navy-900/80">
      <div className="px-4 py-4">
        <div className="flex items-center gap-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-md bg-maroon-500 text-sm font-bold text-white shadow-risk">
            C
          </span>
          <div className="leading-tight">
            <div className="text-sm font-semibold text-slate-100">ClawOps</div>
            <div className="text-[10px] uppercase tracking-[0.18em] text-signal-dim">Mission Control</div>
          </div>
        </div>
      </div>

      <nav className="mt-1 flex flex-col gap-0.5 px-2">
        {NAV.map((n) => {
          const active =
            n.href === "/chief"
              ? pathname === "/chief" || pathname === "/"
              : pathname.startsWith(n.href);
          const hasBadge = "badge" in n && n.badge;
          return (
            <Link
              key={n.href}
              href={n.href}
              className={`group relative flex items-center gap-3 rounded-md px-3 py-2 text-[13px] transition ${
                active
                  ? "bg-navy-700/80 font-medium text-white"
                  : "text-slate-400 hover:bg-navy-700/60 hover:text-white"
              }`}
            >
              {active && (
                <span className="absolute inset-y-1.5 left-0 w-0.5 rounded-r bg-maroon-400" />
              )}
              <span
                className={`w-4 text-center text-[12px] ${
                  active ? "text-maroon-300" : "text-signal-dim group-hover:text-maroon-300"
                }`}
              >
                {n.glyph}
              </span>
              {n.label}
              {hasBadge && badge > 0 && (
                <span className="ml-auto flex h-4 min-w-[16px] items-center justify-center rounded-full bg-maroon-500 px-1 text-[9px] font-bold text-white shadow-risk">
                  {badge > 99 ? "99+" : badge}
                </span>
              )}
            </Link>
          );
        })}
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
