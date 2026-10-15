import { FinancialReportSummary, ReportFilterParams } from "../../models/FinancialReport";
import { Transaction } from "../../models/Transaction";
import useAxiosPrivate from "../useAxiosPrivate";

export function useReports() {
  const axiosPrivate = useAxiosPrivate();

  async function getReportSummary(params: ReportFilterParams): Promise<FinancialReportSummary> {
    const cleanParams: Record<string, string | number> = {};
    if (params.start_date) cleanParams.start_date = params.start_date;
    if (params.end_date) cleanParams.end_date = params.end_date;
    if (params.type && params.type !== "ALL") cleanParams.type = params.type;
    if (params.label_id !== undefined && params.label_id !== "" && params.label_id !== "all") {
      cleanParams.label_id = params.label_id;
    }
    if (params.wallet_id !== undefined && params.wallet_id !== "") {
      cleanParams.wallet_id = params.wallet_id;
    }

    const response = await axiosPrivate.get("/reports/summary/", { params: cleanParams });
    return response.data as FinancialReportSummary;
  }

  async function getReportTransactions(params: ReportFilterParams): Promise<Transaction[]> {
    const cleanParams: Record<string, string | number> = {};
    if (params.start_date) cleanParams.start_date = params.start_date;
    if (params.end_date) cleanParams.end_date = params.end_date;
    if (params.type && params.type !== "ALL") cleanParams.type = params.type;
    if (params.label_id !== undefined && params.label_id !== "" && params.label_id !== "all") {
      cleanParams.label_id = params.label_id;
    }
    if (params.search && params.search.trim()) {
      cleanParams.search = params.search.trim();
    }

    const response = await axiosPrivate.get("/reports/transactions/", { params: cleanParams });
    return response.data as Transaction[];
  }

  async function downloadReportCSV(params: ReportFilterParams): Promise<void> {
    const cleanParams: Record<string, string | number> = {};
    if (params.start_date) cleanParams.start_date = params.start_date;
    if (params.end_date) cleanParams.end_date = params.end_date;
    if (params.type && params.type !== "ALL") cleanParams.type = params.type;
    if (params.label_id !== undefined && params.label_id !== "" && params.label_id !== "all") {
      cleanParams.label_id = params.label_id;
    }

    const response = await axiosPrivate.get("/reports/export/csv/", {
      params: cleanParams,
      responseType: "blob",
    });

    const blob = new Blob([response.data], { type: "text/csv;charset=utf-8;" });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    const startStr = params.start_date || "from";
    const endStr = params.end_date || "to";
    link.setAttribute("download", `bao_cao_tai_chinh_${startStr}_${endStr}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  async function downloadReportExcel(params: ReportFilterParams): Promise<void> {
    const cleanParams: Record<string, string | number> = {};
    if (params.start_date) cleanParams.start_date = params.start_date;
    if (params.end_date) cleanParams.end_date = params.end_date;
    if (params.type && params.type !== "ALL") cleanParams.type = params.type;
    if (params.label_id !== undefined && params.label_id !== "" && params.label_id !== "all") {
      cleanParams.label_id = params.label_id;
    }

    const response = await axiosPrivate.get("/reports/export/excel/", {
      params: cleanParams,
      responseType: "blob",
    });

    const blob = new Blob([response.data], {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    const startStr = params.start_date || "from";
    const endStr = params.end_date || "to";
    link.setAttribute("download", `bao_cao_tai_chinh_${startStr}_${endStr}.xlsx`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  }

  return {
    getReportSummary,
    getReportTransactions,
    downloadReportCSV,
    downloadReportExcel,
  };
}

