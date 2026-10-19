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
import { darkTheme } from "../../theme";
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

  const colors = transactions
    ? transactions.map((obj: AggregatedExpense) => obj.label_color)
    : [];
  const amounts = transactions
    ? transactions.map((obj: AggregatedExpense) => obj.value)
    : [];
  const labels = transactions
    ? transactions.map((obj: AggregatedExpense) =>
        obj.label_name === "Chưa phân loại" ? t("uncategorized") : obj.label_name
      )
    : [];

  const state = useMemo<{
    series: ApexAxisChartSeries | ApexNonAxisChartSeries;
    options: ApexOptions;
  }>(() => {
    return {
      series: amounts,
      options: {
        labels: labels,
        colors: colors,
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
            colors: darkTheme.palette.text.secondary,
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
  }, [transactions, prefersReducedMotion]);

  return (
    <Box
      border="1px solid"
      borderColor={darkTheme.palette.background.paper}
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
        <>
          <Box
            sx={{
              position: "absolute",
              width: "1px",
              height: "1px",
              padding: 0,
              margin: "-1px",
              overflow: "hidden",
              clip: "rect(0, 0, 0, 0)",
              whiteSpace: "nowrap",
              border: 0,
            }}
            component="section"
            aria-label={t("expenses_distribution")}
          >
            <table>
              <caption>{t("expenses_distribution")} - {t("chart_summary")}</caption>
              <thead>
                <tr>
                  <th>{t("label")}</th>
                  <th>{t("amount")}</th>
                </tr>
              </thead>
              <tbody>
                {transactions?.map((item, i) => (
                  <tr key={i}>
                    <td>{item.label_name}</td>
                    <td>{formatValue(item.value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Box>
          <Chart
            options={state.options}
            series={state.series}
            type="pie"
            width="90%"
            height="300px"
          />
        </>
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
