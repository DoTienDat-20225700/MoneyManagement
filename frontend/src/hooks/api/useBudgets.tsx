import {
  BudgetSummary,
  CategoryBudget,
  CreateBudgetPayload,
  UpdateBudgetPayload,
} from "../../models/CategoryBudget";
import useAxiosPrivate from "../useAxiosPrivate";

export function useBudgets() {
  const axiosPrivate = useAxiosPrivate();

  async function getBudgets(month?: number, year?: number): Promise<CategoryBudget[]> {
    const params: Record<string, number> = {};
    if (month !== undefined) params.month = month;
    if (year !== undefined) params.year = year;
    const response = await axiosPrivate.get("/budgets/", { params });
    return response.data as CategoryBudget[];
  }

  async function getBudget(id: number): Promise<CategoryBudget> {
    const response = await axiosPrivate.get(`/budgets/${id}`);
    return response.data as CategoryBudget;
  }

  async function getBudgetSummary(month?: number, year?: number): Promise<BudgetSummary> {
    const params: Record<string, number> = {};
    if (month !== undefined) params.month = month;
    if (year !== undefined) params.year = year;
    const response = await axiosPrivate.get("/budgets/summary/", { params });
    return response.data as BudgetSummary;
  }

  async function createBudget(payload: CreateBudgetPayload): Promise<CategoryBudget> {
    const response = await axiosPrivate.post("/budgets/", payload);
    return response.data as CategoryBudget;
  }

  async function updateBudget({
    id,
    data,
  }: {
    id: number;
    data: UpdateBudgetPayload;
  }): Promise<CategoryBudget> {
    const response = await axiosPrivate.put(`/budgets/${id}`, data);
    return response.data as CategoryBudget;
  }

  async function deleteBudget(id: number): Promise<{ success: boolean; message: string }> {
    const response = await axiosPrivate.delete(`/budgets/${id}`);
    return response.data;
  }

  return {
    getBudgets,
    getBudget,
    getBudgetSummary,
    createBudget,
    updateBudget,
    deleteBudget,
  };
}
