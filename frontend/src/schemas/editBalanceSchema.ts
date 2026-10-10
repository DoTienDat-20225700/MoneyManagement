import { z } from "zod";

export const editBalanceFormSchema = z.object({
  balance: z.string().transform((value) => {
    const parsed = parseFloat(value.replace(/\./g, "").replace(",", "."));
    return isNaN(parsed) ? 0 : parsed;
  }),
});

export type EditBalanceFormData = z.infer<typeof editBalanceFormSchema>;
