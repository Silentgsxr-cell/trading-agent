"use client";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";

const FLASK = process.env.NEXT_PUBLIC_FLASK_URL ?? "http://localhost:5000";

const TAB_NAMES: Record<string, string> = {
  "/":           "cockpit",
  "/logs":       "logs",
  "/memory":     "intelligence",
  "/docs":       "research",
  "/finance":    "finance",
  "/dev":        "dev_queue",
  "/suggestions":"suggestions",
};

export function TabTracker() {
  const pathname   = usePathname();
  const enterRef   = useRef<number>(Date.now());
  const prevRef    = useRef<string>("");

  useEffect(() => {
    const tabName = TAB_NAMES[pathname] ?? pathname.replace(/\//g, "_").slice(1);
    const now     = Date.now();

    // Report duration for previous tab
    if (prevRef.current) {
      const duration_ms = now - enterRef.current;
      fetch(`${FLASK}/api/analytics/tab`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tab:         prevRef.current,
          timestamp:   new Date(enterRef.current).toISOString(),
          duration_ms,
        }),
      }).catch(() => {}); // fire-and-forget, never throw
    }

    prevRef.current  = tabName;
    enterRef.current = now;
  }, [pathname]);

  return null; // renders nothing
}
