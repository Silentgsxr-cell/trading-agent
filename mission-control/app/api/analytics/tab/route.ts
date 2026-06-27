import { NextResponse } from 'next/server'
import { paths, readJSON, writeJSON } from '@/lib/dataPath'

type TabUsage = { tab_counts: Record<string, number>; sessions: unknown[]; last_updated: string }

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}))
  const tab = String(body.tab ?? '').trim()
  if (!tab) return NextResponse.json({ error: 'tab required' }, { status: 400 })
  const usage = readJSON<TabUsage>(paths.tabUsage, { tab_counts: {}, sessions: [], last_updated: '' })
  usage.tab_counts[tab] = (usage.tab_counts[tab] ?? 0) + 1
  usage.last_updated = new Date().toISOString()
  usage.sessions = [...usage.sessions.slice(-999), { tab, timestamp: body.timestamp ?? usage.last_updated, duration_ms: body.duration_ms ?? 0 }]
  writeJSON(paths.tabUsage, usage)
  return NextResponse.json({ success: true })
}
