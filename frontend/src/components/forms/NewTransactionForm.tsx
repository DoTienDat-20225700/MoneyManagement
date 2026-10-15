import { zodResolver } from "@hookform/resolvers/zod";
import AddIcon from "@mui/icons-material/Add";
import {
  Box,
  Button,
  Checkbox,
  CircularProgress,
  FormControl,
  FormControlLabel,
  FormGroup,
  FormLabel,
  InputAdornment,
  MenuItem,
  Radio,
  RadioGroup,
  TextField,
  Typography,
} from "@mui/material";
import { grey } from "@mui/material/colors";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import dayjs from "dayjs";
import { useSnackbar } from "notistack";
import { Controller, useForm } from "react-hook-form";
import { useSearchParams } from "react-router-dom";
import { TypeOption } from "../../enums/Enums";
import { useTransactions } from "../../hooks/api/useTransactions";
import { typeOptionMask } from "../../models/Transaction";
import {
  NewTransactionFormData,
  NewTransactionFormInput,
  newTransactionFormSchema,
} from "../../schemas/newTransactionSchema";
import { formatCurrency } from "../../utils/utils";
import AsyncAutocomplete from "../AsyncAutocomplete";
import { useLanguage } from "../../context/LanguageContext";

function NewTransactionForm() {
  const { language, dateFormat, t } = useLanguage();
  const queryClient = useQueryClient();
  const { createTransaction } = useTransactions();
  const { enqueueSnackbar } = useSnackbar();
  const [_, setSearchParams] = useSearchParams();
  const {
    handleSubmit,
    control,
    watch,
    formState: { errors, isSubmitting },
  } = useForm<NewTransactionFormInput, any, NewTransactionFormData>({
    resolver: zodResolver(newTransactionFormSchema),
    defaultValues: {
      title: "",
      value: "",
      label: null,
      date: dayjs(),
      type: TypeOption.EXPENSE,
      updateWallet: false,
      recurring: false,
      amount: 1,
      duration: "MONTHS",
    },
  });

  const isRecurring = watch("recurring");

  const { mutateAsync, isPending } = useMutation({
    mutationFn: createTransaction,
    onSuccess: () => {
      setSearchParams((state) => {
        state.delete("transaction");
        return state;
      });
      //get transaction id
      // queryClient.setQueryData(['transactions', { id: variables.transaction. }], data)
      queryClient.invalidateQueries({
        queryKey: ["transactions"],
      });
      queryClient.invalidateQueries({
        queryKey: ["wallet"],
      });
      queryClient.invalidateQueries({
        queryKey: ["budgets"],
      });
      queryClient.invalidateQueries({
        queryKey: ["budget_summary"],
      });
      enqueueSnackbar(t("transaction_created"), {
        variant: "success",
        autoHideDuration: 3000,
        anchorOrigin: { horizontal: "right", vertical: "bottom" },
      });
    },
    onError: (err: any) => {
      console.log(err);
      const errorMsg = !err?.response
        ? t("no_server_response")
        : t("err_transaction_create");
      enqueueSnackbar(errorMsg, {
        variant: "error",
        autoHideDuration: 3000,
        anchorOrigin: { horizontal: "right", vertical: "bottom" },
      });
    },
  });

  async function addNewTransaction(data: NewTransactionFormData) {
    await mutateAsync({ transaction: data });
  }

  return (
    <form
      onSubmit={handleSubmit(addNewTransaction)}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: 20,
        width: "500px",
        marginTop: 20,
      }}
    >
      <Controller
        name="title"
        control={control}
        render={({ field: { onChange, value } }) => (
          <TextField
            fullWidth
            autoFocus
            helperText={errors.title ? t("err_title_req") : " "}
            error={!!errors.title}
            onChange={onChange}
            value={value ?? ""}
            label={t("title")}
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
          name="label"
          control={control}
          render={({ field: { onChange, value } }) => (
            <AsyncAutocomplete
              onChange={onChange}
              value={value}
              helperText={errors.label ? t("err_label_req") : " "}
              error={!!errors.label}
            />
          )}
        />

        <Button
          variant="contained"
          onClick={() =>
            setSearchParams((state) => {
              if (!state.get("label")) state.set("label", "1");
              return state;
            })
          }
          sx={{ mb: 3 }}
        >
          <AddIcon />
        </Button>
      </Box>

      <Box
        sx={{
          display: "flex",
          flexDirection: "row",
          alignItems: "center",
          gap: 2,
        }}
      >
        <Controller
          name="value"
          control={control}
          render={({ field: { onChange, value } }) => (
            <TextField
              fullWidth
              helperText={errors.value ? t("err_amount_req") : " "}
              error={!!errors.value}
              onChange={(e) => {
                const formattedValue = formatCurrency(e.target.value);
                onChange(formattedValue);
              }}
              value={value ?? ""}
              label={t("amount")}
              variant="outlined"
              size="small"
              placeholder="0"
              InputProps={{
                style: { fontSize: "14px", height: "40px" },
                endAdornment: (
                  <InputAdornment position="end">đ</InputAdornment>
                ),
              }}
            />
          )}
        />

        <Controller
          name="date"
          control={control}
          render={({ field: { onChange, value } }) => (
            <>
              <LocalizationProvider
                dateAdapter={AdapterDayjs}
                adapterLocale={language}
              >
                <DatePicker
                  label={t("date")}
                  format={dateFormat}
                  value={value}
                  onChange={onChange}
                  slotProps={{
                    textField: {
                      size: "small",
                      error: !!errors.date,
                      helperText: errors.date ? t("err_date_req") : " ",
                    },
                  }}
                />
              </LocalizationProvider>
            </>
          )}
        />
      </Box>
      <Controller
        name="type"
        control={control}
        render={({ field: { onChange, value, name } }) => (
          <FormControl>
            <FormLabel
              sx={{ mb: 1, "&.Mui-disabled": { color: "white" } }}
              disabled={true}
            >
              {t("type")}
            </FormLabel>
            <RadioGroup
              defaultValue={TypeOption.EXPENSE}
              name={name}
              value={value}
              onChange={onChange}
            >
              {Object.values(TypeOption).map((item, i) => {
                return (
                  <FormControlLabel
                    key={i}
                    value={item}
                    control={<Radio />}
                    label={typeOptionMask(item, language)}
                    sx={{
                      backgroundColor: grey[900],
                      p: 1,
                      m: 0.5,
                      borderRadius: 2,
                    }}
                  />
                );
              })}
            </RadioGroup>
          </FormControl>
        )}
      />
      <Typography component="h6">{t("options")}</Typography>
      <FormGroup>
        <FormControlLabel
          control={
            <Controller
              name="updateWallet"
              control={control}
              render={({ field: { onChange, value, name } }) => (
                <Checkbox
                  name={name}
                  checked={value}
                  onChange={onChange}
                  inputProps={{ "aria-label": "controlled" }}
                />
              )}
            />
          }
          label={t("update_wallet")}
        />
        <FormControlLabel
          control={
            <Controller
              name="recurring"
              control={control}
              render={({ field: { onChange, value, name } }) => (
                <Checkbox
                  name={name}
                  checked={value}
                  onChange={onChange}
                  inputProps={{ "aria-label": "controlled" }}
                />
              )}
            />
          }
          label={t("recurring_transaction")}
        />
      </FormGroup>

      {isRecurring && (
        <Box sx={{ display: "flex", gap: 2, alignItems: "center", mt: -1 }}>
          <Typography variant="body2" color="text.secondary">
            {t("every")}:
          </Typography>
          <Controller
            name="amount"
            control={control}
            render={({ field: { onChange, value } }) => (
              <TextField
                type="number"
                size="small"
                sx={{ width: 90 }}
                value={value ?? 1}
                onChange={(e) =>
                  onChange(Math.max(1, parseInt(e.target.value) || 1))
                }
                inputProps={{ min: 1 }}
              />
            )}
          />
          <Controller
            name="duration"
            control={control}
            render={({ field: { onChange, value } }) => (
              <TextField
                select
                size="small"
                sx={{ width: 140 }}
                value={value ?? "MONTHS"}
                onChange={onChange}
              >
                <MenuItem value="DAYS">{t("days")}</MenuItem>
                <MenuItem value="WEEKS">{t("weeks")}</MenuItem>
                <MenuItem value="MONTHS">{t("months")}</MenuItem>
                <MenuItem value="YEARS">{t("years")}</MenuItem>
              </TextField>
            )}
          />
        </Box>
      )}

      <Button
        type="submit"
        variant="contained"
        disabled={isSubmitting || isPending}
        startIcon={isSubmitting || isPending ? <CircularProgress size={16} color="inherit" /> : null}
      >
        {isSubmitting || isPending ? t("loading") : t("add")}
      </Button>
    </form>
  );
}

export default NewTransactionForm;
