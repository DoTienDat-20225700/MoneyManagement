import dayjs, { Dayjs } from "dayjs";
import { z } from "zod";
import { TypeOption } from "../enums/Enums";

export const newTransactionFormSchema = z.object({
  title: z.string().min(1, "Title must be at least 1 character long."),
  value: z
    .union([z.string(), z.number()])
    .transform((val) => {
      if (typeof val === "number") return val;
      const parsed = parseFloat(val.replace(/\./g, "").replace(",", "."));
      return isNaN(parsed) ? 0 : parsed;
    })
    .refine((val) => val >= 1, {
      message: "Please select an amount >= 1.",
    }),
  label: z
    .object({
      id: z.number(),
      name: z.string(),
      color: z.string(),
    })
    .nullable()
    .refine((val) => val !== null && val.name && val.name.trim().length > 0, {
      message: "Please select a label.",
    }),
  date: z.custom<Dayjs>(
    (val) => dayjs.isDayjs(val) && (val as Dayjs).isValid(),
    "Please select a date"
  ),
  type: z.nativeEnum(TypeOption).default(TypeOption.EXPENSE),
  updateWallet: z.boolean().default(false),
  recurring: z.boolean().default(false),
});

export type NewTransactionFormInput = z.input<typeof newTransactionFormSchema>;
export type NewTransactionFormData = z.output<typeof newTransactionFormSchema>;

