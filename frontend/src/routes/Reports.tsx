import { useContext, useMemo, useState, useEffect } from "react";
import FileUploadIcon from "@mui/icons-material/FileUpload";
import PrintOutlinedIcon from "@mui/icons-material/PrintOutlined";
import SearchIcon from "@mui/icons-material/Search";
import ClearIcon from "@mui/icons-material/Clear";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  FormControl,
  Grid,
  IconButton,
  InputAdornment,
  InputLabel,
  MenuItem,
  Select,
  Skeleton,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import { grey } from "@mui/material/colors";
import { useQuery } from "@tanstack/react-query";
import { useSnackbar } from "notistack";
import Chart from "react-apexcharts";
import { ApexOptions } from "apexcharts";
import dayjs from "dayjs";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { DatePicker } from "@mui/x-date-pickers/DatePicker";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";

import AuthContext from "../context/AuthContext";
import { useLanguage } from "../context/LanguageContext";
import { useReports } from "../hooks/api/useReports";
import { useLabels } from "../hooks/api/useLabels";
import { formatValue } from "../utils/utils";
import { paletteTokens } from "../theme";
import { CustomLabel } from "../models/CustomLabel";
import { usePrefersReducedMotion } from "../hooks/usePrefersReducedMotion";
import LatestTransactions from "../components/LatestTransactions";
import CashFlowForecast from "../components/reports/CashFlowForecast";

type PresetRange =
  | "this_month"
  | "last_month"
  | "last_30_days"
  | "this_quarter"
  | "this_year"
  | "custom";

