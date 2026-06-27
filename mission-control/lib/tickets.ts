// Server-only: reads tickets.json from disk.
// Import this only in server components (page.tsx, not DevClient.tsx).

import fs from "fs";
import path from "path";

export type { Ticket, TicketDB, TicketStatus, TicketPriority, TicketComplexity } from "./ticket-types";
export { COMPLEXITY_COLOR, PRIORITY_COLOR, PRIORITY_ORDER } from "./ticket-types";

const PROJECT_ROOT = process.env.CLAWOPS_PROJECT_ROOT || path.resolve(process.cwd(), "..");
const TICKETS_PATH = path.join(PROJECT_ROOT, "data", "tickets.json");

export function getTickets() {
  try {
    if (!fs.existsSync(TICKETS_PATH)) {
      return { paused: false, tickets: [] };
    }
    const raw = fs.readFileSync(TICKETS_PATH, "utf8");
    return JSON.parse(raw) as import("./ticket-types").TicketDB;
  } catch {
    return { paused: false, tickets: [] };
  }
}
