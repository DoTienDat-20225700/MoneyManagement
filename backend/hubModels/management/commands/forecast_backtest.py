"""
Management Command: forecast_backtest (v2 - Rigorous Multi-Seed & Ablation Evaluation)

Thực hiện đánh giá thực nghiệm (backtest) toàn diện thuật toán Dự báo dòng tiền F03:
1. Đa hạt giống cho 6 kịch bản (365 ngày mỗi chuỗi), tách development/test:
   (a) Chi tiêu ổn định có nhiễu (Stable with Noise)
   (b) Chi tiêu có xu hướng tăng (Upward Trend)
   (c) Chi tiêu thất thường có outlier (Volatile with Outliers)
   Kèm kịch bản 4 tùy chọn nếu truyền --real-csv.
2. Thiết kế kiểm thử bóc tách 5 nhánh (Ablation Study):
   - Nhánh A: estimator='mean', winsorize=False (Baseline hiện tại)
   - Nhánh B: estimator='mean', winsorize=True
   - Nhánh C: estimator='ewma', winsorize=False
   - Nhánh D: estimator='ewma', winsorize=True (alpha cố định 0.2)
   - Nhánh E: estimator='ewma_adaptive', winsorize=True (mean hoặc alpha chọn từ quá khứ)
3. Rolling-origin backtest:
   - Chiều dài chuỗi 365 ngày, lịch sử 60 ngày, đường chân trời 30 ngày, bước nhảy 7 ngày (~40 mốc/chuỗi).
   - Tuyệt đối không rò rỉ thông tin tương lai.
4. Chỉ số đánh giá:
   - MAE_daily: trung bình sai số tuyệt đối trên các ngày tương lai h=1..30.
   - RMSE_daily: căn bậc hai trung bình bình phương sai số.
   - MAE_end: sai số tuyệt đối tại ngày cuối h=30.
   - Bias_end: sai số có dấu trung bình tại ngày cuối (Dự báo - Thực tế).
5. Phân tích thống kê:
   - Trung bình ± Độ lệch chuẩn qua 30 seeds.
   - So sánh theo cặp (Paired Comparison) D vs A, D vs B, D vs C:
     Hiệu trung bình, Khoảng tin cậy 95% bằng Bootstrap (2000 resamples), Win Rate (tỷ lệ D tốt hơn).
   - Phân tích độ nhạy alpha in {0.1, 0.2, 0.3, 0.5}.
6. Xuất đầy đủ các file v2 (CSV + Markdown) và in tóm tắt ra console.
"""

import csv
import json
import datetime
from decimal import Decimal, InvalidOperation
import math
import os
import random
from typing import Any, Dict, List, Optional, Tuple

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from hubModels.services.forecasting import (FixedEvent, simulate_cashflow, ADAPTIVE_ALPHA_GRID,
                                           ADAPTIVE_MIN_HISTORY_DAYS, ADAPTIVE_WARMUP_DAYS)


def normalize_daily_spend(
    rows: List[Dict[str, Any]],
) -> Tuple[List[Tuple[datetime.date, Decimal]], Dict[str, int]]:
    """Normalize spending rows without I/O or mutating the input.

    Dates accept ISO YYYY-MM-DD or DD/MM/YYYY. Amounts are non-negative VND
    decimals without thousands separators; zero explicitly records no spending.
    Missing type is accepted. Non-empty type must identify an expense; unknown
    types, income, transfers and negative amounts are excluded. Each rejected row
    is counted once, by its first error (date, amount, sign, then type).
    Calendar bounds come only from accepted rows, including explicit zero rows.
    """
    stats = dict.fromkeys((
        'rows_read', 'rows_excluded', 'missing_date', 'missing_amount',
        'invalid_date', 'invalid_amount', 'wrong_sign', 'excluded_type',
        'zero_filled_days',
    ), 0)
    totals: Dict[datetime.date, Decimal] = {}
    for row in rows:
        stats['rows_read'] += 1
        date_value = row.get('date') or row.get('Ngày')
        if date_value is None or not str(date_value).strip():
            stats['missing_date'] += 1
            continue
        date_text = str(date_value).strip()
        try:
            day = datetime.date.fromisoformat(date_text)
        except ValueError:
            try:
                day = datetime.datetime.strptime(date_text, '%d/%m/%Y').date()
            except ValueError:
                stats['invalid_date'] += 1
                continue
        amount_value = next((row.get(key) for key in ('amount', 'Số tiền', 'value')
                             if row.get(key) is not None and str(row.get(key)).strip()), None)
        if amount_value is None:
            stats['missing_amount'] += 1
            continue
        try:
            amount = Decimal(str(amount_value).strip())
        except InvalidOperation:
            stats['invalid_amount'] += 1
            continue
        if not amount.is_finite():
            stats['invalid_amount'] += 1
            continue
        if amount < 0:
            stats['wrong_sign'] += 1
            continue
        transaction_type = str(row.get('type') or '').strip().upper()
        if transaction_type and transaction_type not in ('EXPENSE', 'SPENDING', 'CHI', 'CHI_TIEU', 'CHI TIÊU'):
            stats['excluded_type'] += 1
            continue
        totals[day] = totals.get(day, Decimal('0')) + amount

    stats['rows_excluded'] = sum(stats[key] for key in (
        'missing_date', 'missing_amount', 'invalid_date', 'invalid_amount',
        'wrong_sign', 'excluded_type',
    ))
    if not totals:
        return [], stats
    first_day, last_day = min(totals), max(totals)
    days = (last_day - first_day).days + 1
    daily = [
        (day, totals.get(day, Decimal('0')))
        for day in (first_day + datetime.timedelta(days=i) for i in range(days))
    ]
    stats['zero_filled_days'] = days - len(totals)
    return daily, stats


def shortfall_metrics(predicted, actual, origin):
    """Classify future days 1..horizon; negative timing means an earlier predicted crossing."""
    predicted_date = next((p['date'] for p in predicted if p['date'] > origin and p['balance'] < 0), None)
    actual_date = next((p['date'] for p in actual if p['date'] > origin and p['balance'] < 0), None)
    tp = predicted_date is not None and actual_date is not None
    return {
        'tp': int(tp), 'fp': int(predicted_date is not None and actual_date is None),
        'fn': int(predicted_date is None and actual_date is not None),
        'tn': int(predicted_date is None and actual_date is None),
        'timing_days': (predicted_date - actual_date).days if tp else None,
        'lead_days': (actual_date - origin).days if tp else None,
        'already_negative': int(actual[0]['balance'] < 0),
    }


