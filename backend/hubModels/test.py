import datetime

from _decimal import Decimal
from dateutil.relativedelta import relativedelta
from django.test import TestCase
from rest_framework.test import APIClient
from .factory import TransactionFactory

from .models import HubUser, CustomLabel, Transaction, TransactionRecurrency, SavingPlan, CategoryBudget, SavingPlanContribution


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


class SavingPlanAdvancedTrackingTestCase(TestCase):
    def setUp(self):
        self.factory = TransactionFactory()
        self.user = self.factory.create_user()
        self.wallet = self.user.get_wallet()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

        self.plan = self.wallet.saving_plans.create(
            title='House Deposit',
            amount=Decimal('10000.00'),
            goal_date=datetime.date(2027, 12, 31),
            description='Saving for first apartment'
        )

    def test_goal_progress_serialization(self):
        # Initial state: 0 contributions
        response = self.client.get(f'/api/savingplan/{self.plan.pk}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(str(response.data['amount_saved'])), Decimal('0.00'))
        self.assertEqual(Decimal(str(response.data['remaining_amount'])), Decimal('10000.00'))
        self.assertEqual(response.data['completion_percentage'], 0.0)
        self.assertEqual(response.data['status'], 'active')

        # Add contribution
        self.client.post(f'/api/savingplans/{self.plan.pk}/contributions/', {
            'amount': '2500.00',
            'date': '2026-10-01',
            'description': 'Initial bonus'
        }, format='json')

        response = self.client.get(f'/api/savingplan/{self.plan.pk}')
        self.assertEqual(Decimal(str(response.data['amount_saved'])), Decimal('2500.00'))
        self.assertEqual(Decimal(str(response.data['remaining_amount'])), Decimal('7500.00'))
        self.assertEqual(response.data['completion_percentage'], 25.0)
        self.assertEqual(response.data['status'], 'active')

        # Add more contribution to reach 100%
        self.client.post(f'/api/savingplans/{self.plan.pk}/contributions/', {
            'amount': '7500.00',
            'date': '2026-10-10',
            'description': 'Final payment'
        }, format='json')

        response = self.client.get(f'/api/savingplan/{self.plan.pk}')
        self.assertEqual(Decimal(str(response.data['amount_saved'])), Decimal('10000.00'))
        self.assertEqual(Decimal(str(response.data['remaining_amount'])), Decimal('0.00'))
        self.assertEqual(response.data['completion_percentage'], 100.0)
        self.assertEqual(response.data['status'], 'completed')

    def test_contribution_crud_and_idempotency(self):
        # 1. Add contribution with idempotency key
        key = 'unique-contrib-key-123'
        resp1 = self.client.post(f'/api/savingplans/{self.plan.pk}/contributions/', {
            'amount': '1000.00',
            'date': '2026-10-05',
            'description': 'Monthly saving',
            'idempotency_key': key,
        }, format='json')
        self.assertEqual(resp1.status_code, 201)
        contrib_id = resp1.data['id']

        # 2. Resubmit with identical idempotency key -> duplicate prevented
        resp2 = self.client.post(f'/api/savingplans/{self.plan.pk}/contributions/', {
            'amount': '1000.00',
            'date': '2026-10-05',
            'description': 'Monthly saving',
            'idempotency_key': key,
        }, format='json')
        self.assertEqual(resp2.status_code, 200)
        self.assertEqual(resp2.data['id'], contrib_id)
        self.assertEqual(self.plan.contributions.count(), 1)

        # 3. List contributions
        list_resp = self.client.get(f'/api/savingplans/{self.plan.pk}/contributions/')
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(len(list_resp.data), 1)

        # 4. Update contribution
        update_resp = self.client.put(f'/api/savingplans/{self.plan.pk}/contributions/{contrib_id}', {
            'amount': '1200.00',
            'description': 'Adjusted monthly saving',
        }, format='json')
        self.assertEqual(update_resp.status_code, 200)
        self.assertEqual(Decimal(str(update_resp.data['amount'])), Decimal('1200.00'))

        # 5. Delete contribution
        del_resp = self.client.delete(f'/api/savingplans/{self.plan.pk}/contributions/{contrib_id}')
        self.assertEqual(del_resp.status_code, 200)
        self.assertEqual(self.plan.contributions.count(), 0)

    def test_contribution_validation(self):
        # Negative amount
        resp = self.client.post(f'/api/savingplans/{self.plan.pk}/contributions/', {
            'amount': '-500.00',
        }, format='json')
        self.assertEqual(resp.status_code, 400)

        # Zero amount
        resp = self.client.post(f'/api/savingplans/{self.plan.pk}/contributions/', {
            'amount': '0.00',
        }, format='json')
        self.assertEqual(resp.status_code, 400)

        # Invalid date
        resp = self.client.post(f'/api/savingplans/{self.plan.pk}/contributions/', {
            'amount': '500.00',
            'date': 'invalid-date',
        }, format='json')
        self.assertEqual(resp.status_code, 400)

    def test_contribution_cross_user_isolation(self):
        other_user = self.factory.create_user()
        other_client = APIClient()
        other_client.force_authenticate(other_user)

        # Other user cannot add contribution to self.plan
        resp = other_client.post(f'/api/savingplans/{self.plan.pk}/contributions/', {
            'amount': '500.00',
        }, format='json')
        self.assertEqual(resp.status_code, 404)

        # Create a contribution by owner
        contrib = self.plan.contributions.create(
            user=self.user,
            amount=Decimal('500.00'),
            date=datetime.date.today()
        )

        # Other user cannot view contributions
        resp = other_client.get(f'/api/savingplans/{self.plan.pk}/contributions/')
        self.assertEqual(resp.status_code, 404)

        # Other user cannot edit contribution
        resp = other_client.put(f'/api/savingplans/{self.plan.pk}/contributions/{contrib.pk}', {
            'amount': '1000.00',
        }, format='json')
        self.assertEqual(resp.status_code, 404)

        # Other user cannot delete contribution
        resp = other_client.delete(f'/api/savingplans/{self.plan.pk}/contributions/{contrib.pk}')
        self.assertEqual(resp.status_code, 404)

    def test_completion_estimate(self):
        # 1. No contributions -> Insufficient history
        est1 = self.plan.get_estimated_completion()
        self.assertIsNone(est1['estimated_date'])
        self.assertIn('Chưa có lịch sử', est1['message'])

        # 2. Contributions spanning multiple days
        today = datetime.date.today()
        # Contribution 1: 10 days ago, 1000
        self.plan.contributions.create(
            user=self.user,
            amount=Decimal('1000.00'),
            date=today - datetime.timedelta(days=10)
        )
        # Contribution 2: 5 days ago, 1000
        self.plan.contributions.create(
            user=self.user,
            amount=Decimal('1000.00'),
            date=today - datetime.timedelta(days=5)
        )
        # Total contributed: 2000 in 10 days => daily_rate = 200/day
        # Remaining: 8000 => 8000 / 200 = 40 days needed
        est2 = self.plan.get_estimated_completion()
        self.assertIsNotNone(est2['estimated_date'])
        self.assertEqual(est2['days_remaining'], 40)
        self.assertEqual(est2['daily_rate'], 200.0)

        # 3. Already completed plan
        self.plan.contributions.create(
            user=self.user,
            amount=Decimal('8000.00'),
            date=today
        )
        est3 = self.plan.get_estimated_completion()
        self.assertEqual(est3['status'], 'completed')
        self.assertIn('hoàn thành', est3['message'].lower())


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


class CategoryBudgetModelTestCase(TestCase):
    def setUp(self):
        self.factory = TransactionFactory()
        self.user = self.factory.create_user()
        self.wallet = self.user.get_wallet()
        self.food_label = CustomLabel.objects.create(wallet=self.wallet, name='Food', color='#2ecc71')
        self.bills_label = CustomLabel.objects.create(wallet=self.wallet, name='Bills', color='#e74c3c')

    def test_create_budget_and_uniqueness_constraint(self):
        budget = CategoryBudget.create_from_json({
            'label': self.food_label.pk,
            'amount': 2000000,
            'month': 10,
            'year': 2026,
        }, user_pk=self.user.pk)

        self.assertEqual(budget.amount, Decimal('2000000.00'))
        self.assertEqual(budget.month, 10)
        self.assertEqual(budget.year, 2026)
        self.assertIsNotNone(budget.created_at)
        self.assertIsNotNone(budget.updated_at)

        # Duplicate budget for same wallet, label, month, year must fail
        from django.core.exceptions import ValidationError
        with self.assertRaises(ValidationError):
            CategoryBudget.create_from_json({
                'label': self.food_label.pk,
                'amount': 3000000,
                'month': 10,
                'year': 2026,
            }, user_pk=self.user.pk)

    def test_budget_validations(self):
        from django.core.exceptions import ValidationError

        # Amount must be positive
        with self.assertRaises(ValidationError):
            CategoryBudget.create_from_json({
                'label': self.food_label.pk,
                'amount': -100,
                'month': 10,
                'year': 2026,
            }, user_pk=self.user.pk)

        # Month must be between 1 and 12
        with self.assertRaises(ValidationError):
            CategoryBudget.create_from_json({
                'label': self.food_label.pk,
                'amount': 500000,
                'month': 13,
                'year': 2026,
            }, user_pk=self.user.pk)

        # Label from another user's wallet
        other_user = self.factory.create_user()
        other_label = CustomLabel.objects.create(wallet=other_user.get_wallet(), name='Other', color='#000000')
        with self.assertRaises(ValidationError):
            CategoryBudget.create_from_json({
                'label': other_label.pk,
                'amount': 500000,
                'month': 10,
                'year': 2026,
            }, user_pk=self.user.pk)

    def test_budget_spent_calculation_and_over_budget(self):
        budget = CategoryBudget.objects.create(
            wallet=self.wallet,
            label=self.food_label,
            amount=Decimal('1000000.00'),
            month=10,
            year=2026,
        )

        # In-scope expenses
        self.factory.create_transaction_filled(
            self.wallet, label=self.food_label, type='EXPENSE', value=300000, date=datetime.date(2026, 10, 5)
        )
        self.factory.create_transaction_filled(
            self.wallet, label=self.food_label, type='EXPENSE', value=400000, date=datetime.date(2026, 10, 10)
        )

        # Out-of-scope: different month
        self.factory.create_transaction_filled(
            self.wallet, label=self.food_label, type='EXPENSE', value=200000, date=datetime.date(2026, 9, 15)
        )

        # Out-of-scope: different label
        self.factory.create_transaction_filled(
            self.wallet, label=self.bills_label, type='EXPENSE', value=500000, date=datetime.date(2026, 10, 12)
        )

        # Out-of-scope: earning transaction with same label
        self.factory.create_transaction_filled(
            self.wallet, label=self.food_label, type='EARNING', value=100000, date=datetime.date(2026, 10, 8)
        )

        # Total spent should only be 300,000 + 400,000 = 700,000
        self.assertEqual(budget.get_spent(), Decimal('700000.00'))
        self.assertEqual(budget.get_remaining(), Decimal('300000.00'))
        self.assertEqual(budget.get_percentage(), 70.0)
        self.assertFalse(budget.is_over_budget())

        # Exceed budget
        self.factory.create_transaction_filled(
            self.wallet, label=self.food_label, type='EXPENSE', value=400000, date=datetime.date(2026, 10, 20)
        )
        self.assertEqual(budget.get_spent(), Decimal('1100000.00'))
        self.assertEqual(budget.get_remaining(), Decimal('0.00'))
        self.assertEqual(budget.get_percentage(), 110.0)
        self.assertTrue(budget.is_over_budget())


class CategoryBudgetAPITestCase(TestCase):
    def setUp(self):
        self.factory = TransactionFactory()
        self.user = self.factory.create_user()
        self.wallet = self.user.get_wallet()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

        self.food_label = CustomLabel.objects.create(wallet=self.wallet, name='Food', color='#2ecc71')
        self.util_label = CustomLabel.objects.create(wallet=self.wallet, name='Utilities', color='#3498db')
        self.shop_label = CustomLabel.objects.create(wallet=self.wallet, name='Shopping', color='#e74c3c')

    def test_list_budgets_for_month_with_calculated_fields_and_statuses(self):
        # 1. Normal status (50%)
        b_food = CategoryBudget.objects.create(
            wallet=self.wallet, label=self.food_label, amount=Decimal('1000000.00'), month=10, year=2026
        )
        self.factory.create_transaction_filled(
            self.wallet, label=self.food_label, type='EXPENSE', value=500000, date=datetime.date(2026, 10, 2)
        )

        # 2. Approaching status (85%)
        b_util = CategoryBudget.objects.create(
            wallet=self.wallet, label=self.util_label, amount=Decimal('1000000.00'), month=10, year=2026
        )
        self.factory.create_transaction_filled(
            self.wallet, label=self.util_label, type='EXPENSE', value=850000, date=datetime.date(2026, 10, 5)
        )

        # 3. Exceeded status (120%)
        b_shop = CategoryBudget.objects.create(
            wallet=self.wallet, label=self.shop_label, amount=Decimal('1000000.00'), month=10, year=2026
        )
        self.factory.create_transaction_filled(
            self.wallet, label=self.shop_label, type='EXPENSE', value=1200000, date=datetime.date(2026, 10, 10)
        )

        res = self.client.get('/api/budgets/?month=10&year=2026')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.data), 3)

        budgets_by_label = {item['label']['name']: item for item in res.data}

        # Food assertions
        food_res = budgets_by_label['Food']
        self.assertEqual(food_res['limit'], '1000000.00')
        self.assertEqual(food_res['spent'], '500000.00')
        self.assertEqual(food_res['remaining'], '500000.00')
        self.assertEqual(food_res['percentage'], 50.0)
        self.assertEqual(food_res['status'], 'normal')
        self.assertFalse(food_res['is_over_budget'])

        # Utilities assertions
        util_res = budgets_by_label['Utilities']
        self.assertEqual(util_res['limit'], '1000000.00')
        self.assertEqual(util_res['spent'], '850000.00')
        self.assertEqual(util_res['remaining'], '150000.00')
        self.assertEqual(util_res['percentage'], 85.0)
        self.assertEqual(util_res['status'], 'approaching')
        self.assertFalse(util_res['is_over_budget'])

        # Shopping assertions
        shop_res = budgets_by_label['Shopping']
        self.assertEqual(shop_res['limit'], '1000000.00')
        self.assertEqual(shop_res['spent'], '1200000.00')
        self.assertEqual(shop_res['remaining'], '0.00')
        self.assertEqual(shop_res['percentage'], 120.0)
        self.assertEqual(shop_res['status'], 'exceeded')
        self.assertTrue(shop_res['is_over_budget'])

    def test_create_and_retrieve_budget_detail(self):
        # Create budget via POST
        create_res = self.client.post('/api/budgets/', {
            'label': self.food_label.pk,
            'amount': 2500000,
            'month': 11,
            'year': 2026,
        }, format='json')
        self.assertEqual(create_res.status_code, 201)
        budget_id = create_res.data['id']
        self.assertEqual(create_res.data['limit'], '2500000.00')
        self.assertEqual(create_res.data['month'], 11)

        # Retrieve single detail via GET /api/budgets/<id>
        detail_res = self.client.get(f'/api/budgets/{budget_id}')
        self.assertEqual(detail_res.status_code, 200)
        self.assertEqual(detail_res.data['id'], budget_id)
        self.assertEqual(detail_res.data['label']['id'], self.food_label.pk)

        # Retrieve non-existent budget
        not_found_res = self.client.get('/api/budgets/99999')
        self.assertEqual(not_found_res.status_code, 404)

    def test_create_budget_validations_and_boundary_behavior(self):
        # Missing category
        res1 = self.client.post('/api/budgets/', {
            'amount': 500000,
            'month': 10,
            'year': 2026,
        }, format='json')
        self.assertEqual(res1.status_code, 400)

        # Zero amount
        res2 = self.client.post('/api/budgets/', {
            'label': self.food_label.pk,
            'amount': 0,
            'month': 10,
            'year': 2026,
        }, format='json')
        self.assertEqual(res2.status_code, 400)

        # Negative amount
        res3 = self.client.post('/api/budgets/', {
            'label': self.food_label.pk,
            'amount': -100000,
            'month': 10,
            'year': 2026,
        }, format='json')
        self.assertEqual(res3.status_code, 400)

        # Invalid month
        res4 = self.client.post('/api/budgets/', {
            'label': self.food_label.pk,
            'amount': 100000,
            'month': 0,
            'year': 2026,
        }, format='json')
        self.assertEqual(res4.status_code, 400)

        # Duplicate budget creation
        self.client.post('/api/budgets/', {
            'label': self.food_label.pk,
            'amount': 500000,
            'month': 10,
            'year': 2026,
        }, format='json')
        dup_res = self.client.post('/api/budgets/', {
            'label': self.food_label.pk,
            'amount': 700000,
            'month': 10,
            'year': 2026,
        }, format='json')
        self.assertEqual(dup_res.status_code, 400)

    def test_update_and_delete_budget(self):
        budget = CategoryBudget.objects.create(
            wallet=self.wallet, label=self.food_label, amount=Decimal('500000.00'), month=10, year=2026
        )

        # Update budget
        update_res = self.client.put(f'/api/budgets/{budget.pk}', {
            'amount': 800000,
        }, format='json')
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.data['limit'], '800000.00')

        budget.refresh_from_db()
        self.assertEqual(budget.amount, Decimal('800000.00'))

        # Delete budget
        del_res = self.client.delete(f'/api/budgets/{budget.pk}')
        self.assertEqual(del_res.status_code, 200)
        self.assertFalse(CategoryBudget.objects.filter(pk=budget.pk).exists())

    def test_budget_summary_endpoint_and_user_isolation(self):
        # Set up budgets for current user
        CategoryBudget.objects.create(
            wallet=self.wallet, label=self.food_label, amount=Decimal('1000000.00'), month=10, year=2026
        )
        CategoryBudget.objects.create(
            wallet=self.wallet, label=self.util_label, amount=Decimal('2000000.00'), month=10, year=2026
        )

        # Expenses for current user
        self.factory.create_transaction_filled(
            self.wallet, label=self.food_label, type='EXPENSE', value=600000, date=datetime.date(2026, 10, 5)
        )
        self.factory.create_transaction_filled(
            self.wallet, label=self.util_label, type='EXPENSE', value=1700000, date=datetime.date(2026, 10, 8)
        )
        # Earning with food label should not be subtracted from expense spending
        self.factory.create_transaction_filled(
            self.wallet, label=self.food_label, type='EARNING', value=500000, date=datetime.date(2026, 10, 10)
        )
        # Unbudgeted expense (shopping label has no budget for this month)
        self.factory.create_transaction_filled(
            self.wallet, label=self.shop_label, type='EXPENSE', value=200000, date=datetime.date(2026, 10, 12)
        )

        # Other user's budget and transactions
        other_user = self.factory.create_user()
        other_wallet = other_user.get_wallet()
        other_label = CustomLabel.objects.create(wallet=other_wallet, name='OtherFood', color='#111111')
        CategoryBudget.objects.create(
            wallet=other_wallet, label=other_label, amount=Decimal('5000000.00'), month=10, year=2026
        )
        self.factory.create_transaction_filled(
            other_wallet, label=other_label, type='EXPENSE', value=4000000, date=datetime.date(2026, 10, 5)
        )

        summary_res = self.client.get('/api/budgets/summary/?month=10&year=2026')
        self.assertEqual(summary_res.status_code, 200)
        data = summary_res.data
        self.assertEqual(data['month'], 10)
        self.assertEqual(data['year'], 2026)
        # Total budget: 1,000,000 + 2,000,000 = 3,000,000 (other user's 5,000,000 strictly excluded)
        self.assertEqual(data['total_budget'], '3000000.00')
        # Total spent in budgeted categories: 600,000 + 1,700,000 = 2,300,000
        self.assertEqual(data['total_spent'], '2300000.00')
        # Total remaining: 700,000
        self.assertEqual(data['total_remaining'], '700000.00')
        # Overall percentage: 2,300,000 / 3,000,000 = 76.67%
        self.assertEqual(data['overall_percentage'], 76.67)
        # Total monthly expenses across all categories: 2,300,000 + 200,000 = 2,500,000
        self.assertEqual(data['total_monthly_expenses'], '2500000.00')
        # Unbudgeted expenses: 200,000
        self.assertEqual(data['unbudgeted_spent'], '200000.00')
        self.assertEqual(data['budget_count'], 2)
        # Statuses: Food (60%) -> normal, Util (85%) -> approaching
        self.assertEqual(data['status_counts']['normal'], 1)
        self.assertEqual(data['status_counts']['approaching'], 1)
        self.assertEqual(data['status_counts']['exceeded'], 0)

    def test_user_ownership_and_unauthorized_access(self):
        other_user = self.factory.create_user()
        other_wallet = other_user.get_wallet()
        other_label = CustomLabel.objects.create(wallet=other_wallet, name='OtherLabel', color='#555555')
        other_budget = CategoryBudget.objects.create(
            wallet=other_wallet, label=other_label, amount=Decimal('500000.00'), month=10, year=2026
        )

        # 1. Current user cannot retrieve other user's budget detail
        res = self.client.get(f'/api/budgets/{other_budget.pk}')
        self.assertEqual(res.status_code, 404)

        # 2. Current user cannot update other user's budget
        update_res = self.client.put(f'/api/budgets/{other_budget.pk}', {'amount': 900000}, format='json')
        self.assertEqual(update_res.status_code, 404)

        # 3. Current user cannot delete other user's budget
        del_res = self.client.delete(f'/api/budgets/{other_budget.pk}')
        self.assertEqual(del_res.status_code, 404)
        self.assertTrue(CategoryBudget.objects.filter(pk=other_budget.pk).exists())

        # 4. Unauthenticated user gets 401
        anon_client = APIClient()
        anon_res = anon_client.get('/api/budgets/')
        self.assertEqual(anon_res.status_code, 401)

    def test_monthly_period_boundaries(self):
        # Budget for October 2026
        budget = CategoryBudget.objects.create(
            wallet=self.wallet, label=self.food_label, amount=Decimal('1000000.00'), month=10, year=2026
        )

        # Transaction on last day of September (2026-09-30) -> MUST NOT be included
        self.factory.create_transaction_filled(
            self.wallet, label=self.food_label, type='EXPENSE', value=100000, date=datetime.date(2026, 9, 30)
        )
        # Transaction on first day of October (2026-10-01) -> MUST be included
        self.factory.create_transaction_filled(
            self.wallet, label=self.food_label, type='EXPENSE', value=200000, date=datetime.date(2026, 10, 1)
        )
        # Transaction on last day of October (2026-10-31) -> MUST be included
        self.factory.create_transaction_filled(
            self.wallet, label=self.food_label, type='EXPENSE', value=300000, date=datetime.date(2026, 10, 31)
        )
        # Transaction on first day of November (2026-11-01) -> MUST NOT be included
        self.factory.create_transaction_filled(
            self.wallet, label=self.food_label, type='EXPENSE', value=400000, date=datetime.date(2026, 11, 1)
        )

        res = self.client.get('/api/budgets/?month=10&year=2026')
        self.assertEqual(res.status_code, 200)
        food_budget_data = res.data[0]
        # Only 200,000 + 300,000 = 500,000 in October
        self.assertEqual(food_budget_data['spent'], '500000.00')
        self.assertEqual(food_budget_data['remaining'], '500000.00')
        self.assertEqual(food_budget_data['percentage'], 50.0)

    def test_expense_aggregation_and_different_categories(self):
        # Two category budgets
        b_food = CategoryBudget.objects.create(
            wallet=self.wallet, label=self.food_label, amount=Decimal('1000000.00'), month=10, year=2026
        )
        b_util = CategoryBudget.objects.create(
            wallet=self.wallet, label=self.util_label, amount=Decimal('800000.00'), month=10, year=2026
        )

        # Multiple transactions for Food on different dates
        self.factory.create_transaction_filled(
            self.wallet, label=self.food_label, type='EXPENSE', value=150000, date=datetime.date(2026, 10, 3)
        )
        self.factory.create_transaction_filled(
            self.wallet, label=self.food_label, type='EXPENSE', value=250000, date=datetime.date(2026, 10, 14)
        )
        self.factory.create_transaction_filled(
            self.wallet, label=self.food_label, type='EXPENSE', value=100000, date=datetime.date(2026, 10, 25)
        )

        # Multiple transactions for Utilities on different dates
        self.factory.create_transaction_filled(
            self.wallet, label=self.util_label, type='EXPENSE', value=300000, date=datetime.date(2026, 10, 5)
        )
        self.factory.create_transaction_filled(
            self.wallet, label=self.util_label, type='EXPENSE', value=340000, date=datetime.date(2026, 10, 20)
        )

        # Income transactions (should NOT reduce expense totals)
        self.factory.create_transaction_filled(
            self.wallet, label=self.food_label, type='EARNING', value=500000, date=datetime.date(2026, 10, 15)
        )
        self.factory.create_transaction_filled(
            self.wallet, label=self.util_label, type='EARNING', value=200000, date=datetime.date(2026, 10, 22)
        )

        # Unlabeled expense (should not affect either category)
        self.factory.create_transaction_filled(
            self.wallet, label=None, type='EXPENSE', value=99000, date=datetime.date(2026, 10, 18)
        )

        res = self.client.get('/api/budgets/?month=10&year=2026')
        self.assertEqual(res.status_code, 200)
        budgets_by_label = {item['label']['name']: item for item in res.data}

        # Food: 150,000 + 250,000 + 100,000 = 500,000 (50%)
        self.assertEqual(budgets_by_label['Food']['spent'], '500000.00')
        self.assertEqual(budgets_by_label['Food']['remaining'], '500000.00')
        self.assertEqual(budgets_by_label['Food']['status'], 'normal')

        # Utilities: 300,000 + 340,000 = 640,000 (640,000 / 800,000 = 80%) -> approaching
        self.assertEqual(budgets_by_label['Utilities']['spent'], '640000.00')
        self.assertEqual(budgets_by_label['Utilities']['remaining'], '160000.00')
        self.assertEqual(budgets_by_label['Utilities']['percentage'], 80.0)
        self.assertEqual(budgets_by_label['Utilities']['status'], 'approaching')

    def test_percentage_and_remaining_balance_edge_cases(self):
        # 1. Zero spending
        b_food = CategoryBudget.objects.create(
            wallet=self.wallet, label=self.food_label, amount=Decimal('500000.00'), month=10, year=2026
        )
        res = self.client.get(f'/api/budgets/{b_food.pk}')
        self.assertEqual(res.data['spent'], '0.00')
        self.assertEqual(res.data['remaining'], '500000.00')
        self.assertEqual(res.data['percentage'], 0.0)
        self.assertEqual(res.data['status'], 'normal')
        self.assertFalse(res.data['is_over_budget'])

        # 2. Exact limit (100%)
        self.factory.create_transaction_filled(
            self.wallet, label=self.food_label, type='EXPENSE', value=500000, date=datetime.date(2026, 10, 5)
        )
        res_100 = self.client.get(f'/api/budgets/{b_food.pk}')
        self.assertEqual(res_100.data['spent'], '500000.00')
        self.assertEqual(res_100.data['remaining'], '0.00')
        self.assertEqual(res_100.data['percentage'], 100.0)
        self.assertEqual(res_100.data['status'], 'approaching')
        self.assertFalse(res_100.data['is_over_budget'])

        # 3. Exceeded (140%)
        self.factory.create_transaction_filled(
            self.wallet, label=self.food_label, type='EXPENSE', value=200000, date=datetime.date(2026, 10, 15)
        )
        res_140 = self.client.get(f'/api/budgets/{b_food.pk}')
        self.assertEqual(res_140.data['spent'], '700000.00')
        self.assertEqual(res_140.data['remaining'], '0.00')
        self.assertEqual(res_140.data['percentage'], 140.0)
        self.assertEqual(res_140.data['status'], 'exceeded')
        self.assertTrue(res_140.data['is_over_budget'])


