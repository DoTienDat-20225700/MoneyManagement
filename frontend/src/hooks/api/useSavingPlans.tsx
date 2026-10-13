import { SavingPlan } from "../../models/SavingPlan";
import useAxiosPrivate from "../useAxiosPrivate";

export function useSavingPlans() {
  const axiosPrivate = useAxiosPrivate();

  async function getSavingPlans(): Promise<SavingPlan[]> {
    const response = await axiosPrivate.get("/savingplans/");
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

  return {
    getSavingPlans,
    getSavingPlan,
    createSavingPlan,
    updateSavingPlan,
    toggleSavingPlan,
    deleteSavingPlan,
  };
}
