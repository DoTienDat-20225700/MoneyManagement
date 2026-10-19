import { useState, useEffect } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  IconButton,
  InputAdornment,
  Radio,
  RadioGroup,
  TextField,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import BalanceIcon from "@mui/icons-material/Balance";
import StarIcon from "@mui/icons-material/Star";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useSnackbar } from "notistack";
import { useLanguage } from "../../context/LanguageContext";
import { useBudgets } from "../../hooks/api/useBudgets";
import { RebalanceSuggestion } from "../../models/CategoryBudget";
import { formatCurrency, formatValue } from "../../utils/utils";

interface RebalanceSuggestionDialogProps {
  open: boolean;
  onClose: () => void;
  targetLabelId: number;
  targetLabelName: string;
  deficitAmount: number;
  month: number;
  year: number;
  onSuccess?: () => void;
}

export default function RebalanceSuggestionDialog({
  open,
  onClose,
  targetLabelId,
  targetLabelName,
  deficitAmount,
  month,
  year,
  onSuccess,
}: RebalanceSuggestionDialogProps) {
  const { t } = useLanguage();
  const queryClient = useQueryClient();
  const { enqueueSnackbar } = useSnackbar();
  const { getRebalanceSuggestions, rebalanceBudget } = useBudgets();

  const [selectedSourceId, setSelectedSourceId] = useState<number | null>(null);
  const [transferAmountInput, setTransferAmountInput] = useState<string>("");
  const [inputError, setInputError] = useState<string>("");

  // Query suggestions for this target category and month/year
  const { data: suggestions, isLoading } = useQuery({
    queryKey: ["rebalance_suggestions", targetLabelId, month, year],
    queryFn: () =>
      getRebalanceSuggestions({
        label_id: targetLabelId,
        month,
        year,
      }),
    enabled: open && !!targetLabelId,
  });

  // Automatically select the top recommendation (which prioritizes non-essential)
  useEffect(() => {
    if (suggestions && suggestions.length > 0) {
      const top = suggestions[0];
      setSelectedSourceId(top.label_id);
      const defaultAmount = Math.min(deficitAmount, Number(top.available_rebalance));
      setTransferAmountInput(formatCurrency(String(Math.round(defaultAmount))));
    } else {
      setSelectedSourceId(null);
      setTransferAmountInput(formatCurrency(String(Math.round(deficitAmount))));
    }
    setInputError("");
  }, [suggestions, deficitAmount, open]);

  const selectedSuggestion = suggestions?.find(
    (s) => s.label_id === selectedSourceId
  );

  const { mutateAsync, isPending } = useMutation({
    mutationFn: rebalanceBudget,
    onSuccess: () => {
      enqueueSnackbar(t("rebalance_success"), {
        variant: "success",
        autoHideDuration: 3000,
        anchorOrigin: { horizontal: "right", vertical: "bottom" },
      });
      queryClient.invalidateQueries({ queryKey: ["budgets"] });
      queryClient.invalidateQueries({ queryKey: ["budget_summary"] });
      if (onSuccess) onSuccess();
      onClose();
    },
    onError: (err: any) => {
      const msg =
        err?.response?.data?.error ||
        err?.response?.data?.message ||
        t("rebalance_err");
      enqueueSnackbar(msg, {
        variant: "error",
        autoHideDuration: 4000,
        anchorOrigin: { horizontal: "right", vertical: "bottom" },
      });
    },
  });

  const handleConfirm = async () => {
    if (!selectedSourceId) {
      setInputError(t("rebalance_source_category"));
      return;
    }

    const cleanAmountStr = transferAmountInput.replace(/\./g, "").replace(/,/g, "").trim();
    const parsedAmount = Number(cleanAmountStr);

    if (!parsedAmount || isNaN(parsedAmount) || parsedAmount <= 0) {
      setInputError(t("err_amount_positive"));
      return;
    }

    if (
      selectedSuggestion &&
      parsedAmount > Number(selectedSuggestion.available_rebalance)
    ) {
      setInputError(
        `${t("rebalance_available")}: ${formatValue(
          selectedSuggestion.available_rebalance
        )}`
      );
      return;
    }

    setInputError("");
    await mutateAsync({
      from_label_id: selectedSourceId,
      to_label_id: targetLabelId,
      amount: parsedAmount,
      month,
      year,
    });
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          backgroundColor: "#121212",
          backgroundImage: "none",
          borderRadius: 3,
          border: "1px solid rgba(255, 255, 255, 0.1)",
        },
      }}
    >
      <DialogTitle
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          pb: 1,
        }}
      >
        <Box sx={{ display: "flex", alignItems: "center", gap: 1.5 }}>
          <BalanceIcon sx={{ color: "warning.main", fontSize: 26 }} />
          <Typography variant="h6" fontWeight={600}>
            {t("rebalance_dialog_title")}
          </Typography>
        </Box>
        <IconButton
          size="small"
          onClick={onClose}
          aria-label={t("close")}
          sx={{ color: "text.secondary" }}
        >
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ pt: 1 }}>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2.5 }}>
          {t("rebalance_dialog_desc")}
        </Typography>

        {/* Deficit card */}
        <Box
          sx={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            p: 2,
            mb: 3,
            borderRadius: 2,
            backgroundColor: "rgba(239, 68, 68, 0.08)",
            border: "1px solid rgba(239, 68, 68, 0.25)",
          }}
        >
          <Box>
            <Typography variant="caption" color="text.secondary" display="block">
              {t("rebalance_target_category")}
            </Typography>
            <Typography variant="subtitle1" fontWeight={600} color="#EF4444">
              {targetLabelName}
            </Typography>
          </Box>
          <Box sx={{ textAlign: "right" }}>
            <Typography variant="caption" color="text.secondary" display="block">
              {t("rebalance_deficit_amount")}
            </Typography>
            <Typography variant="subtitle1" fontWeight={700} color="#EF4444">
              +{formatValue(deficitAmount)} đ
            </Typography>
          </Box>
        </Box>

        {/* Suggestions list */}
        <Typography variant="subtitle2" sx={{ mb: 1.5, fontWeight: 600 }}>
          {t("rebalance_source_category")}
        </Typography>

        {isLoading ? (
          <Box sx={{ display: "flex", justifyContent: "center", py: 4 }}>
            <CircularProgress size={30} />
          </Box>
        ) : !suggestions || suggestions.length === 0 ? (
          <Alert severity="info" sx={{ mb: 2 }}>
            {t("no_rebalance_suggestions")}
          </Alert>
        ) : (
          <FormControl component="fieldset" fullWidth sx={{ mb: 2 }}>
            <RadioGroup
              value={selectedSourceId}
              onChange={(e) => {
                const id = Number(e.target.value);
                setSelectedSourceId(id);
                const found = suggestions.find((s) => s.label_id === id);
                if (found) {
                  const amt = Math.min(deficitAmount, Number(found.available_rebalance));
                  setTransferAmountInput(
                    formatCurrency(String(Math.round(amt)))
                  );
                }
              }}
            >
              {suggestions.map((item: RebalanceSuggestion) => {
                const isSelected = selectedSourceId === item.label_id;
                return (
                  <Box
                    key={item.label_id}
                    onClick={() => {
                      setSelectedSourceId(item.label_id);
                      const amt = Math.min(
                        deficitAmount,
                        Number(item.available_rebalance)
                      );
                      setTransferAmountInput(
                        formatCurrency(String(Math.round(amt)))
                      );
                    }}
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      p: 1.5,
                      mb: 1.2,
                      borderRadius: 2,
                      cursor: "pointer",
                      border: "1px solid",
                      borderColor: isSelected
                        ? "primary.main"
                        : "rgba(255, 255, 255, 0.08)",
                      backgroundColor: isSelected
                        ? "rgba(144, 202, 249, 0.08)"
                        : "rgba(255, 255, 255, 0.02)",
                      transition: "all 0.15s ease",
                      "&:hover": {
                        backgroundColor: "rgba(255, 255, 255, 0.05)",
                      },
                    }}
                  >
                    <Box
                      sx={{
                        display: "flex",
                        alignItems: "center",
                        gap: 1.5,
                      }}
                    >
                      <Radio
                        checked={isSelected}
                        value={item.label_id}
                        size="small"
                        sx={{ p: 0.5 }}
                      />
                      <Box
                        sx={{
                          width: 12,
                          height: 12,
                          borderRadius: "50%",
                          backgroundColor: item.label_color || "#3B82F6",
                        }}
                      />
                      <Box>
                        <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                          <Typography variant="body2" fontWeight={600}>
                            {item.label_name}
                          </Typography>
                          {item.is_non_essential && (
                            <Chip
                              icon={<StarIcon sx={{ "&&": { fontSize: 13, color: "#F59E0B" } }} />}
                              label={t("rebalance_non_essential_badge")}
                              size="small"
                              sx={{
                                height: 20,
                                fontSize: "11px",
                                backgroundColor: "rgba(245, 158, 11, 0.12)",
                                color: "#F59E0B",
                                border: "1px solid rgba(245, 158, 11, 0.3)",
                              }}
                            />
                          )}
                        </Box>
                        <Typography variant="caption" color="text.secondary">
                          {t("rebalance_spent_ratio")}: {item.spent_percentage}% (
                          {formatValue(item.spent)} / {formatValue(item.amount)} đ)
                        </Typography>
                      </Box>
                    </Box>

                    <Box sx={{ textAlign: "right" }}>
                      <Typography variant="caption" color="text.secondary" display="block">
                        {t("rebalance_available")}
                      </Typography>
                      <Typography variant="body2" fontWeight={600} color="success.main">
                        {formatValue(item.available_rebalance)}
                      </Typography>
                    </Box>
                  </Box>
                );
              })}
            </RadioGroup>
          </FormControl>
        )}

        {/* Transfer amount field */}
        {suggestions && suggestions.length > 0 && (
          <TextField
            fullWidth
            label={t("rebalance_amount_label")}
            size="small"
            value={transferAmountInput}
            error={!!inputError}
            helperText={inputError}
            onChange={(e) => {
              setTransferAmountInput(formatCurrency(e.target.value));
              setInputError("");
            }}
            InputProps={{
              endAdornment: <InputAdornment position="end">đ</InputAdornment>,
            }}
            sx={{ mt: 1 }}
          />
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2.5 }}>
        <Button onClick={onClose} variant="outlined" color="inherit">
          {t("rebalance_cancel_btn")}
        </Button>
        {suggestions && suggestions.length > 0 && (
          <Button
            onClick={handleConfirm}
            variant="contained"
            color="primary"
            disabled={isPending || !selectedSourceId}
            startIcon={isPending ? <CircularProgress size={16} color="inherit" /> : null}
          >
            {isPending ? t("loading") : t("rebalance_confirm_btn")}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
}
