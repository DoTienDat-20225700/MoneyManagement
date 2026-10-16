import dayjs, { Dayjs } from "dayjs";
import { z } from "zod";

export const debtContractSchema = z
  .object({
    person_name: z.string().min(1, "err_person_name_req"),
    contact_info: z.string().optional().default(""),
    type: z.enum(["DEBT_BORROWED", "LOAN_GIVEN", "INSTALLMENT"]),
    principal_amount: z
      .union([z.string(), z.number()])
      .transform((val) => {
        if (typeof val === "number") return val;
        const parsed = parseFloat(String(val).replace(/\./g, "").replace(",", "."));
        return isNaN(parsed) ? 0 : parsed;
      })
      .refine((val) => val > 0, {
        message: "err_amount_req",
      }),
    start_date: z.custom<Dayjs>(
      (val) => dayjs.isDayjs(val) && (val as Dayjs).isValid(),
      "err_date_req"
    ),
    due_date: z
      .custom<Dayjs | null>(
        (val) => val === null || (dayjs.isDayjs(val) && (val as Dayjs).isValid()),
        "err_date_req"
      )
      .nullable()
      .optional(),
    installment_months: z
      .union([z.string(), z.number()])
      .optional()
      .nullable()
      .transform((val) => {
        if (val === undefined || val === null || val === "") return null;
        const num = Number(val);
        return isNaN(num) || num <= 0 ? null : Math.floor(num);
      }),
    update_wallet: z.boolean().default(false),
    description: z.string().optional().default(""),
  })
  .refine(
    (data) => {
      if (data.type === "INSTALLMENT") {
        return data.installment_months !== null && data.installment_months > 0;
      }
      return true;
    },
    {
      message: "err_installment_months_req",
      path: ["installment_months"],
    }
  );

export type DebtContractInput = z.input<typeof debtContractSchema>;
export type DebtContractData = z.output<typeof debtContractSchema>;

export const debtPaymentSchema = z.object({
  amount: z
    .union([z.string(), z.number()])
    .transform((val) => {
      if (typeof val === "number") return val;
      const parsed = parseFloat(String(val).replace(/\./g, "").replace(",", "."));
      return isNaN(parsed) ? 0 : parsed;
    })
    .refine((val) => val > 0, {
      message: "err_amount_req",
    }),
  date: z.custom<Dayjs>(
    (val) => dayjs.isDayjs(val) && (val as Dayjs).isValid(),
    "err_date_req"
  ),
  update_wallet: z.boolean().default(false),
  note: z.string().optional().default(""),
});

export type DebtPaymentInput = z.input<typeof debtPaymentSchema>;
export type DebtPaymentData = z.output<typeof debtPaymentSchema>;
