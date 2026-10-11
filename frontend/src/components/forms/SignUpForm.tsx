import { zodResolver } from "@hookform/resolvers/zod";
import { TextField, Button, Typography, Box } from "@mui/material";
import { useForm, Controller } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { useMutation } from "@tanstack/react-query";
import { grey } from "@mui/material/colors";
import { SignUpFormData, signUpFormSchema } from "../../schemas/signUpSchema";
import { useLanguage } from "../../context/LanguageContext";
import { useSnackbar } from "notistack";

function SignUpForm() {
  const navigate = useNavigate();
  const { t } = useLanguage();
  const { SignUp } = useAuth();
  const { enqueueSnackbar } = useSnackbar();

  const { handleSubmit, control } = useForm<SignUpFormData>({
    resolver: zodResolver(signUpFormSchema),
    defaultValues: {
      firstName: "",
      lastName: "",
      email: "",
      password: "",
      confirmPassword: "",
    },
  });

  const { mutate, isPending } = useMutation({
    mutationFn: SignUp,
    onSuccess: () => {
      enqueueSnackbar(t("register_success"), {
        variant: "success",
        autoHideDuration: 3000,
        anchorOrigin: { horizontal: "right", vertical: "bottom" },
      });
      navigate("/auth/sign-in");
    },
    onError: (err: any) => {
      const errorMsg = !err?.response
        ? t("no_server_response")
        : t("err_register_failed");
      enqueueSnackbar(errorMsg, {
        variant: "error",
        autoHideDuration: 3500,
        anchorOrigin: { horizontal: "right", vertical: "bottom" },
      });
    },
  });

  function signUp(data: SignUpFormData) {
    mutate({
      user: {
        firstName: data.firstName,
        lastName: data.lastName,
        email: data.email,
        password: data.password,
      },
    });
  }

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 4,
        width: "420px",
      }}
    >
      <Box>
        <Typography
          variant="h5"
          component="h1"
          fontWeight={600}
          lineHeight={1.6}
        >
          {t("create_account")}
        </Typography>
        <Typography variant="body2" component="p" color={grey[500]} mt={0.5}>
          {t("sign_up_desc")}
        </Typography>
      </Box>
      <form
        onSubmit={handleSubmit(signUp)}
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "20px",
        }}
      >
        <Box
          sx={{
            display: "flex",
            flexDirection: "row",
            alignItems: "center",
            gap: 2,
          }}
        >
          <Controller
            name="firstName"
            control={control}
            render={({ field: { onChange, value }, fieldState: { error } }) => (
              <TextField
                fullWidth
                size="small"
                autoFocus
                helperText={error ? t("err_first_name_req") : null}
                error={!!error}
                onChange={onChange}
                value={value ?? ""}
                label={t("first_name")}
                variant="outlined"
              />
            )}
          />

          <Controller
            name="lastName"
            control={control}
            render={({ field: { onChange, value }, fieldState: { error } }) => (
              <TextField
                fullWidth
                size="small"
                helperText={error ? t("err_last_name_req") : null}
                error={!!error}
                onChange={onChange}
                value={value ?? ""}
                label={t("last_name")}
                variant="outlined"
              />
            )}
          />
        </Box>

        <Controller
          name="email"
          control={control}
          render={({ field: { onChange, value }, fieldState: { error } }) => (
            <TextField
              fullWidth
              size="small"
              helperText={
                error
                  ? error.message === "err_email_invalid"
                    ? t("err_email_invalid")
                    : t("err_email_req")
                  : null
              }
              error={!!error}
              onChange={onChange}
              value={value ?? ""}
              label={t("email")}
              variant="outlined"
            />
          )}
        />

        <Controller
          name="password"
          control={control}
          render={({ field: { onChange, value }, fieldState: { error } }) => (
            <TextField
              fullWidth
              size="small"
              helperText={error ? t("err_password_req") : null}
              error={!!error}
              onChange={onChange}
              value={value ?? ""}
              label={t("password")}
              variant="outlined"
              type="password"
            />
          )}
        />

        <Controller
          name="confirmPassword"
          control={control}
          render={({ field: { onChange, value }, fieldState: { error } }) => (
            <TextField
              fullWidth
              size="small"
              helperText={
                error
                  ? error.message === "err_confirm_password_req"
                    ? t("err_confirm_password_req")
                    : t("err_password_match")
                  : null
              }
              error={!!error}
              onChange={onChange}
              value={value ?? ""}
              label={t("confirm_password")}
              variant="outlined"
              type="password"
            />
          )}
        />

        <Button
          type="submit"
          variant="contained"
          size="medium"
          disabled={isPending}
          sx={{ py: 1.2, fontWeight: 600, textTransform: "none", mt: 1 }}
        >
          {t("sign_up")}
        </Button>
        <Typography
          color="gray"
          variant="body2"
          component="p"
          textAlign="center"
        >
          {t("already_have_account")}{" "}
          <Link to="/auth/sign-in" style={{ color: "#4caf50", fontWeight: 500 }}>
            {t("sign_in")}
          </Link>
        </Typography>
      </form>
    </Box>
  );
}

export default SignUpForm;
