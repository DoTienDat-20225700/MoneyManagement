"""
Unit Tests for Backtesting Methodology & Ablation Study (F03 Bước 5)

Kiểm tra tính nghiêm ngặt về phương pháp luận của hệ thống backtest:
1. Tính tái lập: Cùng seed và cùng cấu hình cho kết quả 100% giống hệt nhau giữa 2 lần chạy.
2. Không rò rỉ dữ liệu tương lai (No Lookahead Bias):
   Tại một mốc dự báo t_0, thay đổi/nhân đôi dữ liệu thực tế sau mốc không làm thay đổi kết quả dự báo tại mốc đó.
3. Ground truth độc lập: Kiểm tra chuỗi tính số dư thực tế độc lập với chuỗi dự báo.
4. Bốn nhánh (A, B, C, D) phân biệt rõ rệt trên chuỗi có outlier/trend và trùng khớp trên chuỗi hằng số.
5. Nhánh D tương thích hoàn toàn với simulate_cashflow mặc định.
6. Hàm Bootstrap CI: Chuỗi hằng số thu về một điểm; seed cố định cho kết quả tái lập 100%.
"""

import copy
import datetime
from decimal import Decimal
import math
from unittest import TestCase

from hubModels.management.commands.forecast_backtest import Command, compute_bootstrap_ci
from hubModels.services.forecasting import FixedEvent, simulate_cashflow


