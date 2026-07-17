import { NextResponse } from 'next/server'
import { paths, readJSON, writeJSON } from '@/lib/dataPath'

type Note = { id: string; text: string; created_at: string }

function nextId(notes: Note[]): string {
  const nums = notes.map(n => parseInt(n.id.replace('NOTE-', ''), 10)).filter(n => !isNaN(n))
  return `NOTE-${String((Math.max(0, ...nums) + 1)).padStart(3, '0')}`
}

export async function GET() {
  return NextResponse.json(readJSON<Note[]>(paths.journalNotes, []))
}

export async function POST(req: Request) {
  const body = await req.json()
  const text = String(body.text ?? '').trim()
  if (!text) return NextResponse.json({ error: 'text required' }, { status: 400 })

  const notes = readJSON<Note[]>(paths.journalNotes, [])
  const note: Note = { id: nextId(notes), text, created_at: new Date().toISOString() }
  notes.push(note)
  writeJSON(paths.journalNotes, notes)
  return NextResponse.json({ success: true, note }, { status: 201 })
}
