import { NextResponse } from "next/server";
import { getAgents, crewHealth } from "@/lib/agents";

export const dynamic = "force-dynamic";

export async function GET() {
  const agents = await getAgents();
  const health = crewHealth(agents);
  return NextResponse.json({ agents, health });
}
