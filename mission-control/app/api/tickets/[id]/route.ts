import { NextResponse } from 'next/server'
import { paths, readJSON } from '@/lib/dataPath'

type Ticket = Record<string, unknown>

export async function GET(_: Request, { params }: { params: { id: string } }) {
  const db = readJSON<{ tickets: Ticket[] }>(paths.tickets, { tickets: [] })
  const ticket = (db.tickets ?? []).find(t => String(t.id).toUpperCase() === params.id.toUpperCase())
  if (!ticket) return NextResponse.json({ error: 'not found' }, { status: 404 })
  return NextResponse.json(ticket)
}
