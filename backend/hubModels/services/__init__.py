"""Services package for hubModels."""

from .forecasting_inputs import (
    FixedEvent,
    ForecastInputs,
    get_daily_variable_spending,
    get_debt_events,
    get_forecast_inputs,
    get_recurring_events,
)
from .forecasting import (
    ForecastResult,
    simulate_cashflow,
    CashFlowForecastService,
    calculate_daily_burn_rate,
)

__all__ = [
    'FixedEvent',
    'ForecastInputs',
    'ForecastResult',
    'get_recurring_events',
    'get_debt_events',
    'get_daily_variable_spending',
    'get_forecast_inputs',
    'simulate_cashflow',
    'CashFlowForecastService',
    'calculate_daily_burn_rate',
]
