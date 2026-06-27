import { NextResponse } from 'next/server'
import { paths, readJSON, writeJSON } from '@/lib/dataPath'

type Ticket = Record<string, unknown>

export async function POST(_: Request, { params }: { params: { id: string } }) {
  const db = readJSON<{ tickets: Ticket[] }>(paths.tickets, { tickets: [] })
  const tickets = db.tickets ?? []
  const idx = tickets.findIndex(t => String(t.id).toUpperCase() === params.id.toUpperCase())
  if (idx === -1) return NextResponse.json({ error: 'not found' }, { status: 404 })
  tickets[idx] = { ...tickets[idx], status: 'open', approved_at: null, updated_at: new Date().toISOString() }
  writeJSON(paths.tickets, { ...db, tickets })
  return NextResponse.json({ success: true, ticket: tickets[idx] })
}
