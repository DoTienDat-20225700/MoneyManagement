"""
Services for preparing input data for Cash Flow Forecasting (F03).

This module provides data-access routines that gather:
1. Recurring transactions (inflows/outflows)
2. Debt and installment commitments
3. Historical daily variable spending
4. Combined forecasting inputs wrapper

All routines maintain ownership isolation per wallet, execute with a fixed number of queries (O(1)),
and represent monetary amounts with Decimal.
"""

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple

from django.db.models import Sum
from django.utils import timezone

from hubModels.models import DebtLoan, Transaction, Wallet, calculate_installment_schedule_data
from hubModels.recurring import calculate_next_occurrence


VALID_SOURCES = {'RECURRING', 'DEBT', 'INSTALLMENT'}


@dataclass(frozen=True)
class FixedEvent:
    """
    Immutable representation of a deterministic cash flow event.

    Attributes:
        date: Scheduled date of the cash flow event.
        title: Human-readable title or label of the event.
        amount: Signed Decimal amount (positive for income/inflows, negative for expense/outflows).
        source: Origin type, one of 'RECURRING', 'DEBT', 'INSTALLMENT'.
        source_id: Database ID of the underlying model instance.
    """
    date: date
    title: str
    amount: Decimal
    source: str
    source_id: int

    def __post_init__(self):
        if self.source not in VALID_SOURCES:
            raise ValueError(f"source must be one of {VALID_SOURCES}, got '{self.source}'")
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, 'amount', Decimal(str(self.amount)))


@dataclass(frozen=True)
class ForecastInputs:
    """
    Encapsulates all aggregated inputs required by cash flow forecasting algorithms.

    Attributes:
        current_balance: Current wallet amount.
        today: Reference calculation date (local date).
        horizon_end: End date of forecasting horizon (today + days).
        events: Chronologically sorted deterministic fixed events.
        daily_variable_history: List of (date, spending) tuples for past history_days.
    """
    current_balance: Decimal
    today: date
    horizon_end: date
    events: List[FixedEvent]
    daily_variable_history: List[Tuple[date, Decimal]]

    def __getitem__(self, item):
        return getattr(self, item)

    def to_dict(self) -> dict:
        return asdict(self)


def get_recurring_events(
    wallet: Wallet,
    start: date,
    end: date,
    today: Optional[date] = None,
) -> List[FixedEvent]:
    """
    Generate recurring events for a given wallet within date range [start, end].

    Business Rules:
    1. Only active recurrent schedules for the specified wallet with update_wallet=True are loaded.
       Schedules with update_wallet=False are ignored because they do not impact wallet balance.
    2. Occurrences already generated as real Transaction rows are skipped to avoid double counting
       against current_balance.
    3. Ungenerated occurrences rule:
       If an occurrence is due today or in the past (occ_date <= today) but has not yet been generated
       as a real Transaction (e.g. background cron has not executed yet), it is assumed that it will occur
       today (event_date = today).
    4. Future occurrences (occ_date > today) occur on their respective occ_date.
    5. Recurrence end_date is respected; occurrences strictly past end_date are discarded.
    6. EXPENSE transactions yield negative amounts; EARNING transactions yield positive amounts.

    Query Performance:
    Loads all relevant schedules and prefetches generated transactions using 2 database queries,
    remaining constant (O(1)) regardless of the number of recurring schedules.
    """
    if today is None:
        today = timezone.localdate()

    # Load active schedules and prefetched generated child transactions
    base_txs = list(
        Transaction.objects.filter(
            wallet=wallet,
            recurrent=True,
            recurrency__active=True,
            update_wallet=True,
        ).select_related('recurrency').prefetch_related('transaction_set')
    )

    events: List[FixedEvent] = []

    for tx in base_txs:
        rec = getattr(tx, 'recurrency', None)
        if not rec or not rec.active:
            continue
        if not rec.amount or rec.amount <= 0:
            continue
        if rec.duration not in {'DAYS', 'WEEKS', 'MONTHS', 'YEARS'}:
            continue

        base_date = tx.date
        end_date_limit = rec.end_date.date() if isinstance(rec.end_date, datetime) else rec.end_date

        generated_dates = {child.date for child in tx.transaction_set.all()}

        if tx.type == 'EXPENSE':
            signed_amount = -Decimal(str(tx.value))
        elif tx.type == 'EARNING':
            signed_amount = Decimal(str(tx.value))
        else:
            continue

        step = 1
        while True:
            occ_date = calculate_next_occurrence(base_date, rec.amount, rec.duration, step)

            # Respect recurrence end_date
            if end_date_limit and occ_date > end_date_limit:
                break

            # Monotonic increase check: if past horizon end and past today, stop
            if occ_date > end and occ_date > today:
                break

            # Skip occurrences already materialized as real transactions
            if occ_date in generated_dates:
                step += 1
                if step > 1000:
                    break
                continue

            # Apply ungenerated occurrence rule:
            # Due today or in the past but ungenerated -> treated as occurring today
            if occ_date <= today:
                event_date = today
            else:
                event_date = occ_date

            if start <= event_date <= end:
                events.append(FixedEvent(
                    date=event_date,
                    title=tx.title,
                    amount=signed_amount,
                    source='RECURRING',
                    source_id=tx.id,
                ))

            step += 1
            if step > 1000:
                break

    return sorted(events, key=lambda e: (e.date, e.source_id))


