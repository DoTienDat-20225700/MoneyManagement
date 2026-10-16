export type DebtType = "DEBT_BORROWED" | "LOAN_GIVEN" | "INSTALLMENT";
export type DebtStatus = "ACTIVE" | "PARTIALLY_PAID" | "FULLY_PAID" | "OVERDUE" | "CLOSED";

export interface InstallmentScheduleItem {
  installment_no: number;
  due_date: string;
  amount: string;
  paid_amount: string;
  is_paid: boolean;
}

export interface DebtPayment {
  id: number;
  debt: number;
  amount: string;
  date: string;
  update_wallet: boolean;
  note?: string;
  created_at?: string;
  updated_at?: string;
}

export interface DebtLoan {
  id: number;
  person_name: string;
  contact_info?: string;
  type: DebtType;
  principal_amount: string;
  start_date: string;
  due_date?: string | null;
  installment_months?: number | null;
  status: DebtStatus;
  description?: string;
  wallet_applied: boolean;
  created_at: string;
  updated_at: string;
  total_paid: string;
  remaining_amount: string;
  overdue_days: number;
  progress_percentage: number;
  payments: DebtPayment[];
  installment_schedule?: InstallmentScheduleItem[];
}

export interface DebtSummary {
  total_loan_given_remaining: string;
  total_debt_borrowed_remaining: string;
  due_in_7_days_count: number;
  overdue_count: number;
  total_debts_count: number;
}
