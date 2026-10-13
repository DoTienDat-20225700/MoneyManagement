from datetime import date, datetime
from django.core.management.base import BaseCommand, CommandError
from hubModels.recurring import process_due_recurring_transactions


class Command(BaseCommand):
    help = 'Processes and generates due recurring transactions up to a target date (default: today).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--as-of',
            type=str,
            dest='as_of',
            default=None,
            help='Target reference date in YYYY-MM-DD format (default: today).',
        )

    def handle(self, *args, **options):
        as_of_str = options.get('as_of')
        as_of_date = None

        if as_of_str:
            try:
                as_of_date = datetime.strptime(as_of_str, '%Y-%m-%d').date()
            except ValueError:
                raise CommandError('Invalid date format for --as-of. Expected YYYY-MM-DD.')

        target_date = as_of_date or date.today()
        self.stdout.write(f"Processing recurring transactions up to {target_date}...")

        result = process_due_recurring_transactions(as_of_date=target_date)

        generated = result['generated_count']
        deactivated = result['deactivated_count']

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully generated {generated} transaction(s). Deactivated {deactivated} expired schedule(s)."
            )
        )
