import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  ButtonGroup,
  Chip,
  CircularProgress,
  Grid,
  InputAdornment,
  Skeleton,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { grey } from "@mui/material/colors";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import TipsAndUpdatesOutlinedIcon from "@mui/icons-material/TipsAndUpdatesOutlined";
import EventNoteOutlinedIcon from "@mui/icons-material/EventNoteOutlined";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import RefreshIcon from "@mui/icons-material/Refresh";
import Chart from "react-apexcharts";
import { ApexOptions } from "apexcharts";
import dayjs from "dayjs";
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { useForecast } from "../../hooks/api/useForecast";
import { usePrefersReducedMotion } from "../../hooks/usePrefersReducedMotion";
import { useLanguage } from "../../context/LanguageContext";
import { formatValue } from "../../utils/utils";
import { paletteTokens } from "../../theme";
import {
  DailyTimelinePoint,
  FixedEventItem,
  RecommendationItem,
} from "../../models/CashFlowForecast";

interface FlattenedFixedEvent {
  id: string;
  date: string;
  title: string;
  amount: number;
  source: "RECURRING" | "DEBT" | "INSTALLMENT";
  balanceAfter: number;
}

export default function CashFlowForecast() {
  const { language, dateFormat, t } = useLanguage();
  const { getCashFlowForecast } = useForecast();
  const prefersReducedMotion = usePrefersReducedMotion();

  // Control state
  const [days, setDays] = useState<30 | 60 | 90>(30);
  const [bufferInput, setBufferInput] = useState<string>("0");
  const [safetyBuffer, setSafetyBuffer] = useState<number>(0);
  const [bufferError, setBufferError] = useState<string>("");

  const handleBufferChange = (val: string) => {
    setBufferInput(val);
    if (!val || val.trim() === "") {
      setSafetyBuffer(0);
      setBufferError("");
      return;
    }
    const num = Number(val);
    if (isNaN(num) || num < 0) {
      setBufferError(t("safety_buffer_invalid"));
    } else {
      setBufferError("");
      setSafetyBuffer(num);
    }
  };

  // Fetch forecast data
  const {
    data: forecast,
    isLoading,
    isError,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ["cashflow_forecast", days, safetyBuffer],
    queryFn: () => getCashFlowForecast({ days, safety_buffer: safetyBuffer }),
    placeholderData: keepPreviousData,
  });

  // Extract flat list of upcoming fixed events from daily timeline
  const upcomingEvents: FlattenedFixedEvent[] = useMemo(() => {
    if (!forecast?.daily_timeline) return [];
    const list: FlattenedFixedEvent[] = [];
    forecast.daily_timeline.forEach((pt: DailyTimelinePoint, dayIdx: number) => {
      pt.fixed_events.forEach((ev: FixedEventItem, evIdx: number) => {
        list.push({
          id: `${pt.date}-${ev.source}-${ev.title}-${dayIdx}-${evIdx}`,
          date: pt.date,
          title: ev.title,
          amount: Number(ev.amount),
          source: ev.source,
          balanceAfter: Number(pt.balance),
        });
      });
    });
    return list;
  }, [forecast?.daily_timeline]);

  // ApexCharts Configuration
  const chartConfig = useMemo<{ series: ApexAxisChartSeries; options: ApexOptions }>(() => {
    if (!forecast?.daily_timeline || forecast.daily_timeline.length === 0) {
      return { series: [], options: {} };
    }

    const timeline = forecast.daily_timeline;
    const categories = timeline.map((pt) => dayjs(pt.date).format("DD/MM"));
    const balanceData = timeline.map((pt) => Number(pt.balance));

    // Y-axis annotations for zero danger line and safety buffer
    const yaxisAnnotations = [
      {
        y: 0,
        borderColor: paletteTokens.error,
        strokeDashArray: 3,
        label: {
          borderColor: paletteTokens.error,
          style: {
            color: paletteTokens.primaryContrastText,
            background: paletteTokens.error,
            fontSize: "11px",
            fontFamily: "Inter",
            fontWeight: 600,
          },
          text: language === "vi" ? "Mức 0đ (Nguy cơ cạn quỹ)" : "0 VND (Insolvency line)",
        },
      },
    ];

    if (safetyBuffer > 0) {
      yaxisAnnotations.push({
        y: safetyBuffer,
        borderColor: paletteTokens.warning,
        strokeDashArray: 4,
        label: {
          borderColor: paletteTokens.warning,
          style: {
            color: paletteTokens.primaryContrastText,
            background: paletteTokens.warning,
            fontSize: "11px",
            fontFamily: "Inter",
            fontWeight: 600,
          },
          text: `${t("safety_buffer")} (${formatValue(safetyBuffer)})`,
        },
      });
    }

    // Point annotations for days with fixed commitments
    const pointAnnotations = timeline
      .map((pt, idx) => {
        if (!pt.fixed_events || pt.fixed_events.length === 0) return null;
        const totalFixed = pt.fixed_events.reduce((acc, e) => acc + Number(e.amount), 0);
        const isNegative = totalFixed < 0;
        const mainTitle = pt.fixed_events[0].title;
        return {
          x: categories[idx],
          y: Number(pt.balance),
          marker: {
            size: 6,
            fillColor: isNegative ? paletteTokens.error : paletteTokens.textPrimary,
            strokeColor: "#ffffff",
            strokeWidth: 2,
            radius: 3,
          },
          label: {
            borderColor: isNegative ? paletteTokens.error : paletteTokens.divider,
            offsetY: isNegative ? 24 : -12,
            style: {
              color: "#ffffff",
              background: isNegative ? paletteTokens.error : paletteTokens.bgCard,
              fontSize: "10px",
              fontFamily: "Inter",
              fontWeight: 600,
            },
            text: `${mainTitle} (${formatValue(totalFixed)})`,
          },
        };
      })
      .filter(Boolean) as any[];

    const options: ApexOptions = {
      chart: {
        id: "cashflow-forecast-line",
        type: "area",
        toolbar: { show: false },
        animations: { enabled: !prefersReducedMotion, speed: 600 },
        background: "transparent",
      },
      colors: [paletteTokens.textPrimary],
      stroke: {
        curve: "smooth",
        width: 3,
      },
      fill: {
        type: "solid",
        opacity: 0,
      },
      dataLabels: { enabled: false },
      xaxis: {
        categories,
        labels: {
          style: { colors: paletteTokens.textSecondary, fontSize: "11px", fontFamily: "Inter" },
          rotate: -45,
          rotateAlways: timeline.length > 45,
        },
        axisBorder: { show: true, color: paletteTokens.divider },
        axisTicks: { show: true, color: paletteTokens.divider },
      },
      yaxis: {
        tickAmount: 6,
        labels: {
          style: { colors: paletteTokens.textSecondary, fontFamily: "Inter" },
          formatter: (val: number) => formatValue(val),
        },
      },
      grid: {
        show: true,
        borderColor: paletteTokens.divider,
        strokeDashArray: 3,
      },
      tooltip: {
        theme: "dark",
        custom: function ({ dataPointIndex }) {
          const pt = timeline[dataPointIndex];
          if (!pt) return "";
          const bal = Number(pt.balance);
          const dateStr = dayjs(pt.date).format(dateFormat);
          let eventsHtml = "";
          if (pt.fixed_events && pt.fixed_events.length > 0) {
            eventsHtml = `
              <div style="margin-top: 8px; padding-top: 6px; border-top: 1px solid rgba(255,255,255,0.15);">
                <div style="font-size: 11px; color: ${paletteTokens.textSecondary}; margin-bottom: 4px;">${t("upcoming_events_title")}:</div>
                ${pt.fixed_events
                  .map((e) => {
                    const amt = Number(e.amount);
                    const color = amt >= 0 ? paletteTokens.primary : paletteTokens.error;
                    const sign = amt >= 0 ? "+" : "";
                    return `<div style="font-size: 11px; display: flex; justify-content: space-between; gap: 12px;">
                      <span>${e.title}</span>
                      <strong style="color: ${color};">${sign}${formatValue(amt)}</strong>
                    </div>`;
                  })
                  .join("")}
              </div>
            `;
          }

          return `
            <div style="padding: 10px 14px; background: ${paletteTokens.bgCard}; border: 1px solid ${paletteTokens.divider}; border-radius: 6px; font-family: Inter, sans-serif;">
              <div style="font-size: 11px; color: ${paletteTokens.textSecondary};">${dateStr}</div>
              <div style="font-size: 14px; font-weight: 600; color: ${bal >= 0 ? paletteTokens.textPrimary : paletteTokens.error}; margin-top: 2px;">
                ${t("balance")}: ${formatValue(bal)}
              </div>
              ${eventsHtml}
            </div>
          `;
        },
      },
      annotations: {
        yaxis: yaxisAnnotations,
        points: pointAnnotations,
      },
    };

    return {
      series: [
        {
          name: t("chart_balance_series"),
          data: balanceData,
        },
      ],
      options,
    };
  }, [forecast?.daily_timeline, safetyBuffer, language, dateFormat, t, prefersReducedMotion]);

  // Translate Recommendation item
  const renderRecommendationText = (rec: RecommendationItem): string => {
    switch (rec.code) {
      case "ALL_CLEAR":
        return t("rec_all_clear");
      case "SHORTFALL_RISK": {
        const dStr = rec.params?.date ? dayjs(rec.params.date).format(dateFormat) : "-";
        const shortfallStr = formatValue(Number(rec.params?.shortfall || 0));
        return t("rec_shortfall_risk")
          .replace("{date}", dStr)
          .replace("{event_title}", rec.params?.event_title || "")
          .replace("{shortfall}", shortfallStr);
      }
      case "REDUCE_DAILY_SPENDING": {
        const cutStr = formatValue(Number(rec.params?.daily_cut || 0));
        return t("rec_reduce_daily")
          .replace("{days_until}", String(rec.params?.days_until || 0))
          .replace("{daily_cut}", cutStr);
      }
      case "BELOW_BUFFER": {
        const dStr = rec.params?.date ? dayjs(rec.params.date).format(dateFormat) : "-";
        const bufferStr = formatValue(Number(rec.params?.buffer || 0));
        return t("rec_below_buffer")
          .replace("{date}", dStr)
          .replace("{buffer}", bufferStr);
      }
      case "LOW_CONFIDENCE":
        return t("rec_low_confidence");
      default:
        return "";
    }
  };

  const getSourceLabel = (src: string): string => {
    if (src === "RECURRING") return t("source_recurring");
    if (src === "DEBT") return t("source_debt");
    if (src === "INSTALLMENT") return t("source_installment");
    return src;
  };

  const getSourceChipColor = (_src: string) => {
    return paletteTokens.controlBorder;
  };

  return (
    <Box>
      {/* 1. Header & Controls Card */}
      <Box
        sx={{
          border: "1px solid",
          borderColor: paletteTokens.divider,
          borderRadius: 2,
          p: { xs: 2, md: 3 },
          mb: 3,
          backgroundColor: paletteTokens.bgPaper,
        }}
      >
        <Grid container spacing={3} alignItems="center">
          <Grid item xs={12} md={7}>
            <Box display="flex" alignItems="center" gap={1.5} mb={0.5}>
              <Typography component="h2" variant="h5" fontWeight={600} color="#fff">
                {t("forecast_title")}
              </Typography>
              {isFetching && <CircularProgress size={16} sx={{ color: paletteTokens.primary }} />}
            </Box>
            <Typography variant="body2" color="text.secondary">
              {t("forecast_subtitle")}
            </Typography>
          </Grid>

          {/* Controls: Horizon & Safety buffer */}
          <Grid item xs={12} md={5}>
            <Box
              display="flex"
              flexWrap="wrap"
              gap={2}
              justifyContent={{ xs: "flex-start", md: "flex-end" }}
              alignItems="center"
            >
              {/* Horizon selector buttons */}
              <Box>
                <Typography variant="caption" color="text.secondary" display="block" mb={0.5}>
                  {t("forecast_horizon")}
                </Typography>
                <ButtonGroup variant="outlined" size="small" sx={{ borderColor: paletteTokens.divider }}>
                  <Button
                    onClick={() => setDays(30)}
                    variant="outlined"
                    sx={{
                      backgroundColor: days === 30 ? "rgba(255, 255, 255, 0.12)" : "transparent",
                      color: days === 30 ? "#fff" : "text.secondary",
                      borderColor: paletteTokens.divider,
                    }}
                  >
                    30d
                  </Button>
                  <Button
                    onClick={() => setDays(60)}
                    variant="outlined"
                    sx={{
                      backgroundColor: days === 60 ? "rgba(255, 255, 255, 0.12)" : "transparent",
                      color: days === 60 ? "#fff" : "text.secondary",
                      borderColor: paletteTokens.divider,
                    }}
                  >
                    60d
                  </Button>
                  <Button
                    onClick={() => setDays(90)}
                    variant="outlined"
                    sx={{
                      backgroundColor: days === 90 ? "rgba(255, 255, 255, 0.12)" : "transparent",
                      color: days === 90 ? "#fff" : "text.secondary",
                      borderColor: paletteTokens.divider,
                    }}
                  >
                    90d
                  </Button>
                </ButtonGroup>
              </Box>

              {/* Safety buffer input */}
              <Box sx={{ minWidth: 170 }}>
                <Typography variant="caption" color="text.secondary" display="block" mb={0.5}>
                  {t("safety_buffer")}
                </Typography>
                <TextField
                  size="small"
                  fullWidth
                  value={bufferInput}
                  onChange={(e) => handleBufferChange(e.target.value)}
                  error={Boolean(bufferError)}
                  helperText={bufferError}
                  inputProps={{ "aria-label": t("safety_buffer") }}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <ShieldOutlinedIcon fontSize="small" sx={{ color: "text.secondary" }} />
                      </InputAdornment>
                    ),
                    endAdornment: (
                      <InputAdornment position="end">
                        <Typography variant="caption" color="text.secondary">
                          ₫
                        </Typography>
                      </InputAdornment>
                    ),
                  }}
                />
              </Box>
            </Box>
          </Grid>
        </Grid>
      </Box>

      {/* Error state */}
      {isError && (
        <Alert
          severity="error"
          sx={{ mb: 3 }}
          action={
            <Button color="inherit" size="small" onClick={() => refetch()} startIcon={<RefreshIcon />}>
              {t("retry")}
            </Button>
          }
        >
          {t("unable_to_load_data")}
        </Alert>
      )}

      {/* 2. Risk Alert Banner */}
      {!isLoading && forecast && (
        <Box sx={{ mb: 3 }}>
          {forecast.risk_level === "CRITICAL" && (
            <Alert
              severity="error"
              icon={<ErrorOutlineIcon fontSize="medium" />}
              sx={{
                backgroundColor: paletteTokens.tint.error12,
                color: paletteTokens.error,
                border: `1px solid ${paletteTokens.error}`,
                "& .MuiAlert-icon": { color: paletteTokens.error },
              }}
            >
              <Box display="flex" alignItems="center" justifyContent="space-between" flexWrap="wrap" gap={1}>
                <Box>
                  <Typography variant="subtitle1" fontWeight={700}>
                    {t("risk_critical")}
                  </Typography>
                  <Typography variant="body2" sx={{ mt: 0.5 }}>
                    {t("risk_critical_desc")
                      .replace("{date}", forecast.first_negative_date ? dayjs(forecast.first_negative_date).format(dateFormat) : "-")
                      .replace("{shortfall}", formatValue(Number(forecast.max_shortfall)))}
                  </Typography>
                </Box>
                {forecast.low_confidence && (
                  <Tooltip title={t("low_confidence_tooltip")}>
                    <Chip
                      label={t("low_confidence_badge")}
                      size="small"
                      sx={{ backgroundColor: paletteTokens.tint.warning12, color: paletteTokens.warning, borderColor: paletteTokens.warning }}
                      variant="outlined"
                    />
                  </Tooltip>
                )}
              </Box>
            </Alert>
          )}

          {forecast.risk_level === "WARNING" && (
            <Alert
              severity="warning"
              icon={<WarningAmberIcon fontSize="medium" />}
              sx={{
                backgroundColor: paletteTokens.tint.warning12,
                color: paletteTokens.warning,
                border: `1px solid ${paletteTokens.warning}`,
                "& .MuiAlert-icon": { color: paletteTokens.warning },
              }}
            >
              <Box display="flex" alignItems="center" justifyContent="space-between" flexWrap="wrap" gap={1}>
                <Box>
                  <Typography variant="subtitle1" fontWeight={700}>
                    {t("risk_warning")}
                  </Typography>
                  <Typography variant="body2" sx={{ mt: 0.5 }}>
                    {t("risk_warning_desc").replace(
                      "{date}",
                      forecast.first_warning_date ? dayjs(forecast.first_warning_date).format(dateFormat) : "-"
                    )}
                  </Typography>
                </Box>
                {forecast.low_confidence && (
                  <Tooltip title={t("low_confidence_tooltip")}>
                    <Chip
                      label={t("low_confidence_badge")}
                      size="small"
                      sx={{ backgroundColor: paletteTokens.tint.warning12, color: paletteTokens.warning, borderColor: paletteTokens.warning }}
                      variant="outlined"
                    />
                  </Tooltip>
                )}
              </Box>
            </Alert>
          )}

          {forecast.risk_level === "SAFE" && forecast.low_confidence && (
            <Alert
              severity="info"
              sx={{
                backgroundColor: "rgba(255, 255, 255, 0.04)",
                color: paletteTokens.textSecondary,
                border: `1px solid ${paletteTokens.divider}`,
              }}
            >
              <Typography variant="body2">
                {t("low_confidence_tooltip")}
              </Typography>
            </Alert>
          )}
        </Box>
      )}

      {/* 3. 4 KPI Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {isLoading ? (
          [1, 2, 3, 4].map((i) => (
            <Grid key={i} item xs={12} sm={6} lg={3}>
              <Box
                border="1px solid"
                borderColor={paletteTokens.divider}
                borderRadius={2}
                padding={3}
                height="100%"
              >
                <Skeleton variant="text" width={110} height={20} />
                <Skeleton variant="rectangular" width="85%" height={32} sx={{ my: 1 }} />
                <Skeleton variant="text" width={140} height={16} />
              </Box>
            </Grid>
          ))
        ) : forecast ? (
          <>
            {/* Card 1: Current balance */}
            <Grid item xs={12} sm={6} lg={3}>
              <Box
                border="1px solid"
                borderColor={paletteTokens.divider}
                borderRadius={2}
                padding={3}
                height="100%"
                sx={{ backgroundColor: paletteTokens.bgCard }}
              >
                <Typography component="h3" variant="body2" color="text.secondary" mb={1}>
                  {t("kpi_current_balance")}
                </Typography>
                <Typography component="span" variant="h5" fontWeight={700} color="text.primary">
                  {formatValue(Number(forecast.current_balance))}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
                  {t("range")}: {dayjs().format(dateFormat)}
                </Typography>
              </Box>
            </Grid>

            {/* Card 2: Projected end balance */}
            <Grid item xs={12} sm={6} lg={3}>
              <Box
                border="1px solid"
                borderColor={paletteTokens.divider}
                borderRadius={2}
                padding={3}
                height="100%"
                sx={{ backgroundColor: paletteTokens.bgCard }}
              >
                <Typography component="h3" variant="body2" color="text.secondary" mb={1}>
                  {t("kpi_projected_end")} (+{days}d)
                </Typography>
                <Typography
                  component="span"
                  variant="h5"
                  fontWeight={700}
                  color={Number(forecast.projected_end_balance) >= 0 ? "text.primary" : paletteTokens.error}
                >
                  {formatValue(Number(forecast.projected_end_balance))}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
                  {dayjs().add(days, "day").format(dateFormat)}
                </Typography>
              </Box>
            </Grid>

            {/* Card 3: Lowest projected balance */}
            <Grid item xs={12} sm={6} lg={3}>
              <Box
                border="1px solid"
                borderColor={paletteTokens.divider}
                borderRadius={2}
                padding={3}
                height="100%"
                sx={{ backgroundColor: paletteTokens.bgCard }}
              >
                <Typography component="h3" variant="body2" color="text.secondary" mb={1}>
                  {t("kpi_lowest_balance")}
                </Typography>
                <Typography
                  component="span"
                  variant="h5"
                  fontWeight={700}
                  color={
                    Number(forecast.lowest_balance) < 0
                      ? paletteTokens.error
                      : Number(forecast.lowest_balance) < safetyBuffer
                      ? paletteTokens.warning
                      : "text.primary"
                  }
                >
                  {formatValue(Number(forecast.lowest_balance))}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
                  {dayjs(forecast.lowest_balance_date).format(dateFormat)}
                </Typography>
              </Box>
            </Grid>

            {/* Card 4: Daily Burn Rate (EWMA) */}
            <Grid item xs={12} sm={6} lg={3}>
              <Box
                border="1px solid"
                borderColor={paletteTokens.divider}
                borderRadius={2}
                padding={3}
                height="100%"
                sx={{ backgroundColor: paletteTokens.bgCard }}
              >
                <Typography component="h3" variant="body2" color="text.secondary" mb={1}>
                  {t("kpi_daily_burn_rate")}
                </Typography>
                <Typography component="span" variant="h5" fontWeight={700} color="text.primary">
                  ~{formatValue(Number(forecast.daily_burn_rate))}
                </Typography>
                <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: "block" }}>
                  {forecast.history_days_used} {language === "vi" ? "ngày dữ liệu" : "days history"}
                </Typography>
              </Box>
            </Grid>
          </>
        ) : null}
      </Grid>

      {/* 4. ApexCharts Cash Flow Timeline Curve */}
      <Box
        sx={{
          border: "1px solid",
          borderColor: paletteTokens.divider,
          borderRadius: 2,
          p: { xs: 2, md: 3 },
          mb: 3,
          backgroundColor: paletteTokens.bgCard,
        }}
      >
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Box>
            <Typography component="h3" variant="h6" fontWeight={600} color="#fff">
              {t("chart_cashflow_title")}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {language === "vi"
                ? `Mô phỏng quỹ tiền từ ${dayjs().format(dateFormat)} đến ${dayjs().add(days, "day").format(dateFormat)}`
                : `Balance simulation from ${dayjs().format(dateFormat)} to ${dayjs().add(days, "day").format(dateFormat)}`}
            </Typography>
          </Box>
        </Box>

        {isLoading ? (
          <Skeleton variant="rectangular" width="100%" height={360} sx={{ borderRadius: 2 }} />
        ) : chartConfig.series.length > 0 ? (
          <Box sx={{ minHeight: 360, width: "100%", position: "relative" }}>
            <Chart options={chartConfig.options} series={chartConfig.series} type="area" height={360} />
            <Box
              component="div"
              sx={{
                position: "absolute",
                width: 1,
                height: 1,
                padding: 0,
                margin: -1,
                overflow: "hidden",
                clip: "rect(0, 0, 0, 0)",
                whiteSpace: "nowrap",
                border: 0,
              }}
            >
              <Typography variant="subtitle2" component="h3">
                {t("chart_cashflow_title")} - {t("chart_summary")}
              </Typography>
              <p>
                {t("kpi_current_balance")}: {formatValue(Number(forecast?.current_balance || 0))},{" "}
                {t("kpi_projected_end")}: {formatValue(Number(forecast?.projected_end_balance || 0))},{" "}
                {t("kpi_lowest_balance")}: {formatValue(Number(forecast?.lowest_balance || 0))}
              </p>
            </Box>
          </Box>
        ) : (
          <Box py={8} textAlign="center">
            <Typography color="text.secondary">{t("unable_to_load_chart")}</Typography>
          </Box>
        )}
      </Box>

      {/* 5. Bottom Row: Smart Recommendations & Upcoming Fixed Events */}
      <Grid container spacing={3}>
        {/* Recommendations Column */}
        <Grid item xs={12} md={5}>
          <Box
            sx={{
              border: "1px solid",
              borderColor: paletteTokens.divider,
              borderRadius: 2,
              p: { xs: 2, md: 3 },
              height: "100%",
              backgroundColor: paletteTokens.bgCard,
            }}
          >
            <Box display="flex" alignItems="center" gap={1.5} mb={2}>
              <TipsAndUpdatesOutlinedIcon sx={{ color: paletteTokens.primary }} />
              <Typography component="h3" variant="h6" fontWeight={600} color="text.primary">
                {t("recommendations_title")}
              </Typography>
            </Box>

            {isLoading ? (
              [1, 2, 3].map((i) => <Skeleton key={i} variant="rounded" height={64} sx={{ mb: 1.5 }} />)
            ) : forecast?.recommendations && forecast.recommendations.length > 0 ? (
              <Box display="flex" flexDirection="column" gap={1.5}>
                {forecast.recommendations.map((rec: RecommendationItem, idx: number) => {
                  const borderColor = paletteTokens.divider;
                  const bgColor = paletteTokens.bgCard;

                  return (
                    <Box
                      key={idx}
                      sx={{
                        p: 2,
                        borderRadius: 2,
                        border: `1px solid ${borderColor}`,
                        backgroundColor: bgColor,
                      }}
                    >
                      <Typography variant="body2" sx={{ color: "text.primary", lineHeight: 1.5 }}>
                        {renderRecommendationText(rec)}
                      </Typography>
                    </Box>
                  );
                })}
              </Box>
            ) : (
              <Typography color="text.secondary">{t("no_upcoming_events")}</Typography>
            )}
          </Box>
        </Grid>

        {/* Upcoming Fixed Events Table Column */}
        <Grid item xs={12} md={7}>
          <Box
            sx={{
              border: "1px solid",
              borderColor: paletteTokens.divider,
              borderRadius: 2,
              p: { xs: 2, md: 3 },
              height: "100%",
              backgroundColor: paletteTokens.bgCard,
            }}
          >
            <Box display="flex" alignItems="center" gap={1.5} mb={2}>
              <EventNoteOutlinedIcon sx={{ color: paletteTokens.primary }} />
              <Typography component="h3" variant="h6" fontWeight={600} color="text.primary">
                {t("upcoming_events_title")}
              </Typography>
            </Box>

            {isLoading ? (
              <Skeleton variant="rectangular" height={220} sx={{ borderRadius: 2 }} />
            ) : upcomingEvents.length > 0 ? (
              <TableContainer sx={{ maxHeight: 360 }}>
                <Table size="small" stickyHeader>
                  <TableHead>
                    <TableRow>
                      <TableCell sx={{ backgroundColor: paletteTokens.bgCard, color: paletteTokens.textSecondary }}>{t("col_date")}</TableCell>
                      <TableCell sx={{ backgroundColor: paletteTokens.bgCard, color: paletteTokens.textSecondary }}>
                        {t("col_event_title")}
                      </TableCell>
                      <TableCell sx={{ backgroundColor: paletteTokens.bgCard, color: paletteTokens.textSecondary }}>
                        {t("col_event_source")}
                      </TableCell>
                      <TableCell align="right" sx={{ backgroundColor: paletteTokens.bgCard, color: paletteTokens.textSecondary }}>
                        {t("col_value")}
                      </TableCell>
                      <TableCell align="right" sx={{ backgroundColor: paletteTokens.bgCard, color: paletteTokens.textSecondary }}>
                        {t("col_event_balance_after")}
                      </TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {upcomingEvents.map((ev) => {
                      const isIncome = ev.amount >= 0;
                      return (
                        <TableRow key={ev.id} hover sx={{ "&:last-child td, &:last-child th": { border: 0 } }}>
                          <TableCell sx={{ color: grey[400], fontSize: "12px", whiteSpace: "nowrap" }}>
                            {dayjs(ev.date).format(dateFormat)}
                          </TableCell>
                          <TableCell sx={{ color: "#fff", fontWeight: 500, fontSize: "13px" }}>{ev.title}</TableCell>
                          <TableCell>
                            <Chip
                              label={getSourceLabel(ev.source)}
                              size="small"
                              variant="outlined"
                              sx={{
                                borderColor: getSourceChipColor(ev.source),
                                color: getSourceChipColor(ev.source),
                                fontSize: "11px",
                                height: 22,
                              }}
                            />
                          </TableCell>
                          <TableCell
                            align="right"
                            sx={{
                              color: isIncome ? paletteTokens.primary : paletteTokens.error,
                              fontWeight: 600,
                              fontSize: "13px",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {isIncome ? `+${formatValue(ev.amount)}` : `-${formatValue(Math.abs(ev.amount))}`}
                          </TableCell>
                          <TableCell
                            align="right"
                            sx={{
                              color: ev.balanceAfter >= 0 ? "#fff" : paletteTokens.error,
                              fontSize: "13px",
                              whiteSpace: "nowrap",
                            }}
                          >
                            {formatValue(ev.balanceAfter)}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Box py={6} textAlign="center">
                <Typography color="text.secondary">{t("no_upcoming_events")}</Typography>
              </Box>
            )}
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
}
