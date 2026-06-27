import { NextResponse } from 'next/server'
import { execSync } from 'child_process'

const SCRIPT = `
tell application "Calendar"
    set startDate to current date
    set endDate to startDate + (7 * days)
    set output to ""
    repeat with cal in calendars
        set calName to name of cal
        try
            set evts to every event of cal whose start date >= startDate and start date <= endDate
            repeat with evt in evts
                try
                    set evtTitle to summary of evt
                    set evtStart to (start date of evt) as string
                    set evtEnd to (end date of evt) as string
                    set allD to "false"
                    try
                        if allday event of evt then set allD to "true"
                    end try
                    set output to output & calName & "||" & evtTitle & "||" & evtStart & "||" & evtEnd & "||" & allD & "\n"
                end try
            end repeat
        end try
    end repeat
    return output
end tell
`

export async function GET() {
  try {
    const stdout = execSync(`osascript -e '${SCRIPT.replace(/'/g, "'\\''")}'`, { timeout: 12000 }).toString()
    const events = stdout.trim().split('\n').filter(Boolean).map(line => {
      const p = line.split('||')
      return p.length >= 4 ? {
        calendar: p[0].trim(),
        title:    p[1].trim(),
        start:    p[2].trim(),
        end:      p[3].trim(),
        allDay:   p[4]?.trim() === 'true',
      } : null
    }).filter(Boolean)
    events.sort((a, b) => (a!.start > b!.start ? 1 : -1))
    return NextResponse.json({ events, error: null })
  } catch (e: unknown) {
    return NextResponse.json({ events: [], error: String(e) })
  }
}
