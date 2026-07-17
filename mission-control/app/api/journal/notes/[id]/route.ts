import { NextResponse } from 'next/server'
import { paths, readJSON, writeJSON } from '@/lib/dataPath'

type Note = { id: string; text: string; created_at: string }

export async function DELETE(_: Request, { params }: { params: { id: string } }) {
  const notes = readJSON<Note[]>(paths.journalNotes, [])
  const filtered = notes.filter(n => n.id.toUpperCase() !== params.id.toUpperCase())
  writeJSON(paths.journalNotes, filtered)
  return NextResponse.json({ success: true })
}