def get_debt_events(
    wallet: Wallet,
    start: date,
    end: date,
    include_receivables: bool = False,
    today: Optional[date] = None,
) -> List[FixedEvent]:
    """
    Generate cash flow events from debt, loan, and installment contracts within [start, end].

    Business Assumptions & Rules:
    1. Future debt settlements assumption:
       All future settlements are assumed to affect the wallet balance (update_wallet=True).
    2. Overdue and due date rules:
       - DEBT_BORROWED: If remaining balance > 0 and due_date in [start, end], emits an outflow (-remaining).
         If due_date is overdue (due_date < today) and remaining balance > 0, it is treated as due today.
       - INSTALLMENT: Evaluates the payment schedule in memory. For each unpaid period whose due_date
         falls within [start, end], emits an outflow for the unpaid portion of that period.
         If an unpaid period is overdue (period due_date < today), it is treated as due today.
       - LOAN_GIVEN: By default (include_receivables=False), no events are emitted (conservative cash flow).
         If include_receivables=True, emits an inflow (+remaining) on due_date if due_date >= today
         and due_date falls within [start, end]. Overdue receivables are excluded.
    3. Contracts with status FULLY_PAID or CLOSED, or contracts with remaining balance <= 0, are ignored.

    Query Performance:
    Loads non-closed contracts with prefetched payments in 2 database queries, avoiding N+1 queries.
    """
    if today is None:
        today = timezone.localdate()

    debts = list(
        DebtLoan.objects.filter(
            wallet=wallet,
        ).exclude(
            status__in=['FULLY_PAID', 'CLOSED']
        ).prefetch_related('payments')
    )

    events: List[FixedEvent] = []

    for debt in debts:
        total_paid = sum((p.amount for p in debt.payments.all()), Decimal('0.00'))
        remaining = max(Decimal('0.00'), debt.principal_amount - total_paid)
        if remaining <= Decimal('0.00'):
            continue

        if debt.type == 'DEBT_BORROWED':
            if not debt.due_date:
                continue

            if debt.due_date < today:
                event_date = today
            else:
                event_date = debt.due_date

            if start <= event_date <= end:
                events.append(FixedEvent(
                    date=event_date,
                    title=debt.person_name,
                    amount=-remaining,
                    source='DEBT',
                    source_id=debt.id,
                ))

        elif debt.type == 'INSTALLMENT':
            schedule = calculate_installment_schedule_data(
                debt.principal_amount,
                debt.installment_months or 0,
                debt.start_date,
                total_paid,
            )
            for item in schedule:
                if item['is_paid']:
                    continue

                period_amount = Decimal(item['amount'])
                period_paid = Decimal(item['paid_amount'])
                unpaid = period_amount - period_paid
                if unpaid <= Decimal('0.00'):
                    continue

                period_due = date.fromisoformat(item['due_date'])
                if period_due < today:
                    event_date = today
                else:
                    event_date = period_due

                if start <= event_date <= end:
                    events.append(FixedEvent(
                        date=event_date,
                        title=f"{debt.person_name} (Kỳ {item['installment_no']})",
                        amount=-unpaid,
                        source='INSTALLMENT',
                        source_id=debt.id,
                    ))

        elif debt.type == 'LOAN_GIVEN':
            if not include_receivables:
                continue
            if not debt.due_date or debt.due_date < today:
                continue

            if start <= debt.due_date <= end:
                events.append(FixedEvent(
                    date=debt.due_date,
                    title=debt.person_name,
                    amount=remaining,
                    source='DEBT',
                    source_id=debt.id,
                ))

    return sorted(events, key=lambda e: (e.date, e.source_id))


