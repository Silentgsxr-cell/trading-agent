import { NextResponse } from 'next/server'
import { paths, readJSON, writeJSON } from '@/lib/dataPath'

type Goal = Record<string, unknown>

function nextId(goals: Goal[]): string {
  const nums = goals.map(g => parseInt(String(g.id ?? '').replace('GOAL-', ''), 10)).filter(n => !isNaN(n))
  return `GOAL-${String((Math.max(0, ...nums) + 1)).padStart(3, '0')}`
}

export async function GET() {
  return NextResponse.json(readJSON<Goal[]>(paths.goals, []))
}

export async function POST(req: Request) {
  const body = await req.json()
  const goals = readJSON<Goal[]>(paths.goals, [])
  const now = new Date().toISOString()
  const goal: Goal = {
    id:           nextId(goals),
    title:        String(body.title ?? '').trim(),
    notes:        String(body.notes ?? '').trim(),
    target_date:  String(body.target_date ?? '').trim(),
    status:       'active',
    created_at:   now,
    completed_at: null,
  }
  if (!goal.title) return NextResponse.json({ error: 'title required' }, { status: 400 })
  goals.push(goal)
  writeJSON(paths.goals, goals)
  return NextResponse.json({ success: true, goal }, { status: 201 })
}
