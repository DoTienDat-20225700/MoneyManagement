import {
  Box,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { ApexOptions } from "apexcharts";
import { useMemo, useState } from "react";
import Chart from "react-apexcharts";
import {
  PieChartRangeOptions,
  PieChartRangeType,
  getPieChartOptionById,
} from "../../enums/Enums";
import { useTransactions } from "../../hooks/api/useTransactions";
import { AggregatedExpense } from "../../models/Transaction";
import { paletteTokens } from "../../theme";
import { getStartDate, pieRangeOptionMask, formatValue } from "../../utils/utils";
import { useLanguage } from "../../context/LanguageContext";
import { usePrefersReducedMotion } from "../../hooks/usePrefersReducedMotion";

function ProfileChart() {
  const { language, t } = useLanguage();
  const prefersReducedMotion = usePrefersReducedMotion();
  const { getTransactions } = useTransactions();

  const [range, setRange] = useState<PieChartRangeType>(
    PieChartRangeOptions.Last30Days
  );

  const endDate = new Date(new Date()); //TO-DO
  const startDate = useMemo(() => {
    return getStartDate(range);
  }, [range]);

  type PromiseType<T> = T extends Promise<infer U> ? U : T;

  const { data: transactions } = useQuery({
    queryKey: ["transactions", startDate],
    queryFn: () => getTransactions(0, 2, startDate, endDate),
  }) as { data: PromiseType<AggregatedExpense[]> };

  const processedData = useMemo(() => {
    if (!transactions || transactions.length === 0) {
      return { labels: [], amounts: [], colors: [] };
    }
    // Sort descending by value (per Rule 9)
    const sorted = [...transactions].sort((a, b) => Number(b.value) - Number(a.value));

    const top5 = sorted.slice(0, 5);
    const rest = sorted.slice(5);

    const finalLabels: string[] = top5.map((obj: AggregatedExpense) =>
      obj.label_name === "Chưa phân loại" ? t("uncategorized") : obj.label_name
    );
    const finalAmounts: number[] = top5.map((obj: AggregatedExpense) => Number(obj.value));
    const finalColors: string[] = top5.map((_, i) => paletteTokens.chart.colors[i]);

    if (rest.length > 0) {
      const restSum = rest.reduce((sum, item) => sum + Number(item.value), 0);
      if (restSum > 0) {
        finalLabels.push(language === "vi" ? "Khác" : "Other");
        finalAmounts.push(restSum);
        finalColors.push(paletteTokens.chart.neutral);
      }
    }

    return {
      labels: finalLabels,
      amounts: finalAmounts,
      colors: finalColors,
    };
  }, [transactions, t]);

  const state = useMemo<{
    series: ApexAxisChartSeries | ApexNonAxisChartSeries;
    options: ApexOptions;
  }>(() => {
    return {
      series: processedData.amounts,
      options: {
        labels: processedData.labels,
        colors: processedData.colors,
        chart: {
          id: "pie",
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
        } as ApexLegend,
        yaxis: {
          labels: {
            formatter: function (val) {
              return formatValue(val);
            },
          },
        },
        tooltip: {
          theme: "dark",
          y: {
            formatter: function (val) {
              return formatValue(val);
            },
          },
        },
        stroke: {
          show: false,
        },
      },
    };
  }, [processedData, prefersReducedMotion]);

  return (
    <Box
      border="1px solid"
      borderColor={paletteTokens.divider}
      borderRadius={2}
      padding={3}
      height={380}
      sx={{ backgroundColor: paletteTokens.bgCard }}
    >
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <Typography component="h2" variant="body1" mb={1}>
          {t("expenses_distribution")}
        </Typography>
        <FormControl size="small" sx={{ width: "200px" }}>
          <InputLabel id="pie-chart-range-select-label">{t("range")}</InputLabel>
          <Select
            labelId="pie-chart-range-select-label"
            id="pie-chart-range-select"
            value={range.id}
            label={t("range")}
            onChange={(e) =>
              setRange(getPieChartOptionById(Number(e.target.value)))
            }
          >
            {Object.values(PieChartRangeOptions).map((item, index) => {
              return (
                <MenuItem key={index} value={item.id}>
                  {pieRangeOptionMask(item, language)}
                </MenuItem>
              );
            })}
          </Select>
        </FormControl>
      </Box>
      {transactions ? (
        <Chart
          options={state.options}
          series={state.series}
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
  );
}

export default ProfileChart;
