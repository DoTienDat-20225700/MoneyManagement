import {
  BarChartRangeOptions,
  BarChartRangeType,
  PieChartRangeOptions,
  PieChartRangeType,
} from "../enums/Enums";

export function formatValue(
  value: number | string | null | undefined,
  _limit?: number
): string {
  if (value === null || value === undefined || value === "") {
    return "0đ";
  }

  const num = typeof value === "string" ? parseFloat(value) : value;
  if (isNaN(num)) {
    return "0đ";
  }

  const sign = num < 0 ? "-" : "";
  const absVal = Math.round(Math.abs(num));
  const formatted = absVal.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ".");

  return `${sign}${formatted}đ`;
}

export function formatCurrency(
  value: string | number | null | undefined
): string {
  if (value === undefined || value === null) return "";
  const stringValue = value.toString();
  let cleanValue = stringValue.replace(/\D/g, "");
  if (!cleanValue) return "";
  cleanValue = cleanValue.replace(/^0+(?!$)/, "");
  return cleanValue.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

export function getStartDate(range: BarChartRangeType | PieChartRangeType) {
  const today = new Date();

  const startDate = new Date(
    today.getFullYear(),
    today.getMonth(),
    today.getDate() - range.amount
  );

  return startDate;
}

export function barRangeOptionMask(option: BarChartRangeType) {
  switch (option) {
    case BarChartRangeOptions.LastMonth:
      return "Last month";
    case BarChartRangeOptions.LastWeek:
      return "Last week";
    case BarChartRangeOptions.LastTwoWeeks:
      return "Last two weeks";
  }
}

export function pieRangeOptionMask(option: PieChartRangeType) {
  switch (option) {
    case PieChartRangeOptions.Last30Days:
      return "Last 30 days";
    case PieChartRangeOptions.Last90Days:
      return "Last 90 days";
    case PieChartRangeOptions.Last180Days:
      return "Last 180 days";
  }
}
