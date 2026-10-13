import datetime

from _decimal import Decimal
from dateutil.relativedelta import relativedelta
from django.test import TestCase
from rest_framework.test import APIClient
from .factory import TransactionFactory

from .models import CustomLabel, Transaction, TransactionRecurrency, SavingPlan


class TransactionTestCase(TestCase):
    STARTER_WALLET_AMOUNT = 1000

    def setUp(self):
        self.factory = TransactionFactory()
        self.user = self.factory.create_user()
        self.wallet = self.user.get_wallet()
        # Adding funds to user wallet
        self.wallet.update_balance(self.STARTER_WALLET_AMOUNT)
        
    def test_transaction_updates_wallet(self):
        """
        Check if a given transaction of type `EXPENSE`, when `update_wallet` is True, updates the wallet's current
        amount
        """
        transaction = self.factory.create_transaction_filled(self.wallet, type='EXPENSE', update_wallet=True)
        current_wallet_amount = self.STARTER_WALLET_AMOUNT - transaction.value
        self.assertEqual(Decimal(current_wallet_amount), self.wallet.get_current_amount())

    def test_transaction_is_from_wallet(self):
        transaction = self.factory.create_transaction_filled(self.wallet)
        self.assertEqual(transaction.is_from_wallet(self.wallet), True)

    def test_recurrent_transaction(self):
        """
        Check if creating a recurrent transaction successfully instantiates a `TransactionRecurrency` object with
        correct values using `create_from_json` function
        """
        transaction = self.factory.create_recurrent_transaction(self.user.pk, amount=2, duration="WEEKS")
        self.assertEqual(transaction.recurrent, True)

        recurrency = transaction.recurrency
        self.assertIsNotNone(recurrency)
        self.assertEqual(recurrency.amount, 2)
        self.assertEqual(recurrency.duration, "WEEKS")

    def test_get_monthly_earnings(self):
        current_month_start = datetime.date.today().replace(day=1)
        out_of_range = current_month_start - relativedelta(days=1)
        in_range = current_month_start + relativedelta(days=1)

        earnings_in_range = self.factory.create_transaction_filled(self.wallet, type="EARNING", value=150)
        earning_in_range2 = self.factory.create_transaction_filled(self.wallet, type="EARNING", value=50, date=in_range)
        earning_in_range3 = self.factory.create_transaction_filled(self.wallet, type="EARNING", value=300,
                                                                  date=current_month_start)

        earning_out_of_range = self.factory.create_transaction_filled(self.wallet, type="EARNING", date=out_of_range)

        # these transactions shouldn't be considered in the queryset since it's not an earning
        expense_in_range = self.factory.create_transaction_filled(self.wallet, type="EXPENSE", date=in_range)

        # Sum of all set transactions values
        expected_value = 500
        monthly_earning = self.wallet.get_monthly_earnings()
        self.assertEqual(expected_value, monthly_earning)

    def test_get_monthly_expenses(self):
        current_month_start = datetime.date.today().replace(day=1)
        out_of_range = current_month_start - relativedelta(days=1)
        in_range = current_month_start + relativedelta(days=1)

        expense_in_range = self.factory.create_transaction_filled(self.wallet, type="EXPENSE", value=150)
        expense_in_range2 = self.factory.create_transaction_filled(self.wallet, type="EXPENSE", value=50, date=in_range)
        expense_in_range3 = self.factory.create_transaction_filled(self.wallet, type="EXPENSE", value=300,
                                                                   date=current_month_start)
        expense_out_of_range = self.factory.create_transaction_filled(self.wallet, type="EXPENSE",date=out_of_range)

        # this transaction shouldn't be considered in the queryset since it's an earning
        earning_in_range = self.factory.create_transaction_filled(self.wallet, type="EARNING", date=in_range)

        expected_value = 500
        monthly_earning = self.wallet.get_monthly_expenses()
        self.assertEqual(expected_value, monthly_earning)


