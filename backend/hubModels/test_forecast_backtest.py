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
import csv
import datetime
from decimal import Decimal
import math
import re
import tempfile
from pathlib import Path
from io import StringIO
from unittest import TestCase
from unittest.mock import patch

from django.core.management.base import CommandError
from hubModels.management.commands import forecast_backtest as backtest
from hubModels.management.commands.forecast_backtest import Command, compute_bootstrap_ci
from hubModels.services.forecasting import FixedEvent, simulate_cashflow


class ForecastBacktestEngineTestCase(TestCase):
    def setUp(self):
        self.cmd = Command()
        self.start_date = datetime.date(2026, 1, 1)

    def _evaluate_with_timeline(self, sim_data, origin_idx, horizon=30):
        forecasts = []

        def record_forecast(*args, **kwargs):
            forecast = simulate_cashflow(*args, **kwargs)
            forecasts.append(forecast)
            return forecast

        with patch(
            'hubModels.management.commands.forecast_backtest.simulate_cashflow',
            side_effect=record_forecast,
        ):
            metrics = self.cmd.evaluate_single_origin(
                sim_data=sim_data,
                origin_idx=origin_idx,
                horizon=horizon,
                scenario='stable_noise',
                seed=42,
                arm='arm_D',
                estimator='ewma',
                winsorize=True,
                alpha=Decimal('0.2'),
            )

        self.assertEqual(len(forecasts), 1)
        return metrics, forecasts[0]

    def test_salary_origin_starts_at_observed_end_of_day_balance(self):
        data = self.cmd.generate_simulation_data(
            'stable_noise', self.start_date, total_days=365, seed=42,
        )
        origin_idx = (datetime.date(2026, 10, 5) - self.start_date).days
        _, forecast = self._evaluate_with_timeline(data, origin_idx)

        self.assertEqual(
            forecast.daily_timeline[0]['balance'], data[origin_idx]['balance'],
        )

    def test_expense_and_event_free_origins_start_at_observed_balance(self):
        data = self.cmd.generate_simulation_data(
            'stable_noise', self.start_date, total_days=365, seed=42,
        )
        for day in (10, 20, 21):
            with self.subTest(day=day):
                origin_idx = (datetime.date(2026, 10, day) - self.start_date).days
                _, forecast = self._evaluate_with_timeline(data, origin_idx)
                self.assertEqual(
                    forecast.daily_timeline[0]['balance'], data[origin_idx]['balance'],
                )

    def test_future_events_are_applied_once_on_the_matching_day(self):
        data = self.cmd.generate_simulation_data(
            'stable_noise', self.start_date, total_days=365, seed=42,
        )
        for day in (4, 9, 19):
            with self.subTest(day=day):
                origin_idx = (datetime.date(2026, 10, day) - self.start_date).days
                _, forecast = self._evaluate_with_timeline(data, origin_idx)
                expected_balance = data[origin_idx]['balance']
                self.assertTrue(data[origin_idx + 1]['fixed_events'])
                for step in range(1, 31):
                    actual_day = data[origin_idx + step]
                    fixed_sum = sum(
                        (event.amount for event in actual_day['fixed_events']),
                        Decimal('0.00'),
                    )
                    expected_balance += fixed_sum - forecast.daily_burn_rate
                    self.assertEqual(forecast.daily_timeline[step]['date'], actual_day['date'])
                    self.assertEqual(forecast.daily_timeline[step]['balance'], expected_balance)

    def test_daily_metrics_use_only_the_horizon_future_points(self):
        data = self.cmd.generate_simulation_data(
            'stable_noise', self.start_date, total_days=365, seed=42,
        )
        origin_idx = (datetime.date(2026, 10, 21) - self.start_date).days
        metrics, forecast = self._evaluate_with_timeline(data, origin_idx)
        errors = [
            float(forecast.daily_timeline[step]['balance'] - data[origin_idx + step]['balance'])
            for step in range(1, 31)
        ]

        self.assertGreater(sum(abs(error) for error in errors), 0)
        self.assertAlmostEqual(metrics['MAE_daily'], sum(abs(error) for error in errors) / 30)
        self.assertAlmostEqual(
            metrics['RMSE_daily'], math.sqrt(sum(error ** 2 for error in errors) / 30),
        )
        self.assertEqual(metrics['abs_err_end'], abs(errors[-1]))
        self.assertEqual(metrics['signed_err_end'], errors[-1])

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


