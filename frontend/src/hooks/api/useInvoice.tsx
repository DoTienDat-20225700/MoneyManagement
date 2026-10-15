import { TypeOption } from "../../enums/Enums";
import useAxiosPrivate from "../useAxiosPrivate";

export interface ParsedInvoiceResult {
  file_name: string;
  title: string;
  value: number | null;
  formatted_value: string;
  date: string;
  formatted_date: string;
  institution: string;
  is_valid: boolean;
}

export interface ImportedTransactionItem {
  id: number;
  title: string;
  value: number;
  formatted_value: string;
  date: string;
}

export interface UploadInvoiceResponse {
  success: boolean;
  message: string;
  imported?: ImportedTransactionItem[];
}

export function useInvoice() {
  const axiosPrivate = useAxiosPrivate();

  async function previewInvoices({
    invoices,
    institution,
  }: {
    invoices: FileList;
    institution?: string;
  }): Promise<ParsedInvoiceResult[]> {
    try {
      const endpoint = `/import/preview/?institution=${encodeURIComponent(institution || "")}`;
      const formData = new FormData();
      if (invoices) {
        for (let i = 0; i < invoices.length; i++) {
          formData.append("files[]", invoices[i]);
        }
      }
      const response = await axiosPrivate.post(endpoint, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      return response.data.results as ParsedInvoiceResult[];
    } catch (error: any) {
      console.log(error);
      throw error;
    }
  }

  async function uploadInvoices({
    invoices,
    institution,
    type,
    label,
    updateWallet,
  }: {
    invoices: FileList;
    institution?: string;
    type?: TypeOption;
    label?: string | number;
    updateWallet?: boolean;
  }): Promise<UploadInvoiceResponse | null> {
    try {
      let endpoint = `/import/?institution=${institution}`;
      if (type) endpoint += `&type=${type}`;
      if (label) endpoint += `&label=${label}`;
      if (updateWallet) endpoint += `&updateWallet=${updateWallet ? 1 : 0}`;

      const formData = new FormData();
      if (invoices) {
        for (let i = 0; i < invoices.length; i++) {
          formData.append("files[]", invoices[i]);
        }
      }

      const response = await axiosPrivate.post(endpoint, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      return response.data as UploadInvoiceResponse;
    } catch (error: any) {
      console.log(error);
      throw error;
    }
  }

  return { uploadInvoices, previewInvoices };
}

