import { useState, useMemo } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
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
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { grey } from "@mui/material/colors";
import AddIcon from "@mui/icons-material/Add";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import CloseIcon from "@mui/icons-material/Close";
import ChevronLeftIcon from "@mui/icons-material/ChevronLeft";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import AccountBalanceWalletOutlinedIcon from "@mui/icons-material/AccountBalanceWalletOutlined";
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
import RebalanceSuggestionDialog from "../components/modals/RebalanceSuggestionDialog";

export default function Budgets() {
  const { language, t } = useLanguage();
  const queryClient = useQueryClient();
  const [rebalanceTarget, setRebalanceTarget] = useState<CategoryBudget | null>(null);
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

  // Helper for status chip matching app palette
  const renderStatusChip = (status: "normal" | "approaching" | "exceeded") => {
    switch (status) {
      case "exceeded":
        return (
          <Chip
            size="small"
            label={t("status_exceeded")}
            sx={{
              backgroundColor: "rgba(242, 86, 89, 0.15)",
              color: "#f25659",
              fontWeight: 600,
              fontSize: "12px",
            }}
          />
        );
      case "approaching":
        return (
          <Chip
            size="small"
            label={t("status_approaching")}
            sx={{
              backgroundColor: "rgba(250, 173, 20, 0.15)",
              color: "#faad14",
              fontWeight: 600,
              fontSize: "12px",
            }}
          />
        );
      default:
        return (
          <Chip
            size="small"
            label={t("status_normal")}
            sx={{
              backgroundColor: "rgba(72, 204, 144, 0.15)",
              color: "#48cc90",
              fontWeight: 600,
              fontSize: "12px",
            }}
          />
        );
    }
  };

  // Helper for progress bar color matching app theme
  const getProgressColor = (status: "normal" | "approaching" | "exceeded") => {
    if (status === "exceeded") return "#f25659";
    if (status === "approaching") return "#faad14";
    return "#48cc90";
  };

  return (
    <Box>
      {/* Header matching Home.tsx */}
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
          {t("budget_management")}
        </Typography>
        <Box sx={{ marginTop: { xs: 2, md: 0 } }}>
          <Button
            variant="contained"
            size="medium"
            startIcon={<AddIcon />}
            onClick={handleOpenCreate}
          >
            {t("add_budget")}
          </Button>
        </Box>
      </Box>

      {/* Filters Bar matching Reports.tsx and Transactions.tsx */}
      <Box
        sx={{
          display: "flex",
          flexWrap: "wrap",
          gap: 1.5,
          alignItems: "center",
          mt: 3,
          mb: 1,
        }}
      >
        <Box display="flex" alignItems="center" gap={1}>
          <IconButton onClick={handlePrevMonth} size="small" sx={{ color: "text.primary" }}>
            <ChevronLeftIcon />
          </IconButton>
          <FormControl size="small" sx={{ minWidth: 120 }}>
            <Select
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(Number(e.target.value))}
            >
              {Array.from({ length: 12 }, (_, i) => i + 1).map((m) => (
                <MenuItem key={m} value={m}>
                  {language === "vi" ? `Tháng ${m}` : `Month ${m}`}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl size="small" sx={{ minWidth: 100 }}>
            <Select
              value={selectedYear}
              onChange={(e) => setSelectedYear(Number(e.target.value))}
            >
              {[2024, 2025, 2026, 2027, 2028].map((y) => (
                <MenuItem key={y} value={y}>
                  {y}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <IconButton onClick={handleNextMonth} size="small" sx={{ color: "text.primary" }}>
            <ChevronRightIcon />
          </IconButton>
        </Box>

        {!isCurrentMonth && (
          <Button
            size="small"
            variant="outlined"
            startIcon={<TodayIcon fontSize="small" />}
            onClick={handleCurrentMonth}
          >
            {t("current_month")}
          </Button>
        )}
      </Box>

      {/* 1. KPI Cards matching WalletGridRow.tsx and Home.tsx */}
      <Grid mt={1} container spacing={2} alignItems={"stretch"}>
        {/* Total Budget */}
        <Grid item xs={12} sm={6} lg={3}>
          <Box
            border="1px solid"
            borderColor={darkTheme.palette.background.paper}
            borderRadius={2}
            padding={3}
            height={"100%"}
          >
            <Typography component="h2" variant="body1" mb={1}>
              {t("total_budget")}
            </Typography>
            <Box display="flex" alignItems="center" gap={2}>
              <Typography component="span" variant="h5" fontWeight={600}>
                {formatValue(summary?.total_budget ?? 0)}
              </Typography>
            </Box>
            <Typography component="p" variant="caption" color="text.secondary" sx={{ mt: 1 }}>
              {summary?.budget_count ?? 0} {t("categories_budgeted")}
            </Typography>
          </Box>
        </Grid>

        {/* Total Spent */}
        <Grid item xs={12} sm={6} lg={3}>
          <Box
            border="1px solid"
            borderColor={darkTheme.palette.background.paper}
            borderRadius={2}
            padding={3}
            height={"100%"}
          >
            <Typography component="h2" variant="body1" mb={1}>
              {t("total_spent")}
            </Typography>
            <Box display="flex" alignItems="center" gap={2}>
              <Typography
                component="span"
                variant="h5"
                fontWeight={600}
                sx={{ color: "#f25659" }}
              >
                -{formatValue(summary?.total_spent ?? 0)}
              </Typography>
            </Box>
            <Typography component="p" variant="caption" color="text.secondary" sx={{ mt: 1 }}>
              {summary?.overall_percentage ?? 0}% {t("percentage_used")}
            </Typography>
          </Box>
        </Grid>

        {/* Total Remaining */}
        <Grid item xs={12} sm={6} lg={3}>
          <Box
            border="1px solid"
            borderColor={darkTheme.palette.background.paper}
            borderRadius={2}
            padding={3}
            height={"100%"}
          >
            <Typography component="h2" variant="body1" mb={1}>
              {t("total_remaining")}
            </Typography>
            <Box display="flex" alignItems="center" gap={2}>
              <Typography
                component="span"
                variant="h5"
                fontWeight={600}
                sx={{
                  color: Number(summary?.total_remaining || 0) >= 0 ? "#48cc90" : "#f25659",
                }}
              >
                {formatValue(summary?.total_remaining ?? 0)}
              </Typography>
            </Box>
            <Typography component="p" variant="caption" color="text.secondary" sx={{ mt: 1 }}>
              {language === "vi" ? "Khả dụng trong tháng" : "Available in month"}
            </Typography>
          </Box>
        </Grid>

        {/* Status Breakdown */}
        <Grid item xs={12} sm={6} lg={3}>
          <Box
            border="1px solid"
            borderColor={darkTheme.palette.background.paper}
            borderRadius={2}
            padding={3}
            height={"100%"}
          >
            <Typography component="h2" variant="body1" mb={1}>
              {language === "vi" ? "Tình trạng hạn mức" : "Status Summary"}
            </Typography>
            <Box display="flex" alignItems="center" gap={1} flexWrap="wrap" sx={{ mt: 1 }}>
              <Chip
                size="small"
                label={`${t("status_normal")}: ${summary?.status_counts?.normal ?? 0}`}
                sx={{
                  backgroundColor: "rgba(72, 204, 144, 0.12)",
                  color: "#48cc90",
                  fontWeight: 600,
                  fontSize: "12px",
                }}
              />
              <Chip
                size="small"
                label={`${t("status_approaching")}: ${summary?.status_counts?.approaching ?? 0}`}
                sx={{
                  backgroundColor: "rgba(250, 173, 20, 0.12)",
                  color: "#faad14",
                  fontWeight: 600,
                  fontSize: "12px",
                }}
              />
              <Chip
                size="small"
                label={`${t("status_exceeded")}: ${summary?.status_counts?.exceeded ?? 0}`}
                sx={{
                  backgroundColor: "rgba(242, 86, 89, 0.12)",
                  color: "#f25659",
                  fontWeight: 600,
                  fontSize: "12px",
                }}
              />
            </Box>
          </Box>
        </Grid>
      </Grid>

      {/* Alert banners */}
      {exceededBudgets.length > 0 && (
        <Alert severity="error" sx={{ mt: 2 }}>
          <strong>{exceededBudgets.length} {t("budget_exceeded_alert")}</strong>{" "}
          ({exceededBudgets.map((b) => b.label.name).join(", ")})
        </Alert>
      )}

      {approachingBudgets.length > 0 && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          <strong>{approachingBudgets.length} {t("budget_approaching_alert")}</strong>{" "}
          ({approachingBudgets.map((b) => b.label.name).join(", ")})
        </Alert>
      )}

      {/* 2. Category Budgets Section */}
      <Box height={"auto"} mt={3} mb={4}>
        <Typography component="h2" variant="h6" mb={1.5}>
          {language === "vi" ? "Danh sách ngân sách danh mục" : "Category Budgets"}
        </Typography>

        {isBudgetsLoading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
            <CircularProgress color="primary" />
          </Box>
        ) : isBudgetsError ? (
          <Alert
            severity="error"
            action={
              <Button color="inherit" size="small" onClick={() => refetchBudgets()}>
                {language === "vi" ? "Thử lại" : "Retry"}
              </Button>
            }
          >
            {t("unable_to_load_data")}
          </Alert>
        ) : budgets && budgets.length > 0 ? (
          <Grid container spacing={2}>
            {budgets.map((budget) => {
              const spentNum = Number(budget.spent);
              const limitNum = Number(budget.limit);
              const remainingNum = Number(budget.remaining);
              const pct = budget.percentage;
              const progressColor = getProgressColor(budget.status);

              return (
                <Grid item xs={12} sm={6} lg={4} key={budget.id}>
                  <Box
                    border="1px solid"
                    borderColor={darkTheme.palette.background.paper}
                    borderRadius={2}
                    padding={3}
                    height="100%"
                    display="flex"
                    flexDirection="column"
                    justifyContent="space-between"
                  >
                    <Box>
                      {/* Header: Label Chip + Status Chip + Actions */}
                      <Box
                        sx={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          mb: 2,
                        }}
                      >
                        <Chip
                          label={budget.label.name}
                          variant="outlined"
                          size="small"
                          style={{
                            borderColor: budget.label.color || darkTheme.palette.primary.main,
                            color: budget.label.color || "inherit",
                            fontWeight: 600,
                          }}
                        />

                        <Box display="flex" alignItems="center" gap={0.5}>
                          {renderStatusChip(budget.status)}
                          <Tooltip title={t("edit_budget")}>
                            <IconButton
                              size="small"
                              onClick={() => handleOpenEdit(budget)}
                              sx={{ color: grey[500], "&:hover": { color: "#fff" } }}
                            >
                              <EditOutlinedIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title={t("delete_budget")}>
                            <IconButton
                              size="small"
                              onClick={() => setDeleteTarget(budget)}
                              sx={{ color: grey[500], "&:hover": { color: "#f25659" } }}
                            >
                              <DeleteOutlineIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        </Box>
                      </Box>

                      {/* Progress Bar */}
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
                            height: 8,
                            borderRadius: 4,
                            backgroundColor: "rgba(255, 255, 255, 0.08)",
                            "& .MuiLinearProgress-bar": {
                              backgroundColor: progressColor,
                              borderRadius: 4,
                            },
                          }}
                        />
                      </Box>
                    </Box>

                    {/* Financial Numbers */}
                    <Box>
                      <Grid
                        container
                        spacing={1.5}
                        sx={{ pt: 1.5, borderTop: `1px solid ${darkTheme.palette.background.paper}` }}
                      >
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
                            sx={{ color: budget.status === "exceeded" ? "#f25659" : "text.primary" }}
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
                              color: remainingNum >= 0 ? "#48cc90" : "#f25659",
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
                            borderRadius: 1,
                            backgroundColor: "rgba(242, 86, 89, 0.1)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            gap: 0.8,
                          }}
                        >
                          <Box sx={{ display: "flex", alignItems: "center", gap: 0.8 }}>
                            <ArrowUpwardIcon sx={{ fontSize: 14, color: "#f25659" }} />
                            <Typography variant="caption" sx={{ color: "#f25659", fontWeight: 600 }}>
                              {language === "vi"
                                ? `Vượt ${formatValue(spentNum - limitNum)}`
                                : `Exceeded by ${formatValue(spentNum - limitNum)}`}
                            </Typography>
                          </Box>

                          <Button
                            size="small"
                            variant="outlined"
                            onClick={() => setRebalanceTarget(budget)}
                            sx={{
                              py: 0.2,
                              px: 1,
                              fontSize: "11px",
                              lineHeight: 1.4,
                              textTransform: "none",
                              fontWeight: 600,
                              borderColor: "rgba(250, 173, 20, 0.5)",
                              color: "#faad14",
                              "&:hover": {
                                borderColor: "#faad14",
                                backgroundColor: "rgba(250, 173, 20, 0.12)",
                              },
                            }}
                          >
                            {t("rebalance_btn")}
                          </Button>
                        </Box>
                      )}
                    </Box>
                  </Box>
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
              borderRadius: 2,
              border: `1px dashed ${darkTheme.palette.background.paper}`,
            }}
          >
            <AccountBalanceWalletOutlinedIcon
              sx={{ fontSize: 48, color: "text.secondary", opacity: 0.5, mb: 1.5 }}
            />
            <Typography variant="h6" fontWeight={600} mb={1}>
              {t("no_budgets_found")}
            </Typography>
            <Typography variant="body2" color="text.secondary" maxWidth={480} mx="auto" mb={2}>
              {t("create_first_budget")}
            </Typography>
            <Button
              variant="contained"
              size="medium"
              startIcon={<AddIcon />}
              onClick={handleOpenCreate}
            >
              {t("add_budget")}
            </Button>
          </Box>
        )}
      </Box>

      {/* Create / Edit Budget Dialog */}
      <Dialog
        open={modalOpen}
        onClose={handleCloseModal}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>{editingBudget ? t("edit_budget") : t("add_budget")}</span>
          <IconButton size="small" onClick={handleCloseModal} sx={{ color: "text.secondary" }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </DialogTitle>

        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: "16px !important" }}>
          {formError && (
            <Alert severity="error" sx={{ borderRadius: 1.5 }}>
              {formError}
            </Alert>
          )}

          {/* Month Indicator info styled in a dark pill */}
          <Box
            sx={{
              backgroundColor: grey[900],
              p: 1.5,
              borderRadius: 2,
              border: `1px solid ${darkTheme.palette.background.paper}`,
            }}
          >
            <Typography variant="body2" color="text.secondary">
              {language === "vi"
                ? `Áp dụng cho kỳ: Tháng ${selectedMonth}/${selectedYear}`
                : `Period: Month ${selectedMonth}/${selectedYear}`}
            </Typography>
          </Box>

          {/* Category Selector */}
          <FormControl fullWidth size="small" disabled={!!editingBudget}>
            <InputLabel id="budget-category-label">{t("label")}</InputLabel>
            <Select
              labelId="budget-category-label"
              value={selectedLabelId}
              label={t("label")}
              onChange={(e) => {
                setSelectedLabelId(e.target.value as number);
                setFormError("");
              }}
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
            size="small"
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
          />

          <Button
            fullWidth
            variant="contained"
            onClick={handleSave}
            disabled={createMutation.isPending || updateMutation.isPending}
            sx={{ height: 42, mt: 1, borderRadius: 2, fontWeight: 600 }}
          >
            {createMutation.isPending || updateMutation.isPending ? (
              <CircularProgress size={20} color="inherit" />
            ) : editingBudget ? (
              t("save")
            ) : (
              t("add")
            )}
          </Button>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={!!deleteTarget}
        onClose={() => setDeleteTarget(null)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span>{t("delete_budget")}</span>
          <IconButton size="small" onClick={() => setDeleteTarget(null)} sx={{ color: "text.secondary" }}>
            <CloseIcon fontSize="small" />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2.5, pt: "16px !important" }}>
          <Typography variant="body2" color="text.secondary">
            {t("confirm_delete_budget")} (<strong>{deleteTarget?.label.name}</strong> -{" "}
            {language === "vi"
              ? `Tháng ${deleteTarget?.month}/${deleteTarget?.year}`
              : `Month ${deleteTarget?.month}/${deleteTarget?.year}`}
            )
          </Typography>

          <Button
            fullWidth
            variant="contained"
            color="error"
            onClick={handleDeleteConfirm}
            disabled={deleteMutation.isPending}
            sx={{ height: 42, borderRadius: 2, fontWeight: 600 }}
          >
            {deleteMutation.isPending ? (
              <CircularProgress size={20} color="inherit" />
            ) : (
              t("delete")
            )}
          </Button>
        </DialogContent>
      </Dialog>

      {rebalanceTarget && (
        <RebalanceSuggestionDialog
          open={!!rebalanceTarget}
          onClose={() => setRebalanceTarget(null)}
          targetLabelId={rebalanceTarget.label.id}
          targetLabelName={rebalanceTarget.label.name}
          deficitAmount={Math.max(
            0,
            Number(rebalanceTarget.spent) - Number(rebalanceTarget.limit)
          )}
          month={selectedMonth}
          year={selectedYear}
          onSuccess={() => {
            setRebalanceTarget(null);
            refetchBudgets();
          }}
        />
      )}
    </Box>
  );
}
