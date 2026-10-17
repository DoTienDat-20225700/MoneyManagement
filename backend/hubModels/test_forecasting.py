import datetime
from decimal import Decimal
import math
from unittest import TestCase as UnitTestCase

from django.test import TestCase
from django.utils import timezone

from hubModels.factory import TransactionFactory
from hubModels.models import (
    DebtLoan,
    DebtPayment,
    Transaction,
    TransactionRecurrency,
    Wallet,
)
from hubModels.services.forecasting import (
    CashFlowForecastService,
    ForecastResult,
    calculate_daily_burn_rate,
    simulate_cashflow,
)
from hubModels.services.forecasting_inputs import FixedEvent


class PureForecastingAlgorithmTestCase(UnitTestCase):
    """
    Pure unit tests for simulate_cashflow and calculate_daily_burn_rate without database access.
    """

    def test_burn_rate_empty_history(self):
        """Khi không có lịch sử chi tiêu: D_variable = 0, low_confidence = True, không lỗi."""
        today = datetime.date(2026, 3, 1)
        d_var, low_conf, used_days = calculate_daily_burn_rate([], today=today)
        self.assertEqual(d_var, Decimal("0.00"))
        self.assertTrue(low_conf)
        self.assertEqual(used_days, 0)

    def test_burn_rate_all_zero_history(self):
        """Khi lịch sử toàn số 0: D_variable = 0, low_confidence = True."""
        today = datetime.date(2026, 3, 1)
        history = [(today - datetime.timedelta(days=i), Decimal("0.00")) for i in range(60, 0, -1)]
        d_var, low_conf, used_days = calculate_daily_burn_rate(history, today=today)
        self.assertEqual(d_var, Decimal("0.00"))
        self.assertTrue(low_conf)
        self.assertEqual(used_days, 0)

    def test_burn_rate_low_confidence_under_14_days(self):
        """Dưới 14 ngày lịch sử thực tế tính từ chi tiêu đầu tiên: low_confidence = True."""
        today = datetime.date(2026, 3, 1)
        # Chỉ có chi tiêu trong 10 ngày gần nhất
        history = []
        for i in range(60, 0, -1):
            cur_d = today - datetime.timedelta(days=i - 1)
            amt = Decimal("100000.00") if i <= 10 else Decimal("0.00")
            history.append((cur_d, amt))

        d_var, low_conf, used_days = calculate_daily_burn_rate(history, today=today)
        self.assertEqual(used_days, 10)
        self.assertTrue(low_conf)
        self.assertGreater(d_var, Decimal("0.00"))

    def test_burn_rate_high_confidence_over_14_days(self):
        """Từ 14 ngày lịch sử trở lên: low_confidence = False."""
        today = datetime.date(2026, 3, 1)
        # Chi tiêu trong 20 ngày gần nhất
        history = []
        for i in range(60, 0, -1):
            cur_d = today - datetime.timedelta(days=i - 1)
            amt = Decimal("200000.00") if i <= 20 else Decimal("0.00")
            history.append((cur_d, amt))

        d_var, low_conf, used_days = calculate_daily_burn_rate(history, today=today)
        self.assertEqual(used_days, 20)
        self.assertFalse(low_conf)
        self.assertGreater(d_var, Decimal("0.00"))

    def test_burn_rate_winsorization_caps_extreme_outliers(self):
        """Một ngày chi tiêu đột biến (outlier) bị chặn tại mean + 3 * std, không làm vọt EWMA."""
        today = datetime.date(2026, 3, 1)
        # 59 ngày chi tiêu 100.000đ, 1 ngày chi tiêu 50.000.000đ (mua xe)
        history = []
        for i in range(60, 0, -1):
            cur_d = today - datetime.timedelta(days=i - 1)
            amt = Decimal("50000000.00") if i == 30 else Decimal("100000.00")
            history.append((cur_d, amt))

        d_var, _, _ = calculate_daily_burn_rate(history, today=today)
        # Nếu không winsorize, EWMA sẽ bị đẩy lên rất cao (vài triệu đến chục triệu)
        # Với winsorize, mức tăng được kiểm soát hợp lý
        self.assertLess(d_var, Decimal("5000000.00"))

    def test_burn_rate_constant_series(self):
        """Chuỗi chi tiêu không đổi thì D_variable bằng chính giá trị đó."""
        today = datetime.date(2026, 3, 1)
        history = [(today - datetime.timedelta(days=i), Decimal("150000.00")) for i in range(30, 0, -1)]
        d_var, low_conf, used_days = calculate_daily_burn_rate(history, today=today)
        self.assertEqual(d_var, Decimal("150000.00"))
        self.assertFalse(low_conf)

    def test_burn_rate_short_series_under_7_days(self):
        """Chuỗi ngắn <= 7 ngày khởi tạo bằng trung bình toàn chuỗi, không lỗi."""
        today = datetime.date(2026, 3, 1)
        history = [
            (today - datetime.timedelta(days=2), Decimal("100000.00")),
            (today - datetime.timedelta(days=1), Decimal("200000.00")),
            (today, Decimal("300000.00")),
        ]
        d_var, low_conf, used_days = calculate_daily_burn_rate(history, today=today)
        # Trung bình = 200.000đ
        self.assertEqual(d_var, Decimal("200000.00"))
        self.assertTrue(low_conf)

    def test_pure_no_events_no_history_balance_constant_low_conf(self):
        """Không có sự kiện, không có lịch sử: balance không đổi, low_confidence = True, không lỗi chia cho 0."""
        today = datetime.date(2026, 3, 1)
        res = simulate_cashflow(
            current_balance=Decimal("15000000.00"),
            events=[],
            daily_history=[],
            today=today,
            days=30,
        )
        self.assertEqual(len(res.daily_timeline), 31)
        for pt in res.daily_timeline:
            self.assertEqual(pt['balance'], Decimal("15000000.00"))
        self.assertTrue(res.low_confidence)
        self.assertEqual(res.daily_burn_rate, Decimal("0.00"))
        self.assertEqual(res.projected_end_balance, Decimal("15000000.00"))

    def test_pure_day_20_expense_5m_decreases_balance_exact_5m(self):
        """Sự kiện chi 5.000.000đ vào ngày thứ 20 của kỳ: đường balance giảm đúng 5.000.000đ tại đúng ngày đó, các ngày khác chỉ giảm D_variable."""
        today = datetime.date(2026, 3, 1)
        current_balance = Decimal("20000000.00")
        target_date = today + datetime.timedelta(days=20)
        events = [
            FixedEvent(
                date=target_date,
                title="Chi phi dot 20",
                amount=Decimal("-5000000.00"),
                source="RECURRING",
                source_id=1,
            )
        ]
        daily_history = [(today - datetime.timedelta(days=i), Decimal("100000.00")) for i in range(30, 0, -1)]

        res = simulate_cashflow(
            current_balance=current_balance,
            events=events,
            daily_history=daily_history,
            today=today,
            days=30,
        )

        d_var = res.daily_burn_rate
        self.assertEqual(d_var, Decimal("100000.00"))
        timeline = res.daily_timeline
        self.assertEqual(len(timeline), 31)
        self.assertEqual(timeline[0]['balance'], Decimal("20000000.00"))

        for t in range(1, 31):
            prev_balance = timeline[t - 1]['balance']
            cur_balance = timeline[t]['balance']
            if t == 20:
                self.assertEqual(cur_balance, prev_balance - d_var - Decimal("5000000.00"))
            else:
                self.assertEqual(cur_balance, prev_balance - d_var)

    def test_pure_ewma_manual_hand_calculated_small_series(self):
        """Công thức EWMA đúng với chuỗi nhỏ tính tay (alpha = 0,2, khởi tạo trung bình 7 ngày đầu); chuỗi hằng số cho D_variable bằng hằng số đó."""
        today = datetime.date(2026, 3, 1)
        small_series = [
            (today - datetime.timedelta(days=10 - i), Decimal(str(val)))
            for i, val in enumerate([100, 100, 100, 100, 100, 100, 100, 150, 200, 100])
        ]
        d_var, low_conf, used_days = calculate_daily_burn_rate(small_series, today=today)
        self.assertEqual(d_var, Decimal("122.40"))

        constant_series = [(today - datetime.timedelta(days=i), Decimal("100000.00")) for i in range(30, 0, -1)]
        d_const, _, _ = calculate_daily_burn_rate(constant_series, today=today)
        self.assertEqual(d_const, Decimal("100000.00"))

    def test_pure_outlier_winsorize_near_100k(self):
        """Outlier: chuỗi ổn định 100.000đ/ngày có một ngày 5.000.000đ: D_variable gần 100.000đ (bị chặn ở ngưỡng mean + 3 sigma), không bị kéo lệch."""
        today = datetime.date(2026, 3, 1)
        history = []
        for i in range(60, 0, -1):
            cur_d = today - datetime.timedelta(days=i - 1)
            amt = Decimal("5000000.00") if i == 30 else Decimal("100000.00")
            history.append((cur_d, amt))

        d_var, low_conf, used_days = calculate_daily_burn_rate(history, today=today)
        self.assertGreaterEqual(d_var, Decimal("100000.00"))
        self.assertLess(d_var, Decimal("110000.00"))

    def test_simulation_timeline_length_and_day_zero_rule(self):
        """Timeline có đúng days+1 điểm; t=0 không trừ chi biến đổi."""
        today = datetime.date(2026, 3, 1)
        current_balance = Decimal("10000000.00")
        events = [
            FixedEvent(
                date=today,
                title="Thu nhập hôm nay",
                amount=Decimal("2000000.00"),
                source="RECURRING",
                source_id=1,
            )
        ]
        daily_history = [(today - datetime.timedelta(days=i), Decimal("100000.00")) for i in range(30, 0, -1)]

        res = simulate_cashflow(
            current_balance=current_balance,
            events=events,
            daily_history=daily_history,
            today=today,
            days=30,
        )

        self.assertEqual(len(res.daily_timeline), 31)
        # t=0: current_balance (10tr) + fixed (2tr) = 12tr (KHÔNG trừ D_var 100k)
        self.assertEqual(res.daily_timeline[0]['date'], today)
        self.assertEqual(res.daily_timeline[0]['balance'], Decimal("12000000.00"))

        # t=1: 12tr - D_var (100k) = 11.900.000đ
        self.assertEqual(res.daily_timeline[1]['date'], today + datetime.timedelta(days=1))
        self.assertEqual(res.daily_timeline[1]['balance'], Decimal("11900000.00"))

    def test_simulation_safe_risk_level(self):
        """Khi số dư luôn an toàn: risk_level = SAFE, is_insolvency_risk = False, ALL_CLEAR."""
        today = datetime.date(2026, 3, 1)
        current_balance = Decimal("50000000.00")
        daily_history = [(today - datetime.timedelta(days=i), Decimal("100000.00")) for i in range(30, 0, -1)]

        res = simulate_cashflow(
            current_balance=current_balance,
            events=[],
            daily_history=daily_history,
            today=today,
            days=30,
            safety_buffer=Decimal("5000000.00"),
        )

        self.assertEqual(res.risk_level, "SAFE")
        self.assertFalse(res.is_insolvency_risk)
        self.assertEqual(res.max_shortfall, Decimal("0.00"))
        self.assertIsNone(res.first_warning_date)
        self.assertIsNone(res.first_negative_date)
        self.assertTrue(any(r['code'] == 'ALL_CLEAR' for r in res.recommendations))

    def test_simulation_warning_below_safety_buffer(self):
        """Khi số dư rơi xuống dưới safety_buffer nhưng không âm: risk_level = WARNING."""
        today = datetime.date(2026, 3, 1)
        # Số dư ban đầu 3.000.000đ, safety_buffer 5.000.000đ -> ngay t=0 đã dưới buffer
        current_balance = Decimal("3000000.00")
        daily_history = [(today - datetime.timedelta(days=i), Decimal("10000.00")) for i in range(30, 0, -1)]

        res = simulate_cashflow(
            current_balance=current_balance,
            events=[],
            daily_history=daily_history,
            today=today,
            days=30,
            safety_buffer=Decimal("5000000.00"),
        )

        self.assertEqual(res.risk_level, "WARNING")
        self.assertFalse(res.is_insolvency_risk)
        self.assertEqual(res.max_shortfall, Decimal("0.00"))
        self.assertEqual(res.first_warning_date, today)
        self.assertIsNone(res.first_negative_date)
        self.assertTrue(any(r['code'] == 'BELOW_BUFFER' for r in res.recommendations))

    def test_simulation_critical_insolvency_risk_and_recommendations(self):
        """Chạm âm: risk_level = CRITICAL, max_shortfall tính đúng, sinh SHORTFALL_RISK và REDUCE_DAILY_SPENDING."""
        today = datetime.date(2026, 3, 1)
        current_balance = Decimal("2000000.00")
        # Ngày 2026-03-05 có khoản chi cố định 5.000.000đ (trả nợ)
        negative_target_date = datetime.date(2026, 3, 5)
        events = [
            FixedEvent(
                date=negative_target_date,
                title="Tra no anh Nam",
                amount=Decimal("-5000000.00"),
                source="DEBT",
                source_id=99,
            )
        ]
        # D_variable = 100.000đ/ngày
        daily_history = [(today - datetime.timedelta(days=i), Decimal("100000.00")) for i in range(30, 0, -1)]

        res = simulate_cashflow(
            current_balance=current_balance,
            events=events,
            daily_history=daily_history,
            today=today,
            days=30,
        )

        self.assertEqual(res.risk_level, "CRITICAL")
        self.assertTrue(res.is_insolvency_risk)
        self.assertEqual(res.first_negative_date, negative_target_date)
        self.assertGreater(res.max_shortfall, Decimal("0.00"))

        rec_codes = [r['code'] for r in res.recommendations]
        self.assertIn("SHORTFALL_RISK", rec_codes)
        self.assertIn("REDUCE_DAILY_SPENDING", rec_codes)

        # Kiểm tra params của SHORTFALL_RISK
        shortfall_rec = next(r for r in res.recommendations if r['code'] == 'SHORTFALL_RISK')
        self.assertEqual(shortfall_rec['params']['date'], negative_target_date.isoformat())
        self.assertEqual(shortfall_rec['params']['event_title'], "Tra no anh Nam")

        # Kiểm tra params của REDUCE_DAILY_SPENDING
        reduce_rec = next(r for r in res.recommendations if r['code'] == 'REDUCE_DAILY_SPENDING')
        self.assertEqual(reduce_rec['params']['days_until'], 4)
        self.assertGreater(Decimal(reduce_rec['params']['daily_cut']), Decimal("0.00"))

    def test_forecast_result_serialization(self):
        """to_dict() định dạng đúng chuỗi 2 chữ số thập phân và ngày ISO."""
        today = datetime.date(2026, 3, 1)
        res = simulate_cashflow(
            current_balance=Decimal("5000000.00"),
            events=[],
            daily_history=[(today - datetime.timedelta(days=i), Decimal("50000.00")) for i in range(30, 0, -1)],
            today=today,
            days=30,
        )

        data = res.to_dict()
        self.assertIsInstance(data['current_balance'], str)
        self.assertEqual(data['current_balance'], "5000000.00")
        self.assertIsInstance(data['projected_end_balance'], str)
        self.assertIsInstance(data['daily_timeline'], list)
        self.assertEqual(data['daily_timeline'][0]['date'], "2026-03-01")

    def test_simulate_cashflow_default_parameters_match_arm_d(self):
        """Gọi simulate_cashflow không truyền estimator và winsorize cho kết quả GIỐNG HỆT nhánh D (ewma, winsorize=True)."""
        today = datetime.date(2026, 3, 1)
        history = [(today - datetime.timedelta(days=i), Decimal(str(100000 + i * 2000))) for i in range(30, 0, -1)]
        current_balance = Decimal("10000000.00")

        res_default = simulate_cashflow(
            current_balance=current_balance,
            events=[],
            daily_history=history,
            today=today,
            days=30,
        )
        res_arm_d = simulate_cashflow(
            current_balance=current_balance,
            events=[],
            daily_history=history,
            today=today,
            days=30,
            estimator="ewma",
            winsorize=True,
        )

        self.assertEqual(res_default.daily_burn_rate, res_arm_d.daily_burn_rate)
        self.assertEqual(res_default.projected_end_balance, res_arm_d.projected_end_balance)
        self.assertEqual(res_default.lowest_balance, res_arm_d.lowest_balance)
        self.assertEqual(len(res_default.daily_timeline), len(res_arm_d.daily_timeline))
        for p_def, p_d in zip(res_default.daily_timeline, res_arm_d.daily_timeline):
            self.assertEqual(p_def['balance'], p_d['balance'])

    def test_four_arms_differentiation_on_outlier_trend_and_constant_series(self):
        """Bốn nhánh (A, B, C, D) cho kết quả khác nhau trên chuỗi outlier/trend và bằng nhau trên chuỗi hằng số."""
        today = datetime.date(2026, 3, 1)

        # 1. Chuỗi có outlier rõ rệt: 59 ngày 100k, 1 ngày 5 triệu
        outlier_history = []
        for i in range(60, 0, -1):
            cur_d = today - datetime.timedelta(days=i - 1)
            amt = Decimal("5000000.00") if i == 25 else Decimal("100000.00")
            outlier_history.append((cur_d, amt))

        d_a, _, _ = calculate_daily_burn_rate(outlier_history, today=today, estimator="mean", winsorize=False)
        d_b, _, _ = calculate_daily_burn_rate(outlier_history, today=today, estimator="mean", winsorize=True)
        d_c, _, _ = calculate_daily_burn_rate(outlier_history, today=today, estimator="ewma", winsorize=False)
        d_d, _, _ = calculate_daily_burn_rate(outlier_history, today=today, estimator="ewma", winsorize=True)

        self.assertLess(d_b, d_a)
        self.assertLess(d_d, d_c)

        # 2. Chuỗi có xu hướng tăng: 100k -> 300k
        trend_history = [
            (today - datetime.timedelta(days=60 - i), Decimal(str(100000 + i * 3500)))
            for i in range(60)
        ]
        t_a, _, _ = calculate_daily_burn_rate(trend_history, today=today, estimator="mean", winsorize=False)
        t_c, _, _ = calculate_daily_burn_rate(trend_history, today=today, estimator="ewma", winsorize=False)

        self.assertGreater(t_c, t_a)

        # 3. Chuỗi hằng số: 150.000đ mỗi ngày -> Cả 4 nhánh đều cho đúng 150.000đ
        const_history = [(today - datetime.timedelta(days=i), Decimal("150000.00")) for i in range(30, 0, -1)]
        c_a, _, _ = calculate_daily_burn_rate(const_history, today=today, estimator="mean", winsorize=False)
        c_b, _, _ = calculate_daily_burn_rate(const_history, today=today, estimator="mean", winsorize=True)
        c_c, _, _ = calculate_daily_burn_rate(const_history, today=today, estimator="ewma", winsorize=False)
        c_d, _, _ = calculate_daily_burn_rate(const_history, today=today, estimator="ewma", winsorize=True)

        self.assertEqual(c_a, Decimal("150000.00"))
        self.assertEqual(c_b, Decimal("150000.00"))
        self.assertEqual(c_c, Decimal("150000.00"))
        self.assertEqual(c_d, Decimal("150000.00"))

    def test_unknown_estimator_raises_error(self):
        """Truyền estimator không hợp lệ phải raise ValueError."""
        today = datetime.date(2026, 3, 1)
        history = [(today - datetime.timedelta(days=1), Decimal("100000.00"))]
        with self.assertRaises(ValueError):
            calculate_daily_burn_rate(history, today=today, estimator="invalid_estimator")


