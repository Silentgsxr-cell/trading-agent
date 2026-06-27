export const dynamic = "force-dynamic";

export default function SystemPage() {
  return (
    <div className="flex h-64 flex-col items-center justify-center gap-3">
      <div className="text-3xl opacity-30">⚙</div>
      <div className="text-sm font-semibold text-slate-200">SYSTEM</div>
      <div className="text-[12px] text-signal-dim">Backend health monitor — coming in a future phase</div>
    </div>
  );
}
