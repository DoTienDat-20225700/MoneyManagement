import { TypeOption } from "../../enums/Enums";
import useAxiosPrivate from "../useAxiosPrivate";

export function useInvoice() {
  const axiosPrivate = useAxiosPrivate();

  async function uploadInvoices({
    invoices,
    institution,
    type,
    updateWallet,
  }: {
    invoices: FileList;
    institution?: String;
    type?: TypeOption;
    updateWallet?: boolean;
  }): Promise<{ [key: string]: string } | null> {
    try {
      let endpoint = `/import/?institution=${institution}`;
      if (type) endpoint += `&type=${type}`;
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

      return await response.data;
    } catch (error: any) {
      console.log(error);
      throw error;
    }
  }

  return { uploadInvoices };
}
