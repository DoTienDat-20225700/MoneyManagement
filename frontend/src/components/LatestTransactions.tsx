import { WarningAmberRounded, EditOutlined, RepeatRounded, Close as CloseIcon } from "@mui/icons-material";
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  FormLabel,
  IconButton,
  InputAdornment,
  InputLabel,
  MenuItem,
  Radio,
  RadioGroup,
  Select,
  TextField,
  Tooltip,
} from "@mui/material";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { grey } from "@mui/material/colors";
import {
  DataGrid,
  GridActionsCellItem,
  GridColDef,
  GridDeleteIcon,
  GridRowId,
  GridRowsProp,
  GridValueFormatterParams,
  viVN,
  enUS,
} from "@mui/x-data-grid";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSnackbar } from "notistack";
import { useState } from "react";
import { useTransactions } from "../hooks/api/useTransactions";
import { useLabels } from "../hooks/api/useLabels";
import {
  Transaction,
  typeOptionColor,
  typeOptionMask,
} from "../models/Transaction";
import { TypeOption } from "../enums/Enums";
import dayjs from "dayjs";
import { formatCurrency, formatValue } from "../utils/utils";
import { useLanguage } from "../context/LanguageContext";

const DASHBOARD_MAX_ROWS = 3;

interface Props {
  data: Transaction[] | null;
  headOnly: boolean;
  limit?: number;
  hideActions?: boolean;
  defaultPageSize?: number;
}

