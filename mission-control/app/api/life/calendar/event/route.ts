import { NextResponse } from 'next/server'
import { execSync } from 'child_process'

export async function POST(req: Request) {
  const { title, start, end, calendar = 'Home' } = await req.json()
  if (!title || !start) return NextResponse.json({ error: 'title and start required' }, { status: 400 })
  const script = `
tell application "Calendar"
    tell calendar "${calendar}"
        make new event with properties {summary:"${title}", start date:date "${start}"${end ? `, end date:date "${end}"` : ''}}
    end tell
end tell
`
  try {
    execSync(`osascript -e '${script.replace(/'/g, "'\\''")}'`, { timeout: 10000 })
    return NextResponse.json({ success: true })
  } catch (e: unknown) {
    return NextResponse.json({ error: String(e) }, { status: 500 })
  }
}
