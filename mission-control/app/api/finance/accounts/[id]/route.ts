import { NextResponse } from 'next/server'
import { paths, readJSON, writeJSON } from '@/lib/dataPath'

type Finance = { accounts: Record<string, unknown>[]; debts: unknown[]; budget: unknown }

export async function PATCH(req: Request, { params }: { params: { id: string } }) {
  const body = await req.json()
  const fin = readJSON<Finance>(paths.finance, { accounts: [], debts: [], budget: {} })
  const idx = fin.accounts.findIndex(a => String(a.id) === params.id)
  if (idx === -1) return NextResponse.json({ error: 'not found' }, { status: 404 })
  fin.accounts[idx] = { ...fin.accounts[idx], ...body }
  writeJSON(paths.finance, fin)
  return NextResponse.json({ success: true, account: fin.accounts[idx] })
}
