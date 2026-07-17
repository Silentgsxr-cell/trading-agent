import path from 'path'
import fs from 'fs'

const DATA = path.resolve(process.cwd(), '..', 'data')

export const paths = {
  suggestions: path.join(DATA, 'suggestions.json'),
  tickets:     path.join(DATA, 'tickets.json'),
  goals:       path.join(DATA, 'goals.json'),
  finance:     path.join(DATA, 'finance.json'),
  tabUsage:    path.join(DATA, 'tab_usage.json'),
  journalNotes: path.join(DATA, 'journal_notes.json'),
}

export function readJSON<T>(p: string, fallback: T): T {
  try { return JSON.parse(fs.readFileSync(p, 'utf8')) as T }
  catch { return fallback }
}

export function writeJSON(p: string, data: unknown): void {
  fs.writeFileSync(p, JSON.stringify(data, null, 2))
}
