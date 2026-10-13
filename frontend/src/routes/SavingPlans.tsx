import { useState } from "react";
import {
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  IconButton,
  InputAdornment,
  LinearProgress,
  Stack,
  TextField,
  Tooltip,
  Typography,
  Alert,
  CircularProgress,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import PauseCircleOutlineIcon from "@mui/icons-material/PauseCircleOutline";
import SavingsOutlinedIcon from "@mui/icons-material/SavingsOutlined";
import EventOutlinedIcon from "@mui/icons-material/EventOutlined";
import FlagOutlinedIcon from "@mui/icons-material/FlagOutlined";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import dayjs, { Dayjs } from "dayjs";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSnackbar } from "notistack";
import { useSavingPlans } from "../hooks/api/useSavingPlans";
import { useWallet } from "../hooks/api/useWallet";
import { SavingPlan } from "../models/SavingPlan";
import { useLanguage } from "../context/LanguageContext";
import { formatCurrency, formatValue } from "../utils/utils";
import { darkTheme } from "../theme";

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
  } = useSavingPlans();
  const { getWallet } = useWallet();

  const { data: plans, isLoading, isError, refetch } = useQuery({
    queryKey: ["saving_plans"],
    queryFn: getSavingPlans,
  });

  const { data: wallet } = useQuery({
    queryKey: ["wallet"],
    queryFn: getWallet,
  });

  // Modal states
  const [modalOpen, setModalOpen] = useState(false);
  const [editingPlan, setEditingPlan] = useState<SavingPlan | null>(null);
  const [title, setTitle] = useState("");
  const [amount, setAmount] = useState("");
  const [goalDate, setGoalDate] = useState<Dayjs | null>(null);
  const [description, setDescription] = useState("");
  const [formError, setFormError] = useState("");

  // Delete confirm modal
  const [deleteId, setDeleteId] = useState<number | null>(null);

  // Filter status state
  const [statusFilter, setStatusFilter] = useState<"all" | "active" | "closed">("all");

  const createMutation = useMutation({
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

  const updateMutation = useMutation({
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

  const deleteMutation = useMutation({
    mutationFn: deleteSavingPlan,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["saving_plans"] });
      enqueueSnackbar(t("plan_deleted"), { variant: "success" });
      setDeleteId(null);
    },
    onError: () => {
      enqueueSnackbar(t("err_plan_delete"), { variant: "error" });
      setDeleteId(null);
    },
  });

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

  function handleSave() {
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
      updateMutation.mutate({ id: editingPlan.id, plan: payload });
    } else {
      createMutation.mutate(payload);
    }
  }

  const activePlans = plans?.filter((p) => p.active) ?? [];
  const filteredPlans = plans?.filter((p) => {
    if (statusFilter === "active") return p.active;
    if (statusFilter === "closed") return !p.active;
    return true;
  }) ?? [];
  const totalTargetAmount = activePlans.reduce(
    (acc, curr) => acc + Number(curr.amount || 0),
    0
  );
  const currentWalletAmount = Number(wallet?.current_amount || 0);

  return (
    <Box>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          mb: 4,
          flexWrap: "wrap",
          gap: 2,
        }}
      >
        <Typography component="h1" variant="h4" fontWeight={600}>
          {t("saving_plans")}
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={handleOpenCreate}
          sx={{ borderRadius: 2, px: 2.5 }}
        >
          {t("add_saving_plan")}
        </Button>
      </Box>

      {/* Section 1: Thống kê tổng quan */}
      <Box sx={{ mb: 1.5 }}>
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
          {t("plans_overview")}
        </Typography>
      </Box>

      {/* Summary Cards */}
      <Grid container spacing={2} sx={{ mb: 2 }} alignItems="stretch">
        <Grid item xs={12} sm={4}>
          <Box
            border="1px solid"
            borderColor={darkTheme.palette.background.paper}
            borderRadius={2}
            padding={3}
            height="100%"
          >
            <Typography component="h2" variant="body1" mb={1}>
              {t("active_plans")}
            </Typography>
            <Typography component="span" variant="h5" fontWeight={600}>
              {activePlans.length} / {plans?.length || 0}
            </Typography>
          </Box>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Box
            border="1px solid"
            borderColor={darkTheme.palette.background.paper}
            borderRadius={2}
            padding={3}
            height="100%"
          >
            <Typography component="h2" variant="body1" mb={1}>
              {t("total_target")}
            </Typography>
            <Typography component="span" variant="h5" fontWeight={600}>
              {formatValue(totalTargetAmount)}
            </Typography>
          </Box>
        </Grid>
        <Grid item xs={12} sm={4}>
          <Box
            border="1px solid"
            borderColor={darkTheme.palette.background.paper}
            borderRadius={2}
            padding={3}
            height="100%"
          >
            <Typography component="h2" variant="body1" mb={1}>
              {t("balance")}
            </Typography>
            <Typography component="span" variant="h5" fontWeight={600}>
              {formatValue(currentWalletAmount)}
            </Typography>
          </Box>
        </Grid>
      </Grid>

      <Divider sx={{ my: 4, borderColor: darkTheme.palette.background.paper }} />

      {/* Section 2: Kế hoạch hiện tại & Bộ lọc trạng thái */}
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: { xs: "flex-start", sm: "center" },
          flexDirection: { xs: "column", sm: "row" },
          gap: 2,
          mb: 3,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <Typography component="h2" variant="h5" fontWeight={600}>
            {t("current_plans")}
          </Typography>
          <Chip
            label={filteredPlans.length}
            size="small"
            sx={{
              borderRadius: "10px",
              backgroundColor: "rgba(255, 255, 255, 0.08)",
              color: "#fff",
              fontWeight: 600,
              fontSize: "12px",
              height: 24,
            }}
          />
        </Box>

        {/* Filter Status Buttons */}
        {plans && plans.length > 0 && (
          <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", gap: 1 }}>
            <Button
              size="small"
              variant={statusFilter === "all" ? "contained" : "outlined"}
              onClick={() => setStatusFilter("all")}
              sx={{
                borderRadius: 2,
                px: 1.8,
                py: 0.5,
                fontSize: "13px",
                textTransform: "none",
                ...(statusFilter === "all"
                  ? {
                      backgroundColor: "rgba(0, 134, 58, 0.25)",
                      borderColor: "rgba(72, 204, 144, 0.4)",
                      color: "#48cc90",
                      "&:hover": { backgroundColor: "rgba(0, 134, 58, 0.35)" },
                    }
                  : {
                      borderColor: darkTheme.palette.background.paper,
                      color: "text.secondary",
                      "&:hover": { borderColor: "rgba(255, 255, 255, 0.2)", color: "#fff" },
                    }),
              }}
            >
              {t("all")} ({plans.length})
            </Button>
            <Button
              size="small"
              variant={statusFilter === "active" ? "contained" : "outlined"}
              onClick={() => setStatusFilter("active")}
              sx={{
                borderRadius: 2,
                px: 1.8,
                py: 0.5,
                fontSize: "13px",
                textTransform: "none",
                ...(statusFilter === "active"
                  ? {
                      backgroundColor: "rgba(0, 134, 58, 0.25)",
                      borderColor: "rgba(72, 204, 144, 0.4)",
                      color: "#48cc90",
                      "&:hover": { backgroundColor: "rgba(0, 134, 58, 0.35)" },
                    }
                  : {
                      borderColor: darkTheme.palette.background.paper,
                      color: "text.secondary",
                      "&:hover": { borderColor: "rgba(255, 255, 255, 0.2)", color: "#fff" },
                    }),
              }}
            >
              {t("plan_active")} ({activePlans.length})
            </Button>
            <Button
              size="small"
              variant={statusFilter === "closed" ? "contained" : "outlined"}
              onClick={() => setStatusFilter("closed")}
              sx={{
                borderRadius: 2,
                px: 1.8,
                py: 0.5,
                fontSize: "13px",
                textTransform: "none",
                ...(statusFilter === "closed"
                  ? {
                      backgroundColor: "rgba(0, 134, 58, 0.25)",
                      borderColor: "rgba(72, 204, 144, 0.4)",
                      color: "#48cc90",
                      "&:hover": { backgroundColor: "rgba(0, 134, 58, 0.35)" },
                    }
                  : {
                      borderColor: darkTheme.palette.background.paper,
                      color: "text.secondary",
                      "&:hover": { borderColor: "rgba(255, 255, 255, 0.2)", color: "#fff" },
                    }),
              }}
            >
              {t("plan_closed")} ({plans.length - activePlans.length})
            </Button>
          </Stack>
        )}
      </Box>

      {/* Loading & Error States */}
      {isLoading && (
        <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
          <CircularProgress />
        </Box>
      )}

      {isError && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => refetch()}>
          {t("unable_to_load_data")}
        </Alert>
      )}

      {/* Empty State */}
      {!isLoading && plans && plans.length === 0 && (
        <Box
          border="1px dashed"
          borderColor={darkTheme.palette.background.paper}
          borderRadius={2}
          textAlign="center"
          py={8}
          px={3}
        >
          <SavingsOutlinedIcon sx={{ fontSize: 60, color: "text.secondary", mb: 2 }} />
          <Typography variant="h6" fontWeight={600} gutterBottom>
            {t("no_saving_plans")}
          </Typography>
          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            onClick={handleOpenCreate}
            sx={{ mt: 2, borderRadius: 2 }}
          >
            {t("add_saving_plan")}
          </Button>
        </Box>
      )}

      {/* No plans matching current filter */}
      {!isLoading && plans && plans.length > 0 && filteredPlans.length === 0 && (
        <Box
          border="1px dashed"
          borderColor={darkTheme.palette.background.paper}
          borderRadius={2}
          textAlign="center"
          py={6}
          px={3}
        >
          <Typography variant="body2" color="text.secondary">
            {t("no_plans_in_status")}
          </Typography>
        </Box>
      )}

      {/* Plans Grid */}
      <Grid container spacing={2}>
        {filteredPlans.map((plan) => {
          const target = Number(plan.amount);
          const percent =
            target > 0
              ? Math.min(100, Math.round((currentWalletAmount / target) * 100))
              : 0;

          return (
            <Grid item xs={12} sm={6} md={4} key={plan.id}>
              <Box
                border="1px solid"
                borderColor={darkTheme.palette.background.paper}
                borderRadius={2}
                height="100%"
                display="flex"
                flexDirection="column"
                justifyContent="space-between"
              >
                <Box padding={3}>
                  <Box
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      mb: 2,
                    }}
                  >
                    <Typography component="h2" variant="h6" fontWeight={600} sx={{ wordBreak: "break-word" }}>
                      {plan.title}
                    </Typography>
                    <Chip
                      label={plan.active ? t("plan_active") : t("plan_closed")}
                      size="small"
                      variant="outlined"
                      sx={{
                        ml: 1,
                        flexShrink: 0,
                        borderColor: darkTheme.palette.background.paper,
                        color: plan.active ? "#fff" : "text.secondary",
                      }}
                    />
                  </Box>

                  {plan.description && (
                    <Typography
                      variant="body2"
                      color="text.secondary"
                      sx={{ mb: 2, minHeight: 36, wordBreak: "break-word" }}
                    >
                      {plan.description}
                    </Typography>
                  )}

                  <Box sx={{ mb: 2 }}>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 0.5 }}>
                      <FlagOutlinedIcon fontSize="small" sx={{ color: "text.secondary" }} />
                      <Typography variant="body2" color="text.secondary">
                        {t("target_amount")}:
                      </Typography>
                      <Typography component="span" variant="body1" fontWeight={600}>
                        {formatValue(target)}
                      </Typography>
                    </Box>

                    {plan.goal_date && (
                      <Box sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}>
                        <EventOutlinedIcon fontSize="small" sx={{ color: "text.secondary" }} />
                        <Typography variant="body2" color="text.secondary">
                          {t("goal_date")}:
                        </Typography>
                        <Typography variant="body2">
                          {dayjs(plan.goal_date).format(dateFormat)}
                        </Typography>
                      </Box>
                    )}
                  </Box>

                  {/* Wallet progress bar */}
                  <Box sx={{ mt: 2 }}>
                    <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.5 }}>
                      <Typography variant="caption" color="text.secondary">
                        {t("plan_progress")} ({t("balance")})
                      </Typography>
                      <Typography variant="caption" fontWeight={600}>
                        {percent}%
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={percent}
                      sx={{
                        height: 8,
                        borderRadius: 4,
                        backgroundColor: "rgba(255, 255, 255, 0.08)",
                        "& .MuiLinearProgress-bar": {
                          backgroundColor: "#00863A",
                          borderRadius: 4,
                        },
                      }}
                    />
                  </Box>
                </Box>

                <Box
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    px: 3,
                    py: 1.5,
                    borderTop: "1px solid",
                    borderColor: darkTheme.palette.background.paper,
                  }}
                >
                  <Tooltip title={plan.active ? t("close_plan") : t("activate_plan")}>
                    <IconButton
                      size="small"
                      color={plan.active ? "warning" : "success"}
                      onClick={() =>
                        toggleMutation.mutate({ id: plan.id, active: !plan.active })
                      }
                    >
                      {plan.active ? (
                        <PauseCircleOutlineIcon fontSize="small" />
                      ) : (
                        <CheckCircleOutlineIcon fontSize="small" />
                      )}
                    </IconButton>
                  </Tooltip>

                  <Stack direction="row" spacing={1}>
                    <Tooltip title={t("edit_saving_plan")}>
                      <IconButton
                        size="small"
                        color="inherit"
                        onClick={() => handleOpenEdit(plan)}
                      >
                        <EditOutlinedIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title={t("delete")}>
                      <IconButton
                        size="small"
                        color="error"
                        onClick={() => setDeleteId(plan.id)}
                      >
                        <DeleteOutlineIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </Stack>
                </Box>
              </Box>
            </Grid>
          );
        })}
      </Grid>

      {/* Add / Edit Dialog */}
      <Dialog
        open={modalOpen}
        onClose={handleCloseModal}
        maxWidth="sm"
        fullWidth
        PaperProps={{
          sx: {
            backgroundColor: "#121316",
            backgroundImage: "none",
            borderRadius: 3,
            border: "1px solid rgba(255, 255, 255, 0.1)",
            boxShadow: "0 16px 48px rgba(0, 0, 0, 0.7)",
            color: "#fff",
          },
        }}
      >
        <DialogTitle sx={{ fontWeight: 600, fontSize: "1.2rem", pt: 3, px: 3, pb: 1 }}>
          {editingPlan ? t("edit_saving_plan") : t("add_saving_plan")}
        </DialogTitle>
        <DialogContent sx={{ display: "flex", flexDirection: "column", gap: 2.2, px: 3, pt: "12px !important" }}>
          {formError && <Alert severity="error">{formError}</Alert>}

          <TextField
            label={t("title")}
            fullWidth
            size="small"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            inputProps={{ maxLength: 50 }}
            autoFocus
            sx={{
              "& .MuiOutlinedInput-root": {
                backgroundColor: "rgba(255, 255, 255, 0.03)",
                borderRadius: 2,
              },
            }}
          />

          <TextField
            label={t("target_amount")}
            fullWidth
            size="small"
            value={amount}
            onChange={(e) => setAmount(formatCurrency(e.target.value))}
            InputProps={{
              endAdornment: <InputAdornment position="end">đ</InputAdornment>,
            }}
            sx={{
              "& .MuiOutlinedInput-root": {
                backgroundColor: "rgba(255, 255, 255, 0.03)",
                borderRadius: 2,
              },
            }}
          />

          <LocalizationProvider dateAdapter={AdapterDayjs} adapterLocale={language}>
            <DatePicker
              label={t("goal_date")}
              format={dateFormat}
              value={goalDate}
              onChange={(newVal) => setGoalDate(newVal)}
              slotProps={{
                textField: {
                  fullWidth: true,
                  size: "small",
                  sx: {
                    "& .MuiOutlinedInput-root": {
                      backgroundColor: "rgba(255, 255, 255, 0.03)",
                      borderRadius: 2,
                    },
                  },
                },
              }}
            />
          </LocalizationProvider>

          <TextField
            label={t("plan_description")}
            fullWidth
            size="small"
            multiline
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            inputProps={{ maxLength: 200 }}
            sx={{
              "& .MuiOutlinedInput-root": {
                backgroundColor: "rgba(255, 255, 255, 0.03)",
                borderRadius: 2,
              },
            }}
          />
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 3, pt: 1, gap: 1.5 }}>
          <Button
            onClick={handleCloseModal}
            variant="outlined"
            size="medium"
            sx={{
              color: "text.secondary",
              borderColor: "rgba(255, 255, 255, 0.15)",
              borderRadius: 2,
              px: 2.5,
              "&:hover": {
                borderColor: "rgba(255, 255, 255, 0.3)",
                backgroundColor: "rgba(255, 255, 255, 0.05)",
                color: "#fff",
              },
            }}
          >
            {t("cancel")}
          </Button>
          <Button
            onClick={handleSave}
            variant="contained"
            size="medium"
            disabled={createMutation.isPending || updateMutation.isPending}
            sx={{
              backgroundColor: "#00863A",
              borderRadius: 2,
              px: 3,
              fontWeight: 600,
              "&:hover": {
                backgroundColor: "#006b2e",
              },
            }}
          >
            {t("save")}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Confirm Delete Dialog */}
      <Dialog
        open={deleteId !== null}
        onClose={() => setDeleteId(null)}
        maxWidth="xs"
        fullWidth
        PaperProps={{
          sx: {
            backgroundColor: "#121316",
            backgroundImage: "none",
            borderRadius: 3,
            border: "1px solid rgba(255, 255, 255, 0.1)",
            boxShadow: "0 16px 48px rgba(0, 0, 0, 0.7)",
            color: "#fff",
          },
        }}
      >
        <DialogTitle sx={{ fontWeight: 600, pt: 2.5, px: 3 }}>
          {t("delete")}
        </DialogTitle>
        <DialogContent sx={{ px: 3, py: 1.5 }}>
          <Typography variant="body2" color="text.secondary">
            {t("confirm_delete_plan")}
          </Typography>
        </DialogContent>
        <DialogActions sx={{ px: 3, pb: 2.5, pt: 1, gap: 1 }}>
          <Button
            onClick={() => setDeleteId(null)}
            variant="outlined"
            size="small"
            sx={{
              color: "text.secondary",
              borderColor: "rgba(255, 255, 255, 0.15)",
              borderRadius: 2,
              "&:hover": {
                borderColor: "rgba(255, 255, 255, 0.3)",
                backgroundColor: "rgba(255, 255, 255, 0.05)",
              },
            }}
          >
            {t("cancel")}
          </Button>
          <Button
            onClick={() => {
              if (deleteId) deleteMutation.mutate(deleteId);
            }}
            color="error"
            variant="contained"
            size="small"
            sx={{ borderRadius: 2, px: 2.5 }}
          >
            {t("delete")}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