function formatDateStr(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function getPresetDates(preset: PresetRange): { start: string; end: string } {
  const now = new Date();
  const y = now.getFullYear();
  const m = now.getMonth();

  switch (preset) {
    case "this_month": {
      const start = new Date(y, m, 1);
      const end = new Date(y, m + 1, 0);
      return { start: formatDateStr(start), end: formatDateStr(end) };
    }
    case "last_month": {
      const start = new Date(y, m - 1, 1);
      const end = new Date(y, m, 0);
      return { start: formatDateStr(start), end: formatDateStr(end) };
    }
    case "last_30_days": {
      const end = new Date();
      const start = new Date();
      start.setDate(end.getDate() - 29);
      return { start: formatDateStr(start), end: formatDateStr(end) };
    }
    case "this_quarter": {
      const qStartMonth = Math.floor(m / 3) * 3;
      const start = new Date(y, qStartMonth, 1);
      const end = new Date(y, qStartMonth + 3, 0);
      return { start: formatDateStr(start), end: formatDateStr(end) };
    }
    case "this_year": {
      const start = new Date(y, 0, 1);
      const end = new Date(y, 11, 31);
      return { start: formatDateStr(start), end: formatDateStr(end) };
    }
    default: {
      const start = new Date(y, m, 1);
      const end = new Date(y, m + 1, 0);
      return { start: formatDateStr(start), end: formatDateStr(end) };
    }
  }
}

export default function Reports() {
  const { user } = useContext(AuthContext);
  const { language, dateFormat, t } = useLanguage();
  const prefersReducedMotion = usePrefersReducedMotion();
  const { enqueueSnackbar } = useSnackbar();
  const { getReportSummary, getReportTransactions, downloadReportExcel } = useReports();
  const { getLabels } = useLabels();

  // Filters state
  const initialPresetDates = getPresetDates("this_month");
  const [preset, setPreset] = useState<PresetRange>("this_month");
  const [startDate, setStartDate] = useState<string>(initialPresetDates.start);
  const [endDate, setEndDate] = useState<string>(initialPresetDates.end);
  const [transactionType, setTransactionType] = useState<"ALL" | "EXPENSE" | "EARNING">("ALL");
  const [selectedLabelId, setSelectedLabelId] = useState<number | "all">("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [isExporting, setIsExporting] = useState(false);
  const [activeTab, setActiveTab] = useState<"history" | "forecast">("history");

  // Debounce search term for transactions list
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(searchTerm);
    }, 300);
    return () => clearTimeout(handler);
  }, [searchTerm]);

  // Date validation
  const isDateInvalid = useMemo(() => {
    return Boolean(startDate && endDate && startDate > endDate);
  }, [startDate, endDate]);

  // Handler for preset change
  const handlePresetChange = (newPreset: PresetRange) => {
    setPreset(newPreset);
    if (newPreset !== "custom") {
      const dates = getPresetDates(newPreset);
      setStartDate(dates.start);
      setEndDate(dates.end);
    }
  };

  // Labels query
  const { data: labels } = useQuery({
    queryKey: ["labels"],
    queryFn: getLabels,
  });

  // Query summary
  const {
    data: reportSummary,
    isLoading: isSummaryLoading,
    isError: isSummaryError,
  } = useQuery({
    queryKey: ["report_summary", startDate, endDate, transactionType, selectedLabelId],
    queryFn: () =>
      getReportSummary({
        start_date: startDate,
        end_date: endDate,
        type: transactionType,
        label_id: selectedLabelId === "all" ? undefined : selectedLabelId,
      }),
    enabled: !isDateInvalid,
  });

  // Query transactions list
  const {
    data: transactionsList,
    isLoading: isTxLoading,
  } = useQuery({
    queryKey: ["report_transactions", startDate, endDate, transactionType, selectedLabelId, debouncedSearch],
    queryFn: () =>
      getReportTransactions({
        start_date: startDate,
        end_date: endDate,
        type: transactionType,
        label_id: selectedLabelId === "all" ? undefined : selectedLabelId,
        search: debouncedSearch,
      }),
    enabled: !isDateInvalid,
  });

  // Export Excel (.xlsx) handler
  const handleExportExcel = async () => {
    try {
      setIsExporting(true);
      await downloadReportExcel({
        start_date: startDate,
        end_date: endDate,
        type: transactionType,
        label_id: selectedLabelId === "all" ? undefined : selectedLabelId,
      });
      enqueueSnackbar(
        language === "vi" ? "Xuất báo cáo Excel thành công!" : "Excel report exported successfully!",
        { variant: "success", autoHideDuration: 3000 }
      );
    } catch (err) {
      console.error(err);
      enqueueSnackbar(
        language === "vi" ? "Lỗi khi xuất báo cáo Excel." : "Failed to export Excel report.",
        { variant: "error", autoHideDuration: 3000 }
      );
    } finally {
      setIsExporting(false);
    }
  };

  // Print PDF handler
  const handlePrint = () => {
    window.print();
  };



  // Numbers parsing
  const totalIncome = Number(reportSummary?.summary?.total_income || 0);
  const totalExpense = Number(reportSummary?.summary?.total_expense || 0);
  const netCashFlow = Number(reportSummary?.summary?.net_cash_flow || 0);
  const avgDailySpending = Number(reportSummary?.summary?.average_daily_spending || 0);

  const incomeChangePct = reportSummary?.comparison?.income_change_percentage ?? 0;
  const expenseChangePct = reportSummary?.comparison?.expense_change_percentage ?? 0;
  const netCashFlowChangePct = reportSummary?.comparison?.net_cash_flow_change_percentage ?? 0;

  // Chart 1: Monthly Trends (Column chart) matching CurrentMonthChart style
  const monthlyTrendsChart = useMemo<{ series: ApexAxisChartSeries; options: ApexOptions }>(() => {
    const trends = reportSummary?.monthly_trends || [];
    const categories = trends.map((t) => t.label);
    const incomeData = trends.map((t) => Number(t.income));
    const expenseData = trends.map((t) => Number(t.expense));

    return {
      series: [
        {
          name: language === "vi" ? "Thu nhập" : "Income",
          data: incomeData,
        },
        {
          name: language === "vi" ? "Chi tiêu" : "Expense",
          data: expenseData,
        },
      ],
      options: {
        chart: {
          id: "monthly-trends-bar",
          type: "bar",
          toolbar: { show: false },
          animations: { enabled: !prefersReducedMotion },
        },
        colors: [paletteTokens.primary, paletteTokens.chart.expense],
        plotOptions: {
          bar: {
            horizontal: false,
            columnWidth: "55%",
            borderRadius: 2,
          },
        },
        dataLabels: { enabled: false },
        stroke: { show: true, width: 2, colors: ["transparent"] },
        xaxis: {
          categories,
          labels: {
            style: { colors: paletteTokens.textSecondary, fontSize: "12px", fontFamily: "Inter" },
          },
        },
        yaxis: {
          tickAmount: 5,
          labels: {
            style: { colors: paletteTokens.textSecondary, fontFamily: "Inter" },
            formatter: (val: number) => formatValue(val),
          },
        },
        grid: {
          show: true,
          borderColor: paletteTokens.divider,
        },
        tooltip: {
          theme: "dark",
          y: {
            formatter: (val: number) => formatValue(val),
          },
        },
        legend: {
          show: true,
          position: "top",
          horizontalAlign: "right",
          labels: { colors: paletteTokens.textSecondary },
          fontFamily: "Inter",
        },
      },
    };
  }, [reportSummary?.monthly_trends, language, prefersReducedMotion]);

  // Chart 2: Category Breakdown (Pie chart with Palette v2 top 5 + "Khác")
  const categoryBreakdownChart = useMemo<{ series: number[]; options: ApexOptions }>(() => {
    const breakdown = reportSummary?.category_breakdown || [];
    const chartColors = paletteTokens.chart.colors;
    const otherColor = paletteTokens.chart.other;

    const sorted = [...breakdown].sort((a, b) => Number(b.total) - Number(a.total));
    let topItems: { name: string; total: number; color: string }[] = [];

    if (sorted.length <= 5) {
      topItems = sorted.map((item, idx) => ({
        name: item.label_name === "Chưa phân loại" ? t("uncategorized") : item.label_name,
        total: Number(item.total),
        color: chartColors[idx % chartColors.length],
      }));
    } else {
      const top5 = sorted.slice(0, 5);
      const others = sorted.slice(5);
      const otherTotal = others.reduce((acc, curr) => acc + Number(curr.total), 0);

      topItems = top5.map((item, idx) => ({
        name: item.label_name === "Chưa phân loại" ? t("uncategorized") : item.label_name,
        total: Number(item.total),
        color: chartColors[idx % chartColors.length],
      }));

      if (otherTotal > 0) {
        topItems.push({
          name: language === "vi" ? "Khác" : "Other",
          total: otherTotal,
          color: otherColor,
        });
      }
    }

    const series = topItems.map((item) => item.total);
    const labelsList = topItems.map((item) => item.name);
    const colorsList = topItems.map((item) => item.color);

    return {
      series,
      options: {
        labels: labelsList,
        colors: colorsList,
        chart: {
          id: "category-breakdown-pie",
          type: "pie",
          toolbar: { show: false },
          animations: { enabled: !prefersReducedMotion },
        },
        dataLabels: {
          enabled: false,
        },
        legend: {
          show: true,
          position: "left",
          labels: {
            colors: paletteTokens.textSecondary,
          },
          fontFamily: "Inter",
        },
        yaxis: {
          labels: {
            formatter: (val: number) => formatValue(val),
          },
        },
        tooltip: {
          theme: "dark",
          y: {
            formatter: (val: number) => formatValue(val),
          },
        },
        stroke: {
          show: false,
        },
      },
    };
  }, [reportSummary?.category_breakdown, language, t, prefersReducedMotion]);

  const userName = user
    ? `${user.first_name || ""} ${user.last_name || ""}`.trim() || user.email
    : "";

  return (
    <>
      {/* Inline Print Styles */}
      <style>
        {`
          @media print {
            @page {
              size: auto;
              margin: 10mm 12mm;
            }
            html, body, #root, .MuiBox-root {
              background: #ffffff !important;
              color: #0f172a !important;
            }
            .no-print, header, nav, .MuiDrawer-root, .MuiButton-root, .MuiAppBar-root, .MuiPagination-root, .MuiTablePagination-root {
              display: none !important;
            }
            .print-only {
              display: block !important;
            }
            .print-avoid-break {
              break-inside: avoid !important;
              page-break-inside: avoid !important;
            }
            .print-card {
              border: 1px solid #e2e8f0 !important;
              background: #ffffff !important;
              box-shadow: none !important;
              break-inside: avoid !important;
              page-break-inside: avoid !important;
            }
            .print-chart-container {
              height: 320px !important;
              border: 1px solid #e2e8f0 !important;
              background: #ffffff !important;
              box-shadow: none !important;
              break-inside: avoid !important;
              page-break-inside: avoid !important;
              overflow: visible !important;
            }
            .MuiTypography-root {
              color: #0f172a !important;
            }
            /* ApexCharts text fix in print */
            .apexcharts-canvas, .apexcharts-svg {
              background: transparent !important;
            }
            .apexcharts-text {
              fill: #1e293b !important;
            }
            .apexcharts-legend-text {
              color: #1e293b !important;
            }
            .apexcharts-gridline {
              stroke: #e2e8f0 !important;
            }
            /* Printable Report Table */
            .report-print-table {
              width: 100%;
              border-collapse: collapse;
              margin-top: 10px;
              font-size: 11px;
              font-family: inherit;
            }
            .report-print-table th {
              background-color: #f1f5f9 !important;
              color: #0f172a !important;
              font-weight: 700;
              border: 1px solid #cbd5e1 !important;
              padding: 6px 8px;
            }
            .report-print-table td {
              border: 1px solid #e2e8f0 !important;
              padding: 5px 8px;
              color: #1e293b !important;
            }
            .report-print-table tr {
              break-inside: avoid !important;
              page-break-inside: avoid !important;
            }
            .report-print-table thead {
              display: table-header-group !important;
            }
            .report-print-table tr:nth-of-type(even) {
              background-color: #f8fafc !important;
            }
          }
          @media screen {
            .print-only {
              display: none !important;
            }
          }
        `}
      </style>

      {/* Printable Header (Visible only in Print / PDF) */}
      <Box className="print-only" sx={{ mb: 2.5, pb: 2, borderBottom: "2px solid #00863A" }}>
        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <Box>
            <Typography component="div" variant="h5" sx={{ fontWeight: 800, color: "#00863A !important", letterSpacing: 0.5 }}>
              MONEYMANAGER
            </Typography>
            <Typography component="div" variant="h6" sx={{ fontWeight: 700, mt: 0.3 }}>
              {language === "vi" ? "BÁO CÁO TÀI CHÍNH" : "FINANCIAL REPORT"}
            </Typography>
          </Box>
          <Box sx={{ textAlign: "right" }}>
            <Typography variant="caption" sx={{ color: "#64748b !important", display: "block" }}>
              {t("generated_at")}: {dayjs().format("DD/MM/YYYY HH:mm:ss")}
            </Typography>
          </Box>
        </Box>

        <Grid container spacing={2} sx={{ mt: 1, pt: 1, borderTop: "1px solid #e2e8f0" }}>
          <Grid item xs={6}>
            <Typography variant="body2" sx={{ fontSize: 12 }}>
              <strong>{t("report_user")}:</strong> {userName}
            </Typography>
            <Typography variant="body2" sx={{ fontSize: 12, mt: 0.5 }}>
              <strong>{language === "vi" ? "Kỳ báo cáo" : "Period"}:</strong> {startDate ? dayjs(startDate).format(dateFormat) : "-"} → {endDate ? dayjs(endDate).format(dateFormat) : "-"} ({reportSummary?.period?.days_count || 0} {language === "vi" ? "ngày" : "days"})
            </Typography>
          </Grid>
          <Grid item xs={6} sx={{ textAlign: "right" }}>
            <Typography variant="body2" sx={{ fontSize: 12 }}>
              <strong>{language === "vi" ? "Bộ lọc giao dịch" : "Filter"}:</strong>{" "}
              {transactionType === "ALL"
                ? (language === "vi" ? "Tất cả giao dịch" : "All transactions")
                : transactionType === "EXPENSE"
                ? (language === "vi" ? "Khoản chi" : "Expense only")
                : (language === "vi" ? "Khoản thu" : "Earning only")}
            </Typography>
            <Typography variant="body2" sx={{ fontSize: 12, mt: 0.5 }}>
              <strong>{language === "vi" ? "Danh mục" : "Category"}:</strong>{" "}
              {selectedLabelId === "all"
                ? (language === "vi" ? "Tất cả danh mục" : "All categories")
                : labels?.find((l: CustomLabel) => l.id === selectedLabelId)?.name || "-"}
            </Typography>
          </Grid>
        </Grid>
      </Box>

      {/* Screen Header matching Home.tsx */}
      <Box
        className="no-print"
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
          {t("reports_title")}
        </Typography>
        {activeTab === "history" && (
          <Box sx={{ marginTop: { xs: 2, md: 0 }, display: "flex", flexWrap: "wrap", gap: 1.5 }}>
            <Button
              variant="contained"
              size="medium"
              startIcon={
                isExporting ? <CircularProgress size={16} color="inherit" /> : <FileUploadIcon />
              }
              onClick={handleExportExcel}
              disabled={isExporting || isDateInvalid}
              sx={{
                backgroundColor: paletteTokens.primary,
                color: paletteTokens.primaryContrastText,
                "&:hover": { backgroundColor: paletteTokens.primaryHover },
              }}
            >
              {t("export_excel")}
            </Button>

            <Button
              variant="outlined"
              size="medium"
              startIcon={<PrintOutlinedIcon />}
              onClick={handlePrint}
              disabled={isDateInvalid}
              sx={{
                borderColor: paletteTokens.controlBorder,
                color: paletteTokens.textPrimary,
                "&:hover": {
                  borderColor: paletteTokens.textSecondary,
                  backgroundColor: "rgba(255, 255, 255, 0.04)",
                },
              }}
            >
              {t("print_report")}
            </Button>
          </Box>
        )}
      </Box>

      {/* Tabs navigation */}
      <Box className="no-print" sx={{ mt: 2, mb: 1, borderBottom: 1, borderColor: "divider" }}>
        <Tabs
          value={activeTab}
          onChange={(_, val) => setActiveTab(val)}
          textColor="primary"
          indicatorColor="primary"
        >
          <Tab
            value="history"
            label={language === "vi" ? "Báo cáo lịch sử" : "Historical Report"}
            sx={{ textTransform: "none", fontWeight: 600, fontSize: "0.95rem" }}
          />
          <Tab
            value="forecast"
            label={language === "vi" ? "Dự báo dòng tiền" : "Cash Flow Forecast"}
            sx={{ textTransform: "none", fontWeight: 600, fontSize: "0.95rem" }}
          />
        </Tabs>
      </Box>

      {activeTab === "forecast" ? (
        <Box className="no-print" sx={{ mt: 2 }}>
          <CashFlowForecast />
        </Box>
      ) : (
        <>
          {/* Filter Row: clean, unboxed, natural spacing */}
      <Box
        className="no-print"
        sx={{
          mt: 3,
          mb: 1,
          display: "flex",
          flexWrap: "wrap",
          gap: 2,
          alignItems: "center",
        }}
      >
        <FormControl size="small" sx={{ minWidth: 160 }}>
          <InputLabel id="preset-select-label">{t("range")}</InputLabel>
          <Select
            labelId="preset-select-label"
            id="preset-select"
            value={preset}
            label={t("range")}
            onChange={(e) => handlePresetChange(e.target.value as PresetRange)}
          >
            <MenuItem value="this_month">{t("filter_this_month")}</MenuItem>
            <MenuItem value="last_month">{t("filter_last_month")}</MenuItem>
            <MenuItem value="last_30_days">{t("filter_last_30_days")}</MenuItem>
            <MenuItem value="this_quarter">{t("filter_this_quarter")}</MenuItem>
            <MenuItem value="this_year">{t("filter_this_year")}</MenuItem>
            <MenuItem value="custom">{t("filter_custom")}</MenuItem>
          </Select>
        </FormControl>

        {preset === "custom" && (
          <LocalizationProvider dateAdapter={AdapterDayjs}>
            <DatePicker
              label={t("start_date")}
              value={startDate ? dayjs(startDate) : null}
              format={dateFormat}
              onChange={(val) => setStartDate(val && val.isValid() ? val.format("YYYY-MM-DD") : "")}
              slotProps={{ textField: { size: "small", sx: { width: 165 } } }}
            />

            <DatePicker
              label={t("end_date")}
              value={endDate ? dayjs(endDate) : null}
              format={dateFormat}
              onChange={(val) => setEndDate(val && val.isValid() ? val.format("YYYY-MM-DD") : "")}
              slotProps={{ textField: { size: "small", sx: { width: 165 } } }}
            />
          </LocalizationProvider>
        )}

        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel id="type-select-label">{t("col_type")}</InputLabel>
          <Select
            labelId="type-select-label"
            id="type-select"
            value={transactionType}
            label={t("col_type")}
            onChange={(e) =>
              setTransactionType(e.target.value as "ALL" | "EXPENSE" | "EARNING")
            }
          >
            <MenuItem value="ALL">{t("type_all")}</MenuItem>
            <MenuItem value="EXPENSE">
              {language === "vi" ? "Khoản chi" : "Expense"}
            </MenuItem>
            <MenuItem value="EARNING">
              {language === "vi" ? "Khoản thu" : "Earning"}
            </MenuItem>
          </Select>
        </FormControl>

        <FormControl size="small" sx={{ minWidth: 170 }}>
          <InputLabel id="category-select-label">{t("col_label")}</InputLabel>
          <Select<number | string>
            labelId="category-select-label"
            id="category-select"
            value={selectedLabelId}
            label={t("col_label")}
            onChange={(e) => {
              const val = e.target.value;
              setSelectedLabelId(val === "all" ? "all" : Number(val));
            }}
          >
            <MenuItem value="all">{t("all_categories")}</MenuItem>
            {labels?.map((cat: CustomLabel) => (
              <MenuItem key={cat.id} value={cat.id}>
                {cat.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      {/* Date Validation Alert */}
      {isDateInvalid && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {language === "vi"
            ? "Ngày bắt đầu không được lớn hơn ngày kết thúc. Vui lòng chọn lại khoảng thời gian hợp lệ."
            : "Start date cannot be after end date. Please choose a valid date range."}
        </Alert>
      )}

      {/* Error Alert */}
      {isSummaryError && !isDateInvalid && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {t("unable_to_load_data")}
        </Alert>
      )}

      {/* Main Grid matching Home.tsx spacing and layout */}
      <Grid mt={1} container spacing={2} alignItems={"stretch"}>
        {/* 1. KPI Cards matching WalletGridRow.tsx */}
        {isSummaryLoading ? (
          <>
            {[1, 2, 3, 4].map((i) => (
              <Grid key={i} item xs={12} sm={6} lg={3}>
                <Box
                  border="1px solid"
                  borderColor={paletteTokens.divider}
                  borderRadius={2}
                  padding={3}
                  height={"100%"}
                >
                  <Skeleton variant="text" width={100} height={24} />
                  <Skeleton variant="rectangular" width="80%" height={36} sx={{ my: 1 }} />
                  <Skeleton variant="text" width={120} height={18} />
                </Box>
              </Grid>
            ))}
          </>
        ) : (
          <>
            {/* Total Income */}
            <Grid item xs={12} sm={6} lg={3}>
              <Box
                className="print-card print-avoid-break"
                border="1px solid"
                borderColor={paletteTokens.divider}
                borderRadius={2}
                padding={3}
                height={"100%"}
              >
                <Typography component="h2" variant="body1" mb={1}>
                  {t("income")}
                </Typography>
                <Box display="flex" alignItems="center" gap={2}>
                  <Typography
                    component="span"
                    variant="h5"
                    fontWeight={600}
                    sx={{ color: paletteTokens.primary }}
                  >
                    +{formatValue(totalIncome)}
                  </Typography>
                </Box>
                <Typography
                  component="p"
                  variant="caption"
                  color={incomeChangePct >= 0 ? paletteTokens.primary : "text.secondary"}
                  sx={{ mt: 1 }}
                >
                  {incomeChangePct >= 0 ? `+${incomeChangePct}%` : `${incomeChangePct}%`}{" "}
                  {t("vs_prev_period")}
                </Typography>
              </Box>
            </Grid>

            {/* Total Expenses */}
            <Grid item xs={12} sm={6} lg={3}>
              <Box
                className="print-card print-avoid-break"
                border="1px solid"
                borderColor={paletteTokens.divider}
                borderRadius={2}
                padding={3}
                height={"100%"}
              >
                <Typography component="h2" variant="body1" mb={1}>
                  {language === "vi" ? "Tổng chi tiêu" : "Total Expenses"}
                </Typography>
                <Box display="flex" alignItems="center" gap={2}>
                  <Typography
                    component="span"
                    variant="h5"
                    fontWeight={600}
                    color="text.primary"
                  >
                    -{formatValue(totalExpense)}
                  </Typography>
                </Box>
                <Typography
                  component="p"
                  variant="caption"
                  color={expenseChangePct > 0 ? paletteTokens.error : paletteTokens.success}
                  sx={{ mt: 1 }}
                >
                  {expenseChangePct > 0 ? `+${expenseChangePct}%` : `${expenseChangePct}%`}{" "}
                  {t("vs_prev_period")}
                </Typography>
              </Box>
            </Grid>

            {/* Net Cash Flow */}
            <Grid item xs={12} sm={6} lg={3}>
              <Box
                className="print-card print-avoid-break"
                border="1px solid"
                borderColor={paletteTokens.divider}
                borderRadius={2}
                padding={3}
                height={"100%"}
              >
                <Typography component="h2" variant="body1" mb={1}>
                  {t("net_cash_flow")}
                </Typography>
                <Box display="flex" alignItems="center" gap={2}>
                  <Typography
                    component="span"
                    variant="h5"
                    fontWeight={600}
                    sx={{ color: netCashFlow >= 0 ? paletteTokens.primary : paletteTokens.error }}
                  >
                    {netCashFlow >= 0 ? `+${formatValue(netCashFlow)}` : formatValue(netCashFlow)}
                  </Typography>
                </Box>
                <Typography
                  component="p"
                  variant="caption"
                  color={netCashFlowChangePct >= 0 ? paletteTokens.primary : paletteTokens.error}
                  sx={{ mt: 1 }}
                >
                  {netCashFlowChangePct > 0 ? `+${netCashFlowChangePct}%` : `${netCashFlowChangePct}%`}{" "}
                  {t("vs_prev_period")}
                </Typography>
              </Box>
            </Grid>

            {/* Average Daily Spending */}
            <Grid item xs={12} sm={6} lg={3}>
              <Box
                className="print-card print-avoid-break"
                border="1px solid"
                borderColor={paletteTokens.divider}
                borderRadius={2}
                padding={3}
                height={"100%"}
              >
                <Typography component="h2" variant="body1" mb={1}>
                  {t("avg_daily_spending")}
                </Typography>
                <Box display="flex" alignItems="center" gap={2}>
                  <Typography component="span" variant="h5" fontWeight={600}>
                    {formatValue(avgDailySpending)}
                  </Typography>
                </Box>
                <Typography component="p" variant="caption" color="text.secondary" sx={{ mt: 1 }}>
                  {reportSummary?.period?.days_count || 1}{" "}
                  {language === "vi" ? "ngày trong kỳ" : "days in period"}
                </Typography>
              </Box>
            </Grid>
          </>
        )}

        {/* 2. Charts matching CurrentMonthChart & ProfileChart (height 380, padding 3) */}
        {/* Monthly Trends */}
        <Grid item xs={12} lg={6}>
          <Box
            className="print-card print-chart-container print-avoid-break"
            border="1px solid"
            borderColor={paletteTokens.divider}
            borderRadius={2}
            padding={3}
            height={380}
          >
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <Typography component="h2" variant="body1" mb={1}>
                {t("monthly_trends_chart")}
              </Typography>
            </Box>
            {reportSummary?.monthly_trends && reportSummary.monthly_trends.length > 0 ? (
              <Chart
                options={monthlyTrendsChart.options}
                series={monthlyTrendsChart.series}
                type="bar"
                height="300px"
              />
            ) : (
              <Typography
                component="p"
                variant="body1"
                sx={{
                  display: "flex",
                  justifyContent: "center",
                  mt: 14,
                  textAlign: "center",
                }}
              >
                {t("unable_to_load_chart")}
              </Typography>
            )}
          </Box>
        </Grid>

        {/* Category Breakdown (Pie chart matching ProfileChart.tsx) */}
        <Grid item xs={12} lg={6}>
          <Box
            className="print-card print-chart-container print-avoid-break"
            border="1px solid"
            borderColor={paletteTokens.divider}
            borderRadius={2}
            padding={3}
            height={380}
          >
            <Box
              sx={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
              }}
            >
              <Typography component="h2" variant="body1" mb={1}>
                {t("category_breakdown_chart")}
              </Typography>
            </Box>
            {categoryBreakdownChart.series.length > 0 ? (
              <Chart
                options={categoryBreakdownChart.options}
                series={categoryBreakdownChart.series}
                type="pie"
                width="90%"
                height="300px"
              />
            ) : (
              <Typography
                component="p"
                variant="body1"
                sx={{
                  display: "flex",
                  justifyContent: "center",
                  mt: 14,
                  textAlign: "center",
                }}
              >
                {t("unable_to_load_chart")}
              </Typography>
            )}
          </Box>
        </Grid>

        {/* 3. Largest Spending Increases Section */}
        <Grid item xs={12}>
          <Box
            className="print-card print-avoid-break"
            border="1px solid"
            borderColor={paletteTokens.divider}
            borderRadius={2}
            padding={3}
          >
            <Box
              sx={{
                display: "flex",
                alignItems: "baseline",
                gap: 1,
                mb: 2,
              }}
            >
              <Typography component="h2" variant="body1">
                {t("largest_spending_increases")}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                ({t("vs_prev_period")})
              </Typography>
            </Box>

            {reportSummary?.largest_spending_increases &&
            reportSummary.largest_spending_increases.length > 0 ? (
              <Grid container spacing={2}>
                {reportSummary.largest_spending_increases.map((item, idx) => (
                  <Grid key={idx} item xs={12} sm={6} md={4}>
                    <Box
                      border="1px solid"
                      borderColor={paletteTokens.divider}
                      borderRadius={2}
                      padding={2}
                    >
                      <Box display="flex" justifyContent="space-between" alignItems="center" mb={1.5}>
                        <Chip
                          icon={
                            <Box
                              component="span"
                              sx={{
                                width: 8,
                                height: 8,
                                borderRadius: "50%",
                                backgroundColor: item.label_color || paletteTokens.primary,
                                ml: "6px !important",
                                mr: "-2px !important",
                              }}
                            />
                          }
                          label={
                            item.label_name === "Chưa phân loại"
                              ? t("uncategorized")
                              : item.label_name
                          }
                          size="small"
                          sx={{
                            backgroundColor: "rgba(255, 255, 255, 0.05)",
                            border: `1px solid ${paletteTokens.divider}`,
                            color: "text.primary",
                            fontSize: "12px",
                          }}
                        />
                        <Typography
                          variant="caption"
                          sx={{ color: paletteTokens.error, fontWeight: 600 }}
                        >
                          +{item.increase_percentage}%
                        </Typography>
                      </Box>
                      <Box display="flex" justifyContent="space-between" alignItems="baseline">
                        <Typography variant="caption" color="text.secondary">
                          {t("previous_period")}: {formatValue(Number(item.previous_spent))}
                        </Typography>
                        <Typography variant="body2" fontWeight={600} sx={{ color: paletteTokens.error }}>
                          +{formatValue(Number(item.increase_amount))}
                        </Typography>
                      </Box>
                    </Box>
                  </Grid>
                ))}
              </Grid>
            ) : (
              <Box display="flex" alignItems="center" gap={1.5} py={1}>
                <CheckCircleOutlineIcon sx={{ color: "text.secondary", fontSize: 20 }} />
                <Typography variant="body2" color="text.secondary">
                  {t("no_increases_found")}
                </Typography>
              </Box>
            )}
          </Box>
        </Grid>

        {/* 4. Filtered Transactions List matching Transactions.tsx */}
        <Grid item xs={12}>
          <Box className="print-avoid-break" height={"auto"} mt={1} mb={4}>
            <Typography component="h2" variant="h6" mb={1.5}>
              {t("transactions_in_period")}
            </Typography>

            {/* Search Input - Hidden in Print */}
            <Box component="form" className="no-print" onSubmit={(e) => e.preventDefault()} sx={{ mb: 2 }}>
              <TextField
                fullWidth
                label=""
                variant="outlined"
                size="medium"
                placeholder={t("find_transaction")}
                inputProps={{ "aria-label": t("find_transaction") }}
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                InputProps={{
                  style: { fontSize: "14px", height: "40px" },
                  startAdornment: (
                    <InputAdornment position="start" sx={{ color: grey[800] }}>
                      <SearchIcon />
                    </InputAdornment>
                  ),
                  endAdornment: (
                    <>
                      {isTxLoading && <CircularProgress size={18} sx={{ mr: 1 }} />}
                      {searchTerm && (
                        <InputAdornment position="end">
                          <IconButton
                            size="small"
                            onClick={() => setSearchTerm("")}
                            edge="end"
                            aria-label={t("clear_search")}
                          >
                            <ClearIcon fontSize="small" />
                          </IconButton>
                        </InputAdornment>
                      )}
                    </>
                  ),
                }}
              />
            </Box>

            {/* Reused LatestTransactions component without actions - Screen only */}
            <Box className="no-print">
              <LatestTransactions data={transactionsList ?? []} headOnly={false} hideActions={true} />
            </Box>

            {/* Print-only Semantic HTML Table for PDF Report */}
            <Box className="print-only">
              <table className="report-print-table">
                <thead>
                  <tr>
                    <th style={{ width: "35px", textAlign: "center" }}>#</th>
                    <th style={{ width: "85px", textAlign: "center" }}>{t("col_date")}</th>
                    <th>{t("col_name")}</th>
                    <th style={{ width: "95px", textAlign: "center" }}>{t("col_type")}</th>
                    <th style={{ width: "120px" }}>{t("col_label")}</th>
                    <th style={{ width: "120px", textAlign: "right" }}>{t("col_value")}</th>
                    <th style={{ width: "60px", textAlign: "center" }}>{language === "vi" ? "Định kỳ" : "Recurrent"}</th>
                    <th style={{ width: "60px", textAlign: "center" }}>{language === "vi" ? "Hoá đơn" : "Invoice"}</th>
                  </tr>
                </thead>
                <tbody>
                  {transactionsList && transactionsList.length > 0 ? (
                    transactionsList.map((tx, idx) => {
                      const isIncome = tx.type === "EARNING";
                      return (
                        <tr key={tx.id}>
                          <td style={{ textAlign: "center" }}>{idx + 1}</td>
                          <td style={{ textAlign: "center" }}>{dayjs(tx.date).format(dateFormat)}</td>
                          <td>{tx.title}</td>
                          <td style={{ textAlign: "center", fontWeight: 600, color: isIncome ? paletteTokens.primary : "text.primary" }}>
                            {isIncome ? (language === "vi" ? "Khoản thu" : "Earning") : (language === "vi" ? "Khoản chi" : "Expense")}
                          </td>
                          <td>{tx.label?.name || (language === "vi" ? "Chưa phân loại" : "Uncategorized")}</td>
                          <td style={{ textAlign: "right", fontWeight: 600, color: isIncome ? paletteTokens.primary : "text.primary" }}>
                            {isIncome ? `+${formatValue(Number(tx.value))}` : `-${formatValue(Number(tx.value))}`}
                          </td>
                          <td style={{ textAlign: "center" }}>{tx.recurrent ? (language === "vi" ? "Có" : "Yes") : "-"}</td>
                          <td style={{ textAlign: "center" }}>{tx.imported ? (language === "vi" ? "Có" : "Yes") : "-"}</td>
                        </tr>
                      );
                    })
                  ) : (
                    <tr>
                      <td colSpan={8} style={{ textAlign: "center", padding: "16px" }}>
                        {t("no_data_in_period")}
                      </td>
                    </tr>
                  )}
                </tbody>
                {transactionsList && transactionsList.length > 0 && (
                  <tfoot>
                    <tr style={{ fontWeight: 700, backgroundColor: "#f1f5f9" }}>
                      <td colSpan={5} style={{ textAlign: "right", paddingRight: "10px" }}>
                        {language === "vi" ? `Tổng cộng (${transactionsList.length} giao dịch):` : `Total (${transactionsList.length} transactions):`}
                      </td>
                      <td style={{ textAlign: "right", color: netCashFlow >= 0 ? paletteTokens.primary : paletteTokens.error }}>
                        {netCashFlow >= 0 ? `+${formatValue(netCashFlow)}` : formatValue(netCashFlow)}
                      </td>
                      <td colSpan={2}></td>
                    </tr>
                  </tfoot>
                )}
              </table>
            </Box>
          </Box>
        </Grid>
      </Grid>
        </>
      )}
    </>
  );
}

