import { NextResponse } from 'next/server'
import { paths, readJSON, writeJSON } from '@/lib/dataPath'

type Goal = Record<string, unknown>

export async function PATCH(req: Request, { params }: { params: { id: string } }) {
  const body = await req.json()
  const goals = readJSON<Goal[]>(paths.goals, [])
  const idx = goals.findIndex(g => String(g.id).toUpperCase() === params.id.toUpperCase())
  if (idx === -1) return NextResponse.json({ error: 'not found' }, { status: 404 })
  const g = { ...goals[idx] }
  for (const field of ['title', 'notes', 'target_date', 'status']) {
    if (field in body) g[field] = body[field]
  }
  if (body.status === 'done' && !g.completed_at) g.completed_at = new Date().toISOString()
  if (body.status === 'active') g.completed_at = null
  goals[idx] = g
  writeJSON(paths.goals, goals)
  return NextResponse.json({ success: true, goal: g })
}

export async function DELETE(_: Request, { params }: { params: { id: string } }) {
  const goals = readJSON<Goal[]>(paths.goals, [])
  const filtered = goals.filter(g => String(g.id).toUpperCase() !== params.id.toUpperCase())
  writeJSON(paths.goals, filtered)
  return NextResponse.json({ success: true })
}
