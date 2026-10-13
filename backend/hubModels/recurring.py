import logging
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from django.db import transaction as db_transaction, IntegrityError
from .models import Transaction, TransactionRecurrency

logger = logging.getLogger(__name__)


def calculate_next_occurrence(base_date: date, amount: int, duration: str, step: int) -> date:
    """Calculate the k-th recurrence date from a base date."""
    if duration == 'DAYS':
        return base_date + timedelta(days=step * amount)
    elif duration == 'WEEKS':
        return base_date + timedelta(weeks=step * amount)
    elif duration == 'MONTHS':
        return base_date + relativedelta(months=step * amount)
    elif duration == 'YEARS':
        return base_date + relativedelta(years=step * amount)
    raise ValueError(f"Unsupported recurrence duration: {duration}")


def process_due_recurring_transactions(as_of_date: date = None) -> dict:
    """
    Scans all active recurrent transactions and generates occurrences due up to `as_of_date`.
    Ensures idempotency using database constraints and existence checks.
    Deactivates schedules that have passed their `end_date`.
    """
    if as_of_date is None:
        as_of_date = date.today()
    elif isinstance(as_of_date, datetime):
        as_of_date = as_of_date.date()

    active_recurrencies = TransactionRecurrency.objects.filter(
        active=True,
        transaction__recurrent=True,
    ).select_related('transaction', 'transaction__wallet', 'transaction__label')

    generated_count = 0
    deactivated_count = 0
    generated_transactions = []

    for rec in active_recurrencies:
        base_tx = rec.transaction
        if not base_tx:
            continue

        if not rec.amount or rec.amount <= 0:
            logger.warning(f"Transaction {base_tx.pk} has invalid recurrence amount: {rec.amount}")
            continue

        valid_durations = {choice[0] for choice in TransactionRecurrency.DURATION_TYPES}
        if rec.duration not in valid_durations:
            logger.warning(f"Transaction {base_tx.pk} has invalid recurrence duration: {rec.duration}")
            continue

        base_date = base_tx.date
        end_date_limit = None
        if rec.end_date:
            end_date_limit = rec.end_date.date() if isinstance(rec.end_date, datetime) else rec.end_date

        # Check if the schedule has already expired before the base date or today
        if end_date_limit and end_date_limit < as_of_date and end_date_limit < base_date:
            rec.active = False
            rec.save(update_fields=['active'])
            deactivated_count += 1
            continue

        step = 1
        while True:
            occ_date = calculate_next_occurrence(base_date, rec.amount, rec.duration, step)

            # Do not generate occurrences past as_of_date (never generate future occurrences)
            if occ_date > as_of_date:
                break

            # If an end date is configured and this occurrence is past end_date, deactivate and stop
            if end_date_limit and occ_date > end_date_limit:
                rec.active = False
                rec.save(update_fields=['active'])
                deactivated_count += 1
                break

            # Idempotency check: verify if this occurrence already exists
            already_exists = Transaction.objects.filter(
                base_transaction=base_tx,
                date=occ_date
            ).exists()

            if not already_exists:
                try:
                    with db_transaction.atomic():
                        new_tx = Transaction(
                            base_transaction=base_tx,
                            wallet=base_tx.wallet,
                            title=base_tx.title,
                            value=base_tx.value,
                            type=base_tx.type,
                            label=base_tx.label,
                            date=occ_date,
                            update_wallet=base_tx.update_wallet,
                            recurrent=False,
                            imported=False,
                        )
                        # Save and update wallet balance atomically if update_wallet is True
                        new_tx.save(is_first_save=True)
                        generated_count += 1
                        generated_transactions.append(new_tx)
                except IntegrityError:
                    # Caught duplicate constraint if another process generated concurrently
                    pass

            step += 1
            # Safety safeguard against runaway loops
            if step > 1000:
                logger.error(f"Recurring transaction {base_tx.pk} reached 1000 iterations safeguard.")
                break

    return {
        'generated_count': generated_count,
        'deactivated_count': deactivated_count,
        'generated_transactions': generated_transactions,
    }