class ForecastingServiceIntegrationTestCase(TestCase):
    """
    Integration tests for CashFlowForecastService with database wallet and queries assertion.
    """

    def setUp(self):
        self.factory = TransactionFactory()
        self.user = self.factory.create_user()
        self.wallet = self.user.get_wallet()
        self.wallet.update_balance(10_000_000)

    def test_forecast_service_runs_and_returns_result(self):
        """CashFlowForecastService.forecast nạp dữ liệu qua get_forecast_inputs và trả về ForecastResult."""
        # Thêm 1 giao dịch định kỳ
        base_tx = Transaction.objects.create(
            wallet=self.wallet,
            title="Tien nha hang thang",
            value=Decimal("4000000.00"),
            date=datetime.date(2026, 1, 1),
            type="EXPENSE",
            update_wallet=True,
            recurrent=True,
        )
        rec = TransactionRecurrency.objects.create(
            transaction=base_tx,
            amount=1,
            duration="MONTHS",
            active=True,
        )
        base_tx.recurrency = rec
        base_tx.save(update_fields=["recurrency"])

        # Thêm khoản nợ
        DebtLoan.objects.create(
            wallet=self.wallet,
            person_name="Chi Nga",
            type="DEBT_BORROWED",
            principal_amount=Decimal("2000000.00"),
            start_date=datetime.date(2026, 1, 1),
            due_date=datetime.date(2026, 2, 1),
            status="ACTIVE",
        )

        res = CashFlowForecastService.forecast(self.wallet, days=30)
        self.assertIsInstance(res, ForecastResult)
        self.assertEqual(res.horizon_days, 30)
        self.assertEqual(res.current_balance, self.wallet.current_amount)

    def test_forecast_service_query_count_is_constant(self):
        """Chứng minh tổng số query của CashFlowForecastService.forecast là 5 và không đổi (2 vs 20)."""
        # Tạo 2 recurring và 2 debts
        for i in range(2):
            base_tx = Transaction.objects.create(
                wallet=self.wallet,
                title=f"Recurring {i}",
                value=Decimal("100000.00"),
                date=datetime.date(2026, 1, 1),
                type="EXPENSE",
                update_wallet=True,
                recurrent=True,
            )
            rec = TransactionRecurrency.objects.create(
                transaction=base_tx,
                amount=1,
                duration="MONTHS",
                active=True,
            )
            base_tx.recurrency = rec
            base_tx.save(update_fields=["recurrency"])

            debt = DebtLoan.objects.create(
                wallet=self.wallet,
                person_name=f"Debt {i}",
                type="DEBT_BORROWED",
                principal_amount=Decimal("5000000.00"),
                start_date=datetime.date(2026, 1, 1),
                due_date=datetime.date(2026, 2, 1),
                status="ACTIVE",
            )
            DebtPayment.objects.create(
                debt=debt,
                amount=Decimal("1000000.00"),
                date=datetime.date(2026, 1, 10),
                update_wallet=False,
            )

        # Chạy kiểm tra query count với 2 records:
        # get_recurring_events = 2 queries
        # get_debt_events = 2 queries
        # get_daily_variable_spending = 1 query
        # Tổng = 5 queries
        with self.assertNumQueries(5):
            CashFlowForecastService.forecast(self.wallet, days=30)

        # Thêm 18 cái nữa (tổng 20 recurring + 20 debts)
        for i in range(2, 20):
            base_tx = Transaction.objects.create(
                wallet=self.wallet,
                title=f"Recurring {i}",
                value=Decimal("100000.00"),
                date=datetime.date(2026, 1, 1),
                type="EXPENSE",
                update_wallet=True,
                recurrent=True,
            )
            rec = TransactionRecurrency.objects.create(
                transaction=base_tx,
                amount=1,
                duration="MONTHS",
                active=True,
            )
            base_tx.recurrency = rec
            base_tx.save(update_fields=["recurrency"])

            debt = DebtLoan.objects.create(
                wallet=self.wallet,
                person_name=f"Debt {i}",
                type="DEBT_BORROWED",
                principal_amount=Decimal("5000000.00"),
                start_date=datetime.date(2026, 1, 1),
                due_date=datetime.date(2026, 2, 1),
                status="ACTIVE",
            )
            DebtPayment.objects.create(
                debt=debt,
                amount=Decimal("1000000.00"),
                date=datetime.date(2026, 1, 10),
                update_wallet=False,
            )

        with self.assertNumQueries(5):
            CashFlowForecastService.forecast(self.wallet, days=30)