class ForecastBacktestReportTestCase(TestCase):
    def _render_report(self, baseline=100.0, proposed=60.0, ci=(-45.0, -35.0),
                       n_seeds=7, scenario='stable_noise', alpha_rows=None):
        metrics = ('MAE_daily', 'MAE_end', 'RMSE_daily', 'Bias_end')
        summary = []
        for arm in 'ABCD':
            row = {
                'scenario': scenario, 'scenario_label': 'Kịch bản kiểm thử',
                'arm': f'arm_{arm}', 'arm_label': f'{arm}: Test', 'n_seeds': n_seeds,
            }
            for metric in metrics:
                row[f'{metric}_mean'] = proposed if arm == 'D' else baseline
                row[f'{metric}_std'] = 1.0
            summary.append(row)
        paired = [
            {
                'scenario': scenario, 'scenario_label': 'Kịch bản kiểm thử',
                'comparison': f'D vs {arm} (Test)', 'metric': metric,
                'mean_diff': proposed - baseline,
                'ci_95_lower': ci[0], 'ci_95_upper': ci[1],
                'win_rate_pct': 42.9, 'n_seeds': n_seeds,
            }
            for arm in 'ABC' for metric in metrics
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'report.md'
            Command().generate_markdown_report(
                str(path), n_seeds, 120, summary, paired, alpha_rows or [],
            )
            return path.read_text()

    def test_conclusion_percentages_match_the_same_reports_summary_table(self):
        for baseline, proposed in ((100.0, 60.0), (100.0, 125.0), (3.21, 2.34)):
            with self.subTest(baseline=baseline, proposed=proposed):
                report = self._render_report(baseline=baseline, proposed=proposed)
                table = report.split('## 3.')[1].split('## 4.')[0]
                amounts = dict(re.findall(
                    r'^\| Kịch bản kiểm thử \| ([ABCD]): Test \| ([\d,.]+) ±',
                    table, re.MULTILINE,
                ))
                expected = (float(amounts['A'].replace(',', ''))
                            - float(amounts['D'].replace(',', '')))
                expected = expected / float(amounts['A'].replace(',', '')) * 100
                conclusions = report.split('### 6.1.')[1].split('### 6.2.')[0]
                percentages = re.findall(r'Cải thiện: (-?\d+\.\d+)%', conclusions)
                self.assertEqual(len(percentages), 9)
                self.assertEqual(percentages, [f'{expected:.2f}'] * 9)
                all_percentages = re.findall(r'(-?\d+(?:\.\d+)?)%', conclusions)
                self.assertCountEqual(
                    all_percentages, [f'{expected:.2f}', '42.9', '95'] * 9,
                )
                self.assertNotIn('trên 40%', report)
                self.assertNotIn('p < 0.05', report)

    def test_conclusions_follow_ci_sign_and_actual_seed_count(self):
        for ci, verdict in (
            ((-45.0, -35.0), 'tốt hơn có ý nghĩa'),
            ((5.0, 15.0), 'kém hơn'),
            ((-5.0, 15.0), 'chưa kết luận được'),
            ((-5.0, 0.0), 'chưa kết luận được'),
            ((0.0, 5.0), 'chưa kết luận được'),
        ):
            with self.subTest(ci=ci):
                report = self._render_report(ci=ci)
                conclusions = report.split('### 6.1.')[1].split('### 6.2.')[0]
                self.assertEqual(conclusions.count(f'Kết luận: {verdict}'), 9)
                self.assertEqual(conclusions.count('Win Rate: 42.9% (7 seed)'), 9)
                self.assertIn(f'[{ci[0]:,.2f}, {ci[1]:,.2f}]', conclusions)
                self.assertNotIn('30 seeds', conclusions)

    def test_zero_baseline_has_no_undefined_percentage(self):
        report = self._render_report(baseline=0.0, proposed=1.0)
        conclusions = report.split('### 6.1.')[1].split('### 6.2.')[0]
        self.assertIn('Cải thiện: không xác định (tham chiếu bằng 0)', conclusions)
        self.assertNotRegex(conclusions, r'Cải thiện: -?\d+\.\d+%')

    def test_single_seed_does_not_support_a_significance_claim(self):
        report = self._render_report(n_seeds=1, scenario='real_data')
        conclusions = report.split('### 6.1.')[1].split('### 6.2.')[0]
        self.assertEqual(conclusions.count('Kết luận: chưa kết luận được'), 9)
        self.assertIn('không đủ seed độc lập', report)
        self.assertNotIn('Chỉ có dữ liệu mô phỏng', report)

    def test_methodology_and_limitations_reflect_the_run(self):
        report = self._render_report()
        self.assertIn('cửa sổ chồng lấn', report)
        self.assertIn('mỗi seed là một đơn vị lấy mẫu độc lập', report)
        self.assertIn('không lấy mẫu riêng từng cửa sổ hoặc từng ngày', report)
        self.assertNotIn('mốc dự báo độc lập', report)
        self.assertIn('5 cửa sổ', report)
        self.assertNotIn('~12 tháng', report)
        limits = report.split('### 6.2.')[1]
        self.assertIn('Chỉ có dữ liệu mô phỏng', limits)
        self.assertIn('1 kịch bản mô phỏng', limits)
        self.assertNotIn('cố định trên 3 kịch bản', limits)
        self.assertIn('chưa có kết quả phân tích độ nhạy alpha', limits)
        report_with_alpha = self._render_report(alpha_rows=[{
            'scenario': 'stable_noise', 'scenario_label': 'Kịch bản kiểm thử',
            'alpha': 0.1, 'MAE_daily_mean': 10.0, 'MAE_daily_std': 1.0,
            'MAE_end_mean': 20.0, 'MAE_end_std': 2.0,
        }])
        self.assertNotIn('chưa có kết quả phân tích độ nhạy alpha', report_with_alpha)


class RealCsvDailySpendTestCase(TestCase):
    def _load_rows(self, rows, initial_balance=None):
        output = StringIO()
        command = Command(stdout=output)
        if initial_balance is not None:
            command.initial_balance = initial_balance
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'spend.csv'
            with path.open('w', newline='', encoding='utf-8') as stream:
                writer = csv.DictWriter(stream, fieldnames=['date', 'amount', 'type'])
                writer.writeheader()
                writer.writerows(rows)
            result = command.load_real_csv_data(str(path))
        return result, output.getvalue()

    def test_normalization_groups_sorts_and_fills_calendar_dates_without_mutation(self):
        rows = [
            {'date': '03/01/2026', 'amount': '12.50'},
            {'date': '2026-01-01', 'amount': '10.25', 'type': 'EXPENSE'},
            {'date': '2026-01-01', 'amount': '20.50', 'type': ' expense '},
        ]
        original = copy.deepcopy(rows)
        daily, stats = backtest.normalize_daily_spend(rows)
        self.assertEqual(daily, [
            (datetime.date(2026, 1, 1), Decimal('30.75')),
            (datetime.date(2026, 1, 2), Decimal('0')),
            (datetime.date(2026, 1, 3), Decimal('12.50')),
        ])
        self.assertEqual(stats['rows_read'], 3)
        self.assertEqual(stats['rows_excluded'], 0)
        self.assertEqual(stats['zero_filled_days'], 1)
        self.assertEqual(rows, original)

    def test_invalid_rows_and_non_expenses_are_excluded_and_counted(self):
        rows = [
            {'date': '2026-01-01', 'amount': '10'},
            {'amount': '10'},
            {'date': '2026-01-02', 'amount': ''},
            {'date': '31/02/2026', 'amount': '10'},
            {'date': '2026-01-02', 'amount': 'abc'},
            {'date': '2026-01-02', 'amount': 'NaN'},
            {'date': '2026-01-02', 'amount': 'Infinity'},
            {'date': '2026-01-02', 'amount': '-10'},
            {'date': '2026-01-02', 'amount': '10', 'type': 'EARNING'},
            {'date': '2026-01-02', 'amount': '10', 'type': 'income'},
            {'date': '2026-01-02', 'amount': '10', 'type': 'TRANSFER'},
            {'date': '2026-01-02', 'amount': '10', 'type': 'unknown'},
        ]
        daily, stats = backtest.normalize_daily_spend(rows)
        self.assertEqual(daily, [(datetime.date(2026, 1, 1), Decimal('10'))])
        self.assertEqual(stats['rows_read'], 12)
        self.assertEqual(stats['rows_excluded'], 11)
        self.assertEqual(stats['missing_date'], 1)
        self.assertEqual(stats['missing_amount'], 1)
        self.assertEqual(stats['invalid_date'], 1)
        self.assertEqual(stats['invalid_amount'], 3)
        self.assertEqual(stats['wrong_sign'], 1)
        self.assertEqual(stats['excluded_type'], 4)

    def test_alias_columns_zero_spend_and_empty_input(self):
        daily, stats = backtest.normalize_daily_spend([
            {'Ngày': '01/01/2026', 'Số tiền': '0'},
            {'Ngày': '03/01/2026', 'value': '100'},
        ])
        self.assertEqual([amount for _, amount in daily], [Decimal('0'), Decimal('0'), Decimal('100')])
        self.assertEqual(stats['zero_filled_days'], 1)
        daily, stats = backtest.normalize_daily_spend([])
        self.assertEqual(daily, [])
        self.assertEqual(stats['rows_read'], 0)

    def test_more_than_90_rows_with_fewer_than_90_calendar_days_is_rejected(self):
        rows = [{'date': '2026-01-01', 'amount': '10'}] * 100
        with self.assertRaisesRegex(CommandError, '1 ngày lịch; cần tối thiểu 90'):
            self._load_rows(rows)

    def test_exactly_90_calendar_days_is_accepted_and_balance_behavior_is_preserved(self):
        data, output = self._load_rows([
            {'date': '2026-03-31', 'amount': '40'},
            {'date': '01/01/2026', 'amount': '10'},
            {'date': '2026-01-01', 'amount': '20'},
        ], initial_balance=Decimal('123456.78'))
        self.assertEqual(len(data), 90)
        self.assertEqual(data[0]['var_expense'], Decimal('30'))
        self.assertEqual(data[0]['balance'], Decimal('123456.78'))
        self.assertEqual(data[-1]['balance'], Decimal('123416.78'))
        for idx, item in enumerate(data):
            self.assertEqual(item['date'], datetime.date(2026, 1, 1) + datetime.timedelta(days=idx))
            self.assertEqual(item['day_idx'], idx)
            self.assertEqual(item['fixed_events'], [])
        self.assertIn('Đã đọc: 3 dòng', output)
        self.assertIn('Đã loại: 0 dòng', output)
        self.assertIn('Điền 0: 88 ngày', output)

    def test_loader_reports_rejection_reasons_and_uses_default_balance(self):
        data, output = self._load_rows([
            {'date': '2026-01-01', 'amount': '10'},
            {'date': '2026-03-31', 'amount': '20'},
            {'date': '', 'amount': '10'},
            {'date': 'bad', 'amount': '10'},
            {'date': '2026-02-01', 'amount': '-1'},
            {'date': '2026-02-01', 'amount': '10', 'type': 'TRANSFER'},
        ])
        self.assertEqual(data[0]['balance'], Decimal('20000000'))
        for text in ('Đã đọc: 6 dòng', 'Đã loại: 4 dòng', 'thiếu ngày: 1',
                     'ngày sai định dạng: 1', 'sai dấu: 1', 'loại giao dịch không phải chi tiêu: 1'):
            self.assertIn(text, output)

    def test_empty_or_unreadable_csv_is_an_explicit_error(self):
        with self.assertRaises(CommandError):
            self._load_rows([])
        with self.assertRaisesRegex(CommandError, 'Không thể đọc CSV'):
            Command().load_real_csv_data('/nonexistent/money-backtest.csv')

    def test_cli_initial_balance_default_and_custom_value(self):
        command = Command()
        parser = command.create_parser('manage.py', 'forecast_backtest')
        self.assertEqual(parser.parse_args([]).initial_balance, '20000000')
        self.assertEqual(parser.parse_args(['--initial-balance', '123456.78']).initial_balance,
                         '123456.78')
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(command, 'load_real_csv_data', side_effect=RuntimeError('stop after load')):
                with self.assertRaisesRegex(RuntimeError, 'stop after load'):
                    command.handle(seeds=2, days=100, real_csv=__file__,
                                   initial_balance=Decimal('123456.78'), output_dir=directory)
        self.assertEqual(command.initial_balance, Decimal('123456.78'))

    def test_invalid_initial_balance_is_rejected(self):
        for balance in ('NaN', 'Infinity', 'bad'):
            with self.subTest(balance=balance), tempfile.TemporaryDirectory() as directory:
                with self.assertRaisesRegex(CommandError, 'initial-balance'):
                    Command(stdout=StringIO()).handle(
                        seeds=2, days=100, real_csv=None,
                        initial_balance=balance, output_dir=directory,
                    )

    def test_exactly_90_days_can_complete_the_backtest(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'real.csv'
            path.write_text('date,amount\n2026-01-01,10\n2026-03-31,20\n')
            output_dir = Path(directory) / 'results'
            Command(stdout=StringIO()).handle(
                seeds=2, days=100, real_csv=str(path),
                initial_balance=Decimal('123456.78'), output_dir=str(output_dir),
            )
            with (output_dir / 'forecast_backtest_points_v2.csv').open() as stream:
                real_points = [row for row in csv.DictReader(stream) if row['scenario'] == 'real_data']
        self.assertEqual(len(real_points), 5)
        self.assertEqual({row['origin_date'] for row in real_points}, {'2026-03-01'})


class AdaptiveBacktestTestCase(TestCase):
    def test_shortfall_confusion_and_timing(self):
        today = datetime.date(2026, 1, 1)
        def timeline(values):
            return [{'date': today + datetime.timedelta(days=i), 'balance': Decimal(value)}
                    for i, value in enumerate(values)]
        metrics = backtest.shortfall_metrics(timeline([10, -1, -2]), timeline([10, 1, -2]), today)
        self.assertEqual(metrics['tp'], 1)
        self.assertEqual(metrics['timing_days'], -1)
        self.assertEqual(metrics['lead_days'], 2)
        self.assertEqual(backtest.shortfall_metrics(timeline([10, 1, 2]), timeline([10, 1, -2]), today)['fn'], 1)
        self.assertEqual(backtest.shortfall_metrics(timeline([10, 1, -2]), timeline([10, 1, 2]), today)['fp'], 1)
        self.assertEqual(backtest.shortfall_metrics(timeline([10, 1, 2]), timeline([10, 1, 2]), today)['tn'], 1)

    def test_adaptive_origin_does_not_leak_future_spend_or_balance(self):
        command = Command()
        data = command.generate_simulation_data('upward_trend', datetime.date(2026, 1, 1), 150, 1000)
        original = command.evaluate_single_origin(data, 70, 30, 'upward_trend', 1000,
                                                  'arm_E', 'ewma_adaptive', True, Decimal('0.2'))
        changed = copy.deepcopy(data)
        for item in changed[71:]:
            item['var_expense'] *= 100
            item['balance'] = Decimal('-99999999')
        modified = command.evaluate_single_origin(changed, 70, 30, 'upward_trend', 1000,
                                                  'arm_E', 'ewma_adaptive', True, Decimal('0.2'))
        self.assertEqual(original['selected_alpha'], modified['selected_alpha'])
        self.assertEqual(original['selected_estimator'], modified['selected_estimator'])

    def test_new_scenarios_and_test_seeds_are_exported_with_adaptive_arm(self):
        with tempfile.TemporaryDirectory() as directory:
            command = Command(stdout=StringIO())
            command.handle(seeds=2, days=100, real_csv=None, output_dir=directory, split='test')
            with (Path(directory) / 'forecast_backtest_points_v2.csv').open() as stream:
                points = list(csv.DictReader(stream))
            self.assertEqual({int(row['seed']) for row in points}, {0, 1})
            self.assertEqual({row['arm'] for row in points}, {f'arm_{arm}' for arm in 'ABCDE'})
            self.assertEqual(len({row['scenario'] for row in points}), 6)
            with (Path(directory) / 'forecast_backtest_paired_v2.csv').open() as stream:
                comparisons = {row['comparison'].split(' (')[0] for row in csv.DictReader(stream)}
            self.assertTrue({'E vs A', 'E vs D'}.issubset(comparisons))
            report = (Path(directory) / 'forecast_backtest_report_v2.md').read_text()
            self.assertIn('1000–1009', report)
            self.assertIn('Precision', report)
            self.assertIn('E vs A', report)

    def test_development_and_test_seed_sets_are_disjoint(self):
        command = Command(stdout=StringIO())
        with tempfile.TemporaryDirectory() as directory:
            command.handle(seeds=2, days=100, real_csv=None, output_dir=directory, split='development')
            with (Path(directory) / 'forecast_backtest_per_seed_v2.csv').open() as stream:
                self.assertEqual({int(row['seed']) for row in csv.DictReader(stream)}, {1000, 1001})
