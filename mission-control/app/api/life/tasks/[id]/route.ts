import { NextResponse } from 'next/server'
import { execSync } from 'child_process'

export async function DELETE(_: Request, { params }: { params: { id: string } }) {
  const title = decodeURIComponent(params.id)
  const script = `
tell application "Reminders"
    repeat with rl in every list
        repeat with r in every reminder of rl
            if name of r is "${title}" then
                delete r
                return "deleted"
            end if
        end repeat
    end repeat
    return "not found"
end tell
`
  try {
    execSync(`osascript -e '${script.replace(/'/g, "'\\''")}'`, { timeout: 10000 })
    return NextResponse.json({ success: true })
  } catch (e: unknown) {
    return NextResponse.json({ error: String(e) }, { status: 500 })
  }
}