class FinancialReportAPITestCase(TestCase):
    def setUp(self):
        self.factory = TransactionFactory()
        self.user = self.factory.create_user()
        self.wallet = self.user.get_wallet()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

        self.food_label = CustomLabel.objects.create(wallet=self.wallet, name='Food', color='#2ecc71')
        self.bills_label = CustomLabel.objects.create(wallet=self.wallet, name='Bills', color='#e74c3c')
        self.salary_label = CustomLabel.objects.create(wallet=self.wallet, name='Salary', color='#3498db')

    def test_report_summary_calculations_and_filtering(self):
        # Current period: 2026-10-01 to 2026-10-10 (10 days)
        # Earnings
        self.factory.create_transaction_filled(
            self.wallet, label=self.salary_label, type='EARNING', value=10000000, date=datetime.date(2026, 10, 1)
        )
        # Expenses
        self.factory.create_transaction_filled(
            self.wallet, label=self.food_label, type='EXPENSE', value=1500000, date=datetime.date(2026, 10, 2)
        )
        self.factory.create_transaction_filled(
            self.wallet, label=self.bills_label, type='EXPENSE', value=2500000, date=datetime.date(2026, 10, 5)
        )
        # Uncategorized expense
        self.factory.create_transaction_filled(
            self.wallet, label=None, type='EXPENSE', value=1000000, date=datetime.date(2026, 10, 8)
        )
        # Out-of-range transaction (2026-10-15)
        self.factory.create_transaction_filled(
            self.wallet, label=self.food_label, type='EXPENSE', value=500000, date=datetime.date(2026, 10, 15)
        )

        res = self.client.get('/api/reports/summary/?start_date=2026-10-01&end_date=2026-10-10')
        self.assertEqual(res.status_code, 200)
        data = res.data

        # Period check
        self.assertEqual(data['period']['days_count'], 10)
        self.assertEqual(data['period']['start_date'], '2026-10-01')
        self.assertEqual(data['period']['end_date'], '2026-10-10')

        # Summary check
        # Total income: 10,000,000
        self.assertEqual(data['summary']['total_income'], '10000000.00')
        # Total expense: 1,500,000 + 2,500,000 + 1,000,000 = 5,000,000
        self.assertEqual(data['summary']['total_expense'], '5000000.00')
        # Net cash flow: 10,000,000 - 5,000,000 = 5,000,000
        self.assertEqual(data['summary']['net_cash_flow'], '5000000.00')
        # Average daily spending: 5,000,000 / 10 = 500,000.00
        self.assertEqual(data['summary']['average_daily_spending'], '500000.00')

        # Category breakdown
        breakdown = {item['label_name']: item for item in data['category_breakdown']}
        self.assertIn('Food', breakdown)
        self.assertIn('Bills', breakdown)
        self.assertIn('Chưa phân loại', breakdown)
        self.assertEqual(breakdown['Bills']['total'], '2500000.00')
        self.assertEqual(breakdown['Bills']['percentage'], 50.0)
        self.assertEqual(breakdown['Food']['total'], '1500000.00')
        self.assertEqual(breakdown['Food']['percentage'], 30.0)
        self.assertEqual(breakdown['Chưa phân loại']['total'], '1000000.00')
        self.assertEqual(breakdown['Chưa phân loại']['percentage'], 20.0)

    def test_report_comparison_with_previous_period(self):
        # Previous period: 2026-10-01 to 2026-10-10 (10 days)
        self.factory.create_transaction_filled(
            self.wallet, label=self.food_label, type='EXPENSE', value=1000000, date=datetime.date(2026, 10, 5)
        )
        self.factory.create_transaction_filled(
            self.wallet, label=self.salary_label, type='EARNING', value=6000000, date=datetime.date(2026, 10, 1)
        )

        # Current period: 2026-10-11 to 2026-10-20 (10 days)
        # Food increased from 1,000,000 to 2,500,000 (+1,500,000, +150%)
        self.factory.create_transaction_filled(
            self.wallet, label=self.food_label, type='EXPENSE', value=2500000, date=datetime.date(2026, 10, 15)
        )
        self.factory.create_transaction_filled(
            self.wallet, label=self.salary_label, type='EARNING', value=8000000, date=datetime.date(2026, 10, 12)
        )

        res = self.client.get('/api/reports/summary/?start_date=2026-10-11&end_date=2026-10-20')
        self.assertEqual(res.status_code, 200)
        data = res.data

        comp = data['comparison']
        self.assertEqual(comp['previous_period']['total_income'], '6000000.00')
        self.assertEqual(comp['previous_period']['total_expense'], '1000000.00')
        # Income change: (8,000,000 - 6,000,000) / 6,000,000 * 100 = 33.33%
        self.assertEqual(comp['income_change_percentage'], 33.33)
        # Expense change: (2,500,000 - 1,000,000) / 1,000,000 * 100 = 150.0%
        self.assertEqual(comp['expense_change_percentage'], 150.0)

        # Largest spending increases
        increases = data['largest_spending_increases']
        self.assertTrue(len(increases) >= 1)
        self.assertEqual(increases[0]['label_name'], 'Food')
        self.assertEqual(increases[0]['increase_amount'], '1500000.00')
        self.assertEqual(increases[0]['increase_percentage'], 150.0)

    def test_report_export_csv_and_injection_prevention(self):
        # Create normal transaction and potentially malicious formula title
        self.factory.create_transaction_filled(
            self.wallet, label=self.food_label, type='EXPENSE', value=120000, date=datetime.date(2026, 10, 2),
            title='=cmd|/c calc!A0'
        )
        self.factory.create_transaction_filled(
            self.wallet, label=self.salary_label, type='EARNING', value=5000000, date=datetime.date(2026, 10, 1),
            title='Lương tháng 10'
        )

        res = self.client.get('/api/reports/export/csv/?start_date=2026-10-01&end_date=2026-10-31')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'text/csv; charset=utf-8-sig')
        self.assertIn('attachment; filename=', res['Content-Disposition'])

        content = res.content.decode('utf-8-sig')
        # Check metadata in header
        self.assertIn('BÁO CÁO TÀI CHÍNH MONEYMANAGER', content)
        self.assertIn('01/10/2026 đến 31/10/2026', content)
        # Formula injection check: '=cmd...' MUST be sanitized to ''=cmd...'
        self.assertIn("'=cmd|/c calc!A0", content)
        self.assertIn('Lương tháng 10', content)

    def test_report_user_isolation(self):
        other_user = self.factory.create_user()
        other_wallet = other_user.get_wallet()
        other_label = CustomLabel.objects.create(wallet=other_wallet, name='SecretOther', color='#000000')
        self.factory.create_transaction_filled(
            other_wallet, label=other_label, type='EXPENSE', value=99999999, date=datetime.date(2026, 10, 5)
        )

        res = self.client.get('/api/reports/summary/?start_date=2026-10-01&end_date=2026-10-31')
        self.assertEqual(res.status_code, 200)
        # Other user's expense of 99,999,999 must NOT appear in this user's summary
        self.assertNotEqual(res.data['summary']['total_expense'], '99999999.00')
        breakdown_names = [item['label_name'] for item in res.data['category_breakdown']]
        self.assertNotIn('SecretOther', breakdown_names)

    def test_report_export_excel(self):
        self.factory.create_transaction_filled(
            self.wallet, label=self.salary_label, type='EARNING', value=5000000, date=datetime.date(2026, 10, 1),
            title='Lương tháng 10'
        )
        self.factory.create_transaction_filled(
            self.wallet, label=self.food_label, type='EXPENSE', value=120000, date=datetime.date(2026, 10, 2),
            title='Ăn uống trưa'
        )

        res = self.client.get('/api/reports/export/excel/?start_date=2026-10-01&end_date=2026-10-31')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertIn('.xlsx', res['Content-Disposition'])

        import openpyxl
        from io import BytesIO
        wb = openpyxl.load_workbook(BytesIO(res.content))
        ws = wb.active
        self.assertEqual(ws['A2'].value, 'BÁO CÁO TÀI CHÍNH MONEYMANAGER')
        # Check table headers in row 8
        self.assertEqual(ws['A8'].value, 'Mã GD')
        self.assertEqual(ws['B8'].value, 'Ngày')
        self.assertEqual(ws['C8'].value, 'Tiêu đề')
        self.assertEqual(ws['D8'].value, 'Loại')
        self.assertEqual(ws['E8'].value, 'Danh mục')
        self.assertEqual(ws['F8'].value, 'Số tiền (VND)')
        # Check data exists in columns
        self.assertTrue(ws['A9'].value is not None)
        self.assertTrue(ws['C9'].value in ['Lương tháng 10', 'Ăn uống trưa'])

    def test_import_preview_and_import_invoices(self):
        import os
        from django.core.files.uploadedfile import SimpleUploadedFile
        sample_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../sample_invoices/bien_lai_vietcombank.png'))
        if os.path.exists(sample_path):
            with open(sample_path, 'rb') as f:
                upload_file = SimpleUploadedFile('bien_lai_vietcombank.png', f.read(), content_type='image/png')

            # 1. Test Preview API
            res_preview = self.client.post(
                '/api/import/preview/?institution=Ngân hàng Việt Nam (Chung / VietQR)',
                {'files[]': upload_file},
                format='multipart'
            )
            self.assertEqual(res_preview.status_code, 200)
            self.assertTrue(res_preview.data['success'])
            self.assertEqual(len(res_preview.data['results']), 1)
            first_result = res_preview.data['results'][0]
            self.assertEqual(first_result['value'], 850000.0)
            self.assertIn('850.000', first_result['formatted_value'])
            self.assertEqual(first_result['formatted_date'], '11/10/2026')

            # 2. Test Import API
            with open(sample_path, 'rb') as f:
                upload_file_2 = SimpleUploadedFile('bien_lai_vietcombank.png', f.read(), content_type='image/png')
            res_import = self.client.post(
                '/api/import/?type=EXPENSE&updateWallet=1',
                {'files[]': upload_file_2},
                format='multipart'
            )
            self.assertEqual(res_import.status_code, 200)
            self.assertTrue(res_import.data['success'])
            self.assertTrue(len(res_import.data['imported']) >= 1)
            self.assertEqual(res_import.data['imported'][0]['value'], 850000.0)


class AuthenticationAndAuthorizationTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.factory = TransactionFactory()

    def test_user_registration_success(self):
        payload = {
            'firstName': 'Nguyen',
            'lastName': 'Van A',
            'email': 'nguyenvana@example.com',
            'password': 'SecurePassword123!',
        }
        response = self.client.post('/api/register/', payload, format='json')
        self.assertEqual(response.status_code, 201)

        user = HubUser.objects.filter(email='nguyenvana@example.com').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.first_name, 'Nguyen')
        self.assertEqual(user.last_name, 'Van A')
        self.assertTrue(user.check_password('SecurePassword123!'))

        wallet = user.get_wallet()
        self.assertIsNotNone(wallet)
        self.assertEqual(wallet.current_amount, Decimal('0.00'))

    def test_user_registration_duplicate_email(self):
        self.factory.create_user(email='existing@example.com')
        payload = {
            'firstName': 'Duplicate',
            'lastName': 'User',
            'email': 'existing@example.com',
            'password': 'Password123!',
        }
        response = self.client.post('/api/register/', payload, format='json')
        self.assertEqual(response.status_code, 400)

    def test_user_registration_invalid_inputs(self):
        # Empty email
        res1 = self.client.post('/api/register/', {'email': '', 'password': 'Pass'}, format='json')
        self.assertEqual(res1.status_code, 400)

        # Invalid email format
        res2 = self.client.post('/api/register/', {'email': 'invalid-email', 'password': 'Pass'}, format='json')
        self.assertEqual(res2.status_code, 400)

        # Empty password
        res3 = self.client.post('/api/register/', {'email': 'valid@example.com', 'password': ''}, format='json')
        self.assertEqual(res3.status_code, 400)

        # Non-dictionary payload
        res4 = self.client.post('/api/register/', 'not-a-dict', format='json')
        self.assertEqual(res4.status_code, 400)

    def test_token_obtain_and_refresh_flow(self):
        user = HubUser.objects.create_user(
            first_name='Test',
            last_name='User',
            email='jwtflow@example.com',
            password='MyPassword123!'
        )

        # 1. Login with valid credentials
        res_login = self.client.post('/api/token/', {
            'email': 'jwtflow@example.com',
            'password': 'MyPassword123!',
        }, format='json')
        self.assertEqual(res_login.status_code, 200)
        self.assertIn('access', res_login.data)
        self.assertIn('refresh_token', res_login.cookies)
        refresh_cookie = res_login.cookies['refresh_token']
        self.assertTrue(refresh_cookie['httponly'])

        # 2. Refresh token using cookie
        self.client.cookies['refresh_token'] = refresh_cookie.value
        res_refresh = self.client.post('/api/token/refresh/')
        self.assertEqual(res_refresh.status_code, 200)
        self.assertIn('access_token', res_refresh.data)

    def test_token_obtain_invalid_credentials(self):
        HubUser.objects.create_user(
            first_name='Test',
            last_name='User',
            email='wrongpwd@example.com',
            password='CorrectPassword!'
        )
        res = self.client.post('/api/token/', {
            'email': 'wrongpwd@example.com',
            'password': 'WrongPassword!',
        }, format='json')
        self.assertEqual(res.status_code, 401)

    def test_token_refresh_without_cookie_fails(self):
        self.client.cookies.clear()
        res = self.client.post('/api/token/refresh/')
        self.assertEqual(res.status_code, 403)

    def test_unauthenticated_requests_are_denied(self):
        anonymous_client = APIClient()
        endpoints = [
            ('GET', '/api/wallet/'),
            ('GET', '/api/transactions/'),
            ('POST', '/api/transaction/'),
            ('GET', '/api/budgets/'),
            ('GET', '/api/budgets/summary/'),
            ('GET', '/api/savingplans/'),
            ('GET', '/api/reports/summary/'),
            ('GET', '/api/reports/transactions/'),
            ('POST', '/api/import/'),
            ('POST', '/api/import/preview/'),
        ]
        for method, url in endpoints:
            if method == 'GET':
                resp = anonymous_client.get(url)
            else:
                resp = anonymous_client.post(url, {}, format='json')
            self.assertEqual(
                resp.status_code,
                401,
                f"Expected 401 Unauthorized for {method} {url}, got {resp.status_code}"
            )


