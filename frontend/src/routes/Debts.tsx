import { useState, useMemo } from "react";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  Dialog,
  DialogContent,
  DialogTitle,
  Drawer,
  FormControl,
  FormControlLabel,
  FormGroup,
  FormHelperText,
  Grid,
  IconButton,
  InputAdornment,
  LinearProgress,
  MenuItem,
  Select,
  Skeleton,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { grey } from "@mui/material/colors";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import CloseIcon from "@mui/icons-material/Close";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import PaymentIcon from "@mui/icons-material/Payment";
import PhoneIcon from "@mui/icons-material/Phone";
import HandshakeIcon from "@mui/icons-material/Handshake";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import dayjs from "dayjs";
import { useSnackbar } from "notistack";
import { Controller, useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

import { useDebts } from "../hooks/api/useDebts";
import { useLanguage } from "../context/LanguageContext";
import { DebtLoan, DebtType } from "../models/Debt";
import {
  DebtContractData,
  DebtContractInput,
  debtContractSchema,
  DebtPaymentData,
  DebtPaymentInput,
  debtPaymentSchema,
} from "../schemas/debtSchema";
import { formatCurrency, formatValue } from "../utils/utils";
import { paletteTokens } from "../theme";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";

export default function Debts() {
  const { dateFormat, t } = useLanguage();
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();
  const {
    getDebts,
    getDebtSummary,
    createDebt,
    deleteDebt,
    createPayment,
    deletePayment,
  } = useDebts();

  // Active Tab: 0 = LOAN_GIVEN, 1 = DEBT_BORROWED, 2 = INSTALLMENT
  const [tabIndex, setTabIndex] = useState<number>(0);
  const currentTabType: DebtType = useMemo(() => {
    if (tabIndex === 0) return "LOAN_GIVEN";
    if (tabIndex === 1) return "DEBT_BORROWED";
    return "INSTALLMENT";
  }, [tabIndex]);

  // Query Debts list & Summary
  const {
    data: debts,
    isLoading: isDebtsLoading,
    isError: isDebtsError,
    refetch: refetchDebts,
  } = useQuery({
    queryKey: ["debts", currentTabType],
    queryFn: () => getDebts(currentTabType),
  });

  const {
    data: summary,
    isLoading: isSummaryLoading,
  } = useQuery({
    queryKey: ["debt_summary"],
    queryFn: getDebtSummary,
  });

  // Modal / Drawer states
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [paymentModalDebt, setPaymentModalDebt] = useState<DebtLoan | null>(null);
  const [detailDrawerDebt, setDetailDrawerDebt] = useState<DebtLoan | null>(null);
  const [deleteTargetDebt, setDeleteTargetDebt] = useState<DebtLoan | null>(null);
  const [deleteTargetPayment, setDeleteTargetPayment] = useState<{
    debtId: number;
    paymentId: number;
  } | null>(null);

  // Form for New Contract (React Hook Form + Zod)
  const {
    register: registerContract,
    handleSubmit: handleSubmitContract,
    control: controlContract,
    reset: resetContract,
    watch: watchContract,
    formState: { errors: contractErrors, isSubmitting: isContractSubmitting },
  } = useForm<DebtContractInput, any, DebtContractData>({
    resolver: zodResolver(debtContractSchema),
    defaultValues: {
      person_name: "",
      contact_info: "",
      type: currentTabType,
      principal_amount: "" as any,
      start_date: dayjs(),
      due_date: null,
      installment_months: null,
      update_wallet: false,
      description: "",
    },
  });

  const selectedContractType = watchContract("type");

  // Form for Payment (React Hook Form + Zod)
  const {
    register: registerPayment,
    handleSubmit: handleSubmitPayment,
    control: controlPayment,
    reset: resetPayment,
    formState: { errors: paymentErrors, isSubmitting: isPaymentSubmitting },
  } = useForm<DebtPaymentInput, any, DebtPaymentData>({
    resolver: zodResolver(debtPaymentSchema),
    defaultValues: {
      amount: "" as any,
      date: dayjs(),
      update_wallet: true,
      note: "",
    },
  });

  // Query invalidation helper
  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ["debts"] });
    queryClient.invalidateQueries({ queryKey: ["debt_summary"] });
    queryClient.invalidateQueries({ queryKey: ["wallet"] });
  };

  // Create Contract Mutation
  const createDebtMutation = useMutation({
    mutationFn: (data: DebtContractData) =>
      createDebt({
        person_name: data.person_name,
        contact_info: data.contact_info,
        type: data.type,
        principal_amount: data.principal_amount,
        start_date: dayjs(data.start_date).format("YYYY-MM-DD"),
        due_date: data.due_date ? dayjs(data.due_date).format("YYYY-MM-DD") : null,
        installment_months: data.installment_months,
        update_wallet: data.update_wallet,
        description: data.description,
      }),
    onSuccess: () => {
      enqueueSnackbar(t("contract_created_success"), { variant: "success" });
      setCreateModalOpen(false);
      resetContract();
      invalidateAll();
    },
    onError: (err: any) => {
      const msg =
        err?.response?.data?.error ||
        err?.response?.data?.message ||
        t("err_debt_create");
      enqueueSnackbar(typeof msg === "object" ? JSON.stringify(msg) : String(msg), {
        variant: "error",
      });
    },
  });

  // Delete Contract Mutation
  const deleteDebtMutation = useMutation({
    mutationFn: (id: number) => deleteDebt(id),
    onSuccess: () => {
      enqueueSnackbar(t("contract_deleted_success"), { variant: "success" });
      setDeleteTargetDebt(null);
      if (detailDrawerDebt?.id === deleteTargetDebt?.id) {
        setDetailDrawerDebt(null);
      }
      invalidateAll();
    },
    onError: (err: any) => {
      enqueueSnackbar(err?.response?.data?.error || t("err_debt_delete"), {
        variant: "error",
      });
    },
  });

  // Record Payment Mutation
  const createPaymentMutation = useMutation({
    mutationFn: ({
      debtId,
      data,
    }: {
      debtId: number;
      data: DebtPaymentData;
    }) =>
      createPayment({
        debtId,
        data: {
          amount: data.amount,
          date: dayjs(data.date).format("YYYY-MM-DD"),
          update_wallet: data.update_wallet,
          note: data.note,
        },
      }),
    onSuccess: (_, vars) => {
      enqueueSnackbar(t("payment_recorded_success"), { variant: "success" });
      setPaymentModalDebt(null);
      resetPayment();
      invalidateAll();
      if (detailDrawerDebt && detailDrawerDebt.id === vars.debtId) {
        queryClient
          .fetchQuery({
            queryKey: ["debts", currentTabType],
            queryFn: () => getDebts(currentTabType),
          })
          .then((updatedList) => {
            const fresh = updatedList.find((d) => d.id === vars.debtId);
            if (fresh) setDetailDrawerDebt(fresh);
          });
      }
    },
    onError: (err: any) => {
      const msg =
        err?.response?.data?.error ||
        err?.response?.data?.amount ||
        t("err_payment_record");
      enqueueSnackbar(typeof msg === "object" ? JSON.stringify(msg) : String(msg), {
        variant: "error",
      });
    },
  });

  // Delete Payment Mutation
  const deletePaymentMutation = useMutation({
    mutationFn: ({
      debtId,
      paymentId,
    }: {
      debtId: number;
      paymentId: number;
    }) => deletePayment({ debtId, paymentId }),
    onSuccess: (_, vars) => {
      enqueueSnackbar(t("payment_deleted_success"), { variant: "success" });
      setDeleteTargetPayment(null);
      invalidateAll();
      if (detailDrawerDebt && detailDrawerDebt.id === vars.debtId) {
        queryClient
          .fetchQuery({
            queryKey: ["debts", currentTabType],
            queryFn: () => getDebts(currentTabType),
          })
          .then((updatedList) => {
            const fresh = updatedList.find((d) => d.id === vars.debtId);
            if (fresh) setDetailDrawerDebt(fresh);
          });
      }
    },
    onError: (err: any) => {
      enqueueSnackbar(err?.response?.data?.error || t("err_payment_delete"), {
        variant: "error",
      });
    },
  });

  // Handlers for Opening Modals
  const handleOpenCreateModal = () => {
    resetContract({
      person_name: "",
      contact_info: "",
      type: currentTabType,
      principal_amount: "" as any,
      start_date: dayjs(),
      due_date: null,
      installment_months: currentTabType === "INSTALLMENT" ? 12 : null,
      update_wallet: false,
      description: "",
    });
    setCreateModalOpen(true);
  };

  const handleOpenPaymentDialog = (debt: DebtLoan) => {
    setPaymentModalDebt(debt);
    const rem = parseFloat(debt.remaining_amount);
    let defaultAmt = rem;
    if (debt.type === "INSTALLMENT" && debt.installment_schedule && debt.installment_schedule.length > 0) {
      const nextUnpaid = debt.installment_schedule.find((s) => !s.is_paid);
      if (nextUnpaid) {
        const nextNeeded = parseFloat(nextUnpaid.amount) - parseFloat(nextUnpaid.paid_amount);
        defaultAmt = Math.min(rem, Math.max(0, nextNeeded));
      }
    }
    resetPayment({
      amount: defaultAmt > 0 ? defaultAmt : ("" as any),
      date: dayjs(),
      update_wallet: true,
      note: "",
    });
  };

  // Status Chip Rendering matching Budgets.tsx palette
  const renderStatusChip = (status: string, overdueDays: number) => {
    if (status === "OVERDUE" || overdueDays > 0) {
      return (
        <Chip
          size="small"
          icon={<ErrorOutlineIcon sx={{ fontSize: "12px !important", color: `${paletteTokens.error} !important` }} />}
          label={
            overdueDays > 0
              ? t("overdue_days_badge").replace("{days}", String(overdueDays))
              : t("status_overdue")
          }
          sx={{
            backgroundColor: paletteTokens.tint.error12,
            color: paletteTokens.error,
            fontWeight: 700,
            fontSize: "12px",
            border: "none",
          }}
        />
      );
    }
    if (status === "PARTIALLY_PAID") {
      return (
        <Chip
          size="small"
          icon={<WarningAmberIcon sx={{ fontSize: "12px !important", color: `${paletteTokens.warning} !important` }} />}
          label={t("status_partially_paid")}
          sx={{
            backgroundColor: paletteTokens.tint.warning12,
            color: paletteTokens.warning,
            fontWeight: 700,
            fontSize: "12px",
            border: "none",
          }}
        />
      );
    }
    if (status === "FULLY_PAID") {
      return (
        <Chip
          size="small"
          label={t("status_fully_paid")}
          sx={{
            backgroundColor: paletteTokens.elevated,
            color: paletteTokens.textSecondary,
            border: `1px solid ${paletteTokens.divider}`,
            fontWeight: 600,
            fontSize: "12px",
          }}
        />
      );
    }
    if (status === "CLOSED") {
      return (
        <Chip
          size="small"
          label={t("status_closed")}
          sx={{
            backgroundColor: paletteTokens.elevated,
            color: paletteTokens.textSecondary,
            border: `1px solid ${paletteTokens.divider}`,
            fontWeight: 600,
            fontSize: "12px",
          }}
        />
      );
    }
    return (
      <Chip
        size="small"
        label={t("status_active")}
        sx={{
          backgroundColor: paletteTokens.elevated,
          color: paletteTokens.textSecondary,
          border: `1px solid ${paletteTokens.divider}`,
          fontWeight: 600,
          fontSize: "12px",
        }}
      />
    );
  };

  // Progress Bar Color Helper
  const getProgressColor = (status: string, overdueDays: number) => {
    if (status === "OVERDUE" || overdueDays > 0) return paletteTokens.error;
    if (status === "PARTIALLY_PAID") return paletteTokens.warning;
    return paletteTokens.primary;
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDayjs}>
      <Box>
      {/* 1. Header matching Budgets.tsx and Home.tsx */}
      <Box
        sx={{
          display: "flex",
          flexDirection: {
            xs: "column",
            md: "row",
          },
          justifyContent: "space-between",
          alignItems: {
            xs: "start",
            md: "center",
          },
        }}
      >
        <Typography component="h1" variant="h4" fontWeight={600}>
          {t("debts_title")}
        </Typography>
        <Box sx={{ marginTop: { xs: 2, md: 0 } }}>
          <Button
            variant="contained"
            size="medium"
            startIcon={<AddIcon />}
            onClick={handleOpenCreateModal}
          >
            {t("new_debt_contract")}
          </Button>
        </Box>
      </Box>

      {/* 2. KPI Summary Cards matching Budgets.tsx and WalletGridRow.tsx */}
      <Grid mt={1} container spacing={2} alignItems={"stretch"}>
        {/* 1. Tổng người khác nợ bạn */}
        <Grid item xs={12} sm={6} lg={3}>
          <Box
            border="1px solid"
            borderColor={paletteTokens.divider}
            borderRadius={2}
            padding={3}
            height={"100%"}
          >
            <Typography component="h2" variant="body1" mb={1}>
              {t("total_loans_given")}
            </Typography>
            <Box display="flex" alignItems="center" gap={2}>
              {isSummaryLoading ? (
                <Skeleton variant="rectangular" width={140} height={32} />
              ) : (
                <Typography
                  component="span"
                  variant="h5"
                  fontWeight={600}
                  sx={{ color: paletteTokens.primary }}
                >
                  {formatValue(summary?.total_loan_given_remaining ?? 0)}
                </Typography>
              )}
            </Box>
            <Typography component="p" variant="caption" color="text.secondary" sx={{ mt: 1 }}>
              {t("tab_loans_given")}
            </Typography>
          </Box>
        </Grid>

        {/* 2. Tổng bạn đang nợ */}
        <Grid item xs={12} sm={6} lg={3}>
          <Box
            border="1px solid"
            borderColor={paletteTokens.divider}
            borderRadius={2}
            padding={3}
            height={"100%"}
          >
            <Typography component="h2" variant="body1" mb={1}>
              {t("total_debts_borrowed")}
            </Typography>
            <Box display="flex" alignItems="center" gap={2}>
              {isSummaryLoading ? (
                <Skeleton variant="rectangular" width={140} height={32} />
              ) : (
                <Typography
                  component="span"
                  variant="h5"
                  fontWeight={600}
                  sx={{ color: "text.primary" }}
                >
                  {formatValue(summary?.total_debt_borrowed_remaining ?? 0)}
                </Typography>
              )}
            </Box>
            <Typography component="p" variant="caption" color="text.secondary" sx={{ mt: 1 }}>
              {t("tab_debts_borrowed")} + {t("tab_installments")}
            </Typography>
          </Box>
        </Grid>

        {/* 3. Đến hạn trong 7 ngày */}
        <Grid item xs={12} sm={6} lg={3}>
          <Box
            border="1px solid"
            borderColor={paletteTokens.divider}
            borderRadius={2}
            padding={3}
            height={"100%"}
          >
            <Typography component="h2" variant="body1" mb={1}>
              {t("due_in_7_days")}
            </Typography>
            <Box display="flex" alignItems="center" gap={2}>
              {isSummaryLoading ? (
                <Skeleton variant="rectangular" width={80} height={32} />
              ) : (
                <Typography component="span" variant="h5" fontWeight={600}>
                  {summary?.due_in_7_days_count ?? 0}
                </Typography>
              )}
            </Box>
            <Typography component="p" variant="caption" color="text.secondary" sx={{ mt: 1 }}>
              {t("due_in_7_days")}
            </Typography>
          </Box>
        </Grid>

        {/* 4. Khoản quá hạn */}
        <Grid item xs={12} sm={6} lg={3}>
          <Box
            border="1px solid"
            borderColor={paletteTokens.divider}
            borderRadius={2}
            padding={3}
            height={"100%"}
          >
            <Typography component="h2" variant="body1" mb={1}>
              {t("overdue_count")}
            </Typography>
            <Box display="flex" alignItems="center" gap={2}>
              {isSummaryLoading ? (
                <Skeleton variant="rectangular" width={80} height={32} />
              ) : (
                <Typography
                  component="span"
                  variant="h5"
                  fontWeight={600}
                  sx={{ color: (summary?.overdue_count ?? 0) > 0 ? paletteTokens.error : "text.primary" }}
                >
                  {summary?.overdue_count ?? 0}
                </Typography>
              )}
            </Box>
            <Typography component="p" variant="caption" color="text.secondary" sx={{ mt: 1 }}>
              {t("status_overdue")}
            </Typography>
          </Box>
        </Grid>
      </Grid>

      {/* Overdue alert banner if any exist */}
      {(summary?.overdue_count ?? 0) > 0 && (
        <Alert severity="error" role="alert" sx={{ mt: 2, backgroundColor: paletteTokens.tint.error12, color: paletteTokens.error, border: `1px solid ${paletteTokens.error}`, "& .MuiAlert-icon": { color: paletteTokens.error } }}>
          <strong>{summary?.overdue_count} {t("status_overdue").toLowerCase()}</strong>
        </Alert>
      )}

      {/* 3. Filter Tabs Bar */}
      <Box sx={{ borderBottom: 1, borderColor: paletteTokens.divider, mt: 3, mb: 3 }}>
        <Tabs
          value={tabIndex}
          onChange={(_, val) => setTabIndex(val)}
          textColor="inherit"
          variant="scrollable"
          scrollButtons="auto"
          sx={{
            "& .MuiTabs-indicator": {
              backgroundColor: paletteTokens.primary,
              height: 3,
              borderRadius: "3px 3px 0 0",
            },
            "& .MuiTab-root": {
              textTransform: "none",
              fontWeight: 600,
              fontSize: "14px",
              color: "text.secondary",
              minHeight: 48,
              "&.Mui-selected": {
                color: "#fff",
              },
            },
          }}
        >
          <Tab label={t("tab_loans_given")} />
          <Tab label={t("tab_debts_borrowed")} />
          <Tab label={t("tab_installments")} />
        </Tabs>
      </Box>

      {/* 4. Contracts Grid & States */}
      <Box height={"auto"} mb={4}>
        {isDebtsLoading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
            <CircularProgress color="primary" />
          </Box>
        ) : isDebtsError ? (
          <Alert
            severity="error"
            action={
              <Button color="inherit" size="small" onClick={() => refetchDebts()}>
                {t("retry")}
              </Button>
            }
          >
            {t("unable_to_load_data")}
          </Alert>
        ) : debts && debts.length > 0 ? (
          <Grid container spacing={2}>
            {debts.map((debt) => {
              const isOverdue = debt.status === "OVERDUE" || debt.overdue_days > 0;
              const isFullyPaid = debt.status === "FULLY_PAID";
              const progressColor = getProgressColor(debt.status, debt.overdue_days);

              return (
                <Grid item xs={12} sm={6} lg={4} key={debt.id}>
                  <Box
                    border="1px solid"
                    borderColor={paletteTokens.divider}
                    borderRadius={2}
                    padding={3}
                    height="100%"
                    display="flex"
                    flexDirection="column"
                    justifyContent="space-between"
                    sx={{ backgroundColor: paletteTokens.bgPaper }}
                  >
                    <Box>
                      {/* Header: Person Name + Status Chip + Delete Action */}
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "flex-start",
                          justifyContent: "space-between",
                          mb: 2,
                        }}
                      >
                        <Box sx={{ pr: 1, minWidth: 0 }}>
                          <Typography variant="body1" fontWeight={700} noWrap>
                            {debt.person_name}
                          </Typography>
                          {debt.contact_info && (
                            <Box sx={{ display: "flex", alignItems: "center", gap: 0.5, mt: 0.5 }}>
                              <PhoneIcon sx={{ fontSize: 13, color: "text.secondary" }} />
                              <Typography variant="caption" color="text.secondary" noWrap>
                                {debt.contact_info}
                              </Typography>
                            </Box>
                          )}
                        </Box>
                        <Box display="flex" alignItems="center" gap={0.5} flexShrink={0}>
                          {renderStatusChip(debt.status, debt.overdue_days)}
                          <Tooltip title={t("delete")}>
                            <IconButton
                              size="small"
                              onClick={() => setDeleteTargetDebt(debt)}
                              aria-label={`${t("delete")}: ${debt.person_name}`}
                              sx={{ color: grey[500], "&:hover": { color: paletteTokens.error } }}
                            >
                              <DeleteOutlineIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </Box>

                      {/* Progress Bar matching Budgets.tsx */}
                      <Box sx={{ mb: 2 }}>
                        <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.8 }}>
                          <Typography variant="caption" color="text.secondary">
                            {t("payment_progress")}
                          </Typography>
                          <Typography
                            variant="caption"
                            fontWeight={700}
                            sx={{ color: progressColor }}
                          >
                            {debt.progress_percentage.toFixed(1)}%
                          </Typography>
                        </Box>
                        <LinearProgress
                          variant="determinate"
                          value={Math.min(100, Math.max(0, debt.progress_percentage))}
                          aria-label={`${t("debt_progress")}: ${debt.person_name}`}
                          aria-valuenow={Math.round(debt.progress_percentage)}
                          sx={{
                            height: 8,
                            borderRadius: 4,
                            backgroundColor: paletteTokens.divider,
                            "& .MuiLinearProgress-bar": {
                              backgroundColor: progressColor,
                              borderRadius: 4,
                            },
                          }}
                        />
                      </Box>

                      {/* Financial Figures: Gốc, Đã trả, Còn lại */}
                      <Grid container spacing={1} sx={{ mb: 1.5 }}>
                        <Grid item xs={4}>
                          <Typography variant="caption" color="text.secondary" display="block">
                            {t("principal_amount")}
                          </Typography>
                          <Typography variant="body2" fontWeight={600}>
                            {formatValue(debt.principal_amount)}
                          </Typography>
                        </Grid>
                        <Grid item xs={4}>
                          <Typography variant="caption" color="text.secondary" display="block">
                            {t("total_paid")}
                          </Typography>
                          <Typography variant="body2" fontWeight={600} sx={{ color: paletteTokens.primary }}>
                            {formatValue(debt.total_paid)}
                          </Typography>
                        </Grid>
                        <Grid item xs={4}>
                          <Typography variant="caption" color="text.secondary" display="block">
                            {t("remaining_debt_amount")}
                          </Typography>
                          <Typography
                            variant="body2"
                            fontWeight={600}
                            sx={{
                              color: isOverdue
                                ? paletteTokens.error
                                : "text.primary",
                            }}
                          >
                            {formatValue(debt.remaining_amount)}
                          </Typography>
                        </Grid>
                      </Grid>

                      {/* Dates */}
                      <Box sx={{ display: "flex", justifyContent: "space-between", mt: 1, mb: 1 }}>
                        <Typography variant="caption" color="text.secondary">
                          {t("start_date_debt")}:{" "}
                          {debt.start_date ? dayjs(debt.start_date).format(dateFormat) : "—"}
                        </Typography>
                        <Typography
                          variant="caption"
                          sx={{
                            color: isOverdue ? paletteTokens.error : "text.secondary",
                            fontWeight: isOverdue ? 700 : 400,
                          }}
                        >
                          {t("due_date")}:{" "}
                          {debt.due_date ? dayjs(debt.due_date).format(dateFormat) : "—"}
                        </Typography>
                      </Box>

                      {/* Installment note if applicable */}
                      {debt.type === "INSTALLMENT" && debt.installment_months && (
                        <Box
                          sx={{
                            mt: 1,
                            p: 1,
                            borderRadius: 1,
                            backgroundColor: paletteTokens.elevated,
                            border: `1px solid ${paletteTokens.divider}`,
                            display: "flex",
                            justifyContent: "space-between",
                          }}
                        >
                          <Typography variant="caption" color="text.secondary">
                            {t("installment_months")}: <strong>{debt.installment_months} {t("months_unit")}</strong>
                          </Typography>
                          <Typography variant="caption" sx={{ fontWeight: 600, color: "text.primary" }}>
                            ~{formatValue(Math.round(parseFloat(debt.principal_amount) / debt.installment_months))}/{t("months_unit")}
                          </Typography>
                        </Box>
                      )}

                      {/* Overdue alert footnote */}
                      {isOverdue && (
                        <Box
                          sx={{
                            mt: 1.5,
                            p: 0.8,
                            px: 1.2,
                            borderRadius: 1,
                            backgroundColor: paletteTokens.tint.error12,
                            display: "flex",
                            alignItems: "center",
                            gap: 0.8,
                          }}
                        >
                          <WarningAmberIcon sx={{ fontSize: 14, color: paletteTokens.error }} />
                          <Typography variant="caption" sx={{ color: paletteTokens.error, fontWeight: 600 }}>
                            {t("overdue_days_badge").replace("{days}", String(debt.overdue_days))}
                          </Typography>
                        </Box>
                      )}

                      {/* Description */}
                      {debt.description && (
                        <Typography
                          variant="caption"
                          color="text.secondary"
                          sx={{
                            mt: 1.5,
                            display: "-webkit-box",
                            WebkitLineClamp: 2,
                            WebkitBoxOrient: "vertical",
                            overflow: "hidden",
                          }}
                        >
                          {debt.description}
                        </Typography>
                      )}
                    </Box>

                    {/* Bottom Action Bar */}
                    <Box
                      sx={{
                        pt: 2,
                        mt: 1,
                        borderTop: `1px solid ${paletteTokens.divider}`,
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        gap: 1,
                      }}
                    >
                      <Button
                        size="small"
                        variant="outlined"
                        startIcon={<PaymentIcon fontSize="small" />}
                        disabled={isFullyPaid}
                        onClick={() => handleOpenPaymentDialog(debt)}
                        sx={{
                          fontSize: "12px",
                          height: 32,
                          px: 1.5,
                          borderColor: paletteTokens.controlBorder,
                          color: paletteTokens.textPrimary,
                          "&:hover": {
                            borderColor: paletteTokens.textSecondary,
                            backgroundColor: "rgba(255, 255, 255, 0.04)",
                          },
                        }}
                      >
                        {t("quick_payment")}
                      </Button>

                      <Button
                        size="small"
                        variant="text"
                        onClick={() => setDetailDrawerDebt(debt)}
                        sx={{
                          fontSize: "12px",
                          height: 32,
                          color: paletteTokens.primary,
                          fontWeight: 600,
                          "&:hover": { backgroundColor: paletteTokens.tint.primary12 },
                        }}
                      >
                        {t("view_details")}
                      </Button>
                    </Box>
                  </Box>
                </Grid>
              );
            })}
          </Grid>
        ) : (
          /* Empty State matching Budgets.tsx and SavingPlans.tsx */
          <Box
            sx={{
              py: 8,
              px: 3,
              textAlign: "center",
              borderRadius: 2,
              border: `1px dashed ${paletteTokens.divider}`,
            }}
          >
            <HandshakeIcon
              sx={{ fontSize: 48, color: "text.secondary", opacity: 0.5, mb: 1.5 }}
            />
            <Typography component="h2" variant="h6" fontWeight={600} mb={1}>
              {t("no_debts_in_tab")}
            </Typography>
            <Typography variant="body2" color="text.secondary" maxWidth={480} mx="auto" mb={2}>
              {t("debts_subtitle")}
            </Typography>
            <Button
              variant="contained"
              size="medium"
              startIcon={<AddIcon />}
              onClick={handleOpenCreateModal}
            >
              {t("new_debt_contract")}
            </Button>
          </Box>
        )}
      </Box>

      {/* 5. Create Contract Dialog */}
      <Dialog
        open={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>{t("new_debt_contract")}</span>
          <IconButton size="small" onClick={() => setCreateModalOpen(false)} aria-label={t("close")} sx={{ color: "text.secondary" }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: "16px !important" }}>
          <Box
            component="form"
            onSubmit={handleSubmitContract((data) => createDebtMutation.mutate(data))}
            sx={{ display: "flex", flexDirection: "column", gap: 2 }}
          >
            {/* Type Selection */}
            <FormControl fullWidth size="small">
              <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, fontWeight: 600 }}>
                {t("contract_type")}
              </Typography>
              <Controller
                name="type"
                control={controlContract}
                render={({ field }) => (
                  <Select {...field} size="small">
                    <MenuItem value="LOAN_GIVEN">{t("type_loan_given")}</MenuItem>
                    <MenuItem value="DEBT_BORROWED">{t("type_debt_borrowed")}</MenuItem>
                    <MenuItem value="INSTALLMENT">{t("type_installment")}</MenuItem>
                  </Select>
                )}
              />
            </FormControl>

            {/* Person Name */}
            <TextField
              {...registerContract("person_name")}
              label={t("person_name")}
              size="small"
              fullWidth
              error={!!contractErrors.person_name}
              helperText={contractErrors.person_name ? t("err_person_name_req") : ""}
            />

            {/* Contact Info */}
            <TextField
              {...registerContract("contact_info")}
              label={t("contact_info")}
              placeholder={t("contact_info_placeholder")}
              size="small"
              fullWidth
            />

            {/* Principal Amount */}
            <Controller
              name="principal_amount"
              control={controlContract}
              render={({ field: { onChange, value } }) => (
                <TextField
                  label={t("principal_amount")}
                  size="small"
                  fullWidth
                  value={value ? formatCurrency(value) : ""}
                  onChange={(e) => {
                    const raw = e.target.value.replace(/\D/g, "");
                    onChange(raw ? Number(raw) : "");
                  }}
                  InputProps={{
                    endAdornment: <InputAdornment position="end">đ</InputAdornment>,
                  }}
                  error={!!contractErrors.principal_amount}
                  helperText={contractErrors.principal_amount?.message}
                />
              )}
            />

            {/* Dates */}
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <Controller
                  name="start_date"
                  control={controlContract}
                  render={({ field: { onChange, value } }) => (
                    <DatePicker
                      label={t("start_date_debt")}
                      value={value}
                      format={dateFormat}
                      onChange={onChange}
                      slotProps={{
                        textField: {
                          size: "small",
                          fullWidth: true,
                          error: !!contractErrors.start_date,
                        },
                      }}
                    />
                  )}
                />
              </Grid>
              <Grid item xs={12} sm={6}>
                <Controller
                  name="due_date"
                  control={controlContract}
                  render={({ field: { onChange, value } }) => (
                    <DatePicker
                      label={t("due_date")}
                      value={value}
                      format={dateFormat}
                      onChange={onChange}
                      slotProps={{
                        textField: {
                          size: "small",
                          fullWidth: true,
                          error: !!contractErrors.due_date,
                        },
                      }}
                    />
                  )}
                />
              </Grid>
            </Grid>

            {/* Installment Months (only if INSTALLMENT) */}
            {selectedContractType === "INSTALLMENT" && (
              <TextField
                {...registerContract("installment_months")}
                label={t("installment_months_label")}
                type="number"
                size="small"
                fullWidth
                placeholder="12"
                error={!!contractErrors.installment_months}
                helperText={
                  contractErrors.installment_months ? t("err_installment_months_req") : ""
                }
              />
            )}

            {/* Update Wallet Option */}
            <FormGroup>
              <FormControlLabel
                control={
                  <Controller
                    name="update_wallet"
                    control={controlContract}
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
              <FormHelperText sx={{ ml: 4, mt: -0.5, color: "text.secondary" }}>
                {t("update_wallet_initial_loan_hint")}
              </FormHelperText>
            </FormGroup>

            {/* Description */}
            <TextField
              {...registerContract("description")}
              label={t("debt_description")}
              multiline
              rows={2}
              size="small"
              fullWidth
            />

            <Button
              type="submit"
              fullWidth
              variant="contained"
              disabled={isContractSubmitting || createDebtMutation.isPending}
              sx={{ height: 42, mt: 1, borderRadius: 2, fontWeight: 600 }}
            >
              {isContractSubmitting || createDebtMutation.isPending ? (
                <CircularProgress size={20} color="inherit" />
              ) : (
                t("save")
              )}
            </Button>
          </Box>
        </DialogContent>
      </Dialog>

      {/* 6. Quick Payment Dialog */}
      <Dialog
        open={!!paymentModalDebt}
        onClose={() => setPaymentModalDebt(null)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>{t("record_payment")}</span>
          <IconButton size="small" onClick={() => setPaymentModalDebt(null)} aria-label={t("close")} sx={{ color: "text.secondary" }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: "16px !important" }}>
          {paymentModalDebt && (
            <Box
              component="form"
              onSubmit={handleSubmitPayment((data) =>
                createPaymentMutation.mutate({ debtId: paymentModalDebt.id, data })
              )}
              sx={{ display: "flex", flexDirection: "column", gap: 2 }}
            >
              {/* Target info banner */}
              <Box
                sx={{
                  p: 1.5,
                  borderRadius: 1.5,
                  bgcolor: paletteTokens.bgPaper,
                  border: `1px solid ${paletteTokens.divider}`,
                }}
              >
                <Typography variant="caption" color="text.secondary" display="block">
                  {paymentModalDebt.person_name}
                </Typography>
                <Typography variant="body2" sx={{ fontWeight: 600, mt: 0.3 }}>
                  {t("remaining_debt_amount")}: {formatValue(paymentModalDebt.remaining_amount)}
                </Typography>
              </Box>

              {/* Amount */}
              <Controller
                name="amount"
                control={controlPayment}
                render={({ field: { onChange, value } }) => (
                  <TextField
                    label={t("payment_amount")}
                    size="small"
                    fullWidth
                    value={value ? formatCurrency(value) : ""}
                    onChange={(e) => {
                      const raw = e.target.value.replace(/\D/g, "");
                      onChange(raw ? Number(raw) : "");
                    }}
                    InputProps={{
                      endAdornment: <InputAdornment position="end">đ</InputAdornment>,
                    }}
                    error={!!paymentErrors.amount}
                    helperText={paymentErrors.amount?.message}
                  />
                )}
              />

              {/* Date */}
              <Controller
                name="date"
                control={controlPayment}
                render={({ field: { onChange, value } }) => (
                  <DatePicker
                    label={t("payment_date")}
                    value={value}
                    format={dateFormat}
                    onChange={onChange}
                    slotProps={{
                      textField: {
                        size: "small",
                        fullWidth: true,
                        error: !!paymentErrors.date,
                      },
                    }}
                  />
                )}
              />

              {/* Update Wallet */}
              <FormGroup>
                <FormControlLabel
                  control={
                    <Controller
                      name="update_wallet"
                      control={controlPayment}
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
                <FormHelperText sx={{ ml: 4, mt: -0.5, color: "text.secondary" }}>
                  {t("update_wallet_payment_hint")}
                </FormHelperText>
              </FormGroup>

              {/* Note */}
              <TextField
                {...registerPayment("note")}
                label={t("payment_note")}
                size="small"
                fullWidth
              />

              <Button
                type="submit"
                fullWidth
                variant="contained"
                disabled={isPaymentSubmitting || createPaymentMutation.isPending}
                sx={{ height: 42, mt: 1, borderRadius: 2, fontWeight: 600 }}
              >
                {isPaymentSubmitting || createPaymentMutation.isPending ? (
                  <CircularProgress size={20} color="inherit" />
                ) : (
                  t("save")
                )}
              </Button>
            </Box>
          )}
        </DialogContent>
      </Dialog>

      {/* 7. Contract Detail Drawer matching SavingPlans.tsx history */}
      <Drawer
        anchor="right"
        open={!!detailDrawerDebt}
        onClose={() => setDetailDrawerDebt(null)}
        PaperProps={{
          sx: {
            width: { xs: "100%", sm: 540 },
            backgroundColor: paletteTokens.elevated,
            backgroundImage: "none",
            borderLeft: `1px solid ${paletteTokens.divider}`,
            p: 3,
          },
        }}
      >
        {detailDrawerDebt && (
          <Box sx={{ display: "flex", flexDirection: "column", height: "100%" }}>
            {/* Header */}
            <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", mb: 2 }}>
              <Box>
                <Typography component="h2" variant="h6" sx={{ fontWeight: 700 }}>
                  {detailDrawerDebt.person_name}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {detailDrawerDebt.contact_info || t("contract_details")}
                </Typography>
              </Box>
              <IconButton onClick={() => setDetailDrawerDebt(null)} size="small" aria-label={t("close")} sx={{ color: "text.secondary" }}>
                <CloseIcon fontSize="small" />
              </IconButton>
            </Box>

            {/* Status & Contract Type */}
            <Box sx={{ mb: 2.5, display: "flex", alignItems: "center", gap: 1 }}>
              {renderStatusChip(detailDrawerDebt.status, detailDrawerDebt.overdue_days)}
              <Chip
                size="small"
                variant="outlined"
                label={
                  detailDrawerDebt.type === "LOAN_GIVEN"
                    ? t("tab_loans_given")
                    : detailDrawerDebt.type === "DEBT_BORROWED"
                    ? t("tab_debts_borrowed")
                    : t("tab_installments")
                }
                sx={{ borderColor: paletteTokens.divider }}
              />
            </Box>

            {/* Financial Summary Box */}
            <Box
              sx={{
                p: 2,
                borderRadius: 2,
                border: `1px solid ${paletteTokens.divider}`,
                bgcolor: paletteTokens.bgPaper,
                mb: 3,
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 2,
              }}
            >
              <Box>
                <Typography variant="caption" color="text.secondary">
                  {t("principal_amount")}
                </Typography>
                <Typography variant="body1" sx={{ fontWeight: 700 }}>
                  {formatValue(detailDrawerDebt.principal_amount)}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  {t("remaining_debt_amount")}
                </Typography>
                <Typography
                  variant="body1"
                  sx={{
                    fontWeight: 700,
                    color:
                      detailDrawerDebt.status === "OVERDUE"
                        ? "#ff8285"
                        : "text.primary",
                  }}
                >
                  {formatValue(detailDrawerDebt.remaining_amount)}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  {t("total_paid")}
                </Typography>
                <Typography variant="body2" sx={{ fontWeight: 600, color: paletteTokens.primary }}>
                  {formatValue(detailDrawerDebt.total_paid)}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  {t("payment_progress")}
                </Typography>
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  {detailDrawerDebt.progress_percentage.toFixed(1)}%
                </Typography>
              </Box>
            </Box>

            {/* Payment History Section */}
            <Box sx={{ mb: 3 }}>
              <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 1.5 }}>
                <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                  {t("payment_history")} ({detailDrawerDebt.payments?.length || 0})
                </Typography>
                {detailDrawerDebt.status !== "FULLY_PAID" && (
                  <Button
                    size="small"
                    variant="outlined"
                    startIcon={<AddIcon />}
                    onClick={() => handleOpenPaymentDialog(detailDrawerDebt)}
                    sx={{ fontSize: "12px", py: 0.3 }}
                  >
                    {t("record_payment")}
                  </Button>
                )}
              </Box>

              {!detailDrawerDebt.payments || detailDrawerDebt.payments.length === 0 ? (
                <Typography variant="caption" color="text.secondary">
                  {t("no_payments_recorded")}
                </Typography>
              ) : (
                <TableContainer
                  sx={{
                    border: `1px solid ${paletteTokens.divider}`,
                    borderRadius: 1.5,
                  }}
                >
                  <Table size="small">
                    <TableHead>
                      <TableRow>
                        <TableCell sx={{ color: grey[500], fontSize: "12px" }}>{t("col_date")}</TableCell>
                        <TableCell sx={{ color: grey[500], fontSize: "12px" }}>{t("col_value")}</TableCell>
                        <TableCell sx={{ color: grey[500], fontSize: "12px" }}>{t("col_wallet")}</TableCell>
                        <TableCell sx={{ color: grey[500], fontSize: "12px" }}>{t("payment_note")}</TableCell>
                        <TableCell align="right" sx={{ color: grey[500], fontSize: "12px" }}></TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {detailDrawerDebt.payments.map((p) => (
                        <TableRow key={p.id} hover>
                          <TableCell sx={{ fontSize: "13px" }}>
                            {p.date ? dayjs(p.date).format(dateFormat) : "—"}
                          </TableCell>
                          <TableCell sx={{ fontSize: "13px", fontWeight: 600, color: paletteTokens.primary }}>
                            {formatValue(p.amount)}
                          </TableCell>
                          <TableCell sx={{ fontSize: "13px" }}>
                            {p.update_wallet ? (
                              <Chip
                                size="small"
                                label={t("col_wallet")}
                                sx={{
                                  height: 20,
                                  fontSize: 10,
                                  backgroundColor: paletteTokens.tint.primary12,
                                  color: paletteTokens.primary,
                                }}
                              />
                            ) : (
                              "—"
                            )}
                          </TableCell>
                          <TableCell sx={{ fontSize: "13px", color: "text.secondary" }}>
                            {p.note || "—"}
                          </TableCell>
                          <TableCell align="right">
                            <IconButton
                              size="small"
                              onClick={() =>
                                setDeleteTargetPayment({
                                  debtId: detailDrawerDebt.id,
                                  paymentId: p.id,
                                })
                              }
                              aria-label={`${t("delete")}: ${formatValue(Number(p.amount))}`}
                              sx={{ color: grey[500], "&:hover": { color: paletteTokens.error } }}
                            >
                              <DeleteOutlineIcon fontSize="small" />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </Box>

            {/* Installment Schedule Section (if type is INSTALLMENT) */}
            {detailDrawerDebt.type === "INSTALLMENT" &&
              detailDrawerDebt.installment_schedule &&
              detailDrawerDebt.installment_schedule.length > 0 && (
                <Box sx={{ mb: 2 }}>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 1.5 }}>
                    {t("installment_schedule")}
                  </Typography>
                  <TableContainer
                    sx={{
                      border: `1px solid ${paletteTokens.divider}`,
                      borderRadius: 1.5,
                      maxHeight: 280,
                    }}
                  >
                    <Table size="small" stickyHeader>
                      <TableHead>
                        <TableRow>
                          <TableCell sx={{ color: grey[500], fontSize: "12px", bgcolor: paletteTokens.elevated }}>
                            {t("period_no")}
                          </TableCell>
                          <TableCell sx={{ color: grey[500], fontSize: "12px", bgcolor: paletteTokens.elevated }}>
                            {t("due_date")}
                          </TableCell>
                          <TableCell sx={{ color: grey[500], fontSize: "12px", bgcolor: paletteTokens.elevated }}>
                            {t("period_amount")}
                          </TableCell>
                          <TableCell sx={{ color: grey[500], fontSize: "12px", bgcolor: paletteTokens.elevated }}>
                            {t("paid_period_amount")}
                          </TableCell>
                          <TableCell align="right" sx={{ color: grey[500], fontSize: "12px", bgcolor: paletteTokens.elevated }}>
                            {t("status_label")}
                          </TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {detailDrawerDebt.installment_schedule.map((item) => (
                          <TableRow key={item.installment_no} hover>
                            <TableCell sx={{ fontSize: "13px", fontWeight: 600 }}>
                              #{item.installment_no}
                            </TableCell>
                            <TableCell sx={{ fontSize: "13px" }}>
                              {item.due_date ? dayjs(item.due_date).format(dateFormat) : "—"}
                            </TableCell>
                            <TableCell sx={{ fontSize: "13px" }}>{formatValue(item.amount)}</TableCell>
                            <TableCell sx={{ fontSize: "13px", color: paletteTokens.primary }}>
                              {formatValue(item.paid_amount)}
                            </TableCell>
                            <TableCell align="right">
                              {item.is_paid ? (
                                <Chip
                                  size="small"
                                  label={t("paid_status")}
                                  sx={{
                                    height: 20,
                                    fontSize: 10,
                                    backgroundColor: paletteTokens.tint.primary12,
                                    color: paletteTokens.primary,
                                  }}
                                />
                              ) : (
                                <Chip
                                  size="small"
                                  variant="outlined"
                                  label={t("unpaid_status")}
                                  sx={{
                                    height: 20,
                                    fontSize: 10,
                                    color: "text.secondary",
                                    borderColor: paletteTokens.divider,
                                  }}
                                />
                              )}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                </Box>
              )}
          </Box>
        )}
      </Drawer>

      {/* 8. Delete Contract Confirmation Dialog matching Budgets.tsx */}
      <Dialog
        open={!!deleteTargetDebt}
        onClose={() => setDeleteTargetDebt(null)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>{t("confirm_delete_debt_title")}</span>
          <IconButton size="small" onClick={() => setDeleteTargetDebt(null)} aria-label={t("close")} sx={{ color: "text.secondary" }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2.5, pt: "16px !important" }}>
          <Typography variant="body2" color="text.secondary">
            {t("confirm_delete_debt_msg")} (<strong>{deleteTargetDebt?.person_name}</strong> -{" "}
            {formatValue(deleteTargetDebt?.principal_amount)})
          </Typography>

          <Button
            fullWidth
            variant="contained"
            color="error"
            onClick={() => deleteTargetDebt && deleteDebtMutation.mutate(deleteTargetDebt.id)}
            disabled={deleteDebtMutation.isPending}
            sx={{ height: 42, borderRadius: 2, fontWeight: 600 }}
          >
            {deleteDebtMutation.isPending ? (
              <CircularProgress size={20} color="inherit" />
            ) : (
              t("delete_debt_action")
            )}
          </Button>
        </DialogContent>
      </Dialog>

      {/* 9. Delete Payment Confirmation Dialog matching Budgets.tsx */}
      <Dialog
        open={!!deleteTargetPayment}
        onClose={() => setDeleteTargetPayment(null)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>{t("confirm_delete_payment_title")}</span>
          <IconButton size="small" onClick={() => setDeleteTargetPayment(null)} aria-label={t("close")} sx={{ color: "text.secondary" }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2.5, pt: "16px !important" }}>
          <Typography variant="body2" color="text.secondary">
            {t("confirm_delete_payment_msg")}
          </Typography>

          <Button
            fullWidth
            variant="contained"
            color="error"
            onClick={() =>
              deleteTargetPayment && deletePaymentMutation.mutate(deleteTargetPayment)
            }
            disabled={deletePaymentMutation.isPending}
            sx={{ height: 42, borderRadius: 2, fontWeight: 600 }}
          >
            {deletePaymentMutation.isPending ? (
              <CircularProgress size={20} color="inherit" />
            ) : (
              t("delete_payment_action")
            )}
          </Button>
        </DialogContent>
      </Dialog>
    </Box>
  </LocalizationProvider>
);
}
