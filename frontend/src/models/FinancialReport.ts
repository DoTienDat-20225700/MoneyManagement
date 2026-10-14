export interface ReportPeriod {
  start_date: string;
  end_date: string;
  days_count: number;
}

export interface ReportSummaryKPI {
  total_income: string;
  total_expense: string;
  net_cash_flow: string;
  average_daily_spending: string;
}

export interface PreviousPeriodSummary {
  start_date: string;
  end_date: string;
  total_income: string;
  total_expense: string;
  net_cash_flow: string;
}

export interface PreviousPeriodComparison {
  previous_period: PreviousPeriodSummary;
  income_change_percentage: number;
  expense_change_percentage: number;
  net_cash_flow_change_percentage: number;
}

export interface CategoryBreakdownItem {
  label_id: number | null;
  label_name: string;
  label_color: string;
  total: string;
  percentage: number;
  transaction_count: number;
}

export interface SpendingIncreaseItem {
  label_id: number | null;
  label_name: string;
  label_color: string;
  current_spent: string;
  previous_spent: string;
  increase_amount: string;
  increase_percentage: number;
}

export interface MonthlyTrendItem {
  month: number;
  year: number;
  label: string;
  income: string;
  expense: string;
  net: string;
}

export interface FinancialReportSummary {
  period: ReportPeriod;
  summary: ReportSummaryKPI;
  comparison: PreviousPeriodComparison;
  category_breakdown: CategoryBreakdownItem[];
  largest_spending_increases: SpendingIncreaseItem[];
  monthly_trends: MonthlyTrendItem[];
}

export interface ReportFilterParams {
  start_date?: string;
  end_date?: string;
  type?: "ALL" | "EXPENSE" | "EARNING";
  label_id?: number | string;
  wallet_id?: number | string;
  search?: string;
}