class ObjectOwnershipAndAccessControlTestCase(TestCase):
    def setUp(self):
        self.factory = TransactionFactory()
        self.user_a = self.factory.create_user(email='usera@example.com')
        self.wallet_a = self.user_a.get_wallet()
        self.wallet_a.set_balance(1000)

        self.user_b = self.factory.create_user(email='userb@example.com')
        self.wallet_b = self.user_b.get_wallet()
        self.wallet_b.set_balance(500)

        self.client_a = APIClient()
        self.client_a.force_authenticate(self.user_a)

    def test_user_a_cannot_view_or_update_user_b_transaction(self):
        tx_b = self.factory.create_transaction_filled(
            self.wallet_b, title='Secret B', value=200, type='EXPENSE', update_wallet=True
        )

        # User A tries to edit User B's transaction
        res_put = self.client_a.put(f'/api/transaction/{tx_b.pk}', {
            'title': 'Hacked',
            'value': 10,
            'type': 'EXPENSE',
            'date': '2026-10-01'
        }, format='json')
        self.assertEqual(res_put.status_code, 404)

        # User A tries to delete User B's transaction
        res_del = self.client_a.delete(f'/api/transaction/{tx_b.pk}')
        self.assertEqual(res_del.status_code, 404)

        # Verify wallet B was not modified
        self.wallet_b.refresh_from_db()
        self.assertEqual(self.wallet_b.current_amount, Decimal('300.00'))

    def test_user_a_cannot_assign_user_b_label_to_transaction(self):
        label_b = CustomLabel.objects.create(wallet=self.wallet_b, name='B Category', color='#123456')

        res = self.client_a.post('/api/transaction/', {
            'title': 'My Transaction',
            'value': 100,
            'type': 'EXPENSE',
            'date': '2026-10-01',
            'label': {'id': label_b.pk}
        }, format='json')
        self.assertEqual(res.status_code, 400)

    def test_user_a_cannot_delete_user_b_custom_label(self):
        label_b = CustomLabel.objects.create(wallet=self.wallet_b, name='Private Label', color='#abcdef')
        res = self.client_a.delete(f'/api/labels/{label_b.pk}')
        self.assertEqual(res.status_code, 404)
        self.assertTrue(CustomLabel.objects.filter(pk=label_b.pk).exists())

    def test_user_a_cannot_access_or_modify_user_b_budget(self):
        label_b = CustomLabel.objects.create(wallet=self.wallet_b, name='Budget B', color='#223344')
        budget_b = CategoryBudget.objects.create(
            wallet=self.wallet_b, label=label_b, amount=Decimal('500.00'), month=10, year=2026
        )

        # User A attempts GET on User B's budget
        res_get = self.client_a.get(f'/api/budgets/{budget_b.pk}')
        self.assertEqual(res_get.status_code, 404)

        # User A attempts PUT
        res_put = self.client_a.put(f'/api/budgets/{budget_b.pk}', {'amount': 100}, format='json')
        self.assertEqual(res_put.status_code, 404)

        # User A attempts DELETE
        res_del = self.client_a.delete(f'/api/budgets/{budget_b.pk}')
        self.assertEqual(res_del.status_code, 404)

        # User A attempts to create budget with User B's category
        res_create = self.client_a.post('/api/budgets/', {
            'label_id': label_b.pk,
            'amount': 300,
            'month': 10,
            'year': 2026,
        }, format='json')
        self.assertEqual(res_create.status_code, 400)

    def test_user_a_cannot_access_or_contribute_to_user_b_saving_plan(self):
        plan_b = SavingPlan.objects.create(
            wallet=self.wallet_b, title='Car Fund', amount=Decimal('10000.00')
        )

        # User A attempts GET
        res_get = self.client_a.get(f'/api/savingplans/{plan_b.pk}')
        self.assertEqual(res_get.status_code, 404)

        # User A attempts PUT
        res_put = self.client_a.put(f'/api/savingplans/{plan_b.pk}', {'title': 'Stolen Plan'}, format='json')
        self.assertEqual(res_put.status_code, 404)

        # User A attempts DELETE
        res_del = self.client_a.delete(f'/api/savingplans/{plan_b.pk}')
        self.assertEqual(res_del.status_code, 404)

        # User A attempts to add a contribution to User B's plan
        res_contrib = self.client_a.post(f'/api/savingplans/{plan_b.pk}/contributions/', {
            'amount': 500,
            'date': '2026-10-15',
        }, format='json')
        self.assertEqual(res_contrib.status_code, 404)
        self.assertEqual(plan_b.contributions.count(), 0)

    def test_reports_wallet_isolation(self):
        # User A attempting to query User B's wallet in reports summary returns 403 Forbidden
        res = self.client_a.get(f'/api/reports/summary/?wallet_id={self.wallet_b.pk}')
        self.assertEqual(res.status_code, 403)


