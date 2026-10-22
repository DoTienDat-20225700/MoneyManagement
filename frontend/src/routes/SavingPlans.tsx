import { useState } from "react";
import {
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Grid,
  IconButton,
  InputAdornment,
  LinearProgress,
  TextField,
  Tooltip,
  Typography,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from "@mui/material";
import { grey } from "@mui/material/colors";
import AddIcon from "@mui/icons-material/Add";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import PauseCircleOutlineIcon from "@mui/icons-material/PauseCircleOutline";
import SavingsOutlinedIcon from "@mui/icons-material/SavingsOutlined";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import CloseIcon from "@mui/icons-material/Close";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import dayjs, { Dayjs } from "dayjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSnackbar } from "notistack";
import { useSavingPlans } from "../hooks/api/useSavingPlans";
import { SavingPlan, SavingPlanContribution } from "../models/SavingPlan";
import { useLanguage } from "../context/LanguageContext";
import { formatCurrency, formatValue } from "../utils/utils";
import { paletteTokens } from "../theme";

export default function SavingPlans() {
  const { language, dateFormat, t } = useLanguage();
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();
  const {
    getSavingPlans,
    createSavingPlan,
    updateSavingPlan,
    toggleSavingPlan,
    deleteSavingPlan,
    getContributions,
    addContribution,
    updateContribution,
    deleteContribution,
  } = useSavingPlans();

  const { data: plans, isLoading, isError, refetch } = useQuery({
    queryKey: ["saving_plans"],
    queryFn: () => getSavingPlans(),
  });

  // Goal Plan Modal states (Create / Edit)
  const [modalOpen, setModalOpen] = useState(false);
  const [editingPlan, setEditingPlan] = useState<SavingPlan | null>(null);
  const [title, setTitle] = useState("");
  const [amount, setAmount] = useState("");
  const [goalDate, setGoalDate] = useState<Dayjs | null>(null);
  const [description, setDescription] = useState("");
  const [formError, setFormError] = useState("");

  // Delete Plan confirm modal
  const [deleteTargetPlan, setDeleteTargetPlan] = useState<SavingPlan | null>(null);

  // Filter status state
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "completed" | "closed">("all");

  // Add Contribution Modal state
  const [contributionModalPlan, setContributionModalPlan] = useState<SavingPlan | null>(null);
  const [contribAmount, setContribAmount] = useState("");
  const [contribDate, setContribDate] = useState<Dayjs | null>(dayjs());
  const [contribDesc, setContribDesc] = useState("");
  const [contribError, setContribError] = useState("");

  // Contribution History Drawer / Modal state
  const [historyModalPlan, setHistoryModalPlan] = useState<SavingPlan | null>(null);
  const [editingContrib, setEditingContrib] = useState<SavingPlanContribution | null>(null);
  const [editContribAmount, setEditContribAmount] = useState("");
  const [editContribDate, setEditContribDate] = useState<Dayjs | null>(dayjs());
  const [editContribDesc, setEditContribDesc] = useState("");
  const [deleteTargetContrib, setDeleteTargetContrib] = useState<SavingPlanContribution | null>(null);

  // Contributions query for active history modal
  const {
    data: planContributions,
    isLoading: isContributionsLoading,
  } = useQuery({
    queryKey: ["contributions", historyModalPlan?.id],
    queryFn: () => (historyModalPlan ? getContributions(historyModalPlan.id) : Promise.resolve([])),
    enabled: !!historyModalPlan,
  });

  // Mutations
  const createPlanMutation = useMutation({
    mutationFn: createSavingPlan,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["saving_plans"] });
      enqueueSnackbar(t("plan_created"), { variant: "success" });
      handleCloseModal();
    },
    onError: () => {
      enqueueSnackbar(t("err_plan_create"), { variant: "error" });
    },
  });

  const updatePlanMutation = useMutation({
    mutationFn: updateSavingPlan,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["saving_plans"] });
      enqueueSnackbar(t("plan_updated"), { variant: "success" });
      handleCloseModal();
    },
    onError: () => {
      enqueueSnackbar(t("err_plan_update"), { variant: "error" });
    },
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) =>
      toggleSavingPlan(id, active),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["saving_plans"] });
      enqueueSnackbar(t("plan_updated"), { variant: "success" });
    },
    onError: () => {
      enqueueSnackbar(t("err_plan_update"), { variant: "error" });
    },
  });

  const deletePlanMutation = useMutation({
    mutationFn: deleteSavingPlan,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["saving_plans"] });
      enqueueSnackbar(t("plan_deleted"), { variant: "success" });
      setDeleteTargetPlan(null);
    },
    onError: () => {
      enqueueSnackbar(t("err_plan_delete"), { variant: "error" });
      setDeleteTargetPlan(null);
    },
  });

  const addContribMutation = useMutation({
    mutationFn: addContribution,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["saving_plans"] });
      if (contributionModalPlan) {
        queryClient.invalidateQueries({ queryKey: ["contributions", contributionModalPlan.id] });
      }
      enqueueSnackbar(t("contribution_added"), { variant: "success" });
      handleCloseContribModal();
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.message || t("err_contribution_add");
      enqueueSnackbar(msg, { variant: "error" });
    },
  });

  const updateContribMutation = useMutation({
    mutationFn: updateContribution,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["saving_plans"] });
      if (historyModalPlan) {
        queryClient.invalidateQueries({ queryKey: ["contributions", historyModalPlan.id] });
      }
      enqueueSnackbar(t("contribution_updated"), { variant: "success" });
      setEditingContrib(null);
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.message || t("err_contribution_update");
      enqueueSnackbar(msg, { variant: "error" });
    },
  });

  const deleteContribMutation = useMutation({
    mutationFn: deleteContribution,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["saving_plans"] });
      if (historyModalPlan) {
        queryClient.invalidateQueries({ queryKey: ["contributions", historyModalPlan.id] });
      }
      enqueueSnackbar(t("contribution_deleted"), { variant: "success" });
      setDeleteTargetContrib(null);
    },
    onError: (err: any) => {
      const msg = err?.response?.data?.message || t("err_contribution_delete");
      enqueueSnackbar(msg, { variant: "error" });
      setDeleteTargetContrib(null);
    },
  });

  // Modal handlers
  function handleOpenCreate() {
    setEditingPlan(null);
    setTitle("");
    setAmount("");
    setGoalDate(null);
    setDescription("");
    setFormError("");
    setModalOpen(true);
  }

  function handleOpenEdit(plan: SavingPlan) {
    setEditingPlan(plan);
    setTitle(plan.title);
    setAmount(formatCurrency(Math.round(Number(plan.amount))));
    setGoalDate(plan.goal_date ? dayjs(plan.goal_date) : null);
    setDescription(plan.description || "");
    setFormError("");
    setModalOpen(true);
  }

  function handleCloseModal() {
    setModalOpen(false);
    setEditingPlan(null);
  }

  function handleSavePlan() {
    if (!title.trim()) {
      setFormError(t("err_title_req"));
      return;
    }
    const cleanNum = Number(amount.replace(/\D/g, ""));
    if (!cleanNum || cleanNum <= 0) {
      setFormError(t("err_amount_req"));
      return;
    }

    const payload = {
      title: title.trim(),
      amount: cleanNum,
      goal_date: goalDate ? goalDate.format("YYYY-MM-DD") : null,
      description: description.trim(),
    };

    if (editingPlan) {
      updatePlanMutation.mutate({ id: editingPlan.id, plan: payload });
    } else {
      createPlanMutation.mutate(payload);
    }
  }

  // Contribution handlers
  function handleOpenAddContrib(plan: SavingPlan) {
    setContributionModalPlan(plan);
    setContribAmount("");
    setContribDate(dayjs());
    setContribDesc("");
    setContribError("");
  }

  function handleCloseContribModal() {
    setContributionModalPlan(null);
    setContribAmount("");
    setContribDesc("");
    setContribError("");
  }

  function handleSaveContribution() {
    if (!contributionModalPlan) return;
    const cleanNum = Number(contribAmount.replace(/\D/g, ""));
    if (!cleanNum || cleanNum <= 0) {
      setContribError(t("err_amount_req"));
      return;
    }

    // Generate unique idempotency key for this submission
    const idempotencyKey =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : `contrib_${Date.now()}_${Math.random()}`;

    addContribMutation.mutate({
      planId: contributionModalPlan.id,
      contribution: {
        amount: cleanNum,
        date: contribDate ? contribDate.format("YYYY-MM-DD") : dayjs().format("YYYY-MM-DD"),
        description: contribDesc.trim(),
        idempotency_key: idempotencyKey,
      },
    });
  }

  // Contribution history modal handlers
  function handleOpenHistory(plan: SavingPlan) {
    setHistoryModalPlan(plan);
    setEditingContrib(null);
    setDeleteTargetContrib(null);
  }

  function handleStartEditContrib(contrib: SavingPlanContribution) {
    setEditingContrib(contrib);
    setEditContribAmount(formatCurrency(Math.round(Number(contrib.amount))));
    setEditContribDate(contrib.date ? dayjs(contrib.date) : dayjs());
    setEditContribDesc(contrib.description || "");
  }

  function handleSaveEditContrib() {
    if (!historyModalPlan || !editingContrib) return;
    const cleanNum = Number(editContribAmount.replace(/\D/g, ""));
    if (!cleanNum || cleanNum <= 0) return;

    updateContribMutation.mutate({
      planId: historyModalPlan.id,
      contribId: editingContrib.id,
      data: {
        amount: cleanNum,
        date: editContribDate ? editContribDate.format("YYYY-MM-DD") : dayjs().format("YYYY-MM-DD"),
        description: editContribDesc.trim(),
      },
    });
  }

  // Filter calculations
  const allPlans = plans ?? [];
  const activePlans = allPlans.filter((p) => p.status === "active");
  const completedPlans = allPlans.filter((p) => p.status === "completed");
  const closedPlans = allPlans.filter((p) => p.status === "closed");

  const filteredPlans = allPlans.filter((p) => {
    if (statusFilter === "active") return p.status === "active";
    if (statusFilter === "completed") return p.status === "completed";
    if (statusFilter === "closed") return p.status === "closed";
    return true;
  });

  const totalTargetAmount = allPlans
    .filter((p) => p.active)
    .reduce((acc, curr) => acc + Number(curr.amount || 0), 0);

  const totalSavedAmount = allPlans.reduce(
    (acc, curr) => acc + Number(curr.amount_saved || 0),
    0
  );

  return (
    <LocalizationProvider dateAdapter={AdapterDayjs}>
      <Box>
        {/* Header matching Home.tsx and Budgets.tsx */}
        <Box
          sx={{
            display: "flex",
            flexDirection: { xs: "column", md: "row" },
            justifyContent: "space-between",
            alignItems: { xs: "start", md: "center" },
          }}
        >
          <Typography component="h1" variant="h4" fontWeight={600}>
            {t("saving_plans")}
          </Typography>
          <Box sx={{ marginTop: { xs: 2, md: 0 } }}>
            <Button
              variant="contained"
              size="medium"
              startIcon={<AddIcon />}
              onClick={handleOpenCreate}
            >
              {t("add_saving_plan")}
            </Button>
          </Box>
        </Box>

        {/* 1. Overview KPI Cards matching WalletGridRow.tsx */}
        <Grid mt={1} container spacing={2} alignItems={"stretch"}>
          {/* Active Plans */}
          <Grid item xs={12} sm={6} lg={3}>
            <Box
              border="1px solid"
              borderColor={paletteTokens.divider}
              borderRadius={2}
              padding={3}
              height="100%"
            >
              <Typography component="h2" variant="body1" mb={1}>
                {t("active_plans")}
              </Typography>
              <Box display="flex" alignItems="center" gap={2}>
                <Typography component="span" variant="h5" fontWeight={600}>
                  {activePlans.length} / {allPlans.length}
                </Typography>
              </Box>
              <Typography component="p" variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                {language === "vi" ? "Mục tiêu đang theo đuổi" : "Ongoing goals"}
              </Typography>
            </Box>
          </Grid>

          {/* Total Target */}
          <Grid item xs={12} sm={6} lg={3}>
            <Box
              border="1px solid"
              borderColor={paletteTokens.divider}
              borderRadius={2}
              padding={3}
              height="100%"
            >
              <Typography component="h2" variant="body1" mb={1}>
                {t("total_target")}
              </Typography>
              <Box display="flex" alignItems="center" gap={2}>
                <Typography component="span" variant="h5" fontWeight={600}>
                  {formatValue(totalTargetAmount)}
                </Typography>
              </Box>
              <Typography component="p" variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                {language === "vi" ? "Tổng ngân sách cần tiết kiệm" : "Total target to reach"}
              </Typography>
            </Box>
          </Grid>

          {/* Total Amount Saved */}
          <Grid item xs={12} sm={6} lg={3}>
            <Box
              border="1px solid"
              borderColor={paletteTokens.divider}
              borderRadius={2}
              padding={3}
              height="100%"
            >
              <Typography component="h2" variant="body1" mb={1}>
                {t("total_saved_all_plans")}
              </Typography>
              <Box display="flex" alignItems="center" gap={2}>
                <Typography
                  component="span"
                  variant="h5"
                  fontWeight={600}
                  sx={{ color: paletteTokens.primary }}
                >
                  {formatValue(totalSavedAmount)}
                </Typography>
              </Box>
              <Typography component="p" variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                {language === "vi" ? "Tổng tiền đã đóng góp thực tế" : "Real money contributed"}
              </Typography>
            </Box>
          </Grid>

          {/* Completed Goals */}
          <Grid item xs={12} sm={6} lg={3}>
            <Box
              border="1px solid"
              borderColor={paletteTokens.divider}
              borderRadius={2}
              padding={3}
              height="100%"
            >
              <Typography component="h2" variant="body1" mb={1}>
                {t("completed_plans")}
              </Typography>
              <Box display="flex" alignItems="center" gap={1.5}>
                <CheckCircleOutlineIcon sx={{ color: paletteTokens.primary, fontSize: 24 }} />
                <Typography component="span" variant="h5" fontWeight={600} sx={{ color: paletteTokens.primary }}>
                  {completedPlans.length}
                </Typography>
              </Box>
              <Typography component="p" variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                {language === "vi" ? "Mục tiêu đã về đích" : "Achieved goals"}
              </Typography>
            </Box>
          </Grid>
        </Grid>

        {/* 2. Filters Bar matching Reports and Budgets */}
        <Box
          sx={{
            display: "flex",
            flexWrap: "wrap",
            gap: 1.5,
            alignItems: "center",
            mt: 3,
            mb: 2,
          }}
        >
          <Button
            size="small"
            variant={statusFilter === "all" ? "contained" : "outlined"}
            onClick={() => setStatusFilter("all")}
          >
            {t("all")} ({allPlans.length})
          </Button>
          <Button
            size="small"
            variant={statusFilter === "active" ? "contained" : "outlined"}
            onClick={() => setStatusFilter("active")}
          >
            {t("plan_active")} ({activePlans.length})
          </Button>
          <Button
            size="small"
            variant={statusFilter === "completed" ? "contained" : "outlined"}
            onClick={() => setStatusFilter("completed")}
          >
            {t("plan_completed")} ({completedPlans.length})
          </Button>
          <Button
            size="small"
            variant={statusFilter === "closed" ? "contained" : "outlined"}
            onClick={() => setStatusFilter("closed")}
          >
            {t("plan_closed")} ({closedPlans.length})
          </Button>
        </Box>

        {/* Loading & Error States */}
        {isLoading && (
          <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
            <CircularProgress color="primary" />
          </Box>
        )}

        {isError && (
          <Alert severity="error" sx={{ mb: 3 }} onClose={() => refetch()}>
            {t("unable_to_load_data")}
          </Alert>
        )}

        {/* Empty State */}
        {!isLoading && allPlans.length === 0 && (
          <Box
            border="1px dashed"
            borderColor={paletteTokens.divider}
            borderRadius={2}
            textAlign="center"
            py={8}
            px={3}
            mt={2}
          >
            <SavingsOutlinedIcon sx={{ fontSize: 60, color: "text.secondary", mb: 2 }} />
            <Typography component="h2" variant="h6" fontWeight={600} gutterBottom>
              {t("no_saving_plans")}
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={handleOpenCreate}
              sx={{ mt: 2 }}
            >
              {t("add_saving_plan")}
            </Button>
          </Box>
        )}

        {/* No plans in current filter */}
        {!isLoading && allPlans.length > 0 && filteredPlans.length === 0 && (
          <Box
            border="1px dashed"
            borderColor={paletteTokens.divider}
            borderRadius={2}
            textAlign="center"
            py={6}
            px={3}
            mt={2}
          >
            <Typography variant="body2" color="text.secondary">
              {t("no_plans_in_status")}
            </Typography>
          </Box>
        )}

        {/* 3. Goal Cards Grid */}
        <Grid container spacing={2}>
          {filteredPlans.map((plan) => {
            const target = Number(plan.amount);
            const saved = Number(plan.amount_saved || 0);
            const remaining = Number(plan.remaining_amount || 0);
            const pct = plan.completion_percentage ?? 0;
            const isCompleted = plan.status === "completed";
            const isClosed = plan.status === "closed";
            const estimate = plan.estimated_completion;

            return (
              <Grid item xs={12} sm={6} lg={4} key={plan.id}>
                <Box
                  border="1px solid"
                  borderColor={paletteTokens.divider}
                  borderRadius={2}
                  padding={3}
                  height="100%"
                  display="flex"
                  flexDirection="column"
                  justifyContent="space-between"
                  sx={{
                    backgroundColor: paletteTokens.bgCard,
                  }}
                >
                  <Box>
                    {/* Header: Title + Status Chip + Actions */}
                    <Box
                      sx={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "flex-start",
                        mb: 1.5,
                      }}
                    >
                      <Box>
                        <Typography
                          component="h2"
                          variant="h6"
                          fontWeight={600}
                          sx={{ wordBreak: "break-word" }}
                        >
                          {plan.title}
                        </Typography>
                        {plan.description && (
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{ mt: 0.5, wordBreak: "break-word" }}
                          >
                            {plan.description}
                          </Typography>
                        )}
                      </Box>

                      {/* Status Chip */}
                      <Box display="flex" alignItems="center" gap={1}>
                        {isCompleted ? (
                          <Chip
                            size="small"
                            label={t("plan_completed")}
                            sx={{
                              backgroundColor: paletteTokens.tint.primary12,
                              color: paletteTokens.primary,
                              fontWeight: 600,
                              fontSize: "12px",
                              border: "none",
                            }}
                          />
                        ) : isClosed ? (
                          <Chip
                            size="small"
                            label={t("plan_closed")}
                            sx={{
                              backgroundColor: paletteTokens.bgCard,
                              color: paletteTokens.textSecondary,
                              border: `1px solid ${paletteTokens.divider}`,
                              fontWeight: 600,
                              fontSize: "12px",
                            }}
                          />
                        ) : (
                          <Chip
                            size="small"
                            label={t("plan_active")}
                            sx={{
                              backgroundColor: paletteTokens.bgCard,
                              color: paletteTokens.textSecondary,
                              border: `1px solid ${paletteTokens.divider}`,
                              fontWeight: 600,
                              fontSize: "12px",
                            }}
                          />
                        )}
                      </Box>
                    </Box>

                    {/* Progress Bar */}
                    <Box sx={{ mt: 2, mb: 2 }}>
                      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.8 }}>
                        <Typography variant="caption" color="text.secondary">
                          {t("plan_progress")}
                        </Typography>
                        <Typography
                          variant="caption"
                          fontWeight={700}
                          sx={{ color: isCompleted ? paletteTokens.success : "text.primary" }}
                        >
                          {pct.toFixed(1)}%
                        </Typography>
                      </Box>
                      <LinearProgress
                        variant="determinate"
                        value={Math.min(100, Math.max(0, pct))}
                        aria-label={`${t("saving_plan_progress")}: ${plan.title}`}
                        aria-valuenow={Math.round(pct)}
                        sx={{
                          height: 8,
                          borderRadius: 4,
                          backgroundColor: paletteTokens.divider,
                          "& .MuiLinearProgress-bar": {
                            backgroundColor: paletteTokens.primary,
                            borderRadius: 4,
                          },
                        }}
                      />
                    </Box>

                    {/* Financial Figures Row */}
                    <Grid
                      container
                      spacing={1.5}
                      sx={{
                        pt: 1.5,
                        pb: 1.5,
                        borderTop: `1px solid ${paletteTokens.divider}`,
                      }}
                    >
                      <Grid item xs={4}>
                        <Typography variant="caption" color="text.secondary" display="block">
                          {t("target_amount")}
                        </Typography>
                        <Typography variant="body2" fontWeight={600}>
                          {formatValue(target)}
                        </Typography>
                      </Grid>

                      <Grid item xs={4}>
                        <Typography variant="caption" color="text.secondary" display="block">
                          {t("amount_saved")}
                        </Typography>
                        <Typography
                          variant="body2"
                          fontWeight={600}
                          sx={{ color: paletteTokens.primary }}
                        >
                          {formatValue(saved)}
                        </Typography>
                      </Grid>

                      <Grid item xs={4}>
                        <Typography variant="caption" color="text.secondary" display="block">
                          {t("remaining_amount")}
                        </Typography>
                        <Typography
                          variant="body2"
                          fontWeight={600}
                          sx={{ color: isCompleted ? paletteTokens.success : "text.primary" }}
                        >
                          {formatValue(remaining)}
                        </Typography>
                      </Grid>
                    </Grid>

                    {/* Dates & Completion Estimate Row */}
                    <Box
                      sx={{
                        pt: 1.5,
                        borderTop: `1px solid ${paletteTokens.divider}`,
                        display: "flex",
                        flexDirection: "column",
                        gap: 0.8,
                      }}
                    >
                      {/* Target Goal Date */}
                      <Box display="flex" alignItems="center" gap={1}>
                        <Typography variant="caption" color="text.secondary">
                          {t("goal_date")}:
                        </Typography>
                        <Typography variant="caption" fontWeight={600}>
                          {plan.goal_date ? dayjs(plan.goal_date).format(dateFormat) : "-"}
                        </Typography>
                      </Box>

                      {/* Estimated Completion Date Forecast */}
                      <Box display="flex" alignItems="center" gap={1} flexWrap="wrap">
                        <Typography variant="caption" color="text.secondary">
                          {t("estimated_completion_date")}:
                        </Typography>
                        {isCompleted ? (
                          <Typography variant="caption" sx={{ color: paletteTokens.primary, fontWeight: 600 }}>
                            {language === "vi" ? "Đã đạt mục tiêu!" : "Goal Achieved!"}
                          </Typography>
                        ) : estimate?.estimated_date ? (
                          <Tooltip title={t("guaranteed_vs_estimate_note")}>
                            <Box display="inline-flex" alignItems="center" gap={0.5} sx={{ cursor: "pointer" }}>
                              <Typography variant="caption" sx={{ color: paletteTokens.warning, fontWeight: 600 }}>
                                {dayjs(estimate.estimated_date).format(dateFormat)}
                              </Typography>
                              <Typography variant="caption" color="text.secondary">
                                (~{estimate.days_remaining} {t("days_left")})
                              </Typography>
                            </Box>
                          </Tooltip>
                        ) : (
                          <Typography variant="caption" color="text.secondary" fontStyle="italic">
                            {estimate?.message || (language === "vi" ? "Chưa đủ dữ liệu đóng góp" : "Insufficient history")}
                          </Typography>
                        )}
                      </Box>
                    </Box>
                  </Box>

                  {/* Card Bottom Actions */}
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      pt: 2,
                      mt: 2,
                      borderTop: `1px solid ${paletteTokens.divider}`,
                      flexWrap: "wrap",
                      gap: 1,
                    }}
                  >
                    <Box display="flex" alignItems="center" gap={1}>
                      {/* Add Contribution button */}
                      <Button
                        size="small"
                        variant="outlined"
                        onClick={() => handleOpenAddContrib(plan)}
                        disabled={isClosed}
                        sx={{
                          borderColor: paletteTokens.controlBorder,
                          color: paletteTokens.textPrimary,
                          "&:hover": {
                            borderColor: paletteTokens.textSecondary,
                            backgroundColor: "rgba(255, 255, 255, 0.04)",
                          },
                        }}
                      >
                        {t("add_contribution")}
                      </Button>

                      {/* View Contribution History button */}
                      <Button
                        size="small"
                        variant="text"
                        onClick={() => handleOpenHistory(plan)}
                        sx={{
                          color: paletteTokens.primary,
                          fontWeight: 600,
                          "&:hover": { backgroundColor: paletteTokens.tint.primary12 },
                        }}
                      >
                        {t("contribution_history")} ({plan.contribution_count || 0})
                      </Button>
                    </Box>

                    {/* Manage Actions */}
                    <Box display="flex" alignItems="center" gap={0.5}>
                      {/* Pause / Activate */}
                      <Tooltip title={plan.active ? t("close_plan") : t("activate_plan")}>
                        <IconButton
                          size="small"
                          aria-label={plan.active ? `${t("pause")}: ${plan.title}` : `${t("resume")}: ${plan.title}`}
                          sx={{ color: grey[500], "&:hover": { color: "#fff" } }}
                          onClick={() =>
                            toggleMutation.mutate({ id: plan.id, active: !plan.active })
                          }
                        >
                          {plan.active ? (
                            <PauseCircleOutlineIcon fontSize="small" />
                          ) : (
                            <PlayArrowIcon fontSize="small" />
                          )}
                        </IconButton>
                      </Tooltip>

                      {/* Edit */}
                      <Tooltip title={t("edit_saving_plan")}>
                        <IconButton
                          size="small"
                          aria-label={`${t("edit")}: ${plan.title}`}
                          sx={{ color: grey[500], "&:hover": { color: "#fff" } }}
                          onClick={() => handleOpenEdit(plan)}
                        >
                          <EditOutlinedIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>

                      {/* Delete */}
                      <Tooltip title={t("delete")}>
                        <IconButton
                          size="small"
                          aria-label={`${t("delete")}: ${plan.title}`}
                          sx={{ color: grey[500], "&:hover": { color: paletteTokens.error } }}
                          onClick={() => setDeleteTargetPlan(plan)}
                        >
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </Box>
                </Box>
              </Grid>
            );
          })}
        </Grid>

        {/* Modal 1: Create / Edit Saving Plan Dialog */}
        <Dialog open={modalOpen} onClose={handleCloseModal} fullWidth maxWidth="xs">
          <DialogTitle sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>{editingPlan ? t("edit_saving_plan") : t("add_saving_plan")}</span>
            <IconButton size="small" onClick={handleCloseModal} aria-label={t("close")} sx={{ color: "text.secondary" }}>
              <CloseIcon fontSize="small" />
            </IconButton>
          </DialogTitle>
          <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: "16px !important" }}>
            {formError && (
              <Alert severity="error" sx={{ borderRadius: 1.5 }}>
                {formError}
              </Alert>
            )}
            <TextField
              label={t("col_name")}
              value={title}
              onChange={(e) => {
                setTitle(e.target.value);
                setFormError("");
              }}
              size="small"
              fullWidth
            />
            <TextField
              label={t("target_amount")}
              value={amount}
              onChange={(e) => {
                setAmount(formatCurrency(e.target.value));
                setFormError("");
              }}
              InputProps={{
                endAdornment: <InputAdornment position="end">đ</InputAdornment>,
              }}
              size="small"
              fullWidth
            />
            <DatePicker
              label={t("goal_date")}
              value={goalDate}
              format={dateFormat}
              onChange={(newValue) => setGoalDate(newValue)}
              slotProps={{ textField: { size: "small", fullWidth: true } }}
            />
            <TextField
              label={t("plan_description")}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              multiline
              rows={2}
              size="small"
              fullWidth
            />
            <Button
              fullWidth
              variant="contained"
              onClick={handleSavePlan}
              disabled={createPlanMutation.isPending || updatePlanMutation.isPending}
              sx={{ height: 42, mt: 1, borderRadius: 2, fontWeight: 600 }}
            >
              {editingPlan ? t("save") : t("add")}
            </Button>
          </DialogContent>
        </Dialog>

        {/* Modal 2: Add Contribution Dialog */}
        <Dialog
          open={!!contributionModalPlan}
          onClose={handleCloseContribModal}
          fullWidth
          maxWidth="xs"
        >
          <DialogTitle sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>{t("add_contribution")}</span>
            <IconButton size="small" onClick={handleCloseContribModal} aria-label={t("close")} sx={{ color: "text.secondary" }}>
              <CloseIcon fontSize="small" />
            </IconButton>
          </DialogTitle>
          <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2, pt: "16px !important" }}>
            {/* Target Goal Summary Note styled in a dark pill */}
            {contributionModalPlan && (
              <Box
                sx={{
                  p: 1.5,
                  borderRadius: 2,
                  backgroundColor: grey[900],
                  border: `1px solid ${paletteTokens.divider}`,
                }}
              >
                <Typography variant="body2" fontWeight={600} noWrap>
                  {contributionModalPlan.title}
                </Typography>
                <Box display="flex" justifyContent="space-between" mt={0.5}>
                  <Typography variant="caption" color="text.secondary">
                    {t("amount_saved")}: {formatValue(Number(contributionModalPlan.amount_saved || 0))}
                  </Typography>
                  <Typography variant="caption" color={paletteTokens.success}>
                    {t("remaining_amount")}: {formatValue(Number(contributionModalPlan.remaining_amount || 0))}
                  </Typography>
                </Box>
              </Box>
            )}

            {contribError && (
              <Alert severity="error" sx={{ borderRadius: 1.5 }}>
                {contribError}
              </Alert>
            )}

            <TextField
              label={t("contribution_amount")}
              value={contribAmount}
              onChange={(e) => {
                setContribAmount(formatCurrency(e.target.value));
                setContribError("");
              }}
              InputProps={{
                endAdornment: <InputAdornment position="end">đ</InputAdornment>,
              }}
              size="small"
              fullWidth
              autoFocus
            />

            <DatePicker
              label={t("contribution_date")}
              value={contribDate}
              format={dateFormat}
              onChange={(val) => setContribDate(val)}
              slotProps={{ textField: { size: "small", fullWidth: true } }}
            />

            <TextField
              label={t("contribution_note")}
              value={contribDesc}
              onChange={(e) => setContribDesc(e.target.value)}
              placeholder="VD: Trích lương tháng 10..."
              size="small"
              fullWidth
            />

            <Button
              fullWidth
              variant="contained"
              onClick={handleSaveContribution}
              disabled={addContribMutation.isPending}
              sx={{ height: 42, mt: 1, borderRadius: 2, fontWeight: 600 }}
            >
              {addContribMutation.isPending ? (
                <CircularProgress size={20} color="inherit" />
              ) : (
                t("add")
              )}
            </Button>
          </DialogContent>
        </Dialog>

        {/* Modal 3: Contribution History Dialog */}
        <Dialog
          open={!!historyModalPlan}
          onClose={() => setHistoryModalPlan(null)}
          fullWidth
          maxWidth="sm"
        >
          <DialogTitle sx={{ fontWeight: 700, pb: 1, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>
              {t("contribution_history")}: {historyModalPlan?.title}
            </span>
            <Chip
              size="small"
              label={`${formatValue(Number(historyModalPlan?.amount_saved || 0))} / ${formatValue(Number(historyModalPlan?.amount || 0))}`}
              sx={{ color: paletteTokens.primary, backgroundColor: paletteTokens.tint.primary12, fontWeight: 600 }}
            />
          </DialogTitle>

          <DialogContent sx={{ pt: 2 }}>
            {/* Inline Add Button in History */}
            {historyModalPlan && historyModalPlan.active && (
              <Box display="flex" justifyContent="flex-end" mb={2}>
                <Button
                  size="small"
                  variant="outlined"
                  startIcon={<AddIcon />}
                  onClick={() => handleOpenAddContrib(historyModalPlan)}
                >
                  {t("add_contribution")}
                </Button>
              </Box>
            )}

            {isContributionsLoading ? (
              <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
                <CircularProgress size={24} />
              </Box>
            ) : planContributions && planContributions.length > 0 ? (
              <TableContainer sx={{ border: `1px solid ${paletteTokens.divider}`, borderRadius: 1.5 }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ color: grey[500], fontSize: "12px" }}>{t("col_date")}</TableCell>
                      <TableCell sx={{ color: grey[500], fontSize: "12px" }}>{t("col_value")}</TableCell>
                      <TableCell sx={{ color: grey[500], fontSize: "12px" }}>{t("contribution_note")}</TableCell>
                      <TableCell align="right" sx={{ color: grey[500], fontSize: "12px" }}>{t("col_actions")}</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {planContributions.map((contrib) => {
                      const isEditingThis = editingContrib?.id === contrib.id;

                      if (isEditingThis) {
                        return (
                          <TableRow key={contrib.id} sx={{ backgroundColor: "rgba(255, 255, 255, 0.03)" }}>
                            <TableCell colSpan={4}>
                              <Box sx={{ display: "flex", flexDirection: "column", gap: 1.5, py: 1 }}>
                                <Box display="flex" gap={1}>
                                  <TextField
                                    size="small"
                                    label={t("col_value")}
                                    value={editContribAmount}
                                    onChange={(e) => setEditContribAmount(formatCurrency(e.target.value))}
                                    InputProps={{
                                      endAdornment: <InputAdornment position="end">đ</InputAdornment>,
                                    }}
                                    sx={{ minWidth: 140 }}
                                  />
                                  <DatePicker
                                    label={t("col_date")}
                                    value={editContribDate}
                                    format={dateFormat}
                                    onChange={(val) => setEditContribDate(val)}
                                    slotProps={{ textField: { size: "small" } }}
                                  />
                                </Box>
                                <TextField
                                  size="small"
                                  label={t("contribution_note")}
                                  value={editContribDesc}
                                  onChange={(e) => setEditContribDesc(e.target.value)}
                                  fullWidth
                                />
                                <Box display="flex" justifyContent="flex-end" gap={1}>
                                  <Button size="small" onClick={() => setEditingContrib(null)} sx={{ color: "text.secondary" }}>
                                    {t("cancel")}
                                  </Button>
                                  <Button
                                    size="small"
                                    variant="contained"
                                    onClick={handleSaveEditContrib}
                                    disabled={updateContribMutation.isPending}
                                  >
                                    {t("save")}
                                  </Button>
                                </Box>
                              </Box>
                            </TableCell>
                          </TableRow>
                        );
                      }

                      return (
                        <TableRow key={contrib.id} hover>
                          <TableCell sx={{ fontSize: "13px" }}>
                            {dayjs(contrib.date).format(dateFormat)}
                          </TableCell>
                          <TableCell sx={{ fontSize: "13px", fontWeight: 600, color: paletteTokens.primary }}>
                            +{formatValue(Number(contrib.amount))}
                          </TableCell>
                          <TableCell sx={{ fontSize: "13px", color: "text.secondary" }}>
                            {contrib.description || "-"}
                          </TableCell>
                          <TableCell align="right">
                            <Tooltip title={t("edit")}>
                              <IconButton
                                size="small"
                                aria-label={t("edit_contribution")}
                                sx={{ color: grey[500], "&:hover": { color: "#fff" } }}
                                onClick={() => handleStartEditContrib(contrib)}
                              >
                                <EditOutlinedIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                            <Tooltip title={t("delete")}>
                              <IconButton
                                size="small"
                                aria-label={t("delete_contribution")}
                                sx={{ color: grey[500], "&:hover": { color: paletteTokens.error } }}
                                onClick={() => setDeleteTargetContrib(contrib)}
                              >
                                <DeleteOutlineIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Box sx={{ py: 4, textAlign: "center" }}>
                <Typography variant="body2" color="text.secondary">
                  {t("no_contributions")}
                </Typography>
              </Box>
            )}
          </DialogContent>
          <DialogActions sx={{ px: 3, pb: 2 }}>
            <Button onClick={() => setHistoryModalPlan(null)}>
              {t("close")}
            </Button>
          </DialogActions>
        </Dialog>

        {/* Modal 4: Delete Plan Confirmation */}
        <Dialog
          open={!!deleteTargetPlan}
          onClose={() => setDeleteTargetPlan(null)}
          maxWidth="xs"
          fullWidth
        >
          <DialogTitle sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>{t("delete")} {t("saving_plans")}</span>
            <IconButton size="small" onClick={() => setDeleteTargetPlan(null)} aria-label={t("close")} sx={{ color: "text.secondary" }}>
              <CloseIcon fontSize="small" />
            </IconButton>
          </DialogTitle>
          <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2.5, pt: "16px !important" }}>
            <Typography variant="body2" color="text.secondary">
              {t("confirm_delete_plan")} (<strong>{deleteTargetPlan?.title}</strong>)
            </Typography>
            <Button
              fullWidth
              variant="contained"
              color="error"
              onClick={() => deleteTargetPlan && deletePlanMutation.mutate(deleteTargetPlan.id)}
              disabled={deletePlanMutation.isPending}
              sx={{ height: 42, borderRadius: 2, fontWeight: 600 }}
            >
              {deletePlanMutation.isPending ? <CircularProgress size={20} color="inherit" /> : t("delete_plan_action")}
            </Button>
          </DialogContent>
        </Dialog>

        {/* Modal 5: Delete Contribution Confirmation */}
        <Dialog
          open={!!deleteTargetContrib}
          onClose={() => setDeleteTargetContrib(null)}
          maxWidth="xs"
          fullWidth
        >
          <DialogTitle sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>{t("delete")} {t("add_contribution")}</span>
            <IconButton size="small" onClick={() => setDeleteTargetContrib(null)} aria-label={t("close")} sx={{ color: "text.secondary" }}>
              <CloseIcon fontSize="small" />
            </IconButton>
          </DialogTitle>
          <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2.5, pt: "16px !important" }}>
            <Typography variant="body2" color="text.secondary">
              {t("confirm_delete_contribution")} (+
              {deleteTargetContrib && formatValue(Number(deleteTargetContrib.amount))})
            </Typography>
            <Button
              fullWidth
              variant="contained"
              color="error"
              onClick={() =>
                historyModalPlan &&
                deleteTargetContrib &&
                deleteContribMutation.mutate({
                  planId: historyModalPlan.id,
                  contribId: deleteTargetContrib.id,
                })
              }
              disabled={deleteContribMutation.isPending}
              sx={{ height: 42, borderRadius: 2, fontWeight: 600 }}
            >
              {deleteContribMutation.isPending ? <CircularProgress size={20} color="inherit" /> : t("delete_contribution")}
            </Button>
          </DialogContent>
        </Dialog>
      </Box>
    </LocalizationProvider>
  );
}