def get_daily_variable_spending(
    wallet: Wallet,
    end: date,
    days: int = 60,
) -> List[Tuple[date, Decimal]]:
    """
    Retrieve historical daily variable spending for a wallet over the interval [end - days + 1, end].

    Business Rules:
    1. Returns exactly `days` tuples of (date, amount), ordered ascending by date.
    2. Days without variable expenses are assigned Decimal('0.00').
    3. Excludes:
       - Recurring base transactions (recurrent=True)
       - Generated recurring transactions (base_transaction_id is not null)
       - Inflows (type != 'EXPENSE')
       - Transactions with update_wallet=False (do not impact wallet balance)

    Query Performance:
    Executes exactly 1 database query aggregating by date using values().annotate(Sum('value')).
    """
    if days <= 0:
        return []

    start_date = end - timedelta(days=days - 1)

    qs = (
        Transaction.objects.filter(
            wallet=wallet,
            type='EXPENSE',
            update_wallet=True,
            date__range=[start_date, end],
            base_transaction__isnull=True,
            recurrent=False,
        )
        .values('date')
        .annotate(daily_total=Sum('value'))
    )

    spending_map = {row['date']: row['daily_total'] or Decimal('0.00') for row in qs}

    result: List[Tuple[date, Decimal]] = []
    for i in range(days):
        cur_date = start_date + timedelta(days=i)
        result.append((cur_date, spending_map.get(cur_date, Decimal('0.00'))))

    return result


def get_forecast_inputs(
    wallet: Wallet,
    days: int,
    history_days: int = 60,
    include_receivables: bool = False,
    today: Optional[date] = None,
) -> ForecastInputs:
    """
    Aggregate all inputs required for cash flow forecasting across a specified horizon.

    Parameters:
        wallet: The target Wallet instance (ownership isolated).
        days: Forecasting horizon in days; strictly validated to be 30, 60, or 90.
        history_days: Number of past days for variable spending history (default: 60).
        include_receivables: Whether to include non-overdue LOAN_GIVEN receivables.
        today: Reference calculation date; defaults to timezone.localdate().

    Returns:
        ForecastInputs dataclass containing current_balance, today, horizon_end,
        sorted fixed events, and daily variable spending history.
    """
    if days not in (30, 60, 90):
        raise ValueError("days must be one of [30, 60, 90]")

    if today is None:
        today = timezone.localdate()

    horizon_end = today + timedelta(days=days)

    recurring_events = get_recurring_events(wallet, start=today, end=horizon_end, today=today)
    debt_events = get_debt_events(wallet, start=today, end=horizon_end, include_receivables=include_receivables, today=today)

    all_events = sorted(recurring_events + debt_events, key=lambda e: (e.date, e.source, e.source_id))
    history = get_daily_variable_spending(wallet, end=today, days=history_days)

    return ForecastInputs(
        current_balance=wallet.current_amount,
        today=today,
        horizon_end=horizon_end,
        events=all_events,
        daily_variable_history=history,
    )
