"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

interface CrewHealth {
  total: number;
  live: number;
  stub: number;
  missing: number;
  thinking: number;
  errors: number;
  idle: number;
}

interface NavItem {
  href: string;
  label: string;
  glyph: string;
  badge?: boolean;
}

interface NavSection {
  label: string | null;
  items: NavItem[];
}

// Grouped by department (Chief of Staff's org chart), not flat — matches
// the vision doc's "dashboard organized by agent ownership." Only routes
// that actually exist go in here; don't add a nav item before its page.
const NAV_SECTIONS: NavSection[] = [
  {
    label: null, // ungrouped — home
    items: [{ href: "/chief", label: "CHIEF", glyph: "⌘" }],
  },
  {
    label: "Trading",
    items: [
      { href: "/markets", label: "MARKETS", glyph: "◈" },
      { href: "/signals", label: "SIGNALS", glyph: "⊕" },
      { href: "/risk",    label: "RISK",    glyph: "⛊" },
      { href: "/logs",    label: "JOURNAL", glyph: "≡" },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { href: "/memory", label: "NEWS & RESEARCH", glyph: "✦" },
      { href: "/docs",   label: "VAULT DOCS",       glyph: "▤" },
    ],
  },
  {
    label: "Personal",
    items: [
      { href: "/life",    label: "LIFE",    glyph: "♡" },
      { href: "/finance", label: "FINANCE", glyph: "$" },
    ],
  },
  {
    label: "System",
    items: [
      { href: "/suggestions", label: "SUGGESTIONS", glyph: "◐" },
      { href: "/dev",          label: "DEV",         glyph: "⌬", badge: true },
      { href: "/system",       label: "SYSTEM",      glyph: "⚙" },
    ],
  },
];

const NAV = NAV_SECTIONS.flatMap((s) => s.items);

export function Sidebar() {
  const pathname = usePathname();
  const [badge, setBadge] = useState(0);
  const [health, setHealth] = useState<CrewHealth | null>(null);

  useEffect(() => {
    let mounted = true;
    async function poll() {
      try {
        const r = await fetch("/api/suggestions/stats");
        if (r.ok && mounted) {
          const d = await r.json();
          setBadge(d.unreviewed ?? 0);
        }
      } catch { /* dashboard's own API — should always be reachable */ }
    }
    poll();
    const id = setInterval(poll, 30_000);
    return () => { mounted = false; clearInterval(id); };
  }, []);

  useEffect(() => {
    let mounted = true;
    async function pollHealth() {
      try {
        const r = await fetch("/api/agents");
        if (r.ok && mounted) {
          const d = await r.json();
          setHealth(d.health ?? null);
        }
      } catch { /* dashboard's own API — should always be reachable */ }
    }
    pollHealth();
    const id = setInterval(pollHealth, 15_000);
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

      {health && (
        <div className="mx-4 mb-3 rounded-md border border-edge bg-navy-800/50 px-3 py-2">
          <div className="flex items-center justify-between text-[9px] uppercase tracking-[0.16em] text-signal-dim">
            <span>Agents</span>
            <span>{health.live}/{health.total} live</span>
          </div>
          <div className="mt-1.5 flex h-1.5 w-full overflow-hidden rounded-full bg-navy-700">
            {health.thinking > 0 && (
              <div className="bg-blue-400 animate-pulseDot" style={{ width: `${(health.thinking / health.total) * 100}%` }} />
            )}
            {health.idle > 0 && (
              <div className="bg-signal-live/60" style={{ width: `${(health.idle / health.total) * 100}%` }} />
            )}
            {health.errors > 0 && (
              <div className="bg-maroon-400" style={{ width: `${(health.errors / health.total) * 100}%` }} />
            )}
            {health.stub > 0 && (
              <div className="bg-signal-warn/50" style={{ width: `${(health.stub / health.total) * 100}%` }} />
            )}
            {health.missing > 0 && (
              <div className="bg-navy-700" style={{ width: `${(health.missing / health.total) * 100}%` }} />
            )}
          </div>
          <div className="mt-1.5 flex flex-wrap gap-x-2.5 gap-y-0.5 text-[9.5px] text-signal-dim">
            <span className="text-blue-300">Thinking {health.thinking}</span>
            <span>Idle {health.idle}</span>
            {health.errors > 0 && <span className="text-maroon-300">Errors {health.errors}</span>}
            <span className="text-signal-warn/80">Stub {health.stub}</span>
          </div>
        </div>
      )}

      <nav className="mt-1 flex flex-col gap-2.5 px-2">
        {NAV_SECTIONS.map((section, si) => (
          <div key={si} className="flex flex-col gap-0.5">
            {section.label && (
              <div className="px-3 pb-0.5 pt-1 text-[9.5px] font-semibold uppercase tracking-[0.18em] text-signal-dim/60">
                {section.label}
              </div>
            )}
            {section.items.map((n) => {
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
          </div>
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
