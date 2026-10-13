export interface SavingPlan {
  id: number;
  title: string;
  amount: number;
  active: boolean;
  goal_date?: string | null;
  description?: string;
}
