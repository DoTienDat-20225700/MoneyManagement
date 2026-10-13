import { useState, useMemo } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  Grid,
  IconButton,
  InputAdornment,
  InputLabel,
  LinearProgress,
  MenuItem,
  Select,
  Stack,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import AccountBalanceWalletOutlinedIcon from "@mui/icons-material/AccountBalanceWalletOutlined";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import TodayIcon from "@mui/icons-material/Today";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSnackbar } from "notistack";
import { useBudgets } from "../hooks/api/useBudgets";
import { useLabels } from "../hooks/api/useLabels";
import { CategoryBudget } from "../models/CategoryBudget";
import { CustomLabel } from "../models/CustomLabel";
import { useLanguage } from "../context/LanguageContext";
import { formatCurrency, formatValue } from "../utils/utils";
import { darkTheme } from "../theme";

export default function Budgets() {
  const { language, t } = useLanguage();
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();
  const {
    getBudgets,
    getBudgetSummary,
    createBudget,
    updateBudget,
    deleteBudget,
  } = useBudgets();
  const { getLabels } = useLabels();

  // Selected period state
  const currentDate = new Date();
  const [selectedMonth, setSelectedMonth] = useState<number>(currentDate.getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState<number>(currentDate.getFullYear());

  // Category labels for create/edit
  const { data: labels } = useQuery({
    queryKey: ["labels"],
    queryFn: getLabels,
  });

  // Budgets for selected month
  const {
    data: budgets,
    isLoading: isBudgetsLoading,
    isError: isBudgetsError,
    refetch: refetchBudgets,
  } = useQuery({
    queryKey: ["budgets", selectedMonth, selectedYear],
    queryFn: () => getBudgets(selectedMonth, selectedYear),
    staleTime: 0,
    refetchOnMount: "always",
  });

  // Summary statistics for selected month
  const { data: summary } = useQuery({
    queryKey: ["budget_summary", selectedMonth, selectedYear],
    queryFn: () => getBudgetSummary(selectedMonth, selectedYear),
    staleTime: 0,
    refetchOnMount: "always",
  });

  // Form modal states
  const [modalOpen, setModalOpen] = useState(false);
  const [editingBudget, setEditingBudget] = useState<CategoryBudget | null>(null);
  const [selectedLabelId, setSelectedLabelId] = useState<number | "">("");
  const [amountInput, setAmountInput] = useState("");
  const [formError, setFormError] = useState("");

  // Delete confirmation modal state
  const [deleteTarget, setDeleteTarget] = useState<CategoryBudget | null>(null);

  // Month navigation helpers
  const handlePrevMonth = () => {
    if (selectedMonth === 1) {
      setSelectedMonth(12);
      setSelectedYear((prev) => prev - 1);
    } else {
      setSelectedMonth((prev) => prev - 1);
    }
  };

  const handleNextMonth = () => {
    if (selectedMonth === 12) {
      setSelectedMonth(1);
      setSelectedYear((prev) => prev + 1);
    } else {
      setSelectedMonth((prev) => prev + 1);
    }
  };

  const handleCurrentMonth = () => {
    const now = new Date();
    setSelectedMonth(now.getMonth() + 1);
    setSelectedYear(now.getFullYear());
  };

  const isCurrentMonth =
    selectedMonth === currentDate.getMonth() + 1 &&
    selectedYear === currentDate.getFullYear();

  // Labels already budgeted in current month
  const budgetedLabelIds = useMemo(() => {
    return new Set(budgets?.map((b) => b.label.id) ?? []);
  }, [budgets]);

  // Mutations
  const createMutation = useMutation({
    mutationFn: createBudget,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["budgets"] });
      queryClient.invalidateQueries({ queryKey: ["budget_summary"] });
      enqueueSnackbar(t("budget_created"), { variant: "success" });
      handleCloseModal();
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.message || t("err_budget_create");
      enqueueSnackbar(msg, { variant: "error" });
    },
  });

  const updateMutation = useMutation({
    mutationFn: updateBudget,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["budgets"] });
      queryClient.invalidateQueries({ queryKey: ["budget_summary"] });
      enqueueSnackbar(t("budget_updated"), { variant: "success" });
      handleCloseModal();
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.message || t("err_budget_update");
      enqueueSnackbar(msg, { variant: "error" });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteBudget,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["budgets"] });
      queryClient.invalidateQueries({ queryKey: ["budget_summary"] });
      enqueueSnackbar(t("budget_deleted"), { variant: "success" });
      setDeleteTarget(null);
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.message || t("err_budget_delete");
      enqueueSnackbar(msg, { variant: "error" });
      setDeleteTarget(null);
    },
  });

  // Modal handlers
  const handleOpenCreate = () => {
    setEditingBudget(null);
    setSelectedLabelId("");
    setAmountInput("");
    setFormError("");
    setModalOpen(true);
  };

  const handleOpenEdit = (budget: CategoryBudget) => {
    setEditingBudget(budget);
    setSelectedLabelId(budget.label.id);
    const rawAmount = Math.round(Number(budget.amount));
    setAmountInput(formatCurrency(rawAmount));
    setFormError("");
    setModalOpen(true);
  };

  const handleCloseModal = () => {
    setModalOpen(false);
    setEditingBudget(null);
    setSelectedLabelId("");
    setAmountInput("");
    setFormError("");
  };

  const handleSave = () => {
    if (!editingBudget && !selectedLabelId) {
      setFormError(t("err_category_req"));
      return;
    }

    const cleanNum = Number(amountInput.replace(/\D/g, ""));
    if (!cleanNum || cleanNum <= 0) {
      setFormError(t("err_amount_positive"));
      return;
    }

    if (editingBudget) {
      updateMutation.mutate({
        id: editingBudget.id,
        data: {
          amount: cleanNum,
          month: selectedMonth,
          year: selectedYear,
        },
      });
    } else {
      if (budgetedLabelIds.has(Number(selectedLabelId))) {
        setFormError(t("budget_already_exists"));
        return;
      }

      createMutation.mutate({
        label: Number(selectedLabelId),
        amount: cleanNum,
        month: selectedMonth,
        year: selectedYear,
      });
    }
  };

  const handleDeleteConfirm = () => {
    if (deleteTarget) {
      deleteMutation.mutate(deleteTarget.id);
    }
  };

  // Status counters & alerts
  const approachingBudgets = budgets?.filter((b) => b.status === "approaching") ?? [];
  const exceededBudgets = budgets?.filter((b) => b.status === "exceeded") ?? [];

  // Helper for status chip
  const renderStatusChip = (status: "normal" | "approaching" | "exceeded") => {
    switch (status) {
      case "exceeded":
        return (
          <Chip
            size="small"
            icon={<ErrorOutlineIcon sx={{ fontSize: "14px !important", color: "#ff4d4f !important" }} />}
            label={t("status_exceeded")}
            sx={{
              backgroundColor: "rgba(255, 77, 79, 0.15)",
              color: "#ff4d4f",
              border: "1px solid rgba(255, 77, 79, 0.35)",
              fontWeight: 600,
              fontSize: "12px",
            }}
          />
        );
      case "approaching":
        return (
          <Chip
            size="small"
            icon={<WarningAmberIcon sx={{ fontSize: "14px !important", color: "#faad14 !important" }} />}
            label={t("status_approaching")}
            sx={{
              backgroundColor: "rgba(250, 173, 20, 0.15)",
              color: "#faad14",
              border: "1px solid rgba(250, 173, 20, 0.35)",
              fontWeight: 600,
              fontSize: "12px",
            }}
          />
        );
      default:
        return (
          <Chip
            size="small"
            icon={<CheckCircleOutlineIcon sx={{ fontSize: "14px !important", color: "#52c41a !important" }} />}
            label={t("status_normal")}
            sx={{
              backgroundColor: "rgba(82, 196, 26, 0.15)",
              color: "#52c41a",
              border: "1px solid rgba(82, 196, 26, 0.35)",
              fontWeight: 600,
              fontSize: "12px",
            }}
          />
        );
    }
  };

  // Helper for progress bar color
  const getProgressColor = (status: "normal" | "approaching" | "exceeded") => {
    if (status === "exceeded") return "#ff4d4f";
    if (status === "approaching") return "#faad14";
    return "#00863A";
  };

  return (
    <Box>
      {/* Page Header */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: { xs: "flex-start", md: "center" },
          flexDirection: { xs: "column", md: "row" },
          gap: 2,
          mb: 3,
        }}
      >
        <Box>
          <Typography component="h1" variant="h4" fontWeight={700}>
            {t("budget_management")}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {t("budget_subtitle")}
          </Typography>
        </Box>

        {/* Add Budget Button */}
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleOpenCreate}
          sx={{
            borderRadius: 2,
            px: 2.5,
            py: 1,
            fontWeight: 600,
            boxShadow: "0 4px 14px rgba(0, 134, 58, 0.35)",
          }}
        >
          {t("add_budget")}
        </Button>
      </Box>

      {/* Month Navigator Toolbar */}
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 1.5,
          p: 1.5,
          px: 2,
          mb: 3,
          borderRadius: 2,
          backgroundColor: "rgba(255, 255, 255, 0.03)",
          border: `1px solid ${darkTheme.palette.background.paper}`,
        }}
      >
        <Stack direction="row" alignItems="center" spacing={1}>
          <Tooltip title={language === "vi" ? "Tháng trước" : "Previous Month"}>
            <IconButton onClick={handlePrevMonth} size="small" sx={{ color: "text.primary" }}>
              <ChevronLeftIcon />
            </IconButton>
          </Tooltip>

          {/* Month & Year Selectors */}
          <FormControl size="small" sx={{ minWidth: 110 }}>
            <Select
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(Number(e.target.value))}
              sx={{
                borderRadius: 1.5,
                fontSize: "14px",
                fontWeight: 600,
                backgroundColor: "rgba(0,0,0,0.2)",
              }}
            >
              {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                <MenuItem key={m} value={m}>
                  {language === "vi" ? `Tháng ${m}` : `Month ${m}`}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 95 }}>
            <Select
              value={selectedYear}
              onChange={(e) => setSelectedYear(Number(e.target.value))}
              sx={{
                borderRadius: 1.5,
                fontSize: "14px",
                fontWeight: 600,
                backgroundColor: "rgba(0,0,0,0.2)",
              }}
            >
              {[2024, 2025, 2026, 2027, 2028].map((y) => (
                <MenuItem key={y} value={y}>
                  {y}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Tooltip title={language === "vi" ? "Tháng tiếp theo" : "Next Month"}>
            <IconButton onClick={handleNextMonth} size="small" sx={{ color: "text.primary" }}>
              <ChevronRightIcon />
            </IconButton>
          </Tooltip>
        </Stack>

        {/* Current Month Quick Jump */}
        {!isCurrentMonth && (
          <Button
            size="small"
            variant="outlined"
            startIcon={<TodayIcon fontSize="small" />}
            onClick={handleCurrentMonth}
            sx={{
              borderRadius: 1.5,
              borderColor: "rgba(255, 255, 255, 0.2)",
              color: "text.primary",
              fontSize: "13px",
            }}
          >
            {t("current_month")}
          </Button>
        )}
      </Box>

      {/* Overview Statistics Cards */}
      <Box sx={{ mb: 1 }}>
        <Typography
          variant="caption"
          sx={{
            color: "text.secondary",
            textTransform: "uppercase",
            letterSpacing: 1.2,
            fontWeight: 700,
            fontSize: "11px",
          }}
        >
          {t("budget_overview")} ({language === "vi" ? `Tháng ${selectedMonth}/${selectedYear}` : `${selectedMonth}/${selectedYear}`})
        </Typography>
      </Box>

      <Grid container spacing={2} sx={{ mb: 3 }} alignItems="stretch">
        {/* Total Budget */}
        <Grid item xs={12} sm={6} md={3}>
          <Box
            border="1px solid"
            borderColor={darkTheme.palette.background.paper}
            borderRadius={2}
            p={2.5}
            height="100%"
            sx={{
              backgroundColor: "rgba(255, 255, 255, 0.02)",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
          >
            <Typography variant="body2" color="text.secondary" mb={1}>
              {t("total_budget")}
            </Typography>
            <Typography variant="h5" fontWeight={700} color="text.primary">
              {formatValue(summary?.total_budget ?? 0)}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
              {summary?.budget_count ?? 0} {t("categories_budgeted")}
            </Typography>
          </Box>
        </Grid>

        {/* Total Spent */}
        <Grid item xs={12} sm={6} md={3}>
          <Box
            border="1px solid"
            borderColor={darkTheme.palette.background.paper}
            borderRadius={2}
            p={2.5}
            height="100%"
            sx={{
              backgroundColor: "rgba(255, 255, 255, 0.02)",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
          >
            <Typography variant="body2" color="text.secondary" mb={1}>
              {t("total_spent")}
            </Typography>
            <Typography variant="h5" fontWeight={700} color="#ff7875">
              {formatValue(summary?.total_spent ?? 0)}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
              {summary?.overall_percentage ?? 0}% {t("percentage_used")}
            </Typography>
          </Box>
        </Grid>

        {/* Total Remaining */}
        <Grid item xs={12} sm={6} md={3}>
          <Box
            border="1px solid"
            borderColor={darkTheme.palette.background.paper}
            borderRadius={2}
            p={2.5}
            height="100%"
            sx={{
              backgroundColor: "rgba(255, 255, 255, 0.02)",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
          >
            <Typography variant="body2" color="text.secondary" mb={1}>
              {t("total_remaining")}
            </Typography>
            <Typography
              variant="h5"
              fontWeight={700}
              color={Number(summary?.total_remaining || 0) > 0 ? "#52c41a" : "text.secondary"}
            >
              {formatValue(summary?.total_remaining ?? 0)}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 1 }}>
              {language === "vi" ? "Khả dụng trong tháng" : "Available in month"}
            </Typography>
          </Box>
        </Grid>

        {/* Status Breakdown */}
        <Grid item xs={12} sm={6} md={3}>
          <Box
            border="1px solid"
            borderColor={darkTheme.palette.background.paper}
            borderRadius={2}
            p={2.5}
            height="100%"
            sx={{
              backgroundColor: "rgba(255, 255, 255, 0.02)",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
          >
            <Typography variant="body2" color="text.secondary" mb={1}>
              {language === "vi" ? "Tình trạng hạn mức" : "Status Summary"}
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" gap={0.5}>
              <Chip
                size="small"
                label={`${t("status_normal")}: ${summary?.status_counts?.normal ?? 0}`}
                sx={{
                  backgroundColor: "rgba(82, 196, 26, 0.12)",
                  color: "#52c41a",
                  fontWeight: 600,
                  fontSize: "11px",
                }}
              />
              <Chip
                size="small"
                label={`${t("status_approaching")}: ${summary?.status_counts?.approaching ?? 0}`}
                sx={{
                  backgroundColor: "rgba(250, 173, 20, 0.12)",
                  color: "#faad14",
                  fontWeight: 600,
                  fontSize: "11px",
                }}
              />
              <Chip
                size="small"
                label={`${t("status_exceeded")}: ${summary?.status_counts?.exceeded ?? 0}`}
                sx={{
                  backgroundColor: "rgba(255, 77, 79, 0.12)",
                  color: "#ff4d4f",
                  fontWeight: 600,
                  fontSize: "11px",
                }}
              />
            </Stack>
          </Box>
        </Grid>
      </Grid>

      {/* Warning Alert Banner for Exceeded or Approaching Categories */}
      {exceededBudgets.length > 0 && (
        <Alert
          severity="error"
          icon={<ErrorOutlineIcon />}
          sx={{
            mb: 2,
            borderRadius: 2,
            backgroundColor: "rgba(255, 77, 79, 0.12)",
            color: "#ff7875",
            border: "1px solid rgba(255, 77, 79, 0.3)",
          }}
        >
          <strong>{exceededBudgets.length} {t("budget_exceeded_alert")}</strong>{" "}
          ({exceededBudgets.map((b) => b.label.name).join(", ")})
        </Alert>
      )}

      {approachingBudgets.length > 0 && (
        <Alert
          severity="warning"
          icon={<WarningAmberIcon />}
          sx={{
            mb: 2,
            borderRadius: 2,
            backgroundColor: "rgba(250, 173, 20, 0.12)",
            color: "#ffc53d",
            border: "1px solid rgba(250, 173, 20, 0.3)",
          }}
        >
          <strong>{approachingBudgets.length} {t("budget_approaching_alert")}</strong>{" "}
          ({approachingBudgets.map((b) => b.label.name).join(", ")})
        </Alert>
      )}

      {/* Main Budget Cards Content */}
      {isBudgetsLoading ? (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress color="primary" />
        </Box>
      ) : isBudgetsError ? (
        <Alert
          severity="error"
          sx={{ borderRadius: 2 }}
          action={
            <Button color="inherit" size="small" onClick={() => refetchBudgets()}>
              {language === "vi" ? "Thử lại" : "Retry"}
            </Button>
          }
        >
          {t("unable_to_load_data")}
        </Alert>
      ) : budgets && budgets.length > 0 ? (
        <Grid container spacing={2.5}>
          {budgets.map((budget) => {
            const spentNum = Number(budget.spent);
            const limitNum = Number(budget.limit);
            const remainingNum = Number(budget.remaining);
            const pct = budget.percentage;
            const progressColor = getProgressColor(budget.status);

            return (
              <Grid item xs={12} sm={6} lg={4} key={budget.id}>
                <Card
                  sx={{
                    borderRadius: 2.5,
                    border: `1px solid ${
                      budget.status === "exceeded"
                        ? "rgba(255, 77, 79, 0.4)"
                        : budget.status === "approaching"
                        ? "rgba(250, 173, 20, 0.4)"
                        : darkTheme.palette.background.paper
                    }`,
                    backgroundColor: "rgba(255, 255, 255, 0.02)",
                    backdropFilter: "blur(10px)",
                    transition: "transform 0.2s ease, box-shadow 0.2s ease",
                    "&:hover": {
                      transform: "translateY(-3px)",
                      boxShadow: "0 8px 24px rgba(0, 0, 0, 0.3)",
                    },
                  }}
                >
                  <CardContent sx={{ p: 2.5 }}>
                    {/* Header: Label + Color Dot + Status Chip + Actions */}
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        mb: 2,
                      }}
                    >
                      <Stack direction="row" alignItems="center" spacing={1.2}>
                        <Box
                          sx={{
                            width: 14,
                            height: 14,
                            borderRadius: "50%",
                            backgroundColor: budget.label.color || "#00863A",
                            boxShadow: `0 0 8px ${budget.label.color || "#00863A"}88`,
                          }}
                        />
                        <Typography variant="h6" fontWeight={700} noWrap>
                          {budget.label.name}
                        </Typography>
                      </Stack>

                      <Stack direction="row" alignItems="center" spacing={0.5}>
                        {renderStatusChip(budget.status)}
                        <Tooltip title={t("edit_budget")}>
                          <IconButton
                            size="small"
                            onClick={() => handleOpenEdit(budget)}
                            sx={{ color: "text.secondary", "&:hover": { color: "#fff" } }}
                          >
                            <EditOutlinedIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title={t("delete_budget")}>
                          <IconButton
                            size="small"
                            onClick={() => setDeleteTarget(budget)}
                            sx={{ color: "text.secondary", "&:hover": { color: "#ff4d4f" } }}
                          >
                            <DeleteOutlineIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </Stack>
                    </Box>

                    {/* Progress Bar with Clamped Value */}
                    <Box sx={{ mb: 2 }}>
                      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.8 }}>
                        <Typography variant="caption" color="text.secondary">
                          {t("percentage_used")}
                        </Typography>
                        <Typography
                          variant="caption"
                          fontWeight={700}
                          sx={{ color: progressColor }}
                        >
                          {pct.toFixed(1)}%
                        </Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={Math.min(100, Math.max(0, pct))}
                        sx={{
                          height: 9,
                          borderRadius: 4.5,
                          backgroundColor: "rgba(255, 255, 255, 0.08)",
                          "& .MuiLinearProgress-bar": {
                            backgroundColor: progressColor,
                            borderRadius: 4.5,
                          },
                        }}
                      />
                    </Box>

                    {/* Financial Numbers */}
                    <Grid container spacing={1.5} sx={{ pt: 1, borderTop: "1px solid rgba(255,255,255,0.06)" }}>
                      <Grid item xs={4}>
                        <Typography variant="caption" color="text.secondary" display="block">
                          {t("budget_limit")}
                        </Typography>
                        <Typography variant="body2" fontWeight={600}>
                          {formatValue(limitNum)}
                        </Typography>
                      </Grid>

                      <Grid item xs={4}>
                        <Typography variant="caption" color="text.secondary" display="block">
                          {t("actual_spent")}
                        </Typography>
                        <Typography
                          variant="body2"
                          fontWeight={600}
                          sx={{ color: budget.status === "exceeded" ? "#ff7875" : "text.primary" }}
                        >
                          {formatValue(spentNum)}
                        </Typography>
                      </Grid>

                      <Grid item xs={4}>
                        <Typography variant="caption" color="text.secondary" display="block">
                          {t("remaining_balance")}
                        </Typography>
                        <Typography
                          variant="body2"
                          fontWeight={600}
                          sx={{
                            color: remainingNum > 0 ? "#52c41a" : "#ff4d4f",
                          }}
                        >
                          {formatValue(remainingNum)}
                        </Typography>
                      </Grid>
                    </Grid>

                    {/* Exceeded footnote indicator */}
                    {budget.is_over_budget && (
                      <Box
                        sx={{
                          mt: 1.5,
                          p: 0.8,
                          px: 1.2,
                          borderRadius: 1.5,
                          backgroundColor: "rgba(255, 77, 79, 0.1)",
                          display: "flex",
                          alignItems: "center",
                          gap: 0.8,
                        }}
                      >
                        <ArrowUpwardIcon sx={{ fontSize: 14, color: "#ff7875" }} />
                        <Typography variant="caption" sx={{ color: "#ff7875", fontWeight: 600 }}>
                          {language === "vi"
                            ? `Vượt ${formatValue(spentNum - limitNum)}`
                            : `Exceeded by ${formatValue(spentNum - limitNum)}`}
                        </Typography>
                      </Box>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            );
          })}
        </Grid>
      ) : (
        /* Empty State */
        <Box
          sx={{
            py: 8,
            px: 3,
            textAlign: "center",
            borderRadius: 3,
            border: `1px dashed ${darkTheme.palette.background.paper}`,
            backgroundColor: "rgba(255, 255, 255, 0.01)",
          }}
        >
          <AccountBalanceWalletOutlinedIcon
            sx={{ fontSize: 64, color: "text.secondary", opacity: 0.5, mb: 2 }}
          />
          <Typography variant="h6" fontWeight={600} mb={1}>
            {t("no_budgets_found")}
          </Typography>
          <Typography variant="body2" color="text.secondary" maxWidth={480} mx="auto" mb={3}>
            {t("create_first_budget")}
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleOpenCreate}
            sx={{ borderRadius: 2, px: 3, fontWeight: 600 }}
          >
            {t("add_budget")}
          </Button>
        </Box>
      )}

      {/* Create / Edit Budget Dialog */}
      <Dialog
        open={modalOpen}
        onClose={handleCloseModal}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle sx={{ fontWeight: 700, pb: 1 }}>
          {editingBudget ? t("edit_budget") : t("add_budget")}
        </DialogTitle>

        <DialogContent sx={{ pt: 2 }}>
          {formError && (
            <Alert severity="error" sx={{ mb: 2, borderRadius: 1.5 }}>
              {formError}
            </Alert>
          )}

          {/* Month Indicator info */}
          <Typography variant="caption" color="text.secondary" display="block" mb={2}>
            {language === "vi"
              ? `Áp dụng cho kỳ: Tháng ${selectedMonth}/${selectedYear}`
              : `Period: Month ${selectedMonth}/${selectedYear}`}
          </Typography>

          {/* Category Selector */}
          <FormControl fullWidth sx={{ mb: 2.5 }} disabled={!!editingBudget}>
            <InputLabel id="budget-category-label">{t("label")}</InputLabel>
            <Select
              labelId="budget-category-label"
              value={selectedLabelId}
              label={t("label")}
              onChange={(e) => {
                setSelectedLabelId(e.target.value as number);
                setFormError("");
              }}
              sx={{ borderRadius: 1.5 }}
            >
              {labels?.map((label: CustomLabel) => {
                const isAlreadyBudgeted =
                  !editingBudget && budgetedLabelIds.has(label.id);

                return (
                  <MenuItem
                    key={label.id}
                    value={label.id}
                    disabled={isAlreadyBudgeted}
                  >
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
                      <Box
                        sx={{
                          width: 12,
                          height: 12,
                          borderRadius: "50%",
                          backgroundColor: label.color || "#00863A",
                        }}
                      />
                      <span>{label.name}</span>
                      {isAlreadyBudgeted && (
                        <Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>
                          ({language === "vi" ? "Đã có ngân sách" : "Already budgeted"})
                        </Typography>
                      )}
                    </Box>
                  </MenuItem>
                );
              })}
            </Select>
          </FormControl>

          {/* Budget Limit Amount */}
          <TextField
            fullWidth
            label={t("budget_limit")}
            value={amountInput}
            onChange={(e) => {
              const formatted = formatCurrency(e.target.value);
              setAmountInput(formatted);
              setFormError("");
            }}
            placeholder="0"
            InputProps={{
              endAdornment: <InputAdornment position="end">đ</InputAdornment>,
            }}
            sx={{ borderRadius: 1.5 }}
          />
        </DialogContent>

        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={handleCloseModal} sx={{ color: "text.secondary" }}>
            {t("cancel")}
          </Button>
          <Button
            variant="contained"
            onClick={handleSave}
            disabled={createMutation.isPending || updateMutation.isPending}
            sx={{ borderRadius: 2, px: 2.5 }}
          >
            {createMutation.isPending || updateMutation.isPending ? (
              <CircularProgress size={20} color="inherit" />
            ) : editingBudget ? (
              t("save")
            ) : (
              t("add")
            )}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle sx={{ fontWeight: 700 }}>
          {t("delete_budget")}
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary">
            {t("confirm_delete_budget")} (<strong>{deleteTarget?.label.name}</strong> -{" "}
            {language === "vi"
              ? `Tháng ${deleteTarget?.month}/${deleteTarget?.year}`
              : `Month ${deleteTarget?.month}/${deleteTarget?.year}`}
            )
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5 }}>
          <Button onClick={() => setDeleteTarget(null)} sx={{ color: "text.secondary" }}>
            {t("cancel")}
          </Button>
          <Button
            variant="contained"
            color="error"
            onClick={handleDeleteConfirm}
            disabled={deleteMutation.isPending}
            sx={{ borderRadius: 2, px: 2.5 }}
          >
            {deleteMutation.isPending ? (
              <CircularProgress size={20} color="inherit" />
            ) : (
              t("delete")
            )}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
