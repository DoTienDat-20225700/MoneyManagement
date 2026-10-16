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

export interface BudgetImpactResponse {
  has_budget: boolean;
  budget_amount: string | number;
  spent_before: string | number;
  spent_after: string | number;
  percent_before: number;
  percent_after: number;
  overspent_amount: string | number;
  status: BudgetStatus;
}

export interface CheckBudgetImpactPayload {
  label_id: number;
  value: number | string;
  date?: string;
}

export interface RebalancePayload {
  from_label_id: number;
  to_label_id: number;
  amount: number | string;
  month: number;
  year: number;
}

export interface RebalanceSuggestion {
  budget_id: number;
  label_id: number;
  label_name: string;
  label_color: string;
  amount: string | number;
  spent: string | number;
  available_rebalance: string | number;
  spent_percentage: number;
  is_non_essential: boolean;
}

