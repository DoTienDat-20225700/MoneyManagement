import { z } from "zod";
import { TypeOption } from "../enums/Enums";
import { BankInstitutions } from "../models/Invoices";

const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB
const ACCEPTED_DOC_TYPES = ["application/pdf"];

export const newInvoiceImportSchema = z
  .object({
    invoices: z
      .instanceof(FileList)
      .refine(
        (files) => files && files.length > 0,
        "err_invoice_req"
      )
      .refine(
        (files) => !files?.[0] || files[0].size <= MAX_FILE_SIZE,
        "err_file_size"
      )
      .refine(
        (files) => !files?.[0] || ACCEPTED_DOC_TYPES.includes(files[0].type),
        "err_file_type"
      ),
    institution: z
      .nativeEnum(BankInstitutions)
      .default(BankInstitutions.GENERAL_VN),
    // global optional attributes
    type: z.nativeEnum(TypeOption).optional(),
    updateWallet: z.boolean().optional(),
  })
  .refine((data) => {
    // Check if updateWallet is true and type is not set
    if (data.updateWallet === true && data.type === undefined) {
      throw new Error("type is required when updateWallet is true");
    }

    // All other cases are valid
    return true;
  });

export type NewInvoiceImportFormData = z.infer<typeof newInvoiceImportSchema>;
