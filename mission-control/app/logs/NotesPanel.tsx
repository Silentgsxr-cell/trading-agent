"use client";
import { useState, useEffect } from "react";

interface Note {
  id: string;
  text: string;
  created_at: string;
}

export default function NotesPanel() {
  const [notes, setNotes] = useState<Note[]>([]);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    fetch("/api/journal/notes")
      .then(r => r.json())
      .then(d => setNotes(Array.isArray(d) ? d : []))
      .finally(() => setLoaded(true));
  }, []);

  async function addNote(e: React.FormEvent) {
    e.preventDefault();
    const text = draft.trim();
    if (!text) return;
    setSaving(true);
    const r = await fetch("/api/journal/notes", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const d = await r.json();
    if (d.success) {
      setNotes(p => [...p, d.note]);
      setDraft("");
    }
    setSaving(false);
  }

  async function removeNote(id: string) {
    setNotes(p => p.filter(n => n.id !== id));
    await fetch(`/api/journal/notes/${id}`, { method: "DELETE" });
  }

  return (
    <section className="panel col-span-12">
      <div className="panel-head">
        <h2 className="text-sm font-semibold text-slate-200">Notes</h2>
        <span className="text-[11px] text-signal-dim">{notes.length} note{notes.length === 1 ? "" : "s"}</span>
      </div>

      <div className="p-3">
        <form onSubmit={addNote} className="mb-3 flex items-center gap-2">
          <input
            value={draft}
            onChange={e => setDraft(e.target.value)}
            placeholder="Add a note…"
            className="flex-1 rounded border border-edge/60 bg-navy-900/40 px-3 py-1.5 text-[12px] text-slate-200 placeholder-signal-dim focus:outline-none"
          />
          <button
            type="submit"
            disabled={saving || !draft.trim()}
            className="rounded border border-signal-live/20 bg-signal-live/5 px-3 py-1.5 text-[12px] text-signal-live disabled:opacity-40 hover:bg-signal-live/10 transition"
          >
            {saving ? "…" : "Add"}
          </button>
        </form>

        {loaded && notes.length === 0 ? (
          <div className="px-1 py-4 text-center text-[12px] text-signal-dim">No notes yet.</div>
        ) : (
          <ul className="space-y-1.5">
            {[...notes].reverse().map(n => (
              <li
                key={n.id}
                className="group flex items-start gap-2 rounded-md border border-edge/60 bg-navy-900/40 px-3 py-2 text-[12px]"
              >
                <div className="min-w-0 flex-1">
                  <div className="whitespace-pre-wrap text-slate-300">{n.text}</div>
                  <div className="mt-0.5 text-[10px] text-signal-dim">{formatWhen(n.created_at)}</div>
                </div>
                <button
                  onClick={() => removeNote(n.id)}
                  className="shrink-0 text-[11px] text-signal-dim opacity-0 transition hover:text-maroon-300 group-hover:opacity-100"
                >
                  remove
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function formatWhen(iso: string): string {
  try {
    return new Date(iso).toLocaleString("en-US", {
      month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
    });
  } catch {
    return iso;
  }
}
