"""
Cash Flow Forecasting & Insolvency Risk Detection Engine (F03).

This service implements a deterministic cash flow simulation algorithm:
1. Daily variable burn rate estimation using Winsorized Exponentially Weighted Moving Average (EWMA).
2. Dynamic balance timeline simulation over horizons of 30, 60, or 90 days.
3. Liquidity risk detection (SAFE, WARNING, CRITICAL) and maximum shortfall quantification.
4. Structured advisory recommendations for proactive cash management.

Architecture:
- simulate_cashflow: Pure deterministic function decoupled from database/ORM for testing and backtesting.
- CashFlowForecastService: Service class integrating with forecasting_inputs.py with O(1) database queries.
"""

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
import math
from typing import Any, Dict, List, Optional, Tuple, Union

from hubModels.models import Wallet
from hubModels.services.forecasting_inputs import FixedEvent, get_forecast_inputs


@dataclass(frozen=True)
class ForecastResult:
    """
    Immutable outcome of a cash flow forecasting simulation.
    """
    horizon_days: int
    current_balance: Decimal
    projected_end_balance: Decimal
    lowest_balance: Decimal
    lowest_balance_date: date
    first_warning_date: Optional[date]
    first_negative_date: Optional[date]
    max_shortfall: Decimal
    risk_level: str
    is_insolvency_risk: bool
    daily_burn_rate: Decimal
    low_confidence: bool
    history_days_used: int
    daily_timeline: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]

    def __getitem__(self, item: str) -> Any:
        return getattr(self, item)

    def to_dict(self) -> Dict[str, Any]:
        """
        Converts the forecast result into an API-ready serializable dictionary
        with currency values formatted to 2 decimal places and ISO dates.
        """
        return {
            'horizon_days': self.horizon_days,
            'current_balance': f"{self.current_balance:.2f}",
            'projected_end_balance': f"{self.projected_end_balance:.2f}",
            'lowest_balance': f"{self.lowest_balance:.2f}",
            'lowest_balance_date': self.lowest_balance_date.isoformat(),
            'first_warning_date': self.first_warning_date.isoformat() if self.first_warning_date else None,
            'first_negative_date': self.first_negative_date.isoformat() if self.first_negative_date else None,
            'max_shortfall': f"{self.max_shortfall:.2f}",
            'risk_level': self.risk_level,
            'is_insolvency_risk': self.is_insolvency_risk,
            'daily_burn_rate': f"{self.daily_burn_rate:.2f}",
            'low_confidence': self.low_confidence,
            'history_days_used': self.history_days_used,
            'daily_timeline': [
                {
                    'date': pt['date'].isoformat() if isinstance(pt['date'], (date, datetime)) else str(pt['date']),
                    'balance': f"{Decimal(str(pt['balance'])):.2f}",
                    'fixed_events': [
                        {
                            'title': fe['title'],
                            'amount': f"{Decimal(str(fe['amount'])):.2f}",
                            'source': fe['source'],
                        }
                        for fe in pt.get('fixed_events', [])
                    ],
                }
                for pt in self.daily_timeline
            ],
            'recommendations': self.recommendations,
        }


def calculate_daily_burn_rate(
    daily_history: List[Union[Tuple[date, Decimal], Decimal, float, int]],
    today: date,
    alpha: Decimal = Decimal('0.2'),
    estimator: str = "ewma",
    winsorize: bool = True,
) -> Tuple[Decimal, bool, int]:
    """
    Estimates daily variable spending burn rate (D_variable) using Winsorized EWMA or Simple Mean.

    Parameters:
    - estimator: "ewma" (default) or "mean" (simple average across historical series).
    - winsorize: True (default) caps extreme outliers at mu + 3 * sigma; False keeps original values.
    - alpha: EWMA smoothing factor (default 0.2).

    Outlier Winsorization Rule:
    When winsorize=True, observations exceeding mu + 3 * sigma are capped (winsorized).
    No days are dropped to maintain the full historical continuum.

    Estimation Rule:
    - If estimator == "ewma":
        EWMA_t = alpha * X_t + (1 - alpha) * EWMA_(t-1), initialized using average of the first 7 days.
    - If estimator == "mean":
        Simple arithmetic mean across the entire (winsorized or raw) history.

    Confidence Rule:
    low_confidence is True if the number of historical days from the first non-zero spending
    up to today is less than 14. If there is no spending history, D_variable = 0 and low_confidence = True.

    Returns:
        (D_variable, low_confidence, history_days_used)
    """
    if not daily_history:
        return Decimal('0.00'), True, 0

    # Extract date and value
    parsed_items: List[Tuple[Optional[date], Decimal]] = []
    for item in daily_history:
        if isinstance(item, tuple) and len(item) == 2:
            d_val = item[0] if isinstance(item[0], date) else None
            parsed_items.append((d_val, Decimal(str(item[1]))))
        else:
            parsed_items.append((None, Decimal(str(item))))

    values = [val for _, val in parsed_items]
    n = len(values)

    # Detect first actual spending date
    first_spending_idx: Optional[int] = None
    for idx, val in enumerate(values):
        if val > Decimal('0.00'):
            first_spending_idx = idx
            break

    if first_spending_idx is None:
        # No recorded spending in history
        return Decimal('0.00'), True, 0

    first_item = parsed_items[first_spending_idx]
    if first_item[0] is not None:
        history_days_used = max(1, (today - first_item[0]).days + 1)
    else:
        history_days_used = n - first_spending_idx

    low_confidence = history_days_used < 14

    # Outlier handling: Winsorization or Raw values
    if winsorize:
        mean_val = sum(values) / Decimal(n)
        variance = sum((x - mean_val) ** 2 for x in values) / Decimal(n)
        std_dev = Decimal(str(math.sqrt(float(variance))))
        upper_threshold = mean_val + Decimal('3') * std_dev
        processed_values = [min(x, upper_threshold) for x in values]
    else:
        processed_values = list(values)

    # Estimator selection
    if estimator == "mean":
        d_val = sum(processed_values) / Decimal(len(processed_values))
    elif estimator == "ewma":
        k = min(7, n)
        init_avg = sum(processed_values[:k]) / Decimal(k)
        ewma = init_avg
        for x in processed_values[k:]:
            ewma = alpha * x + (Decimal('1') - alpha) * ewma
        d_val = ewma
    else:
        raise ValueError(f"Unknown estimator: {estimator}. Supported options are 'ewma' and 'mean'.")

    d_variable = d_val.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    return d_variable, low_confidence, history_days_used


