import { z } from "zod";

export const signInFormSchema = z.object({
  email: z.string().min(1, "err_email_req").email("err_email_invalid"),
  password: z.string().min(1, "err_password_req"),
});

export type SignInFormData = z.infer<typeof signInFormSchema>;