function LatestTransactions(props: Props) {
  const { language, dateFormat, t } = useLanguage();
  const queryClient = useQueryClient();
  const { deleteTransaction, updateTransaction } = useTransactions();
  const { getLabels } = useLabels();
  const { data: labels } = useQuery({
    queryKey: ["labels"],
    queryFn: getLabels,
  });
  const { enqueueSnackbar } = useSnackbar();

  // State for edit transaction dialog
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editItem, setEditItem] = useState<{
    id: number;
    title: string;
    value: number | string;
    type: string;
    date: string;
    labelId: number | string;
  } | null>(null);

  const deleteMutation = useMutation({
    mutationFn: deleteTransaction,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["wallet"] });
      queryClient.invalidateQueries({ queryKey: ["budgets"] });
      queryClient.invalidateQueries({ queryKey: ["budget_summary"] });
      queryClient.invalidateQueries({ queryKey: ["report_summary"] });
      queryClient.invalidateQueries({ queryKey: ["report_transactions"] });
      enqueueSnackbar(t("transaction_deleted"), {
        variant: "success",
        autoHideDuration: 3000,
        anchorOrigin: { horizontal: "right", vertical: "bottom" },
      });
    },
    onError: () => {
      enqueueSnackbar(t("err_transaction_delete"), {
        variant: "error",
        autoHideDuration: 3000,
        anchorOrigin: { horizontal: "right", vertical: "bottom" },
      });
    },
  });

  const updateMutation = useMutation({
    mutationFn: updateTransaction,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transactions"] });
      queryClient.invalidateQueries({ queryKey: ["wallet"] });
      queryClient.invalidateQueries({ queryKey: ["budgets"] });
      queryClient.invalidateQueries({ queryKey: ["budget_summary"] });
      queryClient.invalidateQueries({ queryKey: ["report_summary"] });
      queryClient.invalidateQueries({ queryKey: ["report_transactions"] });
      enqueueSnackbar(t("transaction_updated"), {
        variant: "success",
        autoHideDuration: 3000,
        anchorOrigin: { horizontal: "right", vertical: "bottom" },
      });
      setEditDialogOpen(false);
    },
    onError: () => {
      enqueueSnackbar(t("err_transaction_update"), {
        variant: "error",
        autoHideDuration: 3000,
        anchorOrigin: { horizontal: "right", vertical: "bottom" },
      });
    },
  });

  function handleOpenEdit(id: GridRowId) {
    const item = props.data?.find((t) => t.id === Number(id));
    if (item) {
      const numVal =
        typeof item.value === "string"
          ? parseFloat(item.value)
          : Number(item.value);
      const cleanInt = isNaN(numVal) ? 0 : Math.round(numVal);
      setEditItem({
        id: item.id,
        title: item.title,
        value: formatCurrency(cleanInt),
        type: item.type || TypeOption.EXPENSE,
        date: dayjs(item.date).format("YYYY-MM-DD"),
        labelId: item.label?.id ?? "",
      });
      setEditDialogOpen(true);
    }
  }

  function handleSaveEdit() {
    if (!editItem) return;
    const cleanNum =
      typeof editItem.value === "string"
        ? Number(editItem.value.replace(/\D/g, ""))
        : Number(editItem.value);
    updateMutation.mutate({
      transactionId: editItem.id,
      transaction: {
        title: editItem.title,
        value: cleanNum,
        type: editItem.type,
        date: editItem.date,
        label_id:
          editItem.labelId !== "" &&
          editItem.labelId !== undefined &&
          editItem.labelId !== null
            ? Number(editItem.labelId)
            : null,
      },
    });
  }

  const columns: GridColDef[] = [
    {
      field: "title",
      headerName: t("col_name"),
      flex: 1.5,
      minWidth: 180,
    },
    {
      field: "label",
      headerName: t("col_label"),
      flex: 1,
      minWidth: 140,
      renderCell: (params) => {
        if (params.value && params.value.name) {
          return (
            <Chip
              label={params.value.name}
              variant="outlined"
              size="small"
              style={{ borderColor: params.value.color }}
            />
          );
        }
        return (
          <Chip
            label={t("uncategorized")}
            variant="outlined"
            size="small"
            sx={{
              color: grey[500],
              borderColor: grey[800],
              borderStyle: "dashed",
            }}
          />
        );
      },
    },
    {
      field: "type",
      headerName: t("col_type"),
      width: 130,
      renderCell: (params) => {
        const { bgColor, color } = typeOptionColor(params.value);
        return (
          params.value && (
            <Chip
              label={typeOptionMask(params.value, language)}
              size="small"
              style={{ color, backgroundColor: bgColor }}
            />
          )
        );
      },
    },
    {
      field: "value",
      headerName: t("col_value"),
      width: 140,
      valueFormatter: (params: GridValueFormatterParams) => {
        return formatValue(params.value);
      },
    },
    {
      field: "date",
      headerName: t("col_date"),
      width: 120,
    },
    ...(!props.hideActions
      ? [
          {
            field: "actions",
            type: "actions" as const,
            headerName: t("col_actions"),
            width: 100,
            cellClassName: "actions",
            getActions: ({ id }: { id: GridRowId }) => {
              return [
                <GridActionsCellItem
                  icon={<EditOutlined sx={{ fontSize: 19 }} />}
                  label={t("edit_transaction")}
                  onClick={() => handleOpenEdit(id)}
                  color="inherit"
                />,
                <GridActionsCellItem
                  icon={<GridDeleteIcon sx={{ fontSize: 19 }} />}
                  label={t("delete")}
                  onClick={() => deleteMutation.mutate({ transactionId: Number(id) })}
                  color="inherit"
                />,
              ];
            },
          },
        ]
      : []),
    {
      field: "imported",
      headerName: "",
      width: 45,
      renderCell: (params) => {
        return (
          params.value && (
            <Tooltip title={t("imported_tooltip")}>
              <WarningAmberRounded color="warning" sx={{ fontSize: 20 }} />
            </Tooltip>
          )
        );
      },
    },
    {
      field: "recurrent",
      headerName: "",
      width: 45,
      renderCell: (params) => {
        if (!params.value) return null;
        const dur = params.row.duration ? String(params.row.duration).toLowerCase() : "";
        const durMap: { [key: string]: string } = {
          days: language === "vi" ? "ngày" : "days",
          weeks: language === "vi" ? "tuần" : "weeks",
          months: language === "vi" ? "tháng" : "months",
          years: language === "vi" ? "năm" : "years",
        };
        const durLabel = durMap[dur] || dur;
        const info = params.row.amount ? `${params.row.amount} ${durLabel}` : "";
        return (
          <Tooltip title={`${t("recurring_transaction")}${info ? ` (${info})` : ""}`}>
            <RepeatRounded color="info" sx={{ fontSize: 20 }} />
          </Tooltip>
        );
      },
    },
  ];

  function transformData(data: Transaction[] | null): GridRowsProp | [] {
    return data
      ? data.map((item) => ({
          id: item.id,
          title: item.title,
          label: item.label || "",
          type: item.type,
          value: item.value,
          date: dayjs(item.date).format(dateFormat),
          imported: item.imported || false,
          recurrent: item.recurrent || false,
          amount: item.amount,
          duration: item.duration,
        }))
      : [];
  }

  return (
    <>
      <DataGrid
        rows={
          props.headOnly
            ? transformData(props.data).slice(0, props.limit ?? DASHBOARD_MAX_ROWS)
            : transformData(props.data)
        }
        columns={columns}
        hideFooter={props.headOnly}
        autoHeight
        disableRowSelectionOnClick
        initialState={{
          pagination: {
            paginationModel: { page: 0, pageSize: props.defaultPageSize ?? 25 },
          },
        }}
        pageSizeOptions={[10, 25, 50, 100]}
        localeText={
          language === "vi"
            ? viVN.components.MuiDataGrid.defaultProps.localeText
            : enUS.components.MuiDataGrid.defaultProps.localeText
        }
        sx={{
          "& .MuiDataGrid-row:hover": {
            backgroundColor: "rgba(255, 255, 255, 0.03)",
          },
          "& .MuiDataGrid-row.Mui-selected": {
            backgroundColor: "rgba(255, 255, 255, 0.05)",
          },
        }}
      />

      {/* Edit Transaction Dialog */}
      <Dialog
        open={editDialogOpen}
        onClose={() => setEditDialogOpen(false)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>{t("edit_transaction")}</span>
          <IconButton size="small" onClick={() => setEditDialogOpen(false)} sx={{ color: "text.secondary" }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </DialogTitle>
        <DialogContent
          sx={{ display: "flex", flexDirection: "column", gap: 2, pt: "16px !important" }}
        >
          <TextField
            label={t("col_name")}
            size="small"
            fullWidth
            value={editItem?.title || ""}
            onChange={(e) =>
              setEditItem((prev) =>
                prev ? { ...prev, title: e.target.value } : null
              )
            }
          />

          <FormControl size="small" fullWidth>
            <InputLabel id="edit-transaction-label-label">{t("col_label")}</InputLabel>
            <Select<number | string>
              labelId="edit-transaction-label-label"
              id="edit-transaction-label-select"
              label={t("col_label")}
              value={
                editItem?.labelId !== "" &&
                editItem?.labelId !== undefined &&
                editItem?.labelId !== null
                  ? Number(editItem.labelId)
                  : ""
              }
              onChange={(e) =>
                setEditItem((prev) =>
                  prev
                    ? {
                        ...prev,
                        labelId: e.target.value === "" ? "" : Number(e.target.value),
                      }
                    : null
                )
              }
            >
              <MenuItem value="">
                <em>{t("uncategorized")}</em>
              </MenuItem>
              {labels?.map((l) => (
                <MenuItem key={l.id} value={Number(l.id)}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <Box
                      sx={{
                        width: 12,
                        height: 12,
                        borderRadius: "50%",
                        backgroundColor: l.color,
                      }}
                    />
                    {l.name}
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Amount and Date in 2-column row matching NewTransactionForm */}
          <Box sx={{ display: "flex", flexDirection: "row", alignItems: "center", gap: 2 }}>
            <TextField
              label={t("col_value")}
              size="small"
              fullWidth
              value={editItem?.value ?? ""}
              onChange={(e) =>
                setEditItem((prev) =>
                  prev ? { ...prev, value: formatCurrency(e.target.value) } : null
                )
              }
              InputProps={{
                endAdornment: <InputAdornment position="end">đ</InputAdornment>,
              }}
            />

            <LocalizationProvider dateAdapter={AdapterDayjs}>
              <DatePicker
                label={t("col_date")}
                value={editItem?.date ? dayjs(editItem.date) : null}
                format={dateFormat}
                onChange={(val) =>
                  setEditItem((prev) =>
                    prev ? { ...prev, date: val ? val.format("YYYY-MM-DD") : "" } : null
                  )
                }
                slotProps={{ textField: { size: "small", fullWidth: true } }}
              />
            </LocalizationProvider>
          </Box>

          {/* Type radio group in dark pill boxes matching NewTransactionForm */}
          <FormControl>
            <FormLabel
              sx={{ mb: 1, "&.Mui-disabled": { color: "white" } }}
              disabled={true}
            >
              {t("col_type")}
            </FormLabel>
            <RadioGroup
              value={editItem?.type || TypeOption.EXPENSE}
              onChange={(e) =>
                setEditItem((prev) =>
                  prev ? { ...prev, type: e.target.value as TypeOption } : null
                )
              }
            >
              {Object.values(TypeOption).map((item, i) => (
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
              ))}
            </RadioGroup>
          </FormControl>

          <Button
            fullWidth
            variant="contained"
            onClick={handleSaveEdit}
            disabled={updateMutation.isPending}
            sx={{ height: 42, mt: 1, borderRadius: 2, fontWeight: 600 }}
          >
            {updateMutation.isPending ? (
              <CircularProgress size={20} color="inherit" />
            ) : (
              t("save_changes")
            )}
          </Button>
        </DialogContent>
      </Dialog>
    </>
  );
}

export default LatestTransactions;
