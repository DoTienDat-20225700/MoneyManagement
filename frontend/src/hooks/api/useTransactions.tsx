import { AggregatedExpense, Transaction } from "../../models/Transaction";
import { NewTransactionFormData } from "../../schemas/newTransactionSchema";
import useAxiosPrivate from "../useAxiosPrivate";

export function useTransactions() {
  const axiosPrivate = useAxiosPrivate();

  async function getTransactions(
    limitOrOptions:
      | number
      | {
          limit?: number;
          chartType?: number;
          startDate?: Date;
          endDate?: Date;
          search?: string;
        } = 0,
    chartType: number = 0,
    startDate?: Date,
    endDate?: Date,
    search?: string
  ): Promise<Transaction[] | AggregatedExpense[]> {
    let limit = 0;
    let actualChartType = 0;
    let actualStartDate: Date | undefined;
    let actualEndDate: Date | undefined;
    let actualSearch: string | undefined;

    if (typeof limitOrOptions === "object" && limitOrOptions !== null) {
      limit = limitOrOptions.limit ?? 0;
      actualChartType = limitOrOptions.chartType ?? 0;
      actualStartDate = limitOrOptions.startDate;
      actualEndDate = limitOrOptions.endDate;
      actualSearch = limitOrOptions.search;
    } else {
      limit = limitOrOptions;
      actualChartType = chartType;
      actualStartDate = startDate;
      actualEndDate = endDate;
      actualSearch = search;
    }

    try {
      let endpoint = `/transactions?limit=${limit}&chart_type=${actualChartType}`;
      if (actualStartDate)
        endpoint += `&start_date=${actualStartDate.toISOString().split("T")[0]}`;
      if (actualEndDate)
        endpoint += `&end_date=${actualEndDate.toISOString().split("T")[0]}`;
      if (actualSearch && actualSearch.trim())
        endpoint += `&search=${encodeURIComponent(actualSearch.trim())}`;
      const response = await axiosPrivate.get(endpoint);

      if (actualChartType === 2) {
        return response.data as AggregatedExpense[];
      }
      return response.data as Transaction[];
    } catch (error) {
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
        date: transaction.date.toISOString ? transaction.date.toISOString().split("T")[0] : transaction.date,
        recurrent: transaction.recurring,
      };
      const response = await axiosPrivate.post("/transaction/", newTransaction);
      return response.data;
    } catch (error) {
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
      throw error;
    }
  }

  async function updateTransaction({
    transactionId,
    transaction,
  }: {
    transactionId: number;
    transaction: any;
  }): Promise<{ [key: string]: string } | null> {
    try {
      const response = await axiosPrivate.put(
        `/transaction/${transactionId}`,
        transaction
      );
      return response.data;
    } catch (error) {
      throw error;
    }
  }

  return { getTransactions, createTransaction, deleteTransaction, updateTransaction };
}
