import { NextResponse } from 'next/server'
import { paths, readJSON } from '@/lib/dataPath'

type Finance = {
  accounts: { balance?: number }[]
  debts:    { balance?: number }[]
  budget:   unknown
}

export async function GET() {
  const fin = readJSON<Finance>(paths.finance, { accounts: [], debts: [], budget: { month: '', categories: [] } })
  const total_assets = fin.accounts.reduce((s, a) => s + (a.balance ?? 0), 0)
  const total_debt   = fin.debts.reduce((s, d) => s + (d.balance ?? 0), 0)
  return NextResponse.json({
    accounts:     fin.accounts,
    debts:        fin.debts,
    total_assets: Math.round(total_assets * 100) / 100,
    total_debt:   Math.round(total_debt * 100) / 100,
    net_worth:    Math.round((total_assets - total_debt) * 100) / 100,
  })
}
