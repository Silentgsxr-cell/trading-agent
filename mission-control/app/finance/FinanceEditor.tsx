"use client";

import { useState, useTransition } from "react";
import type { FinanceData } from "@/lib/finance";
import { saveFinanceAction } from "./actions";
import { usd } from "@/lib/format";

interface EditState {
  type: "account" | "debt" | "budget-set" | "budget-add";
  id: string;
  f: Record<string, string>;
}

function debtBarColor(balance: number, original: number): string {
  if (original === 0) return "bg-signal-dim";
  const r = balance / original;
  if (r > 0.8) return "bg-maroon-500";
  if (r > 0.5) return "bg-signal-warn";
  return "bg-signal-live";
}

function debtTextColor(balance: number, original: number): string {
  if (original === 0) return "text-signal-dim";
  const r = balance / original;
  if (r > 0.8) return "text-maroon-300";
  if (r > 0.5) return "text-signal-warn";
  return "text-signal-live";
}

function budgetBarColor(spent: number, budget: number): string {
  if (budget === 0) return "bg-signal-dim";
  const r = spent / budget;
  if (r > 1) return "bg-maroon-500";
  if (r > 0.8) return "bg-signal-warn";
  return "bg-signal-live";
}

const today = () => new Date().toISOString().slice(0, 10);

