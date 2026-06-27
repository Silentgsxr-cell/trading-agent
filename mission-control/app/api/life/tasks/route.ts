import { NextResponse } from 'next/server'
import { execSync } from 'child_process'

const SCRIPT = `
tell application "Reminders"
    set output to ""
    try
        set allLists to every list
        repeat with rl in allLists
            set listName to name of rl
            try
                set rems to every reminder of rl whose completed is false
                repeat with r in rems
                    set rTitle to name of r
                    set rDue to ""
                    try
                        set rDue to (due date of r) as string
                    end try
                    set output to output & listName & "||" & rTitle & "||" & rDue & "\n"
                end repeat
            end try
        end repeat
    end try
    return output
end tell
`

export async function GET() {
  try {
    const stdout = execSync(`osascript -e '${SCRIPT.replace(/'/g, "'\\''")}'`, { timeout: 12000 }).toString()
    const tasks = stdout.trim().split('\n').filter(Boolean).map(line => {
      const p = line.split('||')
      if (p.length < 2) return null
      const due = p[2]?.trim() ?? ''
      return {
        list:  p[0].trim(),
        title: p[1].trim(),
        due:   due === 'missing value' ? '' : due,
      }
    }).filter(Boolean)
    return NextResponse.json({ tasks, error: null })
  } catch (e: unknown) {
    return NextResponse.json({ tasks: [], error: String(e) })
  }
}