class TransactionAPIConsistencyTestCase(TestCase):
    def setUp(self):
        self.factory = TransactionFactory()
        self.user = self.factory.create_user()
        self.wallet = self.user.get_wallet()
        self.wallet.set_balance(1000)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_datetime_input_is_accepted_without_an_obsolete_description(self):
        transaction = Transaction.create_from_json({
            'title': 'Salary',
            'value': 125,
            'type': 'EARNING',
            'date': datetime.datetime.now(),
            'updateWallet': True,
        }, self.user.pk)

        self.wallet.refresh_from_db()
        self.assertEqual(transaction.date, datetime.date.today())
        self.assertEqual(self.wallet.current_amount, Decimal('1125.00'))

    def test_edit_reverses_previous_effect_before_applying_new_effect(self):
        transaction = self.factory.create_transaction_filled(
            self.wallet, title='Groceries', value=100, type='EXPENSE', update_wallet=True)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.current_amount, Decimal('900.00'))

        response = self.client.put(f'/api/transaction/{transaction.pk}', {
            'title': 'Refund',
            'value': 250,
            'type': 'EARNING',
            'date': '2026-10-01',
        }, format='json')

        self.assertEqual(response.status_code, 200)
        self.wallet.refresh_from_db()
        transaction.refresh_from_db()
        self.assertEqual(transaction.date, datetime.date(2026, 10, 1))
        self.assertEqual(self.wallet.current_amount, Decimal('1250.00'))

    def test_delete_reverses_effect_once_and_missing_or_foreign_records_are_not_server_errors(self):
        transaction = self.factory.create_transaction_filled(
            self.wallet, value=75, type='EXPENSE', update_wallet=True)

        response = self.client.delete(f'/api/transaction/{transaction.pk}')
        self.assertEqual(response.status_code, 200)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.current_amount, Decimal('1000.00'))

        response = self.client.delete(f'/api/transaction/{transaction.pk}')
        self.assertEqual(response.status_code, 404)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.current_amount, Decimal('1000.00'))

        other_user = self.factory.create_user()
        other_transaction = self.factory.create_transaction_filled(
            other_user.get_wallet(), value=20, type='EXPENSE', update_wallet=True)
        response = self.client.delete(f'/api/transaction/{other_transaction.pk}')
        self.assertEqual(response.status_code, 404)

    def test_invalid_transaction_input_returns_400(self):
        response = self.client.delete('/api/transaction/')
        self.assertEqual(response.status_code, 400)

        response = self.client.post('/api/transaction/', {
            'title': 'Invalid',
            'value': '-10',
            'type': 'EXPENSE',
            'date': 'not-a-date',
            'updateWallet': True,
        }, format='json')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Transaction.objects.count(), 0)

        response = self.client.put('/api/transaction/999999', {
            'title': 'Missing',
        }, format='json')
        self.assertEqual(response.status_code, 404)

    def test_labels_are_validated_and_scoped_to_the_current_user(self):
        response = self.client.delete('/api/label/')
        self.assertEqual(response.status_code, 400)

        response = self.client.post('/api/label/', {
            'name': '',
            'color': 'not-a-colour',
        }, format='json')
        self.assertEqual(response.status_code, 400)

        other_user = self.factory.create_user()
        other_label = CustomLabel.objects.create(
            wallet=other_user.get_wallet(), name='Private', color='#000000')
        response = self.client.delete(f'/api/label/{other_label.pk}')
        self.assertEqual(response.status_code, 404)