export function FinanceEditor({ initial }: { initial: FinanceData }) {
  const [data, setData] = useState(initial);
  const [edit, setEdit] = useState<EditState | null>(null);
  const [isPending, startTransition] = useTransition();

  function commit(updated: FinanceData) {
    setData(updated);
    setEdit(null);
    startTransition(() => saveFinanceAction(updated));
  }

  const totalAssets = data.accounts.reduce((s, a) => s + a.balance, 0);
  const totalDebts = data.debts.reduce((s, d) => s + d.balance, 0);
  const netWorth = totalAssets - totalDebts;

  const isEdit = (type: EditState["type"], id: string) =>
    edit?.type === type && edit.id === id;

  return (
    <div className="space-y-5">

      {/* ── Net Worth ──────────────────────────────────────────────── */}
      <section className="panel p-5">
        <div className="label mb-1">Net Worth Snapshot</div>
        <div className={`font-mono text-4xl font-bold ${netWorth >= 0 ? "text-signal-live" : "text-maroon-300"}`}>
          {usd(netWorth)}
        </div>
        <div className="mt-2 flex gap-6 text-sm">
          <span className="text-signal-dim">
            Assets <span className="font-mono text-slate-200">{usd(totalAssets)}</span>
          </span>
          <span className="text-signal-dim">
            Debt <span className="font-mono text-maroon-300">{usd(totalDebts)}</span>
          </span>
        </div>
        {isPending && <div className="mt-1 text-[10px] text-signal-dim">Saving…</div>}
      </section>

      {/* ── Accounts ───────────────────────────────────────────────── */}
      <section className="panel">
        <div className="panel-head">
          <h2 className="text-sm font-semibold text-slate-200">Accounts</h2>
          <span className="text-[11px] text-signal-dim">{usd(totalAssets)} total</span>
        </div>
        <div className="grid grid-cols-1 gap-4 p-4 sm:grid-cols-3">
          {data.accounts.map((acc) => (
            <div key={acc.id} className="panel p-4">
              <div className="label">{acc.role}</div>
              <div className="mt-0.5 text-sm font-semibold text-slate-100">{acc.name}</div>

              {isEdit("account", acc.id) ? (
                <div className="mt-3 space-y-2">
                  <input
                    type="number"
                    autoFocus
                    className="w-full rounded border border-edge bg-navy-800 px-2 py-1.5 font-mono text-sm text-slate-100 focus:border-signal-live focus:outline-none"
                    placeholder="New balance"
                    value={edit!.f.balance}
                    onChange={(e) => setEdit({ ...edit!, f: { balance: e.target.value } })}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        const val = parseFloat(edit!.f.balance);
                        if (!isNaN(val))
                          commit({ ...data, accounts: data.accounts.map((a) => a.id === acc.id ? { ...a, balance: val, updatedAt: today() } : a) });
                      }
                      if (e.key === "Escape") setEdit(null);
                    }}
                  />
                  <div className="flex gap-2">
                    <button
                      className="flex-1 rounded bg-signal-live/20 px-2 py-1 text-xs text-signal-live hover:bg-signal-live/30"
                      onClick={() => {
                        const val = parseFloat(edit!.f.balance);
                        if (!isNaN(val))
                          commit({ ...data, accounts: data.accounts.map((a) => a.id === acc.id ? { ...a, balance: val, updatedAt: today() } : a) });
                      }}
                    >Save</button>
                    <button
                      className="flex-1 rounded bg-navy-700 px-2 py-1 text-xs text-signal-dim hover:text-slate-200"
                      onClick={() => setEdit(null)}
                    >Cancel</button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="mt-2 font-mono text-2xl font-semibold text-slate-100">{usd(acc.balance)}</div>
                  <div className="mt-0.5 text-[10px] text-signal-dim">Updated {acc.updatedAt}</div>
                  <button
                    className="mt-3 w-full rounded border border-edge px-2 py-1 text-xs text-signal-dim hover:border-signal-live/40 hover:text-slate-200"
                    onClick={() => setEdit({ type: "account", id: acc.id, f: { balance: String(acc.balance) } })}
                  >Edit Balance</button>
                </>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* ── Debt Tracker ───────────────────────────────────────────── */}
      <section className="panel">
        <div className="panel-head">
          <h2 className="text-sm font-semibold text-slate-200">Debt Tracker</h2>
          <span className="text-[11px] text-signal-dim">{usd(totalDebts)} remaining</span>
        </div>
        <div className="space-y-3 p-4">
          {data.debts.map((debt) => {
            const pct = debt.original > 0 ? Math.min(1, debt.balance / debt.original) : 0;
            return (
              <div key={debt.id} className="panel p-4">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-200">{debt.name}</span>
                  <span className={`font-mono text-sm font-semibold ${debtTextColor(debt.balance, debt.original)}`}>
                    {usd(debt.balance)}
                  </span>
                </div>
                <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-navy-700">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${debtBarColor(debt.balance, debt.original)}`}
                    style={{ width: `${pct * 100}%` }}
                  />
                </div>
                <div className="mt-1 flex justify-between text-[10px] text-signal-dim">
                  <span>
                    {debt.original > 0
                      ? `${Math.round(pct * 100)}% remaining`
                      : "Set original balance to enable tracking"}
                  </span>
                  <span>of {usd(debt.original)}</span>
                </div>

                {isEdit("debt", debt.id) ? (
                  <div className="mt-3 space-y-2">
                    <div className="flex gap-2">
                      <div className="flex-1">
                        <div className="label mb-1">Current Balance</div>
                        <input
                          type="number"
                          autoFocus
                          className="w-full rounded border border-edge bg-navy-800 px-2 py-1.5 font-mono text-sm text-slate-100 focus:border-signal-live focus:outline-none"
                          value={edit!.f.balance}
                          onChange={(e) => setEdit({ ...edit!, f: { ...edit!.f, balance: e.target.value } })}
                        />
                      </div>
                      <div className="flex-1">
                        <div className="label mb-1">Original Balance</div>
                        <input
                          type="number"
                          className="w-full rounded border border-edge bg-navy-800 px-2 py-1.5 font-mono text-sm text-slate-100 focus:border-signal-live focus:outline-none"
                          value={edit!.f.original}
                          onChange={(e) => setEdit({ ...edit!, f: { ...edit!.f, original: e.target.value } })}
                        />
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <button
                        className="flex-1 rounded bg-signal-live/20 px-2 py-1 text-xs text-signal-live hover:bg-signal-live/30"
                        onClick={() => {
                          const bal = parseFloat(edit!.f.balance);
                          const orig = parseFloat(edit!.f.original);
                          if (!isNaN(bal))
                            commit({ ...data, debts: data.debts.map((d) => d.id === debt.id ? { ...d, balance: bal, original: isNaN(orig) ? d.original : orig } : d) });
                        }}
                      >Save</button>
                      <button
                        className="flex-1 rounded bg-navy-700 px-2 py-1 text-xs text-signal-dim hover:text-slate-200"
                        onClick={() => setEdit(null)}
                      >Cancel</button>
                    </div>
                  </div>
                ) : (
                  <button
                    className="mt-3 w-full rounded border border-edge px-2 py-1 text-xs text-signal-dim hover:border-signal-live/40 hover:text-slate-200"
                    onClick={() => setEdit({ type: "debt", id: debt.id, f: { balance: String(debt.balance), original: String(debt.original) } })}
                  >Edit</button>
                )}
              </div>
            );
          })}
        </div>
      </section>

      {/* ── Budget ─────────────────────────────────────────────────── */}
      <section className="panel">
        <div className="panel-head">
          <h2 className="text-sm font-semibold text-slate-200">Monthly Budget</h2>
          <span className="text-[11px] text-signal-dim">{data.budget.month}</span>
        </div>
        <div className="grid grid-cols-1 gap-4 p-4 sm:grid-cols-2 lg:grid-cols-3">
          {data.budget.categories.map((cat) => {
            const pct = cat.budget > 0 ? Math.min(1.05, cat.spent / cat.budget) : 0;
            const remaining = cat.budget - cat.spent;
            return (
              <div key={cat.id} className="panel p-4">
                <div className="flex items-start justify-between gap-1">
                  <span className="text-sm font-medium text-slate-200">{cat.name}</span>
                  <span className="shrink-0 font-mono text-xs text-signal-dim">
                    {usd(cat.spent)} / {usd(cat.budget)}
                  </span>
                </div>
                <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-navy-700">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${budgetBarColor(cat.spent, cat.budget)}`}
                    style={{ width: `${Math.min(100, pct * 100)}%` }}
                  />
                </div>
                <div className="mt-1 text-[10px] text-signal-dim">
                  {cat.budget > 0
                    ? remaining >= 0
                      ? `${usd(remaining)} left · ${Math.round(pct * 100)}% used`
                      : `${usd(Math.abs(remaining))} over budget`
                    : "No budget set"}
                </div>

                {isEdit("budget-set", cat.id) ? (
                  <div className="mt-3 space-y-2">
                    <input
                      type="number"
                      autoFocus
                      className="w-full rounded border border-edge bg-navy-800 px-2 py-1.5 font-mono text-sm text-slate-100 focus:border-signal-live focus:outline-none"
                      placeholder="Monthly budget"
                      value={edit!.f.budget}
                      onChange={(e) => setEdit({ ...edit!, f: { budget: e.target.value } })}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          const val = parseFloat(edit!.f.budget);
                          if (!isNaN(val))
                            commit({ ...data, budget: { ...data.budget, categories: data.budget.categories.map((c) => c.id === cat.id ? { ...c, budget: val } : c) } });
                        }
                        if (e.key === "Escape") setEdit(null);
                      }}
                    />
                    <div className="flex gap-2">
                      <button
                        className="flex-1 rounded bg-signal-live/20 px-2 py-1 text-xs text-signal-live hover:bg-signal-live/30"
                        onClick={() => {
                          const val = parseFloat(edit!.f.budget);
                          if (!isNaN(val))
                            commit({ ...data, budget: { ...data.budget, categories: data.budget.categories.map((c) => c.id === cat.id ? { ...c, budget: val } : c) } });
                        }}
                      >Save</button>
                      <button
                        className="flex-1 rounded bg-navy-700 px-2 py-1 text-xs text-signal-dim hover:text-slate-200"
                        onClick={() => setEdit(null)}
                      >Cancel</button>
                    </div>
                  </div>
                ) : isEdit("budget-add", cat.id) ? (
                  <div className="mt-3 space-y-2">
                    <input
                      type="number"
                      autoFocus
                      className="w-full rounded border border-edge bg-navy-800 px-2 py-1.5 font-mono text-sm text-slate-100 focus:border-signal-live focus:outline-none"
                      placeholder="Amount spent"
                      value={edit!.f.amount}
                      onChange={(e) => setEdit({ ...edit!, f: { amount: e.target.value } })}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") {
                          const val = parseFloat(edit!.f.amount);
                          if (!isNaN(val) && val > 0)
                            commit({ ...data, budget: { ...data.budget, categories: data.budget.categories.map((c) => c.id === cat.id ? { ...c, spent: c.spent + val } : c) } });
                        }
                        if (e.key === "Escape") setEdit(null);
                      }}
                    />
                    <div className="flex gap-2">
                      <button
                        className="flex-1 rounded bg-signal-live/20 px-2 py-1 text-xs text-signal-live hover:bg-signal-live/30"
                        onClick={() => {
                          const val = parseFloat(edit!.f.amount);
                          if (!isNaN(val) && val > 0)
                            commit({ ...data, budget: { ...data.budget, categories: data.budget.categories.map((c) => c.id === cat.id ? { ...c, spent: c.spent + val } : c) } });
                        }}
                      >Add</button>
                      <button
                        className="flex-1 rounded bg-navy-700 px-2 py-1 text-xs text-signal-dim hover:text-slate-200"
                        onClick={() => setEdit(null)}
                      >Cancel</button>
                    </div>
                  </div>
                ) : (
                  <div className="mt-3 flex gap-2">
                    <button
                      className="flex-1 rounded border border-edge px-2 py-1 text-xs text-signal-dim hover:border-signal-live/40 hover:text-slate-200"
                      onClick={() => setEdit({ type: "budget-set", id: cat.id, f: { budget: String(cat.budget) } })}
                    >Set Budget</button>
                    <button
                      className="flex-1 rounded border border-edge px-2 py-1 text-xs text-signal-dim hover:border-signal-live/40 hover:text-slate-200"
                      onClick={() => setEdit({ type: "budget-add", id: cat.id, f: { amount: "" } })}
                    >+ Spend</button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
