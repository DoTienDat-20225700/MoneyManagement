export interface SavingPlanContribution {
  id: number;
  saving_plan: number;
  amount: number | string;
  date: string;
  description?: string;
  idempotency_key?: string;
  created_at?: string;
  updated_at?: string;
}

export interface EstimatedCompletion {
  status: "active" | "completed" | "closed";
  estimated_date: string | null;
  message: string | null;
  daily_rate: number;
  days_remaining: number | null;
}

export interface SavingPlan {
  id: number;
  title: string;
  amount: number | string;
  target_amount?: number | string;
  active: boolean;
  goal_date?: string | null;
  target_date?: string | null;
  description?: string;
  amount_saved: number | string;
  remaining_amount: number | string;
  completion_percentage: number;
  status: "active" | "completed" | "closed";
  contribution_count: number;
  estimated_completion?: EstimatedCompletion;
}