def compute_bootstrap_ci(
    diffs: List[float],
    n_resamples: int = 2000,
    ci: float = 0.95,
    seed: int = 12345,
) -> Tuple[float, float, float]:
    """
    Tính khoảng tin cậy Bootstrap 95% cho giá trị trung bình của danh sách sai khác theo cặp.
    Returns: (mean_diff, ci_lower, ci_upper)
    """
    n = len(diffs)
    if n == 0:
        return 0.0, 0.0, 0.0

    mean_val = sum(diffs) / n
    # Nếu dữ liệu hằng số hoặc tất cả giá trị bằng nhau, CI thu về chính điểm đó
    if all(math.isclose(x, diffs[0], rel_tol=1e-9) for x in diffs):
        return mean_val, mean_val, mean_val

    rng = random.Random(seed)
    bootstrap_means = []
    for _ in range(n_resamples):
        sample = rng.choices(diffs, k=n)
        bootstrap_means.append(sum(sample) / n)

    bootstrap_means.sort()
    alpha_half = (1.0 - ci) / 2.0
    lower_idx = int(alpha_half * n_resamples)
    upper_idx = int((1.0 - alpha_half) * n_resamples)
    upper_idx = min(upper_idx, n_resamples - 1)

    ci_lower = bootstrap_means[lower_idx]
    ci_upper = bootstrap_means[upper_idx]
    return mean_val, ci_lower, ci_upper


