import { z } from "zod";

export const signUpFormSchema = z
  .object({
    firstName: z.string().min(1, "err_first_name_req"),
    lastName: z.string().min(1, "err_last_name_req"),
    email: z.string().min(1, "err_email_req").email("err_email_invalid"),
    password: z.string().min(6, "err_password_req"),
    confirmPassword: z.string().min(1, "err_confirm_password_req"),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "err_password_match",
    path: ["confirmPassword"],
  });

export type SignUpFormData = z.infer<typeof signUpFormSchema>;