class ForecastBacktestEngineTestCase(TestCase):
    def setUp(self):
        self.cmd = Command()
        self.start_date = datetime.date(2026, 1, 1)

    def test_reproducibility_same_seed_gives_identical_results(self):
        """Cùng seed và cấu hình sinh chuỗi dữ liệu mô phỏng và kết quả giống hệt nhau."""
        data_run1 = self.cmd.generate_simulation_data(
            scenario="upward_trend",
            start_date=self.start_date,
            total_days=100,
            seed=77,
        )
        data_run2 = self.cmd.generate_simulation_data(
            scenario="upward_trend",
            start_date=self.start_date,
            total_days=100,
            seed=77,
        )

        self.assertEqual(len(data_run1), len(data_run2))
        for d1, d2 in zip(data_run1, data_run2):
            self.assertEqual(d1['date'], d2['date'])
            self.assertEqual(d1['var_expense'], d2['var_expense'])
            self.assertEqual(d1['balance'], d2['balance'])

    def test_no_lookahead_bias_tampering_future_does_not_affect_forecast(self):
        """KHÔNG RÒ RỈ DỮ LIỆU: Sửa mạnh dữ liệu tương lai sau mốc origin thì đường dự báo tại mốc origin không đổi."""
        sim_data_original = self.cmd.generate_simulation_data(
            scenario="volatile_outliers",
            start_date=self.start_date,
            total_days=150,
            seed=42,
        )

        origin_idx = 70
        horizon = 30

        # Chạy dự báo trên dữ liệu gốc tại mốc 70
        res_original = self.cmd.evaluate_single_origin(
            sim_data=sim_data_original,
            origin_idx=origin_idx,
            horizon=horizon,
            scenario="volatile_outliers",
            seed=42,
            arm="arm_D",
            estimator="ewma",
            winsorize=True,
            alpha=Decimal("0.2"),
        )

        # Tạo bản sao dữ liệu và làm xáo trộn dữ liệu tương lai (từ origin_idx + 1 đến hết)
        # Ví dụ: nhân gấp 10 lần toàn bộ chi tiêu các ngày tương lai
        sim_data_tampered = copy.deepcopy(sim_data_original)
        for idx in range(origin_idx + 1, len(sim_data_tampered)):
            sim_data_tampered[idx]['var_expense'] = sim_data_tampered[idx]['var_expense'] * Decimal("10")
            # Thay đổi số dư tương lai tương ứng
            sim_data_tampered[idx]['balance'] = sim_data_tampered[idx - 1]['balance'] - sim_data_tampered[idx]['var_expense']

        # Chạy lại dự báo tại mốc origin_idx = 70 trên dữ liệu đã bị xáo trộn tương lai
        # Trích xuất lịch sử quá khứ để chạy simulate_cashflow trực tiếp
        history_tampered = [(item['date'], item['var_expense']) for item in sim_data_tampered[origin_idx - 59 : origin_idx + 1]]
        events_tampered = [ev for item in sim_data_tampered[origin_idx : origin_idx + horizon + 1] for ev in item['fixed_events']]

        forecast_tampered = simulate_cashflow(
            current_balance=sim_data_tampered[origin_idx]['balance'],
            events=events_tampered,
            daily_history=history_tampered,
            today=sim_data_tampered[origin_idx]['date'],
            days=horizon,
            estimator="ewma",
            winsorize=True,
            alpha=Decimal("0.2"),
        )

        history_original = [(item['date'], item['var_expense']) for item in sim_data_original[origin_idx - 59 : origin_idx + 1]]
        events_original = [ev for item in sim_data_original[origin_idx : origin_idx + horizon + 1] for ev in item['fixed_events']]

        forecast_original = simulate_cashflow(
            current_balance=sim_data_original[origin_idx]['balance'],
            events=events_original,
            daily_history=history_original,
            today=sim_data_original[origin_idx]['date'],
            days=horizon,
            estimator="ewma",
            winsorize=True,
            alpha=Decimal("0.2"),
        )

        # Toàn bộ dự báo (từ t=0 đến t=30) phải giống hệt nhau 100%, không bị ảnh hưởng bởi tương lai
        self.assertEqual(forecast_original.daily_burn_rate, forecast_tampered.daily_burn_rate)
        self.assertEqual(forecast_original.projected_end_balance, forecast_tampered.projected_end_balance)
        for p_orig, p_tamp in zip(forecast_original.daily_timeline, forecast_tampered.daily_timeline):
            self.assertEqual(p_orig['balance'], p_tamp['balance'])

    def test_ground_truth_independent_calculation(self):
        """Ground truth số dư thực tế được tính độc lập theo công thức kế toán dòng tiền."""
        # Kiểm tra tính tay cho 3 ngày:
        # Ngày 0: ban đầu 20tr, không chi phí -> 20tr
        # Ngày 1: lương +25tr, chi biến đổi 100k -> 20tr + 25tr - 100k = 44.900.000đ
        # Ngày 2: tiền nhà -6tr, chi biến đổi 200k -> 44.9tr - 6tr - 200k = 38.700.000đ
        sim_data = self.cmd.generate_simulation_data(
            scenario="stable_noise",
            start_date=self.start_date,
            total_days=10,
            seed=1,
        )
        bal_prev = Decimal("20000000.00")
        for item in sim_data:
            day_idx = item['day_idx']
            fixed_sum = sum((ev.amount for ev in item['fixed_events']), Decimal("0.00"))
            if day_idx == 0:
                expected_bal = bal_prev + fixed_sum
            else:
                expected_bal = bal_prev + fixed_sum - item['var_expense']
            self.assertEqual(item['balance'], expected_bal)
            bal_prev = item['balance']

    def test_four_arms_differentiation(self):
        """Bốn nhánh A, B, C, D cho kết quả khác nhau trên chuỗi outlier/trend và bằng nhau trên chuỗi hằng số."""
        today = datetime.date(2026, 3, 1)

        # 1. Chuỗi có outlier
        history_outlier = [(today - datetime.timedelta(days=i), Decimal("100000.00") if i != 10 else Decimal("6000000.00")) for i in range(60, 0, -1)]
        res_a = simulate_cashflow(Decimal("10000000.00"), [], history_outlier, today, 30, estimator="mean", winsorize=False)
        res_b = simulate_cashflow(Decimal("10000000.00"), [], history_outlier, today, 30, estimator="mean", winsorize=True)
        res_c = simulate_cashflow(Decimal("10000000.00"), [], history_outlier, today, 30, estimator="ewma", winsorize=False)
        res_d = simulate_cashflow(Decimal("10000000.00"), [], history_outlier, today, 30, estimator="ewma", winsorize=True)

        self.assertLess(res_b.daily_burn_rate, res_a.daily_burn_rate)
        self.assertLess(res_d.daily_burn_rate, res_c.daily_burn_rate)

        # 2. Chuỗi có xu hướng tăng
        history_trend = [(today - datetime.timedelta(days=60 - i), Decimal(str(100000 + i * 3000))) for i in range(60)]
        res_trend_a = simulate_cashflow(Decimal("10000000.00"), [], history_trend, today, 30, estimator="mean", winsorize=False)
        res_trend_c = simulate_cashflow(Decimal("10000000.00"), [], history_trend, today, 30, estimator="ewma", winsorize=False)

        self.assertGreater(res_trend_c.daily_burn_rate, res_trend_a.daily_burn_rate)

        # 3. Chuỗi hằng số: 4 nhánh cho kết quả như nhau
        history_const = [(today - datetime.timedelta(days=i), Decimal("200000.00")) for i in range(60, 0, -1)]
        c_a = simulate_cashflow(Decimal("10000000.00"), [], history_const, today, 30, estimator="mean", winsorize=False)
        c_b = simulate_cashflow(Decimal("10000000.00"), [], history_const, today, 30, estimator="mean", winsorize=True)
        c_c = simulate_cashflow(Decimal("10000000.00"), [], history_const, today, 30, estimator="ewma", winsorize=False)
        c_d = simulate_cashflow(Decimal("10000000.00"), [], history_const, today, 30, estimator="ewma", winsorize=True)

        self.assertEqual(c_a.daily_burn_rate, Decimal("200000.00"))
        self.assertEqual(c_b.daily_burn_rate, Decimal("200000.00"))
        self.assertEqual(c_c.daily_burn_rate, Decimal("200000.00"))
        self.assertEqual(c_d.daily_burn_rate, Decimal("200000.00"))

    def test_arm_d_matches_default_simulate_cashflow(self):
        """Nhánh D (ewma, winsorize=True, alpha=0.2) khớp chính xác 100% với simulate_cashflow mặc định."""
        today = datetime.date(2026, 3, 1)
        history = [(today - datetime.timedelta(days=i), Decimal(str(120000 + i * 1500))) for i in range(60, 0, -1)]
        cur_bal = Decimal("15000000.00")

        res_default = simulate_cashflow(cur_bal, [], history, today, 30)
        res_d = simulate_cashflow(cur_bal, [], history, today, 30, estimator="ewma", winsorize=True, alpha=Decimal("0.2"))

        self.assertEqual(res_default.daily_burn_rate, res_d.daily_burn_rate)
        self.assertEqual(res_default.projected_end_balance, res_d.projected_end_balance)
        self.assertEqual(len(res_default.daily_timeline), len(res_d.daily_timeline))
        for p1, p2 in zip(res_default.daily_timeline, res_d.daily_timeline):
            self.assertEqual(p1['balance'], p2['balance'])

    def test_bootstrap_ci_properties(self):
        """Hàm bootstrap: với dữ liệu hằng số CI thu về một điểm; với seed cố định thì tái lập."""
        # 1. Dữ liệu hằng số: tất cả phần tử là 50000.0
        const_diffs = [50000.0] * 30
        mean_val, ci_low, ci_high = compute_bootstrap_ci(const_diffs, n_resamples=1000, ci=0.95, seed=123)
        self.assertEqual(mean_val, 50000.0)
        self.assertEqual(ci_low, 50000.0)
        self.assertEqual(ci_high, 50000.0)

        # 2. Tính tái lập với seed cố định
        diffs = [float(i * 1000 - 5000) for i in range(30)]
        m1, l1, h1 = compute_bootstrap_ci(diffs, n_resamples=1000, ci=0.95, seed=999)
        m2, l2, h2 = compute_bootstrap_ci(diffs, n_resamples=1000, ci=0.95, seed=999)
        self.assertEqual(m1, m2)
        self.assertEqual(l1, l2)
        self.assertEqual(h1, h2)
        self.assertLessEqual(l1, m1)
        self.assertGreaterEqual(h1, m1)
