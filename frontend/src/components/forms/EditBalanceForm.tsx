import { zodResolver } from "@hookform/resolvers/zod";
import { InputAdornment, TextField } from "@mui/material";
import { grey } from "@mui/material/colors";
import { useQueryClient, useMutation } from "@tanstack/react-query";
import { Controller, useForm } from "react-hook-form";
import {
  EditBalanceFormData,
  editBalanceFormSchema,
} from "../../schemas/editBalanceSchema";
import { useWallet } from "../../hooks/api/useWallet";
import { formatCurrency } from "../../utils/utils";

import { useLanguage } from "../../context/LanguageContext";
import { useSnackbar } from "notistack";

interface Props {
  setState: React.Dispatch<React.SetStateAction<boolean>>;
}

function EditBalanceForm(props: Props) {
  const { t } = useLanguage();
  const { enqueueSnackbar } = useSnackbar();
  const queryClient = useQueryClient();
  const { updateWallet } = useWallet();

  const {
    handleSubmit,
    control,
  } = useForm<EditBalanceFormData>({
    resolver: zodResolver(editBalanceFormSchema),
    defaultValues: {
      balance: "",
    },
  });

  const { mutateAsync } = useMutation({
    mutationFn: updateWallet,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["wallet"],
      });
      props.setState(false);
    },
    onError: (err: any) => {
      const errorMsg = !err?.response
        ? t("no_server_response")
        : t("err_balance_update");
      enqueueSnackbar(errorMsg, {
        variant: "error",
        autoHideDuration: 3000,
        anchorOrigin: { horizontal: "right", vertical: "bottom" },
      });
    },
  });

  async function editBalance(data: EditBalanceFormData) {
    const parsed = parseFloat((data.balance ?? "").replace(/\./g, "").replace(",", "."));
    await mutateAsync({
      value: isNaN(parsed) ? 0 : parsed,
    });
  }

  return (
    <form
      onSubmit={handleSubmit(editBalance)}
      id="editBalance"
      className="flex flex-row items-center justify-center gap-1"
    >
      <Controller
        name="balance"
        control={control}
        render={({ field: { onChange, value }, fieldState: { error } }) => (
          <TextField
            error={!!error}
            onChange={(e) => {
              const formattedValue = formatCurrency(e.target.value);
              onChange(formattedValue);
            }}
            value={value ?? ""}
            label=""
            variant="outlined"
            size="small"
            sx={{ borderColor: grey[800], maxHeight: "32px" }}
            placeholder="0"
            InputProps={{
              style: { fontSize: "20px", height: "38px" },
              endAdornment: (
                <InputAdornment position="end">đ</InputAdornment>
              ),
            }}
          />
        )}
      />
    </form>
  );
}

export default EditBalanceForm;
