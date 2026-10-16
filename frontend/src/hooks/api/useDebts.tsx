import { DebtLoan, DebtPayment, DebtSummary, DebtType } from "../../models/Debt";
import useAxiosPrivate from "../useAxiosPrivate";

export function useDebts() {
  const axiosPrivate = useAxiosPrivate();

  async function getDebts(type?: DebtType, status?: string): Promise<DebtLoan[]> {
    const params: Record<string, string> = {};
    if (type) params.type = type;
    if (status) params.status = status;
    const response = await axiosPrivate.get("/debts/", { params });
    return response.data as DebtLoan[];
  }

  async function getDebt(id: number): Promise<DebtLoan> {
    const response = await axiosPrivate.get(`/debts/${id}`);
    return response.data as DebtLoan;
  }

  async function getDebtSummary(): Promise<DebtSummary> {
    const response = await axiosPrivate.get("/debts/summary/");
    return response.data as DebtSummary;
  }

  async function createDebt(payload: {
    person_name: string;
    contact_info?: string;
    type: DebtType;
    principal_amount: number | string;
    start_date: string;
    due_date?: string | null;
    installment_months?: number | null;
    update_wallet?: boolean;
    description?: string;
  }): Promise<DebtLoan> {
    const response = await axiosPrivate.post("/debts/", payload);
    return response.data as DebtLoan;
  }

  async function updateDebt({
    id,
    data,
  }: {
    id: number;
    data: {
      person_name?: string;
      contact_info?: string;
      principal_amount?: number | string;
      due_date?: string | null;
      description?: string;
    };
  }): Promise<DebtLoan> {
    const response = await axiosPrivate.put(`/debts/${id}`, data);
    return response.data as DebtLoan;
  }

  async function deleteDebt(id: number): Promise<{ success: boolean; message: string }> {
    const response = await axiosPrivate.delete(`/debts/${id}`);
    return response.data;
  }

  async function getPayments(debtId: number): Promise<DebtPayment[]> {
    const response = await axiosPrivate.get(`/debts/${debtId}/payments/`);
    return response.data as DebtPayment[];
  }

  async function createPayment({
    debtId,
    data,
  }: {
    debtId: number;
    data: {
      amount: number | string;
      date: string;
      update_wallet?: boolean;
      note?: string;
    };
  }): Promise<DebtPayment> {
    const response = await axiosPrivate.post(`/debts/${debtId}/payments/`, data);
    return response.data as DebtPayment;
  }

  async function updatePayment({
    debtId,
    paymentId,
    data,
  }: {
    debtId: number;
    paymentId: number;
    data: {
      amount?: number | string;
      date?: string;
      update_wallet?: boolean;
      note?: string;
    };
  }): Promise<DebtPayment> {
    const response = await axiosPrivate.put(`/debts/${debtId}/payments/${paymentId}`, data);
    return response.data as DebtPayment;
  }

  async function deletePayment({
    debtId,
    paymentId,
  }: {
    debtId: number;
    paymentId: number;
  }): Promise<{ success: boolean; message: string }> {
    const response = await axiosPrivate.delete(`/debts/${debtId}/payments/${paymentId}`);
    return response.data;
  }

  return {
    getDebts,
    getDebt,
    getDebtSummary,
    createDebt,
    updateDebt,
    deleteDebt,
    getPayments,
    createPayment,
    updatePayment,
    deletePayment,
  };
}