class InvoiceImportValidationTestCase(TestCase):
    def setUp(self):
        self.factory = TransactionFactory()
        self.user = self.factory.create_user(email='importsec@example.com')
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_import_without_files_returns_400(self):
        res1 = self.client.post('/api/import/')
        self.assertEqual(res1.status_code, 400)

        res2 = self.client.post('/api/import/preview/')
        self.assertEqual(res2.status_code, 400)

    def test_import_unsupported_file_extension_returns_400(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        fake_exe = SimpleUploadedFile('exploit.exe', b'MZExecutableBinaryData', content_type='application/x-msdownload')

        res_import = self.client.post('/api/import/', {'files[]': fake_exe}, format='multipart')
        self.assertEqual(res_import.status_code, 400)

        fake_sh = SimpleUploadedFile('script.sh', b'#!/bin/bash\necho 1', content_type='text/x-shellscript')
        res_preview = self.client.post('/api/import/preview/', {'files[]': fake_sh}, format='multipart')
        self.assertEqual(res_preview.status_code, 400)

    def test_import_oversized_file_returns_400(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        # 11 MB simulated file
        oversized = SimpleUploadedFile('big_invoice.pdf', b'a' * (11 * 1024 * 1024), content_type='application/pdf')
        res = self.client.post('/api/import/', {'files[]': oversized}, format='multipart')
        self.assertEqual(res.status_code, 400)

    def test_import_corrupted_file_handles_gracefully(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        corrupted = SimpleUploadedFile('corrupt.pdf', b'NOT_A_VALID_PDF_HEADER', content_type='application/pdf')
        res = self.client.post('/api/import/', {'files[]': corrupted}, format='multipart')
        # Should return user-friendly error response, not unhandled 500
        self.assertIn(res.status_code, [400, 422])


class BoundaryAndValidationTestCase(TestCase):
    def setUp(self):
        self.factory = TransactionFactory()
        self.user = self.factory.create_user(email='boundary@example.com')
        self.wallet = self.user.get_wallet()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_transaction_negative_and_zero_amount(self):
        # Value = 0
        res0 = self.client.post('/api/transaction/', {
            'title': 'Zero Test', 'value': 0, 'type': 'EXPENSE', 'date': '2026-10-15'
        }, format='json')
        self.assertEqual(res0.status_code, 400)

        # Value < 0
        res_neg = self.client.post('/api/transaction/', {
            'title': 'Negative Test', 'value': -500, 'type': 'EXPENSE', 'date': '2026-10-15'
        }, format='json')
        self.assertEqual(res_neg.status_code, 400)

        # Non-numeric
        res_str = self.client.post('/api/transaction/', {
            'title': 'String Test', 'value': 'abc', 'type': 'EXPENSE', 'date': '2026-10-15'
        }, format='json')
        self.assertEqual(res_str.status_code, 400)

    def test_transaction_invalid_dates_and_types(self):
        # Invalid date
        res_date = self.client.post('/api/transaction/', {
            'title': 'Bad Date', 'value': 100, 'type': 'EXPENSE', 'date': 'invalid-date'
        }, format='json')
        self.assertEqual(res_date.status_code, 400)

        # Invalid type
        res_type = self.client.post('/api/transaction/', {
            'title': 'Bad Type', 'value': 100, 'type': 'TRANSFER', 'date': '2026-10-15'
        }, format='json')
        self.assertEqual(res_type.status_code, 400)

    def test_wallet_balance_invalid_values(self):
        res1 = self.client.put('/api/wallet/', 'not-a-number', format='json')
        self.assertEqual(res1.status_code, 422)

        res2 = self.client.put('/api/wallet/', True, format='json')
        self.assertEqual(res2.status_code, 422)

    def test_budget_boundary_month_and_year(self):
        label = CustomLabel.objects.create(wallet=self.wallet, name='Food', color='#FF0000')

        # Month < 1
        res1 = self.client.post('/api/budgets/', {
            'label_id': label.pk, 'amount': 100, 'month': 0, 'year': 2026
        }, format='json')
        self.assertEqual(res1.status_code, 400)

        # Month > 12
        res2 = self.client.post('/api/budgets/', {
            'label_id': label.pk, 'amount': 100, 'month': 13, 'year': 2026
        }, format='json')
        self.assertEqual(res2.status_code, 400)

        # Year < 2000
        res3 = self.client.post('/api/budgets/', {
            'label_id': label.pk, 'amount': 100, 'month': 5, 'year': 1999
        }, format='json')
        self.assertEqual(res3.status_code, 400)

        # Year > 2100
        res4 = self.client.post('/api/budgets/', {
            'label_id': label.pk, 'amount': 100, 'month': 5, 'year': 2101
        }, format='json')
        self.assertEqual(res4.status_code, 400)

        # Amount <= 0
        res5 = self.client.post('/api/budgets/', {
            'label_id': label.pk, 'amount': -50, 'month': 5, 'year': 2026
        }, format='json')
        self.assertEqual(res5.status_code, 400)

    def test_saving_plan_boundary_amounts(self):
        # Negative target amount
        res1 = self.client.post('/api/savingplans/', {
            'title': 'Test Plan', 'amount': -100
        }, format='json')
        self.assertEqual(res1.status_code, 400)

        # Zero target amount
        res2 = self.client.post('/api/savingplans/', {
            'title': 'Test Plan', 'amount': 0
        }, format='json')
        self.assertEqual(res2.status_code, 400)

        # Negative contribution amount
        plan = SavingPlan.objects.create(wallet=self.wallet, title='Goal', amount=Decimal('1000.00'))
        res3 = self.client.post(f'/api/savingplans/{plan.pk}/contributions/', {
            'amount': -50
        }, format='json')
        self.assertEqual(res3.status_code, 400)

    def test_nonexistent_resource_endpoints_return_404(self):
        self.assertEqual(self.client.get('/api/budget/999999').status_code, 404)
        self.assertEqual(self.client.delete('/api/transaction/999999').status_code, 404)
        self.assertEqual(self.client.get('/api/savingplan/999999').status_code, 404)
        self.assertEqual(self.client.delete('/api/labels/999999').status_code, 404)









