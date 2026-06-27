import { NextResponse } from 'next/server'
import { paths, readJSON, writeJSON } from '@/lib/dataPath'

type Card = Record<string, unknown>

function nextId(cards: Card[]): string {
  const nums = cards.map(c => parseInt(String(c.id ?? '').replace('SUG-', ''), 10)).filter(n => !isNaN(n))
  return `SUG-${String((Math.max(0, ...nums) + 1)).padStart(3, '0')}`
}

export async function GET() {
  const cards = readJSON<Card[]>(paths.suggestions, [])
  return NextResponse.json(cards)
}

export async function POST(req: Request) {
  const body = await req.json()
  const cards = readJSON<Card[]>(paths.suggestions, [])
  const now = new Date().toISOString()
  const card: Card = {
    id:          nextId(cards),
    title:       String(body.title ?? '').trim(),
    body:        String(body.body ?? '').trim(),
    priority:    Number(body.priority ?? 5),
    agent:       String(body.agent ?? 'UNKNOWN'),
    status:      'pending',
    tags:        body.tags ?? [],
    created_at:  now,
    updated_at:  now,
  }
  if (!card.title) return NextResponse.json({ error: 'title required' }, { status: 400 })
  cards.push(card)
  writeJSON(paths.suggestions, cards)
  return NextResponse.json({ success: true, card }, { status: 201 })
}
