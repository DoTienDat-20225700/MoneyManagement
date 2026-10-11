import { z } from "zod";

export const newLabelFormSchema = z.object({
  name: z.string().min(1, "err_label_name_req"),
  color: z.string(),
});

export type NewLabelFormData = z.infer<typeof newLabelFormSchema>;
