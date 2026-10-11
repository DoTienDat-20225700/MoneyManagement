import { z } from "zod";
import { TypeOption } from "../enums/Enums";
import { BankInstitutions } from "../models/Invoices";

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ACCEPTED_DOC_TYPES = [
  "application/pdf",
  "image/png",
  "image/jpeg",
  "image/jpg",
  "image/webp",
];
const ACCEPTED_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg", ".webp"];

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
        (files) => {
          if (!files?.[0]) return true;
          const file = files[0];
          if (file.type && ACCEPTED_DOC_TYPES.includes(file.type)) {
            return true;
          }
          const lowerName = file.name.toLowerCase();
          return ACCEPTED_EXTENSIONS.some((ext) => lowerName.endsWith(ext));
        },
        "err_file_type"
      ),
    institution: z
      .nativeEnum(BankInstitutions)
      .default(BankInstitutions.GENERAL_VN),
    // global optional attributes
    type: z.nativeEnum(TypeOption).optional(),
    label: z.union([z.string(), z.number()]).optional(),
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
