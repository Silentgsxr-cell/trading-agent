"use server";
import { promises as fs } from "node:fs";
import { revalidatePath } from "next/cache";
import { PATHS } from "@/lib/config";
import type { FinanceData } from "@/lib/finance";

export async function saveFinanceAction(data: FinanceData): Promise<void> {
  await fs.writeFile(PATHS.financeJson, JSON.stringify(data, null, 2), "utf8");
  revalidatePath("/finance");
}
