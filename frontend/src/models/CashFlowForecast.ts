export type RiskLevel = "SAFE" | "WARNING" | "CRITICAL";

export interface FixedEventItem {
  title: string;
  amount: string;
  source: "RECURRING" | "DEBT" | "INSTALLMENT";
}

export interface DailyTimelinePoint {
  date: string;
  balance: string;
  fixed_events: FixedEventItem[];
}

export interface RecommendationItem {
  code:
    | "SHORTFALL_RISK"
    | "REDUCE_DAILY_SPENDING"
    | "BELOW_BUFFER"
    | "LOW_CONFIDENCE"
    | "ALL_CLEAR";
  params: Record<string, any>;
}

export interface CashFlowForecastResponse {
  horizon_days: number;
  current_balance: string;
  projected_end_balance: string;
  lowest_balance: string;
  lowest_balance_date: string;
  first_warning_date: string | null;
  first_negative_date: string | null;
  max_shortfall: string;
  risk_level: RiskLevel;
  is_insolvency_risk: boolean;
  daily_burn_rate: string;
  low_confidence: boolean;
  history_days_used: number;
  daily_timeline: DailyTimelinePoint[];
  recommendations: RecommendationItem[];
}

export interface ForecastParams {
  days?: 30 | 60 | 90;
  safety_buffer?: number | string;
}
