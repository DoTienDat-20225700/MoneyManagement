import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { Box, Button, CircularProgress, TextField, Typography } from "@mui/material";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { useSnackbar } from "notistack";
import {
  NewLabelFormData,
  newLabelFormSchema,
} from "../../schemas/newLabelSchema";
import { grey } from "@mui/material/colors";
import { useLabels } from "../../hooks/api/useLabels";
import { useLanguage } from "../../context/LanguageContext";

function NewLabelForm() {
  const { t } = useLanguage();
  const queryClient = useQueryClient();
  const { createLabel } = useLabels();
  const { enqueueSnackbar } = useSnackbar();
  const [_, setSearchParams] = useSearchParams();
  const {
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<NewLabelFormData>({
    resolver: zodResolver(newLabelFormSchema),
    defaultValues: {
      name: "",
      color: "#000000",
    },
  });

  const { mutateAsync, isPending } = useMutation({
    mutationFn: createLabel,
    onSuccess: () => {
      setSearchParams((state) => {
        state.delete("label");
        return state;
      });
      queryClient.invalidateQueries({
        queryKey: ["wallet"],
      });
      queryClient.invalidateQueries({
        queryKey: ["labels"],
      });
      enqueueSnackbar(t("label_created"), {
        variant: "success",
        autoHideDuration: 3000,
        anchorOrigin: { horizontal: "right", vertical: "bottom" },
      });
    },
    onError: (err: any) => {
      console.log(err);
      const errorMsg = !err?.response
        ? t("no_server_response")
        : t("err_label_create");
      enqueueSnackbar(errorMsg, {
        variant: "error",
        autoHideDuration: 3000,
        anchorOrigin: { horizontal: "right", vertical: "bottom" },
      });
    },
  });

  async function addNewLabel(data: NewLabelFormData) {
    await mutateAsync({ label: data });
  }

  return (
    <form
      onSubmit={handleSubmit(addNewLabel)}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 20,
        width: "500px",
        marginTop: 20,
      }}
    >
      <Controller
        name="name"
        control={control}
        render={({ field: { onChange, value } }) => (
          <TextField
            fullWidth
            autoFocus
            helperText={errors.name ? t("err_label_name_req") : " "}
            error={!!errors.name}
            onChange={onChange}
            value={value}
            label={t("label_name")}
            variant="outlined"
            size="small"
          />
        )}
      />
      <Box
        sx={{
          display: "flex",
          flexDirection: "row",
          alignItems: "center",
          gap: 2,
        }}
      >
        <Controller
          name="color"
          control={control}
          render={({ field: { onChange, value, name } }) => (
            <>
              <Typography>{value}</Typography>
              <TextField
                name={name}
                onChange={onChange}
                value={value}
                label={t("color")}
                variant="outlined"
                size="small"
                type="color"
                fullWidth
                sx={{ borderColor: grey[800], maxHeight: "32px" }}
              />
            </>
          )}
        />
      </Box>

      <Button
        type="submit"
        variant="contained"
        disabled={isSubmitting || isPending}
        startIcon={isSubmitting || isPending ? <CircularProgress size={16} color="inherit" /> : null}
      >
        {isSubmitting || isPending ? t("loading") : t("create")}
      </Button>
    </form>
  );
}

export default NewLabelForm;
