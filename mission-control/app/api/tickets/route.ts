import { NextResponse } from 'next/server'
import { paths, readJSON, writeJSON } from '@/lib/dataPath'

type Ticket = Record<string, unknown>
type TicketDB = { tickets: Ticket[] }

function nextId(tickets: Ticket[]): string {
  const nums = tickets.map(t => parseInt(String(t.id ?? '').replace('TICKET-', ''), 10)).filter(n => !isNaN(n))
  return `TICKET-${String((Math.max(0, ...nums) + 1)).padStart(3, '0')}`
}

export async function GET() {
  const db = readJSON<TicketDB>(paths.tickets, { tickets: [] })
  return NextResponse.json(db.tickets ?? [])
}

export async function POST(req: Request) {
  const body = await req.json()
  const db = readJSON<TicketDB>(paths.tickets, { tickets: [] })
  const tickets = db.tickets ?? []
  const now = new Date().toISOString()
  const ticket: Ticket = {
    id:          nextId(tickets),
    title:       String(body.title ?? '').trim(),
    description: String(body.description ?? '').trim(),
    priority:    String(body.priority ?? 'medium'),
    status:      'open',
    created_at:  now,
    updated_at:  now,
  }
  if (!ticket.title) return NextResponse.json({ error: 'title required' }, { status: 400 })
  tickets.push(ticket)
  writeJSON(paths.tickets, { ...db, tickets })
  return NextResponse.json({ success: true, ticket }, { status: 201 })
}
