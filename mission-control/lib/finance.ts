import "server-only";
import { promises as fs } from "node:fs";
import { PATHS } from "./config";

export interface Account {
  id: string;
  name: string;
  role: string;
  balance: number;
  updatedAt: string;
}

export interface Debt {
  id: string;
  name: string;
  balance: number;
  original: number;
}

export interface BudgetCategory {
  id: string;
  name: string;
  budget: number;
  spent: number;
}

export interface FinanceData {
  accounts: Account[];
  debts: Debt[];
  budget: {
    month: string;
    categories: BudgetCategory[];
  };
}

const DEFAULT: FinanceData = {
  accounts: [
    { id: "webull", name: "Webull", role: "Main Trading", balance: 6000, updatedAt: "2026-06-24" },
    { id: "fidelity", name: "Fidelity", role: "401k", balance: 4000, updatedAt: "2026-06-24" },
    { id: "robinhood", name: "Robinhood", role: "Side Project", balance: 50, updatedAt: "2026-06-24" },
  ],
  debts: [
    { id: "student-loans", name: "Student Loans", balance: 9000, original: 9000 },
    { id: "credit-card", name: "Credit Card", balance: 0, original: 0 },
    { id: "other", name: "Other Debt", balance: 5000, original: 5000 },
  ],
  budget: {
    month: new Date().toISOString().slice(0, 7),
    categories: [
      { id: "housing", name: "Housing", budget: 0, spent: 0 },
      { id: "food", name: "Food", budget: 0, spent: 0 },
      { id: "transport", name: "Transport", budget: 0, spent: 0 },
      { id: "trading", name: "Trading / Investing", budget: 0, spent: 0 },
      { id: "debt-payments", name: "Debt Payments", budget: 0, spent: 0 },
      { id: "other", name: "Other", budget: 0, spent: 0 },
    ],
  },
};

export async function getFinance(): Promise<FinanceData> {
  try {
    const raw = await fs.readFile(PATHS.financeJson, "utf8");
    return JSON.parse(raw) as FinanceData;
  } catch {
    return DEFAULT;
  }
}
