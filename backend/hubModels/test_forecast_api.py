import datetime
from decimal import Decimal
import time

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from hubModels.factory import TransactionFactory
from hubModels.models import (
    DebtLoan,
    DebtPayment,
    Transaction,
    TransactionRecurrency,
)
from hubModels.services import CashFlowForecastService


class CashFlowForecastAPITestCase(TestCase):
    def setUp(self):
        self.factory = TransactionFactory()
        self.user = self.factory.create_user()
        self.wallet = self.user.get_wallet()
        self.wallet.update_balance(10_000_000)

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        # Other user for isolation checks
        self.other_user = self.factory.create_user()
        self.other_wallet = self.other_user.get_wallet()
        self.other_wallet.update_balance(20_000_000)

    def test_unauthenticated_request_rejected(self):
        """Yêu cầu chưa đăng nhập phải bị từ chối với mã 401."""
        unauthed_client = APIClient()
        response = unauthed_client.get('/api/forecast/cashflow/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_default_params_success(self):
        """GET /api/forecast/cashflow/ mặc định days=30, safety_buffer=0."""
        response = self.client.get('/api/forecast/cashflow/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['horizon_days'], 30)
        self.assertEqual(data['current_balance'], "10000000.00")
        self.assertIn('projected_end_balance', data)
        self.assertIn('lowest_balance', data)
        self.assertIn('lowest_balance_date', data)
        self.assertIn('risk_level', data)
        self.assertIn('daily_burn_rate', data)
        self.assertIn('daily_timeline', data)
        self.assertEqual(len(data['daily_timeline']), 31)
        self.assertIn('recommendations', data)

    def test_invalid_days_param_returns_400(self):
        """days không phải 30, 60, 90 trả 400 kèm thông điệp tiếng Việt."""
        for invalid in [15, 45, 100, -1, 'abc']:
            response = self.client.get(f'/api/forecast/cashflow/?days={invalid}')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            data = response.json()
            self.assertFalse(data.get('success', True))
            self.assertIn("Khoảng thời gian dự báo phải là", data.get('message', ''))

    def test_invalid_safety_buffer_returns_400(self):
        """safety_buffer âm hoặc không hợp lệ trả 400 kèm thông điệp tiếng Việt."""
        for invalid in [-100, -0.01, 'invalid']:
            response = self.client.get(f'/api/forecast/cashflow/?safety_buffer={invalid}')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            data = response.json()
            self.assertFalse(data.get('success', True))
            self.assertIn("Ngưỡng an toàn phải là số không âm hợp lệ.", data.get('message', ''))

    def test_valid_horizons_60_and_90(self):
        """days=60 cho timeline 61 điểm; days=90 cho timeline 91 điểm."""
        r60 = self.client.get('/api/forecast/cashflow/?days=60')
        self.assertEqual(r60.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r60.json()['daily_timeline']), 61)

        r90 = self.client.get('/api/forecast/cashflow/?days=90')
        self.assertEqual(r90.status_code, status.HTTP_200_OK)
        self.assertEqual(len(r90.json()['daily_timeline']), 91)

    def test_safety_buffer_triggers_warning_risk_level(self):
        """safety_buffer > 0 khi số dư rơi dưới ngưỡng an toàn trả về risk_level = WARNING."""
        # Ví có 10tr, đặt safety_buffer = 15tr -> ngay lập tức dưới buffer
        response = self.client.get('/api/forecast/cashflow/?days=30&safety_buffer=15000000')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data['risk_level'], 'WARNING')
        self.assertFalse(data['is_insolvency_risk'])
        self.assertTrue(any(r['code'] == 'BELOW_BUFFER' for r in data['recommendations']))

    def test_insolvency_critical_risk_level_response(self):
        """Khi có khoản chi cố định gây âm ví: risk_level = CRITICAL và sinh SHORTFALL_RISK."""
        today = timezone.localdate()
        due_date = today + datetime.timedelta(days=10)

        # Khoản nợ phải trả 15.000.000đ (vượt số dư 10.000.000đ)
        DebtLoan.objects.create(
            wallet=self.wallet,
            person_name="No lon",
            type="DEBT_BORROWED",
            principal_amount=Decimal("15000000.00"),
            start_date=today,
            due_date=due_date,
            status="ACTIVE",
        )

        response = self.client.get('/api/forecast/cashflow/?days=30')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['risk_level'], 'CRITICAL')
        self.assertTrue(data['is_insolvency_risk'])
        self.assertEqual(data['first_negative_date'], due_date.isoformat())
        self.assertGreater(Decimal(data['max_shortfall']), Decimal("0.00"))

        codes = [r['code'] for r in data['recommendations']]
        self.assertIn('SHORTFALL_RISK', codes)

    def test_ownership_isolation_via_api(self):
        """Endpoint chỉ trả dữ liệu ví của request.user; không bị ảnh hưởng bởi user khác."""
        other_client = APIClient()
        other_client.force_authenticate(user=self.other_user)

        # User B tạo khoản nợ lớn
        today = timezone.localdate()
        DebtLoan.objects.create(
            wallet=self.other_wallet,
            person_name="No cua User B",
            type="DEBT_BORROWED",
            principal_amount=Decimal("99000000.00"),
            start_date=today,
            due_date=today + datetime.timedelta(days=5),
            status="ACTIVE",
        )

        # User A gọi API -> hoàn toàn an toàn (SAFE), số dư 10tr
        res_a = self.client.get('/api/forecast/cashflow/?days=30')
        self.assertEqual(res_a.status_code, status.HTTP_200_OK)
        data_a = res_a.json()
        self.assertEqual(data_a['current_balance'], "10000000.00")
        self.assertEqual(data_a['risk_level'], 'SAFE')

        # User B gọi API -> bị CRITICAL do khoản nợ 99tr
        res_b = other_client.get('/api/forecast/cashflow/?days=30')
        self.assertEqual(res_b.status_code, status.HTTP_200_OK)
        data_b = res_b.json()
        self.assertEqual(data_b['risk_level'], 'CRITICAL')

    def test_integration_recurring_debt_installment_all_appear_on_timeline(self):
        """Giao dịch định kỳ hàng tháng, nợ DEBT_BORROWED có due_date và kỳ trả góp đều xuất hiện đúng ngày trong daily_timeline."""
        from dateutil.relativedelta import relativedelta

        today = timezone.localdate()
        date_rec = today + datetime.timedelta(days=5)
        date_debt = today + datetime.timedelta(days=12)
        date_inst = today + datetime.timedelta(days=18)

        # 1. Định kỳ hàng tháng
        tx = Transaction.objects.create(
            wallet=self.wallet,
            title="Tien Internet",
            value=Decimal("300000.00"),
            date=date_rec - relativedelta(months=1),
            type="EXPENSE",
            update_wallet=True,
            recurrent=True,
        )
        rec = TransactionRecurrency.objects.create(
            transaction=tx,
            amount=1,
            duration="MONTHS",
            active=True,
        )
        tx.recurrency = rec
        tx.save(update_fields=['recurrency'])

        # 2. Nợ DEBT_BORROWED có due_date
        DebtLoan.objects.create(
            wallet=self.wallet,
            person_name="Anh Tuan",
            type="DEBT_BORROWED",
            principal_amount=Decimal("2000000.00"),
            start_date=today - datetime.timedelta(days=10),
            due_date=date_debt,
            status="ACTIVE",
        )

        # 3. Trả góp INSTALLMENT
        # Bắt đầu từ date_inst - 1 tháng, 3 kỳ -> kỳ 1 rơi đúng vào date_inst
        DebtLoan.objects.create(
            wallet=self.wallet,
            person_name="Mua Laptop Tra Gop",
            type="INSTALLMENT",
            principal_amount=Decimal("15000000.00"),
            installment_months=3,
            start_date=date_inst - relativedelta(months=1),
            status="ACTIVE",
        )

        response = self.client.get('/api/forecast/cashflow/?days=30')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        timeline = response.json()['daily_timeline']

        # Tìm các ngày tương ứng trong timeline
        pt_rec = next((pt for pt in timeline if pt['date'] == date_rec.isoformat()), None)
        pt_debt = next((pt for pt in timeline if pt['date'] == date_debt.isoformat()), None)
        pt_inst = next((pt for pt in timeline if pt['date'] == date_inst.isoformat()), None)

        self.assertIsNotNone(pt_rec)
        self.assertIsNotNone(pt_debt)
        self.assertIsNotNone(pt_inst)

        # Kiểm tra events
        rec_events = [e['source'] for e in pt_rec['fixed_events']]
        debt_events = [e['source'] for e in pt_debt['fixed_events']]
        inst_events = [e['source'] for e in pt_inst['fixed_events']]

        self.assertIn('RECURRING', rec_events)
        self.assertIn('DEBT', debt_events)
        self.assertIn('INSTALLMENT', inst_events)

    def test_integration_create_recurring_expense_5m_day_20_drops_5m(self):
        """Tạo định kỳ chi 5.000.000đ ngày 20 thì đường dự báo giảm đúng 5.000.000đ tại ngày 20."""
        from dateutil.relativedelta import relativedelta

        today = timezone.localdate()
        target_day_20 = today + datetime.timedelta(days=20)

        # Tạo giao dịch định kỳ có ngày kế tiếp đúng vào ngày 20
        tx = Transaction.objects.create(
            wallet=self.wallet,
            title="Dong tien hoc phi",
            value=Decimal("5000000.00"),
            date=target_day_20 - relativedelta(months=1),
            type="EXPENSE",
            update_wallet=True,
            recurrent=True,
        )
        rec = TransactionRecurrency.objects.create(
            transaction=tx,
            amount=1,
            duration="MONTHS",
            active=True,
        )
        tx.recurrency = rec
        tx.save(update_fields=['recurrency'])

        response = self.client.get('/api/forecast/cashflow/?days=30')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        timeline = data['daily_timeline']

        pt_19 = timeline[19]
        pt_20 = timeline[20]
        d_var = Decimal(data['daily_burn_rate'])

        bal_19 = Decimal(pt_19['balance'])
        bal_20 = Decimal(pt_20['balance'])

        # Ngày 20 phải giảm đúng d_var + 5.000.000đ
        self.assertEqual(bal_20, bal_19 - d_var - Decimal("5000000.00"))

    def test_integration_constant_query_count_across_days_and_transactions(self):
        """Chứng minh số query của endpoint không tăng khi days từ 30 lên 90 và khi tăng số giao dịch."""
        from django.test.utils import CaptureQueriesContext
        from django.db import connection

        # Gọi trước để làm ấm cache xác thực (auth/session/token nếu có)
        self.client.get('/api/forecast/cashflow/?days=30')

        # Đo số query tại days=30 bằng CaptureQueriesContext
        with CaptureQueriesContext(connection) as ctx30:
            self.client.get('/api/forecast/cashflow/?days=30')
        query_count_30 = len(ctx30.captured_queries)

        # Đo số query tại days=90 -> số query phải bằng đúng days=30
        with self.assertNumQueries(query_count_30):
            self.client.get('/api/forecast/cashflow/?days=90')

        # Thêm 50 giao dịch thông thường và 10 định kỳ
        today = timezone.localdate()
        txs = [
            Transaction(
                wallet=self.wallet,
                title=f"Sample Tx {i}",
                value=Decimal("50000.00"),
                date=today - datetime.timedelta(days=i % 30),
                type="EXPENSE",
                update_wallet=False,
            )
            for i in range(50)
        ]
        Transaction.objects.bulk_create(txs)

        # Đo lại với số giao dịch đã tăng nhiều lần: số query vẫn bằng đúng query_count_30!
        with self.assertNumQueries(query_count_30):
            self.client.get('/api/forecast/cashflow/?days=90')

    def test_integration_benchmark_90_days_with_10000_transactions(self):
        """Hiệu năng: benchmark 90 ngày với 10.000 giao dịch. Đo thời gian thực tế, mục tiêu dưới 350ms."""
        today = timezone.localdate()

        # Sinh 10.000 giao dịch phân bổ trong 60 ngày qua
        bulk_txs = [
            Transaction(
                wallet=self.wallet,
                title=f"Benchmark Tx {i}",
                value=Decimal(str((i % 200 + 1) * 1000)),
                date=today - datetime.timedelta(days=(i % 60)),
                type="EXPENSE",
                update_wallet=False,
            )
            for i in range(10_000)
        ]
        Transaction.objects.bulk_create(bulk_txs, batch_size=2000)

        # Thêm các sự kiện định kỳ & nợ cố định
        for i in range(5):
            tx = Transaction.objects.create(
                wallet=self.wallet,
                title=f"Recurring Expense {i}",
                value=Decimal("500000.00"),
                date=today - datetime.timedelta(days=30),
                type="EXPENSE",
                update_wallet=False,
                recurrent=True,
            )
            rec = TransactionRecurrency.objects.create(
                transaction=tx,
                amount=1,
                duration="MONTHS",
                active=True,
            )
            tx.recurrency = rec
            tx.save(update_fields=['recurrency'])

            debt = DebtLoan.objects.create(
                wallet=self.wallet,
                person_name=f"Creditor {i}",
                type="INSTALLMENT",
                principal_amount=Decimal("12000000.00"),
                installment_months=12,
                start_date=today - datetime.timedelta(days=60),
                status="ACTIVE",
            )
            DebtPayment.objects.create(
                debt=debt,
                amount=Decimal("1000000.00"),
                date=today - datetime.timedelta(days=30),
                update_wallet=False,
            )

        # Warm-up run
        CashFlowForecastService.forecast(self.wallet, days=90)

        # Đo thời gian thực tế của service qua 5 lần chạy
        durations = []
        for _ in range(5):
            start = time.perf_counter()
            res = CashFlowForecastService.forecast(self.wallet, days=90)
            durations.append(time.perf_counter() - start)
            self.assertEqual(res.horizon_days, 90)

        avg_duration_sec = sum(durations) / len(durations)
        avg_ms = avg_duration_sec * 1000
        min_ms = min(durations) * 1000
        max_ms = max(durations) * 1000

        print(f"\n[BENCHMARK RESULT] 10,000 Transactions - 90 Days Horizon:")
        print(f"  Average execution time: {avg_ms:.2f} ms")
        print(f"  Min: {min_ms:.2f} ms | Max: {max_ms:.2f} ms")
        print(f"  Target: < 350.00 ms")

        # Kiểm tra ngưỡng SLA 350ms
        self.assertLess(avg_ms, 350.0, f"Benchmark exceeded 350ms: {avg_ms:.2f} ms")
