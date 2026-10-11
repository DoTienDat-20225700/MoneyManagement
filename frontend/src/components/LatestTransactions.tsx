import { WarningAmberRounded } from "@mui/icons-material";
import { Chip, Tooltip } from "@mui/material";
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
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useSnackbar } from "notistack";
import React from "react";
import { useTransactions } from "../hooks/api/useTransactions";
import { Transaction, typeOptionColor, typeOptionMask } from "../models/Transaction";
import dayjs from "dayjs";
import { formatValue } from "../utils/utils";
import { useLanguage } from "../context/LanguageContext";

const MAX_ROWS = 10;

interface Props {
  data: Transaction[] | null;
  headOnly: boolean;
}

function LatestTransactions(props: Props) {
  const { language, dateFormat, t } = useLanguage();
  const queryClient = useQueryClient();
  const { deleteTransaction } = useTransactions();
  const { enqueueSnackbar } = useSnackbar();

  const columns: GridColDef[] = [
    {
      field: "title",
      headerName: t("col_name"),
      width: 300,
    },
    {
      field: "label",
      headerName: t("col_label"),
      width: 300,
      renderCell: (params) => {
        return (
          params.value && (
            <Chip
              label={params.value.name}
              variant="outlined"
              style={{ borderColor: params.value.color }}
            />
          )
        );
      },
    },
    {
      field: "type",
      headerName: t("col_type"),
      width: 300,
      renderCell: (params) => {
        const { bgColor, color } = typeOptionColor(params.value);
        return (
          params.value && (
            <Chip
              label={typeOptionMask(params.value, language)}
              style={{ color, backgroundColor: bgColor }}
            />
          )
        );
      },
    },
    {
      field: "value",
      headerName: t("col_value"),
      width: 300,
      valueFormatter: (params: GridValueFormatterParams) => {
        return formatValue(params.value);
      },
    },
    {
      field: "date",
      headerName: t("col_date"),
      width: 200,
    },
    {
      field: "actions",
      type: "actions",
      headerName: t("col_actions"),
      width: 200,
      cellClassName: "actions",
      getActions: ({ id }) => {
        return [
          <GridActionsCellItem
            icon={<GridDeleteIcon />}
            label={t("delete")}
            onClick={() => handleDeleteTransaction(id)}
            color="inherit"
          />,
        ];
      },
    },
    {
      field: "imported",
      headerName: "",
      width: 100,
      renderCell: (params) => {
        return (
          params.value && (
            <Tooltip title={t("imported_tooltip")}>
              <WarningAmberRounded color="warning" />
            </Tooltip>
          )
        );
      },
    },
  ];

  const { mutateAsync } = useMutation({
    mutationFn: deleteTransaction,
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["transactions"],
      });
      queryClient.invalidateQueries({
        queryKey: ["wallet"],
      });
      enqueueSnackbar(t("transaction_deleted"), {
        variant: "success",
        autoHideDuration: 3000,
        anchorOrigin: { horizontal: "right", vertical: "bottom" },
      });
    },
    onError: (err: any) => {
      console.log(err);
      const errorMsg = !err?.response
        ? t("no_server_response")
        : t("err_transaction_delete");
      enqueueSnackbar(errorMsg, {
        variant: "error",
        autoHideDuration: 3000,
        anchorOrigin: { horizontal: "right", vertical: "bottom" },
      });
    },
  });

  const [rows, setRows] = React.useState(props.data);

  async function handleDeleteTransaction(id: GridRowId) {
    // TODO: Add are you sure alert
    await mutateAsync({
      transactionId: Number(id),
    });
    setRows(
      rows &&
        rows.filter((row) => {
          row.id !== id;
        })
    );
  }

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
        }))
      : [];
  }

  return (
    <>
      <DataGrid
        rows={
          props.headOnly
            ? transformData(props.data).slice(0, MAX_ROWS)
            : transformData(props.data)
        }
        columns={columns}
        hideFooter={props.headOnly}
        autoHeight
        localeText={
          language === "vi"
            ? viVN.components.MuiDataGrid.defaultProps.localeText
            : enUS.components.MuiDataGrid.defaultProps.localeText
        }
      />
    </>
  );
}

export default LatestTransactions;
