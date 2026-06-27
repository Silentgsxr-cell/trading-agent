import { NextResponse } from 'next/server'
import { paths, readJSON } from '@/lib/dataPath'

type Card = { status?: string; priority?: number; agent?: string }

export async function GET() {
  const cards = readJSON<Card[]>(paths.suggestions, [])
  const pending   = cards.filter(c => c.status === 'pending').length
  const approved  = cards.filter(c => c.status === 'approved').length
  const discarded = cards.filter(c => c.status === 'discarded').length
  const high_priority = cards.filter(c => (c.priority ?? 0) >= 8 && c.status === 'pending').length
  const by_agent: Record<string, number> = {}
  for (const c of cards) {
    const a = c.agent ?? 'UNKNOWN'
    by_agent[a] = (by_agent[a] ?? 0) + 1
  }
  return NextResponse.json({ total: cards.length, pending, approved, discarded, high_priority, by_agent })
}
