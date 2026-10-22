import { Box, Button, Chip, Grid, LinearProgress, Skeleton, Stack, Typography } from "@mui/material";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { useBudgets } from "../../hooks/api/useBudgets";
import { useLanguage } from "../../context/LanguageContext";
import { darkTheme, paletteTokens, statusColors, BudgetStatus } from "../../theme";
import { formatValue } from "../../utils/utils";

export default function DashboardBudgetSummary() {
  const { language, t } = useLanguage();
  const { getBudgetSummary, getBudgets } = useBudgets();

  const now = new Date();
  const currentMonth = now.getMonth() + 1;
  const currentYear = now.getFullYear();

  const {
    data: summary,
    isLoading: isSummaryLoading,
  } = useQuery({
    queryKey: ["budget_summary", currentMonth, currentYear],
    queryFn: () => getBudgetSummary(currentMonth, currentYear),
    staleTime: 0,
    refetchOnMount: "always",
  });

  const {
    data: budgets,
    isLoading: isBudgetsLoading,
  } = useQuery({
    queryKey: ["budgets", currentMonth, currentYear],
    queryFn: () => getBudgets(currentMonth, currentYear),
    staleTime: 0,
    refetchOnMount: "always",
  });

  const isLoading = isSummaryLoading || isBudgetsLoading;

  if (isLoading) {
    return (
      <Grid item xs={12}>
        <Box
          border="1px solid"
          borderColor={darkTheme.palette.background.paper}
          borderRadius={2}
          p={3}
          sx={{ backgroundColor: "rgba(255, 255, 255, 0.02)" }}
        >
          <Skeleton variant="text" width={240} height={32} sx={{ mb: 2 }} />
          <Grid container spacing={2}>
            <Grid item xs={12} md={6}>
              <Skeleton variant="rectangular" height={100} sx={{ borderRadius: 1.5 }} />
            </Grid>
            <Grid item xs={12} md={6}>
              <Skeleton variant="rectangular" height={100} sx={{ borderRadius: 1.5 }} />
            </Grid>
          </Grid>
        </Box>
      </Grid>
    );
  }

  const budgetCount = summary?.budget_count ?? 0;
  const totalBudget = Number(summary?.total_budget || 0);
  const budgetedSpent = Number(summary?.total_spent || 0);
  const remainingBudget = Number(summary?.total_remaining || 0);
  const overallPercentage = summary?.overall_percentage ?? 0;

  const totalMonthlyExpenses = Number(summary?.total_monthly_expenses || 0);
  const unbudgetedSpent = Number(summary?.unbudgeted_spent || 0);

  // Filter categories approaching or exceeding limit
  const atRiskBudgets =
    budgets?.filter((b) => b.status === "exceeded" || b.status === "approaching") ?? [];

  return (
    <Grid item xs={12}>
      <Box
        border="1px solid"
        borderColor={darkTheme.palette.background.paper}
        borderRadius={2}
        p={{ xs: 2.5, sm: 3 }}
        sx={{
          backgroundColor: "rgba(255, 255, 255, 0.02)",
          backdropFilter: "blur(10px)",
        }}
      >
        {/* Header */}
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 1.5,
            mb: 2.5,
          }}
        >
          <Stack direction="row" alignItems="center" spacing={1.2}>
            <Typography component="h2" variant="h6" fontWeight={700}>
              {t("budget_summary_widget_title")}
            </Typography>
            <Chip
              size="small"
              label={language === "vi" ? `Tháng ${currentMonth}/${currentYear}` : `${currentMonth}/${currentYear}`}
              sx={{
                fontSize: "12px",
                fontWeight: 600,
                backgroundColor: "rgba(255, 255, 255, 0.06)",
              }}
            />
          </Stack>

          <Button
            component={Link}
            to="/budgets"
            size="small"
            variant="text"
            endIcon={<ArrowForwardIcon fontSize="small" />}
            sx={{
              color: "#48cc90",
              fontWeight: 600,
              "&:hover": { backgroundColor: "rgba(72, 204, 144, 0.1)" },
            }}
          >
            {t("manage_budgets")}
          </Button>
        </Box>

        {/* Empty state: No budgets configured */}
        {budgetCount === 0 ? (
          <Box
            sx={{
              p: 3,
              textAlign: "center",
              borderRadius: 2,
              border: "1px dashed rgba(255, 255, 255, 0.12)",
              backgroundColor: "rgba(255, 255, 255, 0.01)",
            }}
          >
            <Typography variant="body2" color="text.secondary" mb={2}>
              {t("no_budgets_this_month")}
            </Typography>
            <Button
              component={Link}
              to="/budgets"
              variant="contained"
              size="small"
              sx={{ borderRadius: 1.5, fontWeight: 600 }}
            >
              {t("setup_budget_cta")}
            </Button>
          </Box>
        ) : (
          <Grid container spacing={3}>
            {/* Left Column: Spending Coverage & Budget Distinction */}
            <Grid item xs={12} md={6}>
              <Box
                sx={{
                  p: 2.5,
                  borderRadius: 2,
                  backgroundColor: "rgba(0, 0, 0, 0.2)",
                  border: "1px solid rgba(255, 255, 255, 0.06)",
                  height: "100%",
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "space-between",
                }}
              >
                <Box>
                  <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", mb: 1 }}>
                    <Typography variant="caption" color="text.secondary" fontWeight={600} textTransform="uppercase">
                      {t("budgeted_spending")} / {t("total_budget")}
                    </Typography>
                    {(() => {
                      const overallStatus: BudgetStatus =
                        overallPercentage > 100 ? "exceeded" : overallPercentage >= 80 ? "approaching" : "normal";
                      const overallColors = statusColors(overallStatus);
                      return (
                        <Typography
                          variant="body2"
                          fontWeight={700}
                          sx={{ color: overallColors.color }}
                        >
                          {overallPercentage.toFixed(1)}% {t("percentage_used")}
                        </Typography>
                      );
                    })()}
                  </Box>

                  {/* Primary Budget Progress Bar */}
                  {(() => {
                    const overallStatus: BudgetStatus =
                      overallPercentage > 100 ? "exceeded" : overallPercentage >= 80 ? "approaching" : "normal";
                    const overallColors = statusColors(overallStatus);
                    return (
                      <LinearProgress
                        variant="determinate"
                        value={Math.min(100, Math.max(0, overallPercentage))}
                        aria-label={t("budget_progress")}
                        aria-valuenow={Math.round(overallPercentage)}
                        sx={{
                          height: 8,
                          borderRadius: 4,
                          mb: 2,
                          backgroundColor: "rgba(255, 255, 255, 0.36)",
                          "& .MuiLinearProgress-bar": {
                            backgroundColor: overallColors.progressColor,
                            borderRadius: 4,
                          },
                        }}
                      />
                    );
                  })()}

                  {/* Budget breakdown figures */}
                  <Grid container spacing={1.5} sx={{ mb: 2 }}>
                    <Grid item xs={4}>
                      <Typography variant="caption" color="text.secondary" display="block">
                        {t("total_budget")}
                      </Typography>
                      <Typography variant="body2" fontWeight={700}>
                        {formatValue(totalBudget)}
                      </Typography>
                    </Grid>
                    <Grid item xs={4}>
                      <Typography variant="caption" color="text.secondary" display="block">
                        {t("budgeted_spending")}
                      </Typography>
                      <Typography variant="body2" fontWeight={700} color={paletteTokens.error}>
                        {formatValue(budgetedSpent)}
                      </Typography>
                    </Grid>
                    <Grid item xs={4}>
                      <Typography variant="caption" color="text.secondary" display="block">
                        {t("remaining_balance")}
                      </Typography>
                      <Typography
                        variant="body2"
                        fontWeight={700}
                        color={remainingBudget > 0 ? "#48cc90" : paletteTokens.error}
                      >
                        {formatValue(remainingBudget)}
                      </Typography>
                    </Grid>
                  </Grid>
                </Box>

                {/* Clear distinction: Budgeted vs Unbudgeted vs Total Monthly Spending */}
                <Box
                  sx={{
                    pt: 1.5,
                    borderTop: "1px solid rgba(255, 255, 255, 0.08)",
                    display: "flex",
                    flexDirection: "column",
                    gap: 0.8,
                  }}
                >
                  <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <Stack direction="row" alignItems="center" spacing={0.8}>
                      <InfoOutlinedIcon sx={{ fontSize: 15, color: "text.secondary" }} />
                      <Typography variant="caption" color="text.secondary">
                        {t("total_monthly_spending")}:
                      </Typography>
                    </Stack>
                    <Typography variant="body2" fontWeight={700} color="text.primary">
                      {formatValue(totalMonthlyExpenses)}
                    </Typography>
                  </Box>

                  {unbudgetedSpent > 0 ? (
                    <Box
                      sx={{
                        p: 1,
                        px: 1.2,
                        borderRadius: 1.5,
                        backgroundColor: "rgba(255, 255, 255, 0.03)",
                        border: "1px solid rgba(255, 255, 255, 0.05)",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                      }}
                    >
                      <Typography variant="caption" color="text.secondary">
                        {t("unbudgeted_spending")} ({language === "vi" ? "danh mục chưa đặt ngân sách" : "no budget set"}):
                      </Typography>
                      <Typography variant="caption" fontWeight={700} color={paletteTokens.warning}>
                        {formatValue(unbudgetedSpent)}
                      </Typography>
                    </Box>
                  ) : (
                    <Typography variant="caption" color="text.secondary" sx={{ fontStyle: "italic" }}>
                      {language === "vi"
                        ? "100% chi tiêu trong tháng đều thuộc các danh mục có ngân sách."
                        : "100% of monthly spending is covered by budgets."}
                    </Typography>
                  )}
                </Box>
              </Box>
            </Grid>

            {/* Right Column: Categories Close to or Over Limit */}
            <Grid item xs={12} md={6}>
              <Box
                sx={{
                  p: 2.5,
                  borderRadius: 2,
                  backgroundColor: "rgba(0, 0, 0, 0.2)",
                  border: "1px solid rgba(255, 255, 255, 0.06)",
                  height: "100%",
                  display: "flex",
                  flexDirection: "column",
                }}
              >
                <Typography variant="caption" color="text.secondary" fontWeight={600} textTransform="uppercase" mb={1.5}>
                  {atRiskBudgets.length > 0 ? t("categories_at_risk") : t("all_budgets_safe")}
                </Typography>

                {atRiskBudgets.length > 0 ? (
                  <Stack spacing={1.5} sx={{ height: "auto" }}>
                    {atRiskBudgets.map((budget) => {
                      const isExceeded = budget.status === "exceeded";
                      const pct = budget.percentage;
                      const sc = statusColors(budget.status as BudgetStatus);

                      return (
                        <Box
                          key={budget.id}
                          sx={{
                            p: 1.5,
                            borderRadius: 1.5,
                            backgroundColor: "transparent",
                            border: "1px solid rgba(255, 255, 255, 0.08)",
                          }}
                        >
                          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", mb: 0.8 }}>
                            <Stack direction="row" alignItems="center" spacing={1}>
                              <Box
                                sx={{
                                  width: 10,
                                  height: 10,
                                  borderRadius: "50%",
                                  backgroundColor: budget.label.color || "#00863A",
                                }}
                              />
                              <Typography variant="body2" fontWeight={600}>
                                {budget.label.name}
                              </Typography>
                            </Stack>

                            <Chip
                              size="small"
                              icon={
                                isExceeded ? (
                                  <ErrorOutlineIcon sx={{ fontSize: "12px !important", color: `${sc.color} !important` }} />
                                ) : (
                                  <WarningAmberIcon sx={{ fontSize: "12px !important", color: `${sc.color} !important` }} />
                                )
                              }
                              label={isExceeded ? t("status_exceeded") : t("status_approaching")}
                              sx={{
                                height: 20,
                                fontSize: "11px",
                                fontWeight: 700,
                                backgroundColor: sc.bg,
                                color: sc.color,
                              }}
                            />
                          </Box>

                          <LinearProgress
                            variant="determinate"
                            value={Math.min(100, Math.max(0, pct))}
                            aria-label={`${t("budget_progress")}: ${budget.label.name}`}
                            aria-valuenow={Math.round(pct)}
                            sx={{
                              height: 6,
                              borderRadius: 3,
                              mb: 0.8,
                              backgroundColor: "rgba(255, 255, 255, 0.36)",
                              "& .MuiLinearProgress-bar": {
                                backgroundColor: sc.progressColor,
                                borderRadius: 3,
                              },
                            }}
                          />

                          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <Typography variant="caption" color="text.secondary">
                              {formatValue(budget.spent)} / {formatValue(budget.limit)}
                            </Typography>
                            <Typography variant="caption" fontWeight={700} sx={{ color: sc.color }}>
                              {pct.toFixed(0)}%
                            </Typography>
                          </Box>
                        </Box>
                      );
                    })}
                  </Stack>
                ) : (
                  <Box
                    sx={{
                      my: "auto",
                      py: 2,
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "center",
                      textAlign: "center",
                      gap: 1,
                    }}
                  >
                    <Typography variant="body2" fontWeight={600} color="text.secondary">
                      {t("all_budgets_safe")}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" maxWidth={280}>
                      {language === "vi"
                        ? `Tất cả ${budgetCount} danh mục đều đang chi tiêu dưới 80% hạn mức.`
                        : `All ${budgetCount} categories are currently spending below 80% of their limit.`}
                    </Typography>
                  </Box>
                )}
              </Box>
            </Grid>
          </Grid>
        )}
      </Box>
    </Grid>
  );
}
