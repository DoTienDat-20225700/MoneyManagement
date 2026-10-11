import { zodResolver } from "@hookform/resolvers/zod";
import { TextField, Button, Typography, Box } from "@mui/material";
import { useForm, Controller } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../hooks/useAuth";
import { SignInFormData, signInFormSchema } from "../../schemas/signInSchema";
import { useMutation } from "@tanstack/react-query";
import { grey } from "@mui/material/colors";
import { useLanguage } from "../../context/LanguageContext";
import { useSnackbar } from "notistack";

function SignInForm() {
  const navigate = useNavigate();
  const { t } = useLanguage();
  const { SignIn } = useAuth();
  const { enqueueSnackbar } = useSnackbar();

  const { handleSubmit, control } = useForm<SignInFormData>({
    resolver: zodResolver(signInFormSchema),
  });

  const { mutate, isPending } = useMutation({
    mutationFn: SignIn,
    onSuccess: () => {
      navigate("/");
    },
    onError: (err: any) => {
      const errorMsg = !err?.response
        ? t("no_server_response")
        : t("err_invalid_credentials");
      enqueueSnackbar(errorMsg, {
        variant: "error",
        autoHideDuration: 3500,
        anchorOrigin: { horizontal: "right", vertical: "bottom" },
      });
    },
  });

  function signIn(data: SignInFormData) {
    mutate({ email: data.email, password: data.password });
  }

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: 5,
        width: "400px",
      }}
    >
      <Box>
        <Typography
          variant="h5"
          component="h1"
          fontWeight={600}
          lineHeight={1.6}
        >
          {t("welcome_back")}
        </Typography>
        <Typography variant="body2" component="p" color={grey[500]} mt={0.5}>
          {t("sign_in_desc")}
        </Typography>
      </Box>
      <form
        onSubmit={handleSubmit(signIn)}
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "24px",
        }}
      >
        <Controller
          name="email"
          control={control}
          render={({ field: { onChange, value }, fieldState: { error } }) => (
            <TextField
              fullWidth
              size="small"
              autoFocus
              helperText={
                error
                  ? error.message === "err_email_invalid"
                    ? t("err_email_invalid")
                    : t("err_email_req")
                  : null
              }
              defaultValue={""}
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
              defaultValue={""}
              error={!!error}
              onChange={onChange}
              value={value ?? ""}
              label={t("password")}
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
          sx={{ py: 1.2, fontWeight: 600, textTransform: "none" }}
        >
          {t("sign_in")}
        </Button>
        <Typography
          color="gray"
          variant="body2"
          component="p"
          textAlign="center"
        >
          {t("dont_have_account")}{" "}
          <Link to="/auth/sign-up" style={{ color: "#4caf50", fontWeight: 500 }}>
            {t("sign_up")}
          </Link>
        </Typography>
      </form>
    </Box>
  );
}

export default SignInForm;