def simulate_cashflow(
    current_balance: Decimal,
    events: List[Union[FixedEvent, Dict[str, Any]]],
    daily_history: List[Union[Tuple[date, Decimal], Decimal, float, int]],
    today: date,
    days: int,
    safety_buffer: Decimal = Decimal('0.00'),
    alpha: Decimal = Decimal('0.2'),
    estimator: str = "ewma",
    winsorize: bool = True,
) -> ForecastResult:
    """
    Pure simulation function that projects daily cash balances without any database calls.

    Timeline Rules:
    - Timeline spans days + 1 points, from t=0 (today) to t=days (today + days).
    - t=0: balance = current_balance + sum(fixed events on today).
      Variable spending is NOT deducted on t=0 because current_balance already incorporates today's spending.
    - t>=1: W(t) = W(t-1) + sum(fixed events on date t) - D_variable.

    Risk Detection Rules:
    - lowest_balance and lowest_balance_date (first date where balance reaches lowest level).
    - first_warning_date: first date where balance < safety_buffer.
    - first_negative_date: first date where balance < 0.
    - risk_level:
        CRITICAL if any balance < 0
        WARNING if balance < safety_buffer (and not negative, safety_buffer > 0)
        SAFE otherwise
    - is_insolvency_risk = (risk_level == 'CRITICAL')
    - max_shortfall = maximum shortfall amount (abs of lowest balance if negative, else 0).

    Recommendations:
    - SHORTFALL_RISK: identifies largest fixed outflow on or immediately before insolvency date.
    - REDUCE_DAILY_SPENDING: calculates required daily spending cut to avert insolvency.
    - BELOW_BUFFER: warns about dip below safety buffer.
    - LOW_CONFIDENCE: advises when historical data is under 14 days.
    - ALL_CLEAR: emitted when risk level is SAFE.
    """
    if not isinstance(current_balance, Decimal):
        current_balance = Decimal(str(current_balance))
    if not isinstance(safety_buffer, Decimal):
        safety_buffer = Decimal(str(safety_buffer))

    d_variable, low_confidence, history_days_used = calculate_daily_burn_rate(
        daily_history=daily_history,
        today=today,
        alpha=alpha,
        estimator=estimator,
        winsorize=winsorize,
    )

    # Standardize events into (date, amount, title, source)
    normalized_events: List[Dict[str, Any]] = []
    for ev in events:
        if isinstance(ev, dict):
            ev_date = ev['date'] if isinstance(ev['date'], date) else date.fromisoformat(str(ev['date']))
            ev_amt = Decimal(str(ev['amount']))
            ev_title = str(ev.get('title', ''))
            ev_source = str(ev.get('source', ''))
        else:
            ev_date = ev.date
            ev_amt = Decimal(str(ev.amount))
            ev_title = ev.title
            ev_source = ev.source
        normalized_events.append({
            'date': ev_date,
            'amount': ev_amt,
            'title': ev_title,
            'source': ev_source,
        })

    # Group fixed events by date
    events_by_date: Dict[date, List[Dict[str, Any]]] = {}
    for ev in normalized_events:
        events_by_date.setdefault(ev['date'], []).append(ev)

    # Build timeline: days + 1 points (t = 0 to days)
    daily_timeline: List[Dict[str, Any]] = []
    prev_balance = current_balance

    lowest_balance: Optional[Decimal] = None
    lowest_balance_date: date = today
    first_negative_date: Optional[date] = None
    first_warning_date: Optional[date] = None

    for t in range(days + 1):
        cur_date = today + timedelta(days=t)
        cur_events = events_by_date.get(cur_date, [])
        fixed_sum = sum((e['amount'] for e in cur_events), Decimal('0.00'))

        if t == 0:
            balance = current_balance + fixed_sum
        else:
            balance = prev_balance + fixed_sum - d_variable

        prev_balance = balance

        # Track lowest balance and dates
        if lowest_balance is None or balance < lowest_balance:
            lowest_balance = balance
            lowest_balance_date = cur_date

        if balance < Decimal('0.00') and first_negative_date is None:
            first_negative_date = cur_date

        if balance < safety_buffer and first_warning_date is None:
            first_warning_date = cur_date

        daily_timeline.append({
            'date': cur_date,
            'balance': balance,
            'fixed_events': [
                {
                    'title': e['title'],
                    'amount': e['amount'],
                    'source': e['source'],
                }
                for e in cur_events
            ],
        })

    assert lowest_balance is not None
    projected_end_balance = daily_timeline[-1]['balance']

    # Determine risk level & shortfall
    if lowest_balance < Decimal('0.00'):
        risk_level = 'CRITICAL'
        is_insolvency_risk = True
        max_shortfall = abs(lowest_balance)
    elif safety_buffer > Decimal('0.00') and first_warning_date is not None:
        risk_level = 'WARNING'
        is_insolvency_risk = False
        max_shortfall = Decimal('0.00')
    else:
        risk_level = 'SAFE'
        is_insolvency_risk = False
        max_shortfall = Decimal('0.00')

    # Generate structured recommendations
    recommendations: List[Dict[str, Any]] = []

    if low_confidence:
        recommendations.append({
            'code': 'LOW_CONFIDENCE',
            'params': {},
        })

    if risk_level == 'CRITICAL':
        assert first_negative_date is not None
        # Identify the largest fixed expense on or before first_negative_date
        relevant_fixed_expenses = [
            e for e in normalized_events
            if e['date'] <= first_negative_date and e['amount'] < Decimal('0.00')
        ]
        if relevant_fixed_expenses:
            largest_expense_event = min(relevant_fixed_expenses, key=lambda e: e['amount'])
            event_title = largest_expense_event['title']
        else:
            event_title = "Chi tiêu sinh hoạt định kỳ"

        recommendations.append({
            'code': 'SHORTFALL_RISK',
            'params': {
                'date': first_negative_date.isoformat(),
                'shortfall': f"{max_shortfall:.2f}",
                'event_title': event_title,
            },
        })

        days_until = (first_negative_date - today).days
        if days_until > 0:
            daily_cut = (max_shortfall / Decimal(days_until)).quantize(Decimal('1'), rounding=ROUND_CEILING)
            recommendations.append({
                'code': 'REDUCE_DAILY_SPENDING',
                'params': {
                    'days_until': days_until,
                    'daily_cut': f"{daily_cut:.2f}",
                },
            })

    elif risk_level == 'WARNING':
        assert first_warning_date is not None
        recommendations.append({
            'code': 'BELOW_BUFFER',
            'params': {
                'date': first_warning_date.isoformat(),
                'buffer': f"{safety_buffer:.2f}",
            },
        })

    else:
        recommendations.append({
            'code': 'ALL_CLEAR',
            'params': {},
        })

    return ForecastResult(
        horizon_days=days,
        current_balance=current_balance,
        projected_end_balance=projected_end_balance,
        lowest_balance=lowest_balance,
        lowest_balance_date=lowest_balance_date,
        first_warning_date=first_warning_date,
        first_negative_date=first_negative_date,
        max_shortfall=max_shortfall,
        risk_level=risk_level,
        is_insolvency_risk=is_insolvency_risk,
        daily_burn_rate=d_variable,
        low_confidence=low_confidence,
        history_days_used=history_days_used,
        daily_timeline=daily_timeline,
        recommendations=recommendations,
    )


class CashFlowForecastService:
    """
    Facade service integrating data-access inputs with the pure simulation algorithm.
    Guarantees O(1) fixed database queries.
    """

    @classmethod
    def forecast(
        cls,
        wallet: Wallet,
        days: int = 30,
        safety_buffer: Decimal = Decimal('0.00'),
    ) -> ForecastResult:
        """
        Executes a cash flow forecast for the given wallet.
        """
        inputs = get_forecast_inputs(wallet, days=days)
        return simulate_cashflow(
            current_balance=inputs.current_balance,
            events=inputs.events,
            daily_history=inputs.daily_variable_history,
            today=inputs.today,
            days=days,
            safety_buffer=safety_buffer,
        )
