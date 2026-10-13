import { CustomLabel } from "./CustomLabel";

export type BudgetStatus = "normal" | "approaching" | "exceeded";

export interface CategoryBudget {
  id: number;
  label: CustomLabel;
  amount: string | number;
  limit: string | number;
  month: number;
  year: number;
  spent: string | number;
  remaining: string | number;
  percentage: number;
  status: BudgetStatus;
  is_over_budget: boolean;
  created_at?: string;
  updated_at?: string;
}

export interface BudgetSummary {
  month: number;
  year: number;
  total_budget: string;
  total_spent: string;
  total_remaining: string;
  overall_percentage: number;
  total_monthly_expenses?: string;
  unbudgeted_spent?: string;
  budget_count: number;
  status_counts: {
    normal: number;
    approaching: number;
    exceeded: number;
  };
}

export interface CreateBudgetPayload {
  label: number;
  amount: number | string;
  month: number;
  year: number;
}

export interface UpdateBudgetPayload {
  amount?: number | string;
  month?: number;
  year?: number;
  label?: number;
}
