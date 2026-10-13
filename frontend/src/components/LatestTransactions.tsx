import { WarningAmberRounded, EditOutlined, RepeatRounded } from "@mui/icons-material";
import {
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  InputAdornment,
  InputLabel,
  MenuItem,
  Select,
  TextField,
  Tooltip,
} from "@mui/material";
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
    {
      field: "actions",
      type: "actions",
      headerName: t("col_actions"),
      width: 100,
      cellClassName: "actions",
      getActions: ({ id }) => {
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
        PaperProps={{
          style: { background: "#141414", borderRadius: 12 },
        }}
      >
        <DialogTitle>{t("edit_transaction")}</DialogTitle>
        <DialogContent
          sx={{ display: "flex", flexDirection: "column", gap: 2.5, pt: "20px !important" }}
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

          <FormControl size="small" fullWidth>
            <InputLabel id="edit-transaction-type-label">{t("col_type")}</InputLabel>
            <Select
              labelId="edit-transaction-type-label"
              id="edit-transaction-type-select"
              label={t("col_type")}
              value={editItem?.type || TypeOption.EXPENSE}
              onChange={(e) =>
                setEditItem((prev) =>
                  prev ? { ...prev, type: e.target.value as TypeOption } : null
                )
              }
            >
              <MenuItem value={TypeOption.EXPENSE}>
                {typeOptionMask(TypeOption.EXPENSE, language)}
              </MenuItem>
              <MenuItem value={TypeOption.EARNING}>
                {typeOptionMask(TypeOption.EARNING, language)}
              </MenuItem>
            </Select>
          </FormControl>

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

          <TextField
            label={t("col_date")}
            type="date"
            size="small"
            fullWidth
            InputLabelProps={{ shrink: true }}
            value={editItem?.date || ""}
            onChange={(e) =>
              setEditItem((prev) =>
                prev ? { ...prev, date: e.target.value } : null
              )
            }
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2 }}>
          <Button onClick={() => setEditDialogOpen(false)} color="inherit">
            {t("cancel")}
          </Button>
          <Button
            onClick={handleSaveEdit}
            variant="contained"
            disabled={updateMutation.isPending}
          >
            {t("save_changes")}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}

export default LatestTransactions;
