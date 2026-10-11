import dayjs, { Dayjs } from "dayjs";
import { z } from "zod";
import { TypeOption } from "../enums/Enums";

export const newTransactionFormSchema = z.object({
  title: z.string().min(1, "err_title_req"),
  value: z
    .union([z.string(), z.number()])
    .transform((val) => {
      if (typeof val === "number") return val;
      const parsed = parseFloat(val.replace(/\./g, "").replace(",", "."));
      return isNaN(parsed) ? 0 : parsed;
    })
    .refine((val) => val >= 1, {
      message: "err_amount_req",
    }),
  label: z
    .object({
      id: z.number(),
      name: z.string(),
      color: z.string(),
    })
    .nullable()
    .refine((val) => val !== null && val.name && val.name.trim().length > 0, {
      message: "err_label_req",
    }),
  date: z.custom<Dayjs>(
    (val) => dayjs.isDayjs(val) && (val as Dayjs).isValid(),
    "err_date_req"
  ),
  type: z.nativeEnum(TypeOption).default(TypeOption.EXPENSE),
  updateWallet: z.boolean().default(false),
  recurring: z.boolean().default(false),
});

export type NewTransactionFormInput = z.input<typeof newTransactionFormSchema>;
export type NewTransactionFormData = z.output<typeof newTransactionFormSchema>;

