import { SavingPlan, SavingPlanContribution } from "../../models/SavingPlan";
import useAxiosPrivate from "../useAxiosPrivate";

export function useSavingPlans() {
  const axiosPrivate = useAxiosPrivate();

  async function getSavingPlans(status?: string): Promise<SavingPlan[]> {
    const url = status ? `/savingplans/?status=${status}` : "/savingplans/";
    const response = await axiosPrivate.get(url);
    return response.data as SavingPlan[];
  }

  async function getSavingPlan(id: number): Promise<SavingPlan> {
    const response = await axiosPrivate.get(`/savingplan/${id}`);
    return response.data as SavingPlan;
  }

  async function createSavingPlan(plan: {
    title: string;
    amount: number | string;
    goal_date?: string | null;
    description?: string;
    active?: boolean;
  }): Promise<SavingPlan> {
    const response = await axiosPrivate.post("/savingplan/", plan);
    return response.data as SavingPlan;
  }

  async function updateSavingPlan({
    id,
    plan,
  }: {
    id: number;
    plan: {
      title?: string;
      amount?: number | string;
      goal_date?: string | null;
      description?: string;
      active?: boolean;
    };
  }): Promise<SavingPlan> {
    const response = await axiosPrivate.put(`/savingplan/${id}`, plan);
    return response.data as SavingPlan;
  }

  async function toggleSavingPlan(id: number, active?: boolean): Promise<SavingPlan> {
    const payload = active !== undefined ? { active } : {};
    const response = await axiosPrivate.patch(`/savingplan/${id}`, payload);
    return response.data as SavingPlan;
  }

  async function deleteSavingPlan(id: number): Promise<{ success: boolean; message: string }> {
    const response = await axiosPrivate.delete(`/savingplan/${id}`);
    return response.data;
  }

  async function getContributions(planId: number): Promise<SavingPlanContribution[]> {
    const response = await axiosPrivate.get(`/savingplans/${planId}/contributions/`);
    return response.data as SavingPlanContribution[];
  }

  async function addContribution({
    planId,
    contribution,
  }: {
    planId: number;
    contribution: {
      amount: number | string;
      date?: string;
      description?: string;
      idempotency_key?: string;
    };
  }): Promise<SavingPlanContribution> {
    const response = await axiosPrivate.post(
      `/savingplans/${planId}/contributions/`,
      contribution
    );
    return response.data as SavingPlanContribution;
  }

  async function updateContribution({
    planId,
    contribId,
    data,
  }: {
    planId: number;
    contribId: number;
    data: {
      amount?: number | string;
      date?: string;
      description?: string;
    };
  }): Promise<SavingPlanContribution> {
    const response = await axiosPrivate.put(
      `/savingplans/${planId}/contributions/${contribId}/`,
      data
    );
    return response.data as SavingPlanContribution;
  }

  async function deleteContribution({
    planId,
    contribId,
  }: {
    planId: number;
    contribId: number;
  }): Promise<{ success: boolean; message: string }> {
    const response = await axiosPrivate.delete(
      `/savingplans/${planId}/contributions/${contribId}/`
    );
    return response.data;
  }

  return {
    getSavingPlans,
    getSavingPlan,
    createSavingPlan,
    updateSavingPlan,
    toggleSavingPlan,
    deleteSavingPlan,
    getContributions,
    addContribution,
    updateContribution,
    deleteContribution,
  };
}
