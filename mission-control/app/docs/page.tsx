import { getDocs } from "@/lib/vault";
import { ago } from "@/lib/format";

export const dynamic = "force-dynamic";

// Research = institutional brain archive. Trading-relevant notes only —
// finances / EIN / family / LLC are denylisted in lib/config.ts.
export default async function DocsPage() {
  const docs = await getDocs();

  return (
    <div className="space-y-5">
      <div className="flex items-end justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Research Library</h1>
          <p className="text-[13px] text-signal-dim">Strategy, handoffs, and trading notes from the vault & project.</p>
        </div>
        <span className="chip border-edge text-signal-dim">{docs.length} docs · sensitive notes excluded</span>
      </div>

      {docs.length === 0 ? (
        <div className="panel p-12 text-center">
          <div className="text-sm font-medium text-slate-300">No trading research found</div>
          <div className="mt-1 text-[12px] text-signal-dim">
            Looked in the vault root and project README/HANDOFF. Add notes tagged trading/strategy to populate this.
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
          {docs.map((d) => (
            <article key={d.source + d.relPath} className="panel flex flex-col gap-2 p-4 transition hover:border-maroon-600/40">
              <div className="flex items-start justify-between">
                <h2 className="text-sm font-semibold text-slate-100">{d.title}</h2>
                <span className={`chip ${d.source === "vault" ? "border-edge text-signal-dim" : "border-signal-live/30 text-signal-live"}`}>
                  {d.source}
                </span>
              </div>
              <p className="text-[12px] leading-relaxed text-slate-400">{d.excerpt || "—"}</p>
              {d.tags.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {d.tags.map((t) => (
                    <span key={t} className="chip border-edge text-signal-dim">#{t}</span>
                  ))}
                </div>
              )}
              <div className="mt-auto flex items-center justify-between pt-1 text-[10px] text-signal-dim">
                <span className="font-mono">{d.relPath}</span>
                <span>{ago(d.modified)}</span>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
