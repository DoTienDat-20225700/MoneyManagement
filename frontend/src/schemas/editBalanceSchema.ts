import { z } from "zod";

export const editBalanceFormSchema = z.object({
  balance: z.string(),
});

export type EditBalanceFormData = z.infer<typeof editBalanceFormSchema>;
