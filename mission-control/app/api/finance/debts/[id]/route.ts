import { NextResponse } from 'next/server'
import { paths, readJSON, writeJSON } from '@/lib/dataPath'

type Finance = { accounts: unknown[]; debts: Record<string, unknown>[]; budget: unknown }

export async function PATCH(req: Request, { params }: { params: { id: string } }) {
  const body = await req.json()
  const fin = readJSON<Finance>(paths.finance, { accounts: [], debts: [], budget: {} })
  const idx = fin.debts.findIndex(d => String(d.id) === params.id)
  if (idx === -1) return NextResponse.json({ error: 'not found' }, { status: 404 })
  fin.debts[idx] = { ...fin.debts[idx], ...body }
  writeJSON(paths.finance, fin)
  return NextResponse.json({ success: true, debt: fin.debts[idx] })
}