class SavingPlanAPITestCase(TestCase):
    def setUp(self):
        self.factory = TransactionFactory()
        self.user = self.factory.create_user()
        self.wallet = self.user.get_wallet()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_create_and_list_saving_plans(self):
        response = self.client.post('/api/savingplan/', {
            'title': 'New Laptop',
            'amount': '1500.00',
            'goal_date': '2026-12-31',
            'description': 'Saving for work machine',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        plan_id = response.data.get('id')
        self.assertIsNotNone(plan_id)
        self.assertEqual(response.data['title'], 'New Laptop')
        self.assertEqual(response.data['active'], True)

        # List plans
        response = self.client.get('/api/savingplans/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], plan_id)

    def test_saving_plan_validation(self):
        # Missing title
        response = self.client.post('/api/savingplan/', {
            'title': '',
            'amount': 500,
        }, format='json')
        self.assertEqual(response.status_code, 400)

        # Invalid amount (negative)
        response = self.client.post('/api/savingplan/', {
            'title': 'Car',
            'amount': -100,
        }, format='json')
        self.assertEqual(response.status_code, 400)

        # Invalid date
        response = self.client.post('/api/savingplan/', {
            'title': 'Car',
            'amount': 100,
            'goal_date': 'invalid-date',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_get_detail_and_update_saving_plan(self):
        plan = self.user.get_wallet().saving_plans.create(
            title='Vacation',
            amount=Decimal('2000.00'),
            goal_date=datetime.date(2026, 11, 1),
            description='Beach trip'
        )

        # Get details
        response = self.client.get(f'/api/savingplan/{plan.pk}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['title'], 'Vacation')

        # Update details
        response = self.client.put(f'/api/savingplan/{plan.pk}', {
            'title': 'Europe Vacation',
            'amount': '3000.00',
        }, format='json')
        self.assertEqual(response.status_code, 200)
        plan.refresh_from_db()
        self.assertEqual(plan.title, 'Europe Vacation')
        self.assertEqual(plan.amount, Decimal('3000.00'))

    def test_toggle_active_and_delete_saving_plan(self):
        plan = self.user.get_wallet().saving_plans.create(
            title='Emergency Fund',
            amount=Decimal('5000.00'),
            active=True
        )

        # Toggle / Deactivate plan via patch
        response = self.client.patch(f'/api/savingplan/{plan.pk}', {
            'active': False
        }, format='json')
        self.assertEqual(response.status_code, 200)
        plan.refresh_from_db()
        self.assertFalse(plan.active)

        # Toggle back
        response = self.client.patch(f'/api/savingplan/{plan.pk}')
        self.assertEqual(response.status_code, 200)
        plan.refresh_from_db()
        self.assertTrue(plan.active)

        # Delete plan
        response = self.client.delete(f'/api/savingplan/{plan.pk}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.user.get_wallet().saving_plans.count(), 0)

    def test_saving_plan_isolation_between_users(self):
        other_user = self.factory.create_user()
        other_plan = other_user.get_wallet().saving_plans.create(
            title='Secret Fund',
            amount=Decimal('9999.00')
        )

        # Trying to view other user's plan
        response = self.client.get(f'/api/savingplan/{other_plan.pk}')
        self.assertEqual(response.status_code, 404)

        # Trying to edit other user's plan
        response = self.client.put(f'/api/savingplan/{other_plan.pk}', {
            'title': 'Hacked',
        }, format='json')
        self.assertEqual(response.status_code, 404)

        # Trying to delete other user's plan
        response = self.client.delete(f'/api/savingplan/{other_plan.pk}')
        self.assertEqual(response.status_code, 404)


class RecurringTransactionsTestCase(TestCase):
    def setUp(self):
        self.factory = TransactionFactory()
        self.user = self.factory.create_user()
        self.wallet = self.user.get_wallet()
        self.wallet.set_balance(1000)

    def test_recurring_generation_and_idempotency(self):
        from .recurring import process_due_recurring_transactions

        # Create a monthly recurring transaction starting 2 months ago
        start_date = datetime.date(2026, 8, 1)
        base_tx = Transaction.objects.create(
            wallet=self.wallet,
            title='Gym Subscription',
            value=Decimal('50.00'),
            type='EXPENSE',
            date=start_date,
            update_wallet=True,
            recurrent=True,
        )
        TransactionRecurrency.objects.create(
            transaction=base_tx,
            amount=1,
            duration='MONTHS',
            active=True
        )
        base_tx.recurrency = TransactionRecurrency.objects.get(transaction=base_tx)
        base_tx.save()

        # Target date is 2026-10-12
        as_of = datetime.date(2026, 10, 12)
        result = process_due_recurring_transactions(as_of_date=as_of)

        # Due dates: 2026-09-01 and 2026-10-01 (2 occurrences)
        self.assertEqual(result['generated_count'], 2)
        generated = Transaction.objects.filter(base_transaction=base_tx)
        self.assertEqual(generated.count(), 2)

        # Wallet should be updated: 1000 - 50 - 50 = 900
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.current_amount, Decimal('900.00'))

        # Run again with same as_of date: MUST be idempotent (0 new transactions generated)
        result2 = process_due_recurring_transactions(as_of_date=as_of)
        self.assertEqual(result2['generated_count'], 0)
        self.assertEqual(Transaction.objects.filter(base_transaction=base_tx).count(), 2)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.current_amount, Decimal('900.00'))

    def test_recurring_with_end_date(self):
        from .recurring import process_due_recurring_transactions

        from django.utils import timezone
        start_date = datetime.date(2026, 9, 1)
        end_date = timezone.make_aware(datetime.datetime(2026, 9, 20, 23, 59, 59))
        base_tx = Transaction.objects.create(
            wallet=self.wallet,
            title='Weekly Course',
            value=Decimal('20.00'),
            type='EXPENSE',
            date=start_date,
            update_wallet=False,
            recurrent=True,
        )
        rec = TransactionRecurrency.objects.create(
            transaction=base_tx,
            amount=1,
            duration='WEEKS',
            end_date=end_date,
            active=True
        )

        as_of = datetime.date(2026, 10, 12)
        result = process_due_recurring_transactions(as_of_date=as_of)

        # Week 1: Sep 8 (generated), Week 2: Sep 15 (generated), Week 3: Sep 22 (> Sep 20 end_date -> stops & deactivates)
        self.assertEqual(result['generated_count'], 2)
        rec.refresh_from_db()
        self.assertFalse(rec.active)


class TransactionSearchAndSerializationTestCase(TestCase):
    def setUp(self):
        self.factory = TransactionFactory()
        self.user = self.factory.create_user()
        self.wallet = self.user.get_wallet()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_search_transactions_by_title_label_type_amount(self):
        food_label = CustomLabel.objects.create(wallet=self.wallet, name='Dining', color='#ff0000')
        t1 = self.factory.create_transaction_filled(
            self.wallet, title='Coffee at Starbucks', value=55, type='EXPENSE', label=food_label, date=datetime.date(2026, 10, 1))
        t2 = self.factory.create_transaction_filled(
            self.wallet, title='Freelance Payment', value=800, type='EARNING', date=datetime.date(2026, 10, 2))
        t3 = self.factory.create_transaction_filled(
            self.wallet, title='Electric Bill', value=120, type='EXPENSE', date=datetime.date(2026, 10, 3))

        # Search by title keyword
        res = self.client.get('/api/transactions/?search=Coffee')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['title'], 'Coffee at Starbucks')

        # Search by label name
        res = self.client.get('/api/transactions/?search=Dining')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], t1.pk)

        # Search by type keyword (EARNING / Thu)
        res = self.client.get('/api/transactions/?search=EARNING')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], t2.pk)

        # Search by amount
        res = self.client.get('/api/transactions/?search=120')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['id'], t3.pk)

    def test_recurring_transaction_serialization(self):
        from hubModels.serializers import TransactionSerializer

        t_recurrent = self.factory.create_recurrent_transaction(self.user.pk, amount=3, duration='MONTHS')
        serializer = TransactionSerializer(t_recurrent)
        self.assertTrue(serializer.data['recurrent'])
        self.assertEqual(serializer.data['amount'], 3)
        self.assertEqual(serializer.data['duration'], 'MONTHS')

        # Non-recurrent transaction
        t_regular = self.factory.create_transaction_filled(self.wallet)
        serializer_reg = TransactionSerializer(t_regular)
        self.assertFalse(serializer_reg.data['recurrent'])
        self.assertIsNone(serializer_reg.data['amount'])
        self.assertIsNone(serializer_reg.data['duration'])

    def test_get_transactions_with_limit_and_chart_type_zero(self):
        for i in range(5):
            self.factory.create_transaction_filled(
                self.wallet, title=f'Trans {i}', value=10 * (i + 1), type='EXPENSE', date=datetime.date(2026, 10, i + 1)
            )

        res = self.client.get('/api/transactions/?limit=3&chart_type=0')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 3)
        self.assertEqual(res.data[0]['title'], 'Trans 4')
        self.assertEqual(res.data[1]['title'], 'Trans 3')
        self.assertEqual(res.data[2]['title'], 'Trans 2')

