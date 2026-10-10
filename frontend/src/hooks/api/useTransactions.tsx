import { AggregatedExpense, Transaction } from "../../models/Transaction";
import { NewTransactionFormData } from "../../schemas/newTransactionSchema";
import useAxiosPrivate from "../useAxiosPrivate";

export function useTransactions() {
  const axiosPrivate = useAxiosPrivate();

  async function getTransactions(
    limit: number = 0,
    chartType: number = 0,
    startDate?: Date,
    endDate?: Date
  ): Promise<Transaction[] | AggregatedExpense[]> {
    try {
      let endpoint = `/transactions?limit=${limit}&chart_type=${chartType}`;
      if (startDate)
        endpoint += `&start_date=${startDate.toISOString().split("T")[0]}`;
      if (endDate)
        endpoint += `&end_date=${endDate.toISOString().split("T")[0]}`;
      const response = await axiosPrivate.get(endpoint);

      if (chartType === 2) {
        return response.data as AggregatedExpense[];
      }
      return response.data as Transaction[];
    } catch (error) {
      console.log(error);
      throw error;
    }
  }

  async function createTransaction({
    transaction,
  }: {
    transaction: NewTransactionFormData;
  }): Promise<{ [key: string]: string } | null> {
    try {
      const newTransaction = {
        ...transaction,
        date: transaction.date,
      };
      const response = await axiosPrivate.post("/transaction/", newTransaction);
      return response.data;
    } catch (error) {
      console.log(error);
      throw error;
    }
  }

  async function deleteTransaction({
    transactionId,
  }: {
    transactionId: number;
  }): Promise<{ [key: string]: string } | null> {
    try {
      const response = await axiosPrivate.delete(
        `/transaction/${transactionId}`
      );
      return response.data;
    } catch (error) {
      console.log(error);
      throw error;
    }
  }

  return { getTransactions, createTransaction, deleteTransaction };
}
