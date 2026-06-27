import { getTickets } from "@/lib/tickets";
import { DevClient } from "./DevClient";

export const dynamic = "force-dynamic";

export default function DevPage() {
  const db = getTickets();
  return <DevClient db={db} />;
}
