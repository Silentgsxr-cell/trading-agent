import { NextResponse } from 'next/server'
import { paths, readJSON, writeJSON } from '@/lib/dataPath'

type Card = Record<string, unknown>

export async function POST(_: Request, { params }: { params: { id: string } }) {
  const cards = readJSON<Card[]>(paths.suggestions, [])
  const idx = cards.findIndex(c => String(c.id).toUpperCase() === params.id.toUpperCase())
  if (idx === -1) return NextResponse.json({ error: 'not found' }, { status: 404 })
  cards[idx] = { ...cards[idx], status: 'approved', approved_at: new Date().toISOString(), updated_at: new Date().toISOString() }
  writeJSON(paths.suggestions, cards)
  return NextResponse.json({ success: true, card: cards[idx] })
}