class Command(BaseCommand):
    help = "Backtest 6 kịch bản, 5 nhánh A-E, seed development/test tách biệt, bootstrap và phát hiện thiếu hụt."

    def add_arguments(self, parser):
        parser.add_argument(
            '--seeds',
            type=int,
            default=None,
            help='Số lượng seed ngẫu nhiên độc lập (mặc định: 30)',
        )
        parser.add_argument('--split', choices=('development', 'test'), default='test',
                            help='Development seeds 1000..1009; held-out test seeds 0..29.')
        parser.add_argument(
            '--days',
            type=int,
            default=365,
            help='Độ dài chuỗi mô phỏng theo ngày (mặc định: 365)',
        )
        parser.add_argument(
            '--real-csv',
            type=str,
            default=None,
            help='CSV chi tiêu VND: date (YYYY-MM-DD hoặc DD/MM/YYYY), amount không âm; type tùy chọn, chỉ nhận loại chi tiêu.',
        )
        parser.add_argument(
            '--initial-balance',
            type=str,
            default='20000000',
            help='Số dư giả định ban đầu cho dữ liệu CSV thực (VND, mặc định: 20000000); không đổi các kịch bản mô phỏng.',
        )
        parser.add_argument(
            '--output-dir',
            type=str,
            default=os.path.join(settings.BASE_DIR, 'evaluation_results'),
            help='Thư mục lưu các file kết quả (mặc định: backend/evaluation_results)',
        )

    def handle(self, *args, **options):
        self.evaluation_split = options.get('split', 'test')
        seed_start = 1000 if self.evaluation_split == 'development' else 0
        num_seeds = options['seeds'] or (10 if self.evaluation_split == 'development' else 30)
        if not 2 <= num_seeds <= (10 if self.evaluation_split == 'development' else 30):
            raise CommandError('Use 2..10 development seeds or 2..30 test seeds.')
        self.seed_ids = list(range(seed_start, seed_start + num_seeds))
        total_days = options['days']
        real_csv_path = options['real_csv']
        output_dir = options['output_dir']
        try:
            self.initial_balance = Decimal(str(options.get('initial_balance', '20000000')))
        except (InvalidOperation, ValueError, TypeError) as error:
            raise CommandError('--initial-balance phải là số VND hữu hạn.') from error
        if not self.initial_balance.is_finite():
            raise CommandError('--initial-balance phải là số VND hữu hạn.')
        os.makedirs(output_dir, exist_ok=True)

        self.stdout.write(self.style.MIGRATE_HEADING("======================================================================"))
        self.stdout.write(self.style.MIGRATE_HEADING("  F03 CASH FLOW FORECASTING - RIGOROUS BACKTESTING & ABLATION STUDY   "))
        self.stdout.write(self.style.MIGRATE_HEADING("======================================================================"))
        self.stdout.write(f"Số lượng seeds: {num_seeds}")
        self.stdout.write(f"Độ dài chuỗi: {total_days} ngày")
        self.stdout.write(f"Thư mục xuất kết quả: {output_dir}\n")

        # Cấu hình 4 nhánh thử nghiệm (Ablation arms)
        arms = [
            ("arm_A", "mean", False, Decimal("0.2"), "A: Mean (Raw) - Baseline"),
            ("arm_B", "mean", True, Decimal("0.2"), "B: Mean (Winsorized)"),
            ("arm_C", "ewma", False, Decimal("0.2"), "C: EWMA (Raw)"),
            ("arm_D", "ewma", True, Decimal("0.2"), "D: EWMA (Winsorized) - Fixed"),
            ("arm_E", "ewma_adaptive", True, Decimal("0.2"), "E: Adaptive Mean/EWMA (Winsorized)"),
        ]

        scenarios = ["stable_noise", "upward_trend", "volatile_outliers",
                     "weekend_spending", "habit_shift", "sparse_spending"]
        scenario_labels = {
            "stable_noise": "1. Chi tiêu ổn định có nhiễu (Stable)",
            "upward_trend": "2. Chi tiêu có xu hướng tăng (Upward Trend)",
            "volatile_outliers": "3. Chi tiêu thất thường có outlier (Volatile/Outlier)",
        }

        scenario_labels.update({
            'weekend_spending': '4. Chi nhiều cuối tuần',
            'habit_shift': '5. Thay đổi thói quen giữa chừng',
            'sparse_spending': '6. Chi tiêu thưa',
        })

        # Nếu người dùng truyền real-csv, thêm kịch bản 4
        real_data_loaded = None
        if real_csv_path:
            real_data_loaded = self.load_real_csv_data(real_csv_path)
            if real_data_loaded:
                scenarios.append("real_data")
                scenario_labels["real_data"] = f"7. Dữ liệu thực nghiệm ({os.path.basename(real_csv_path)})"

        points_rows: List[Dict[str, Any]] = []
        seed_metrics_rows: List[Dict[str, Any]] = []

        start_date = datetime.date(2026, 1, 1)

        # Chạy 30 seeds
        for sc in scenarios:
            self.stdout.write(self.style.SUCCESS(f">> Đang chạy kịch bản: {scenario_labels[sc]} ..."))
            for seed_idx in self.seed_ids:
                # Với kịch bản thực tế, chỉ chạy 1 lần dữ liệu thực (không phụ thuộc seed)
                if sc == "real_data":
                    sim_data = real_data_loaded
                else:
                    sim_data = self.generate_simulation_data(
                        scenario=sc,
                        start_date=start_date,
                        total_days=total_days,
                        seed=seed_idx,
                    )

                # Mốc rolling-origin: lịch sử 60 ngày, horizon 30 ngày, bước nhảy 7 ngày
                max_origin = len(sim_data) - 30
                # CSV: origin 59 includes 60 history days, leaving 30 future days in a 90-day series.
                origin_start = 59 if sc == 'real_data' else 60
                origin_indices = list(range(origin_start, max_origin, 7))

                # Đánh giá trên từng nhánh
                for arm_code, estimator, winsorize, alpha, arm_label in arms:
                    seed_points = []
                    for origin_idx in origin_indices:
                        pt_res = self.evaluate_single_origin(
                            sim_data=sim_data,
                            origin_idx=origin_idx,
                            horizon=30,
                            scenario=sc,
                            seed=seed_idx,
                            arm=arm_code,
                            estimator=estimator,
                            winsorize=winsorize,
                            alpha=alpha,
                        )
                        seed_points.append(pt_res)
                        points_rows.append(pt_res)

                    # Tính chỉ số gộp của seed này
                    mae_daily_seed = sum(p['MAE_daily'] for p in seed_points) / len(seed_points)
                    rmse_daily_seed = math.sqrt(sum(p['RMSE_daily'] ** 2 for p in seed_points) / len(seed_points))
                    mae_end_seed = sum(p['abs_err_end'] for p in seed_points) / len(seed_points)
                    bias_end_seed = sum(p['signed_err_end'] for p in seed_points) / len(seed_points)

                    seed_metrics_rows.append({
                        "scenario": sc,
                        "scenario_label": scenario_labels[sc],
                        "seed": seed_idx,
                        "arm": arm_code,
                        "arm_label": arm_label,
                        "MAE_daily": mae_daily_seed,
                        "RMSE_daily": rmse_daily_seed,
                        "MAE_end": mae_end_seed,
                        "Bias_end": bias_end_seed,
                    })

                if sc == "real_data":
                    break

        # ==============================================================================
        # 1. Xuất forecast_backtest_points_v2.csv
        # ==============================================================================
        points_csv_path = os.path.join(output_dir, "forecast_backtest_points_v2.csv")
        with open(points_csv_path, mode="w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "scenario", "seed", "arm", "origin_date",
                "MAE_daily", "RMSE_daily", "abs_err_end", "signed_err_end",
                "selected_alpha", "selected_estimator", "alpha_fallback",
                *[f"{cohort}_{key}" for cohort in ('risk', 'stress')
                  for key in ('tp', 'fp', 'fn', 'tn', 'timing_days', 'lead_days', 'already_negative')]
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in points_rows:
                writer.writerow(r)

        # ==============================================================================
        # 2. Xuất forecast_backtest_per_seed_v2.csv
        # ==============================================================================
        per_seed_csv_path = os.path.join(output_dir, "forecast_backtest_per_seed_v2.csv")
        with open(per_seed_csv_path, mode="w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "scenario", "scenario_label", "seed", "arm", "arm_label",
                "MAE_daily", "RMSE_daily", "MAE_end", "Bias_end"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in seed_metrics_rows:
                writer.writerow(r)

        # ==============================================================================
        # 3. Tổng hợp Trung bình ± Độ lệch chuẩn -> forecast_backtest_summary_v2.csv
        # ==============================================================================
        summary_rows: List[Dict[str, Any]] = []
        metrics_list = ["MAE_daily", "RMSE_daily", "MAE_end", "Bias_end"]

        for sc in scenarios:
            for arm_code, _, _, _, arm_label in arms:
                matching_seeds = [
                    r for r in seed_metrics_rows
                    if r['scenario'] == sc and r['arm'] == arm_code
                ]
                if not matching_seeds:
                    continue
                n_count = len(matching_seeds)
                row_dict: Dict[str, Any] = {
                    "scenario": sc,
                    "scenario_label": scenario_labels[sc],
                    "arm": arm_code,
                    "arm_label": arm_label,
                    "n_seeds": n_count,
                }
                for m in metrics_list:
                    vals = [r[m] for r in matching_seeds]
                    mean_val = sum(vals) / n_count
                    std_val = math.sqrt(sum((v - mean_val) ** 2 for v in vals) / (n_count - 1)) if n_count > 1 else 0.0
                    row_dict[f"{m}_mean"] = round(mean_val, 2)
                    row_dict[f"{m}_std"] = round(std_val, 2)

                summary_rows.append(row_dict)

        summary_csv_path = os.path.join(output_dir, "forecast_backtest_summary_v2.csv")
        with open(summary_csv_path, mode="w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "scenario", "scenario_label", "arm", "arm_label", "n_seeds",
                "MAE_daily_mean", "MAE_daily_std",
                "RMSE_daily_mean", "RMSE_daily_std",
                "MAE_end_mean", "MAE_end_std",
                "Bias_end_mean", "Bias_end_std",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in summary_rows:
                writer.writerow(r)

        # ==============================================================================
        # 4. So sánh theo cặp D vs A, D vs B, D vs C -> forecast_backtest_paired_v2.csv
        # ==============================================================================
        paired_rows: List[Dict[str, Any]] = []
        comparisons = [
            ("arm_D", "arm_A", "D vs A (Proposed vs Baseline)"),
            ("arm_D", "arm_B", "D vs B (Effect of EWMA with Winsorize)"),
            ("arm_D", "arm_C", "D vs C (Effect of Winsorize with EWMA)"),
            ("arm_E", "arm_A", "E vs A (Adaptive vs Mean)"),
            ("arm_E", "arm_D", "E vs D (Adaptive vs Fixed EWMA)"),
        ]

        for sc in scenarios:
            for arm_x, arm_y, pair_label in comparisons:
                # Lấy dữ liệu cùng seed
                seeds_x = {r['seed']: r for r in seed_metrics_rows if r['scenario'] == sc and r['arm'] == arm_x}
                seeds_y = {r['seed']: r for r in seed_metrics_rows if r['scenario'] == sc and r['arm'] == arm_y}
                common_seeds = sorted(set(seeds_x.keys()).intersection(seeds_y.keys()))
                if not common_seeds:
                    continue

                for m in ["MAE_daily", "MAE_end", "RMSE_daily", "Bias_end"]:
                    # Hiệu số: X - Y (âm nghĩa là X nhỏ hơn Y)
                    diffs = [seeds_x[s][m] - seeds_y[s][m] for s in common_seeds]
                    mean_diff, ci_low, ci_high = compute_bootstrap_ci(diffs, n_resamples=2000, ci=0.95, seed=12345)

                    # Win rate: Với MAE và RMSE (thấp hơn là tốt hơn): X < Y
                    # Với Bias: độ lớn |Bias| nhỏ hơn (gần 0 hơn) là tốt hơn
                    if m == "Bias_end":
                        wins = sum(1 for s in common_seeds if abs(seeds_x[s][m]) < abs(seeds_y[s][m]))
                    else:
                        wins = sum(1 for s in common_seeds if seeds_x[s][m] < seeds_y[s][m])
                    win_rate = (wins / len(common_seeds)) * 100.0

                    paired_rows.append({
                        "scenario": sc,
                        "scenario_label": scenario_labels[sc],
                        "comparison": pair_label,
                        "metric": m,
                        "mean_diff": round(mean_diff, 2),
                        "ci_95_lower": round(ci_low, 2),
                        "ci_95_upper": round(ci_high, 2),
                        "win_rate_pct": round(win_rate, 1),
                        "n_seeds": len(common_seeds),
                    })

        paired_csv_path = os.path.join(output_dir, "forecast_backtest_paired_v2.csv")
        with open(paired_csv_path, mode="w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "scenario", "scenario_label", "comparison", "metric",
                "mean_diff", "ci_95_lower", "ci_95_upper", "win_rate_pct", "n_seeds"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in paired_rows:
                writer.writerow(r)

        # ==============================================================================
        # 5. Phân tích độ nhạy Alpha -> forecast_backtest_alpha_v2.csv
        # ==============================================================================
        self.stdout.write(self.style.SUCCESS(">> Đang phân tích độ nhạy tham số alpha in {0.1, 0.2, 0.3, 0.5} ..."))
        alpha_candidates = [Decimal("0.1"), Decimal("0.2"), Decimal("0.3"), Decimal("0.5")]
        alpha_rows: List[Dict[str, Any]] = []

        for sc in [s for s in scenarios if s != "real_data"]:
            for alpha_val in alpha_candidates:
                alpha_seed_maes_daily = []
                alpha_seed_maes_end = []

                for seed_idx in self.seed_ids:
                    sim_data = self.generate_simulation_data(
                        scenario=sc,
                        start_date=start_date,
                        total_days=total_days,
                        seed=seed_idx,
                    )
                    max_origin = len(sim_data) - 30
                    origin_indices = list(range(60, max_origin, 7))

                    origins_daily = []
                    origins_end = []
                    for origin_idx in origin_indices:
                        pt_res = self.evaluate_single_origin(
                            sim_data=sim_data,
                            origin_idx=origin_idx,
                            horizon=30,
                            scenario=sc,
                            seed=seed_idx,
                            arm="alpha_sensitivity",
                            estimator="ewma",
                            winsorize=True,
                            alpha=alpha_val,
                        )
                        origins_daily.append(pt_res['MAE_daily'])
                        origins_end.append(pt_res['abs_err_end'])

                    alpha_seed_maes_daily.append(sum(origins_daily) / len(origins_daily))
                    alpha_seed_maes_end.append(sum(origins_end) / len(origins_end))

                mean_daily = sum(alpha_seed_maes_daily) / len(alpha_seed_maes_daily)
                std_daily = math.sqrt(sum((v - mean_daily) ** 2 for v in alpha_seed_maes_daily) / (len(alpha_seed_maes_daily) - 1))

                mean_end = sum(alpha_seed_maes_end) / len(alpha_seed_maes_end)
                std_end = math.sqrt(sum((v - mean_end) ** 2 for v in alpha_seed_maes_end) / (len(alpha_seed_maes_end) - 1))

                alpha_rows.append({
                    "scenario": sc,
                    "scenario_label": scenario_labels[sc],
                    "alpha": float(alpha_val),
                    "MAE_daily_mean": round(mean_daily, 2),
                    "MAE_daily_std": round(std_daily, 2),
                    "MAE_end_mean": round(mean_end, 2),
                    "MAE_end_std": round(std_end, 2),
                })

        alpha_csv_path = os.path.join(output_dir, "forecast_backtest_alpha_v2.csv")
        with open(alpha_csv_path, mode="w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "scenario", "scenario_label", "alpha",
                "MAE_daily_mean", "MAE_daily_std",
                "MAE_end_mean", "MAE_end_std"
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in alpha_rows:
                writer.writerow(r)

        self.risk_rows = []
        for sc in scenarios:
            for arm_code, *_ in arms:
                subset = [p for p in points_rows if p['scenario'] == sc and p['arm'] == arm_code]
                for cohort in ('risk', 'stress'):
                    counts = {key: sum(p[f'{cohort}_{key}'] for p in subset) for key in ('tp', 'fp', 'fn', 'tn')}
                    timing = [p[f'{cohort}_timing_days'] for p in subset if p[f'{cohort}_timing_days'] is not None]
                    leads = [p[f'{cohort}_lead_days'] for p in subset if p[f'{cohort}_lead_days'] is not None]
                    self.risk_rows.append(dict(
                        scenario=sc, arm=arm_code, cohort=cohort, **counts,
                        precision=counts['tp'] / (counts['tp'] + counts['fp']) if counts['tp'] + counts['fp'] else None,
                        recall=counts['tp'] / (counts['tp'] + counts['fn']) if counts['tp'] + counts['fn'] else None,
                        timing_days=sum(timing) / len(timing) if timing else None,
                        lead_days=sum(leads) / len(leads) if leads else None,
                        timing_n=len(timing), early=sum(t < 0 for t in timing), late=sum(t > 0 for t in timing),
                        already_negative=sum(p[f'{cohort}_already_negative'] for p in subset),
                    ))
        with open(os.path.join(output_dir, 'forecast_backtest_shortfall_v2.csv'), 'w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(self.risk_rows[0]))
            writer.writeheader()
            writer.writerows(self.risk_rows)
        protocol = dict(split=self.evaluation_split, seeds=self.seed_ids,
                        development_seeds=list(range(1000, 1010)), test_seeds=list(range(30)),
                        alpha_grid=[str(a) for a in ADAPTIVE_ALPHA_GRID] + ['mean'],
                        min_history_days=ADAPTIVE_MIN_HISTORY_DAYS, warmup_days=ADAPTIVE_WARMUP_DAYS,
                        history_days=60, horizon_days=30, origin_stride=7, stress_balance=1000000)
        with open(os.path.join(output_dir, 'forecast_backtest_protocol.json'), 'w', encoding='utf-8') as stream:
            json.dump(protocol, stream, indent=2)

        # ==============================================================================
        # 6. Báo cáo Markdown -> forecast_backtest_report_v2.md
        # ==============================================================================
        report_md_path = os.path.join(output_dir, "forecast_backtest_report_v2.md")
        self.generate_markdown_report(
            report_md_path=report_md_path,
            num_seeds=num_seeds,
            total_days=total_days,
            summary_rows=summary_rows,
            paired_rows=paired_rows,
            alpha_rows=alpha_rows,
        )

        # In bảng tóm tắt ngắn gọn ra terminal
        self.print_terminal_summary(summary_rows, paired_rows)

        self.stdout.write(self.style.SUCCESS(f"\n[HOÀN TẤT V2] Đã xuất toàn bộ kết quả thực nghiệm:"))
        self.stdout.write(f"  1. Chi tiết từng mốc: {points_csv_path}")
        self.stdout.write(f"  2. Chỉ số theo từng seed: {per_seed_csv_path}")
        self.stdout.write(f"  3. Bảng tổng hợp Mean ± Std: {summary_csv_path}")
        self.stdout.write(f"  4. So sánh theo cặp Paired (CI 95% + Win rate): {paired_csv_path}")
        self.stdout.write(f"  5. Độ nhạy alpha: {alpha_csv_path}")
        self.stdout.write(f"  6. Báo cáo Markdown: {report_md_path}\n")

    def generate_simulation_data(
        self,
        scenario: str,
        start_date: datetime.date,
        total_days: int = 365,
        seed: int = 42,
    ) -> List[Dict[str, Any]]:
        """
        Sinh chuỗi thời gian mô phỏng ground truth độc lập với thuật toán dự báo.
        Ground truth: Balance_t = Balance_{t-1} + sum(FixedEvents_t) - VariableExpense_t
        """
        rng = random.Random(seed)
        initial_balance = Decimal("20000000.00")
        current_balance = initial_balance

        data: List[Dict[str, Any]] = []

        for day_idx in range(total_days):
            cur_date = start_date + datetime.timedelta(days=day_idx)
            day_of_month = cur_date.day

            # Sự kiện cố định định kỳ hàng tháng giống nhau cho mọi kịch bản
            fixed_events: List[FixedEvent] = []
            if day_of_month == 5:
                fixed_events.append(FixedEvent(
                    date=cur_date,
                    title="Lương định kỳ",
                    amount=Decimal("25000000.00"),
                    source="RECURRING",
                    source_id=101,
                ))
            if day_of_month == 10:
                fixed_events.append(FixedEvent(
                    date=cur_date,
                    title="Tiền thuê nhà",
                    amount=Decimal("-6000000.00"),
                    source="RECURRING",
                    source_id=102,
                ))
            if day_of_month == 20:
                fixed_events.append(FixedEvent(
                    date=cur_date,
                    title="Tiện ích & Internet",
                    amount=Decimal("-1200000.00"),
                    source="RECURRING",
                    source_id=103,
                ))

            # Sinh chi tiêu biến đổi thực tế
            if scenario == "stable_noise":
                # Ổn định quanh 150.000đ/ngày, nhiễu gauss std = 25.000đ
                val = max(10000.0, rng.gauss(150000.0, 25000.0))
            elif scenario == "upward_trend":
                # Xu hướng tăng tuyến tính từ 100.000đ lên 260.000đ/ngày
                trend = 100000.0 + (160000.0 * (day_idx / total_days))
                val = max(10000.0, rng.gauss(trend, 20000.0))
            elif scenario == "volatile_outliers":
                # Thất thường: nền 130.000đ, độ lệch 35.000đ
                val = max(10000.0, rng.gauss(130000.0, 35000.0))
                # Các cú sốc outlier đột biến định kỳ: ngày 25, 95, 185, 275 (+5.500.000đ)
                if day_idx in {25, 95, 185, 275}:
                    val += 5500000.0
            elif scenario == 'weekend_spending':
                val = max(0, rng.gauss(300000 if cur_date.weekday() >= 5 else 100000, 25000))
            elif scenario == 'habit_shift':
                val = max(0, rng.gauss(100000 if day_idx < total_days // 2 else 350000, 25000))
            elif scenario == 'sparse_spending':
                val = max(0, rng.gauss(400000, 75000)) if rng.random() < 0.2 else 0.0
            else:
                val = 150000.0

            var_expense = Decimal(str(round(val, 2)))

            # Cập nhật số dư thực tế độc lập
            fixed_sum = sum((ev.amount for ev in fixed_events), Decimal("0.00"))
            if day_idx == 0:
                current_balance = current_balance + fixed_sum
            else:
                current_balance = current_balance + fixed_sum - var_expense

            data.append({
                "day_idx": day_idx,
                "date": cur_date,
                "var_expense": var_expense,
                "fixed_events": fixed_events,
                "balance": current_balance,
            })

        return data

    def load_real_csv_data(self, file_path: str) -> Optional[List[Dict[str, Any]]]:
        """Read, audit and normalize CSV spending into at least 90 calendar days.

        Balances remain hypothetical: the first day starts at initial_balance
        without subtracting that day's spending, preserving the existing convention.
        """
        try:
            with open(file_path, mode="r", encoding="utf-8-sig", newline="") as stream:
                rows = list(csv.DictReader(stream, strict=True))
        except (OSError, UnicodeError, csv.Error) as error:
            raise CommandError(f"Không thể đọc CSV {file_path}: {error}") from error

        items, stats = normalize_daily_spend(rows)
        self.stdout.write(f"Đã đọc: {stats['rows_read']} dòng; Đã loại: {stats['rows_excluded']} dòng.")
        for key, label in (
            ('missing_date', 'thiếu ngày'),
            ('missing_amount', 'thiếu số tiền'),
            ('invalid_date', 'ngày sai định dạng'),
            ('invalid_amount', 'số tiền sai định dạng hoặc không hữu hạn'),
            ('wrong_sign', 'sai dấu'),
            ('excluded_type', 'loại giao dịch không phải chi tiêu'),
        ):
            self.stdout.write(f"  {label}: {stats[key]}")
        self.stdout.write(f"Điền 0: {stats['zero_filled_days']} ngày; sau chuẩn hóa: {len(items)} ngày lịch.")
        if len(items) < 90:
            raise CommandError(f"CSV {file_path} có {len(items)} ngày lịch; cần tối thiểu 90 ngày sau chuẩn hóa.")

        bal = getattr(self, 'initial_balance', Decimal('20000000.00'))
        self.stdout.write(f"Số dư giả định ban đầu cho CSV: {bal} VND (ngày đầu chưa trừ chi tiêu).")
        sim_data = []
        for idx, (cur_d, amt) in enumerate(items):
            if idx > 0:
                bal -= amt
            sim_data.append({
                "day_idx": idx,
                "date": cur_d,
                "var_expense": amt,
                "fixed_events": [],
                "balance": bal,
            })
        return sim_data

    def evaluate_single_origin(
        self,
        sim_data: List[Dict[str, Any]],
        origin_idx: int,
        horizon: int,
        scenario: str,
        seed: int,
        arm: str,
        estimator: str,
        winsorize: bool,
        alpha: Decimal,
    ) -> Dict[str, Any]:
        """
        Đánh giá tại một mốc origin:
        - Số dư tại origin là số dư cuối ngày, đã gồm sự kiện và chi tiêu ngày đó.
        - CHỈ trích xuất lịch sử 60 ngày trước mốc.
        - CHỈ trích xuất sự kiện tương lai trong (origin, origin + horizon].
        - Chạy simulate_cashflow với cấu hình nhánh tương ứng.
        - Timeline tại step 0 bằng số dư quan sát tại origin (sai số 0).
        - Tính MAE_daily, RMSE_daily trên step 1..horizon; sai số cuối tại step horizon.
        """
        origin_item = sim_data[origin_idx]
        origin_date = origin_item['date']
        current_balance = origin_item['balance']

        # 1. Trích xuất đúng 60 ngày quá khứ [origin_idx - 59 .. origin_idx]
        history_window = sim_data[origin_idx - 59 : origin_idx + 1]
        daily_history = [(item['date'], item['var_expense']) for item in history_window]

        # 2. Trích xuất sự kiện cố định tương lai
        future_window = sim_data[origin_idx + 1 : origin_idx + horizon + 1]
        scheduled_events: List[FixedEvent] = []
        for item in future_window:
            scheduled_events.extend(item['fixed_events'])

        # 3. Chạy thuật toán mô phỏng (tất cả các nhánh đều đi qua simulate_cashflow)
        forecast_res = simulate_cashflow(
            current_balance=current_balance,
            events=scheduled_events,
            daily_history=daily_history,
            today=origin_date,
            days=horizon,
            alpha=alpha,
            estimator=estimator,
            winsorize=winsorize,
        )

        # 4. Đo sai số so với ground truth của chuỗi tương lai
        daily_errors = []
        for step in range(1, horizon + 1):
            future_actual = sim_data[origin_idx + step]
            actual_bal = future_actual['balance']
            projected_bal = forecast_res.daily_timeline[step]['balance']
            err = float(projected_bal - actual_bal)
            daily_errors.append(err)

        mae_daily = sum(abs(e) for e in daily_errors) / len(daily_errors)
        rmse_daily = math.sqrt(sum(e ** 2 for e in daily_errors) / len(daily_errors))
        abs_err_end = abs(daily_errors[-1])
        signed_err_end = daily_errors[-1]

        actual_timeline = [sim_data[origin_idx + step] for step in range(horizon + 1)]
        risks = {}
        for cohort, offset in (('risk', Decimal('0')), ('stress', Decimal('1000000') - current_balance)):
            predicted = [dict(point, balance=point['balance'] + offset) for point in forecast_res.daily_timeline]
            actual = [dict(point, balance=point['balance'] + offset) for point in actual_timeline]
            risks.update({f'{cohort}_{key}': value for key, value in
                          shortfall_metrics(predicted, actual, origin_date).items()})

        return {
            "scenario": scenario,
            "seed": seed,
            "arm": arm,
            "origin_date": origin_date.isoformat(),
            "MAE_daily": mae_daily,
            "RMSE_daily": rmse_daily,
            "abs_err_end": abs_err_end,
            "signed_err_end": signed_err_end,
            "selected_alpha": str(forecast_res.selected_alpha) if forecast_res.selected_alpha is not None else '',
            "selected_estimator": forecast_res.selected_estimator or estimator,
            "alpha_fallback": forecast_res.alpha_fallback,
            **risks,
        }

    def print_terminal_summary(
        self,
        summary_rows: List[Dict[str, Any]],
        paired_rows: List[Dict[str, Any]],
    ):
        """In bảng tóm tắt đẹp mắt ra terminal."""
        self.stdout.write("\n" + self.style.SUCCESS("=" * 115))
        self.stdout.write(self.style.SUCCESS(
            f"{'KỊCH BẢN':<36} | {'NHÁNH (ARM)':<28} | {'MAE NGÀY (Mean±Std)':<22} | {'MAE CUỐI (Mean±Std)':<22}"
        ))
        self.stdout.write(self.style.SUCCESS("=" * 115))

        for r in summary_rows:
            sc_short = r['scenario_label'].split(".")[1].strip()
            arm_short = r['arm_label'].split(":")[1].strip()
            daily_str = f"{r['MAE_daily_mean']:>10,.0f} ± {r['MAE_daily_std']:<8,.0f}"
            end_str = f"{r['MAE_end_mean']:>10,.0f} ± {r['MAE_end_std']:<8,.0f}"
            self.stdout.write(f"{sc_short:<36} | {arm_short:<28} | {daily_str:<22} | {end_str:<22}")

        self.stdout.write("-" * 115)
        self.stdout.write(self.style.SUCCESS("\nSO SÁNH THEO CẶP (PAIRED COMPARISON - BOOTSTRAP 95% CI):"))
        self.stdout.write(self.style.SUCCESS(
            f"{'KỊCH BẢN':<32} | {'CẶP SO SÁNH':<30} | {'CHỈ SỐ':<12} | {'HIỆU TRUNG BÌNH':<16} | {'BOOTSTRAP 95% CI':<24} | {'WIN RATE':<10}"
        ))
        self.stdout.write(self.style.SUCCESS("-" * 135))

        for p in paired_rows:
            if p['metric'] in ["MAE_daily", "MAE_end"]:
                sc_short = p['scenario_label'].split(".")[1].strip()
                ci_str = f"[{p['ci_95_lower']:>10,.0f}, {p['ci_95_upper']:>10,.0f}]"
                self.stdout.write(
                    f"{sc_short:<32} | {p['comparison']:<30} | {p['metric']:<12} | {p['mean_diff']:>14,.0f} đ | {ci_str:<24} | {p['win_rate_pct']:>8.1f}%"
                )

    def generate_markdown_report(
        self,
        report_md_path: str,
        num_seeds: int,
        total_days: int,
        summary_rows: List[Dict[str, Any]],
        paired_rows: List[Dict[str, Any]],
        alpha_rows: List[Dict[str, Any]],
    ):
        """Tạo file markdown báo cáo chi tiết đầy đủ bảng số liệu và phân tích hạn chế."""
        with open(report_md_path, mode="w", encoding="utf-8") as f:
            f.write("# BÁO CÁO ĐÁNH GIÁ THỰC NGHIỆM THUẬT TOÁN DỰ BÁO DÒNG TIỀN F03 (V2)\n\n")

            f.write("## 1. Cấu Hình Thực Nghiệm & Thiết Kế Đánh Giá\n\n")
            f.write(f"- **Số seed mô phỏng cấu hình:** {num_seeds} hạt giống độc lập; split {getattr(self, 'evaluation_split', 'test')}. Số seed thực tế theo từng kịch bản được ghi ở mục 3.\n")
            f.write(f"- **Độ dài chuỗi mô phỏng:** {total_days} ngày.\n")
            f.write("- **Cửa sổ lịch sử quan sát:** 60 ngày gần nhất.\n")
            f.write("- **Đường chân trời dự báo (Horizon):** 30 ngày.\n")
            n_origins = len(range(60, total_days - 30, 7))
            f.write(f"- **Bước nhảy Rolling-Origin:** 7 ngày, {n_origins} cửa sổ chồng lấn mỗi chuỗi mô phỏng; horizon 30 ngày. Số cửa sổ của dữ liệu thực phụ thuộc độ dài chuỗi nhập.\n")
            f.write("- **Bootstrap 95% CI:** 2.000 lần lấy mẫu, random seed = 12345; mỗi seed là một đơn vị lấy mẫu độc lập. Chỉ số được tổng hợp qua các cửa sổ trong mỗi seed trước khi lấy sai khác theo cặp; không lấy mẫu riêng từng cửa sổ hoặc từng ngày.\n")
            f.write("  Các cửa sổ chồng lấn có phụ thuộc thời gian. CI phản ánh biến thiên giữa các chuỗi seed trong thiết kế này, không coi các cửa sổ là quan sát độc lập và không đại diện trực tiếp cho quần thể người dùng thực. Với dưới 2 seed, CI suy biến không đủ để kết luận ý nghĩa thống kê.\n")
            f.write(f"- **Tách dữ liệu:** seed phát triển 1000–1009; seed kiểm tra 0–29 (lần chạy này: {getattr(self, 'seed_ids', list(range(num_seeds)))}). Chốt cấu hình trên development trước khi chạy test; không chọn lại cấu hình từ kết quả test. Alpha mỗi origin chỉ chọn từ lịch sử đến origin.\n")
            f.write(f"- **Chính sách thích nghi:** lưới {list(map(str, ADAPTIVE_ALPHA_GRID))} + mean; tối thiểu {ADAPTIVE_MIN_HISTORY_DAYS} ngày; warm-up {ADAPTIVE_WARMUP_DAYS} ngày; MAE một bước trên mục tiêu thô; winsorize riêng từng fold. Warm-up được chọn bằng seed phát triển qua kiểm tra chuỗi tĩnh, không tối ưu theo seed kiểm tra. Lưới và ngưỡng tối thiểu được ấn định trước theo thiết kế.\n")
            f.write("- **Năm nhánh thực nghiệm bóc tách (Ablation Arms):**\n")
            f.write("  - **Nhánh A (Baseline):** Ước lượng Trung bình trượt 60 ngày phẳng, không xử lý outlier (`estimator='mean', winsorize=False`).\n")
            f.write("  - **Nhánh B:** Ước lượng Trung bình trượt có xử lý Winsorization (`estimator='mean', winsorize=True`).\n")
            f.write("  - **Nhánh C:** Ước lượng EWMA không xử lý outlier (`estimator='ewma', winsorize=False, alpha=0.2`).\n")
            f.write("  - **Nhánh D (Cố định):** Ước lượng Winsorized EWMA (`estimator='ewma', winsorize=True, alpha=0.2`).\n")
            f.write("  - **Nhánh E:** Mean/EWMA thích nghi + Winsorization; giữ mặc định ứng dụng là D.\n\n")

            f.write("## 2. Định Nghĩa Các Chỉ Số Sai Số\n\n")
            f.write("- **Quy ước origin:** Số dư tại origin là số dư cuối ngày; chỉ áp dụng sự kiện trong (origin, origin + horizon]. Step 0 bằng số dư quan sát và không được tính vào MAE_daily/RMSE_daily.\n")
            f.write("- **MAE_daily (Mean Absolute Error theo ngày):** Trung bình sai số tuyệt đối giữa số dư dự báo và số dư thực tế trên 30 ngày tương lai (h=1..30):\n")
            f.write("  $$\\text{MAE}_{\\text{daily}} = \\frac{1}{30} \\sum_{h=1}^{30} |\\hat{W}_h - W_h|$$\n")
            f.write("- **RMSE_daily (Root Mean Squared Error theo ngày):** Căn bậc hai trung bình bình phương sai số, phản ánh mức độ nhạy cảm với các sai lệch lớn:\n")
            f.write("  $$\\text{RMSE}_{\\text{daily}} = \\sqrt{\\frac{1}{30} \\sum_{h=1}^{30} (\\hat{W}_h - W_h)^2}$$\n")
            f.write("- **MAE_end (Sai số tuyệt đối cuối kỳ):** Sai số tuyệt đối tại ngày cuối cùng của đường chân trời (bước $h=30$):\n")
            f.write("  $$\\text{MAE}_{\\text{end}} = |\\hat{W}_{30} - W_{30}|$$\n")
            f.write("- **Bias_end (Độ chệch cuối kỳ có dấu):** Sai số có dấu $\\hat{W}_{30} - W_{30}$. Giá trị dương biểu thị dự báo lạc quan (đánh giá số dư cao hơn thực tế); giá trị âm biểu thị dự báo bi quan/thận trọng.\n\n")

            f.write("## 3. Kết Quả Tổng Hợp (Trung Bình ± Độ Lệch Chuẩn Qua Các Seed)\n\n")
            f.write("Số seed theo từng kịch bản: " + "; ".join(
                f"{r['scenario_label']}: {r['n_seeds']} seed"
                for r in summary_rows if r['arm'] == 'arm_D'
            ) + ".\n\n")
            f.write("| Kịch bản | Nhánh | MAE_daily (đ) | RMSE_daily (đ) | MAE_end (đ) | Bias_end (đ) |\n")
            f.write("| :--- | :--- | :---: | :---: | :---: | :---: |\n")
            for r in summary_rows:
                sc_short = r['scenario_label']
                arm_short = r['arm_label']
                f.write(f"| {sc_short} | {arm_short} | {r['MAE_daily_mean']:,.2f} ± {r['MAE_daily_std']:,.2f} | {r['RMSE_daily_mean']:,.2f} ± {r['RMSE_daily_std']:,.2f} | {r['MAE_end_mean']:,.2f} ± {r['MAE_end_std']:,.2f} | {r['Bias_end_mean']:,.2f} ± {r['Bias_end_std']:,.2f} |\n")

            f.write("\n## 4. Bảng So Sánh Theo Cặp (Paired Comparison) & Kiểm Định Bootstrap 95% CI\n\n")
            f.write("Hiệu số được tính bằng **Nhánh X - Nhánh Y**. Với MAE và RMSE, hiệu số âm mang ý nghĩa nhánh đề xuất có sai số nhỏ hơn (tốt hơn). Win Rate là tỷ lệ % số seed mà nhánh đề xuất đạt sai số nhỏ hơn.\n\n")
            f.write("| Kịch bản | Cặp so sánh | Chỉ số | Hiệu trung bình (đ) | Khoảng tin cậy 95% Bootstrap (đ) | Win Rate (%) |\n")
            f.write("| :--- | :--- | :---: | :---: | :---: | :---: |\n")
            for p in paired_rows:
                f.write(f"| {p['scenario_label']} | {p['comparison']} | {p['metric']} | {p['mean_diff']:,.2f} | [{p['ci_95_lower']:,.2f}, {p['ci_95_upper']:,.2f}] | {p['win_rate_pct']}% |\n")

            f.write("\n## 5. Phân Tích Độ Nhạy Tham Số Alpha (Nhánh D: EWMA + Winsorize)\n\n")
            f.write("| Kịch bản | Alpha ($\\alpha$) | MAE_daily (đ) | MAE_end (đ) |\n")
            f.write("| :--- | :---: | :---: | :---: |\n")
            for a in alpha_rows:
                f.write(f"| {a['scenario_label']} | {a['alpha']} | {a['MAE_daily_mean']:,.0f} ± {a['MAE_daily_std']:,.0f} | {a['MAE_end_mean']:,.0f} ± {a['MAE_end_std']:,.0f} |\n")

            f.write("\n## 6. Thảo Luận Kết Quả & Giới Hạn Nghiên Cứu\n\n")
            f.write("### 6.1. Nhận xét khách quan:\n\n")
            f.write("Cải thiện = (tham chiếu - nhánh đang xét) / tham chiếu × 100; giá trị âm nghĩa là nhánh đang xét có sai số cao hơn. A là baseline; B và C là các nhánh đối chiếu ablation. Kết luận dựa trên CI của hiệu nhánh đang xét - tham chiếu, không suy ra p-value. Bias_end là sai số có dấu nên không dùng dấu CI của Bias_end để kết luận tốt/kém.\n\n")
            summaries = {(r['scenario'], r['arm']): r for r in summary_rows}
            comparisons = {f'{candidate} vs {reference}': (f'arm_{candidate}', f'arm_{reference}')
                           for candidate, reference in (('D', 'A'), ('D', 'B'), ('D', 'C'), ('E', 'A'), ('E', 'D'))}
            for p in paired_rows:
                if p['metric'] not in ('MAE_daily', 'MAE_end', 'RMSE_daily'):
                    continue
                comparison = p['comparison'].split(' (')[0]
                candidate_arm, reference_arm = comparisons.get(comparison, (None, None))
                reference = summaries.get((p['scenario'], reference_arm))
                proposed = summaries.get((p['scenario'], candidate_arm))
                if reference is None or proposed is None:
                    continue
                metric = p['metric']
                baseline_value = reference[f'{metric}_mean']
                proposed_value = proposed[f'{metric}_mean']
                improvement = (
                    f"{(baseline_value - proposed_value) / baseline_value * 100:.2f}%"
                    if baseline_value != 0 else "không xác định (tham chiếu bằng 0)"
                )
                if p['n_seeds'] < 2:
                    verdict = 'chưa kết luận được (không đủ seed độc lập)'
                elif p['ci_95_upper'] < 0:
                    verdict = 'tốt hơn có ý nghĩa'
                elif p['ci_95_lower'] > 0:
                    verdict = 'kém hơn'
                else:
                    verdict = 'chưa kết luận được'
                f.write(
                    f"- **{p['scenario_label']} — {comparison}, {metric}:** "
                    f"Cải thiện: {improvement}; Win Rate: {p['win_rate_pct']:.1f}% ({p['n_seeds']} seed); "
                    f"hiệu trung bình {candidate_arm[-1]} - tham chiếu: {p['mean_diff']:,.2f} đ; "
                    f"CI 95%: [{p['ci_95_lower']:,.2f}, {p['ci_95_upper']:,.2f}] đ. "
                    f"Kết luận: {verdict}.\n"
                )

            f.write("\n### 6.2. Các giới hạn còn lại (Limitations):\n\n")
            scenarios = {r['scenario'] for r in summary_rows}
            simulated = scenarios - {'real_data'}
            if 'real_data' not in scenarios:
                f.write("- Chỉ có dữ liệu mô phỏng trong lần chạy này, chưa có kiểm chứng trên dữ liệu thực.\n")
            else:
                f.write("- Dữ liệu thực trong lần chạy này chỉ là một chuỗi nhập từ CSV, không phải nhiều seed độc lập hay một mẫu đại diện cho người dùng.\n")
            if simulated:
                f.write(f"- Có {len(simulated)} kịch bản mô phỏng trong lần chạy này; kết quả chỉ phản ánh các phân phối được mô phỏng, không bảo đảm khái quát cho hành vi chi tiêu khác.\n")
            if simulated.intersection({'stable_noise', 'upward_trend', 'volatile_outliers'}):
                f.write("- Các kịch bản mô phỏng hiện có chưa mô hình hóa ngày lễ/Tết; chỉ kịch bản weekend_spending mô hình hóa khác biệt cuối tuần.\n")
            insufficient = sorted({p['scenario_label'] for p in paired_rows if p['n_seeds'] < 2})
            if insufficient:
                f.write("- Các kịch bản không đủ seed độc lập để suy luận từ bootstrap: " + "; ".join(insufficient) + ".\n")
            f.write("- Các cửa sổ chồng lấn không làm tăng số đơn vị độc lập; CI theo seed chỉ phản ánh bất định giữa các seed dưới thiết kế hiện tại.\n")
            if alpha_rows:
                alphas = sorted({r['alpha'] for r in alpha_rows})
                f.write(f"- Phân tích độ nhạy chỉ bao gồm các alpha {alphas}; đây là phân tích nhạy của D, không dùng để chọn lại cấu hình E từ tập kiểm tra.\n")
            else:
                f.write("- Lần chạy này chưa có kết quả phân tích độ nhạy alpha.\n")

            adaptive = summaries.get(('stable_noise', 'arm_E'))
            mean = summaries.get(('stable_noise', 'arm_A'))
            if adaptive and mean and adaptive['MAE_daily_mean'] > mean['MAE_daily_mean']:
                f.write("- E vẫn có MAE ngày cao hơn A ở chuỗi ổn định. Việc chọn ứng viên trên cửa sổ 60 ngày hữu hạn có chi phí chọn tham số và phương sai ước lượng alpha; đây là giải thích khả dĩ, không phải bằng chứng nhân quả. Không điều chỉnh lại thuật toán theo kết quả test này.\n")
            if getattr(self, 'risk_rows', None):
                f.write("\n## 7. Phát hiện thiếu hụt tiền\n\n")
                f.write("CRITICAL ở đây là có số dư âm trong step 1..30. Precision = TP/(TP+FP), Recall = TP/(TP+FN); N/A khi mẫu số bằng 0. Timing = ngày âm đầu tiên dự báo - ngày âm đầu tiên thực tế (âm: sớm, dương: muộn), chỉ tính cho TP; Lead = số ngày từ origin đến ngày âm thực tế của TP. Các thống kê theo origin là mô tả, không coi cửa sổ chồng lấn là mẫu độc lập.\n\n")
                f.write("Cohort risk dùng số dư gốc; cohort stress đặt số dư tại mỗi origin về 1.000.000đ và giữ nguyên gia số tiền thực tế/tương lai. Stress là tình huống giả định có kiểm soát, không phải kết quả trên số dư quan sát. Already-negative đếm origin đã âm. Không gộp hai cohort.\n\n")
                f.write("| Kịch bản | Nhánh | Cohort | TP | FP | FN | TN | Precision | Recall | Timing (ngày) | Lead (ngày) | Số TP | Sớm | Muộn | Already-negative |\n")
                f.write("|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n")
                for row in self.risk_rows:
                    values = [row[key] if row[key] is not None else 'N/A'
                              for key in ('scenario', 'arm', 'cohort', 'tp', 'fp', 'fn', 'tn', 'precision', 'recall', 'timing_days', 'lead_days', 'timing_n', 'early', 'late', 'already_negative')]
                    f.write('| ' + ' | '.join(f'{value:.3f}' if isinstance(value, float) else str(value) for value in values) + ' |\n')
