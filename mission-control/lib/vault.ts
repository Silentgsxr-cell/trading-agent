import "server-only";
import { promises as fs } from "node:fs";
import path from "node:path";
import { PATHS, DOC_DENYLIST, DOC_ALLOW_HINTS } from "./config";

export interface DocEntry {
  title: string;
  relPath: string;
  source: "vault" | "project";
  modified: number;
  size: number;
  excerpt: string;
  tags: string[];
}

function isDenied(name: string): boolean {
  const lower = name.toLowerCase();
  return DOC_DENYLIST.some((d) => lower.includes(d));
}
function isAllowed(name: string): boolean {
  const lower = name.toLowerCase();
  return DOC_ALLOW_HINTS.some((h) => lower.includes(h));
}

function stripFrontmatter(text: string): { body: string; tags: string[] } {
  let tags: string[] = [];
  let body = text;
  const fm = text.match(/^---\n([\s\S]*?)\n---\n?/);
  if (fm) {
    const block = fm[1];
    const tagLine = block.match(/tags:\s*\[([^\]]*)\]/);
    if (tagLine) tags = tagLine[1].split(",").map((t) => t.trim()).filter(Boolean);
    body = text.slice(fm[0].length);
  }
  return { body, tags };
}

// Backstop: even inside an allow-listed note, mask any reference to a
// denylisted personal domain (e.g. Trading.md links to [[Finances]]).
function scrubSensitive(text: string): string {
  let out = text;
  for (const term of DOC_DENYLIST) {
    out = out.replace(new RegExp(term.replace(/[.*+?^${}()|[\]\\&]/g, "\\$&"), "gi"), "▮▮▮");
  }
  return out;
}

function excerptOf(body: string, n = 220): string {
  const clean = scrubSensitive(body)
    .replace(/^#+\s*/gm, "")
    .replace(/>\s?/g, "")
    .replace(/\[\[([^\]]+)\]\]/g, "$1")
    .replace(/[*_`]/g, "")
    .replace(/\n{2,}/g, " · ")
    .replace(/\n/g, " ")
    .trim();
  return clean.length > n ? clean.slice(0, n).trimEnd() + "…" : clean;
}

// Trading-relevant docs only: vault root .md (allow-listed, denylist enforced)
// plus the project's own README/HANDOFF/notes.
export async function getDocs(): Promise<DocEntry[]> {
  const docs: DocEntry[] = [];

  // 1) Vault root markdown
  try {
    const entries = await fs.readdir(PATHS.vaultRoot, { withFileTypes: true });
    for (const e of entries) {
      if (!e.isFile() || !e.name.endsWith(".md")) continue;
      if (isDenied(e.name) || !isAllowed(e.name)) continue;
      const full = path.join(PATHS.vaultRoot, e.name);
      const [text, stat] = await Promise.all([fs.readFile(full, "utf8"), fs.stat(full)]);
      const { body, tags } = stripFrontmatter(text);
      docs.push({
        title: e.name.replace(/\.md$/, ""),
        relPath: e.name,
        source: "vault",
        modified: stat.mtimeMs,
        size: stat.size,
        excerpt: excerptOf(body),
        tags,
      });
    }
  } catch { /* vault not reachable */ }

  // 2) Project docs (README, HANDOFF, notes/*)
  const projDocs = ["README.md", "HANDOFF.md"];
  for (const rel of projDocs) {
    const full = path.join(PATHS.agentsV2Dir, "..", rel);
    try {
      const [text, stat] = await Promise.all([fs.readFile(full, "utf8"), fs.stat(full)]);
      if (isDenied(rel)) continue;
      const { body, tags } = stripFrontmatter(text);
      docs.push({
        title: rel.replace(/\.md$/, ""),
        relPath: rel,
        source: "project",
        modified: stat.mtimeMs,
        size: stat.size,
        excerpt: excerptOf(body),
        tags,
      });
    } catch { /* not present */ }
  }

  return docs.sort((a, b) => b.modified - a.modified);
}
