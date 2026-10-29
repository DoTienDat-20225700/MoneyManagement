#!/usr/bin/env python3
"""
MoneyManagement - Plot Forecast Backtest Evaluation Charts
Tạo 3 biểu đồ chuẩn học thuật (300 DPI, tiếng Việt) từ dữ liệu backtest F03:
1. fig1_ablation_mae_comparison.png (Grouped Bar Chart - So sánh MAE các nhánh bóc tách)
2. fig2_alpha_sensitivity_curve.png (Line Plot + Confidence Band - Phân tích độ nhạy Alpha)
3. fig3_paired_bootstrap_ci.png (Forest Plot - Khoảng tin cậy Bootstrap 95% D vs A)
"""

import os
import csv
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

# Setup directory paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVAL_DIR = os.path.join(BASE_DIR, "evaluation_results")
CHARTS_DIR = os.path.join(EVAL_DIR, "charts")
os.makedirs(CHARTS_DIR, exist_ok=True)

# Configure Matplotlib fonts and styles
plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica', 'DejaVu Sans', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 11


def read_csv_rows(filepath):
    with open(filepath, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


def plot_fig1_ablation_mae():
    """
    Biểu đồ 1: So sánh MAE_daily và MAE_end giữa 4 nhánh bóc tách trên 3 kịch bản.
    Grouped Bar Chart kèm Error Bars (± std).
    """
    filepath = os.path.join(EVAL_DIR, "forecast_backtest_summary_v2.csv")
    rows = read_csv_rows(filepath)

    scenarios = [
        ("stable_noise", "1. Ổn định (Stable)"),
        ("upward_trend", "2. Xu hướng tăng (Upward)"),
        ("volatile_outliers", "3. Thất thường/Outlier"),
    ]

    arms = [
        ("arm_A", "A: Mean (Raw) - Baseline", "#95a5a6"),
        ("arm_B", "B: Mean (Winsorized)", "#3498db"),
        ("arm_C", "C: EWMA (Raw)", "#e67e22"),
        ("arm_D", "D: EWMA (Winsorized) - Đề xuất", "#27ae60"),
    ]

    # Organize data: data[scenario][arm] = {MAE_daily_mean, MAE_daily_std, MAE_end_mean, MAE_end_std}
    data = {}
    for r in rows:
        sc = r["scenario"]
        arm = r["arm"]
        if sc not in data:
            data[sc] = {}
        data[sc][arm] = {
            "mae_daily": float(r["MAE_daily_mean"]) / 1e6,
            "mae_daily_std": float(r["MAE_daily_std"]) / 1e6,
            "mae_end": float(r["MAE_end_mean"]) / 1e6,
            "mae_end_std": float(r["MAE_end_std"]) / 1e6,
        }

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6), sharey=False)
    fig.suptitle(
        "SO SÁNH SAI SỐ MAE GIỮA CÁC NHÁNH THỰC NGHIỆM BÓC TÁCH (ABLATION STUDY)",
        fontsize=14,
        fontweight="bold",
        y=0.98,
    )

    bar_width = 0.18
    num_arms = len(arms)
    indices = range(len(scenarios))

    for idx_arm, (arm_key, arm_name, color) in enumerate(arms):
        offset = (idx_arm - (num_arms - 1) / 2) * bar_width

        # Panel 1: MAE_daily
        y1_vals = [data[sc_key][arm_key]["mae_daily"] for sc_key, _ in scenarios]
        y1_errs = [data[sc_key][arm_key]["mae_daily_std"] for sc_key, _ in scenarios]
        x1_pos = [i + offset for i in indices]

        rects1 = ax1.bar(
            x1_pos,
            y1_vals,
            width=bar_width,
            yerr=y1_errs,
            capsize=4,
            label=arm_name,
            color=color,
            edgecolor="#2c3e50",
            linewidth=0.8,
            alpha=0.9,
        )

        # Label values on bars
        for rect in rects1:
            h = rect.get_height()
            ax1.text(
                rect.get_x() + rect.get_width() / 2.0,
                h + 0.04,
                f"{h:.2f}",
                ha="center",
                va="bottom",
                fontsize=8.5,
                rotation=0,
            )

        # Panel 2: MAE_end
        y2_vals = [data[sc_key][arm_key]["mae_end"] for sc_key, _ in scenarios]
        y2_errs = [data[sc_key][arm_key]["mae_end_std"] for sc_key, _ in scenarios]
        x2_pos = [i + offset for i in indices]

        rects2 = ax2.bar(
            x2_pos,
            y2_vals,
            width=bar_width,
            yerr=y2_errs,
            capsize=4,
            label=arm_name,
            color=color,
            edgecolor="#2c3e50",
            linewidth=0.8,
            alpha=0.9,
        )

        for rect in rects2:
            h = rect.get_height()
            ax2.text(
                rect.get_x() + rect.get_width() / 2.0,
                h + 0.06,
                f"{h:.2f}",
                ha="center",
                va="bottom",
                fontsize=8.5,
                rotation=0,
            )

    # Style Panel 1
    ax1.set_title("(a) Sai số MAE theo ngày (MAE_daily)", fontsize=12, fontweight="bold", pad=12)
    ax1.set_xticks(indices)
    ax1.set_xticklabels([sc_label for _, sc_label in scenarios], fontsize=10.5, fontweight="medium")
    ax1.set_ylabel("MAE (Triệu VNĐ)", fontsize=11, fontweight="bold")
    ax1.grid(axis="y", linestyle="--", alpha=0.5)
    ax1.set_ylim(0, max([data[sc][arm]["mae_daily"] for sc, _ in scenarios for arm, _, _ in arms]) * 1.25)

    # Style Panel 2
    ax2.set_title("(b) Sai số MAE số dư cuối kỳ (MAE_end)", fontsize=12, fontweight="bold", pad=12)
    ax2.set_xticks(indices)
    ax2.set_xticklabels([sc_label for _, sc_label in scenarios], fontsize=10.5, fontweight="medium")
    ax2.set_ylabel("MAE (Triệu VNĐ)", fontsize=11, fontweight="bold")
    ax2.grid(axis="y", linestyle="--", alpha=0.5)
    ax2.set_ylim(0, max([data[sc][arm]["mae_end"] for sc, _ in scenarios for arm, _, _ in arms]) * 1.25)

    # Shared Legend
    handles, labels = ax1.get_legend_handles_labels()
    fig.legend(
        handles,
        labels,
        loc="lower center",
        ncol=4,
        bbox_to_anchor=(0.5, -0.05),
        frameon=True,
        facecolor="#fdfefe",
        edgecolor="#bdc3c7",
        fontsize=10.5,
    )

    plt.tight_layout(rect=[0, 0.04, 1, 0.95])
    out_path = os.path.join(CHARTS_DIR, "fig1_ablation_mae_comparison.png")
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Đã xuất {out_path}")


def plot_fig2_alpha_sensitivity():
    """
    Biểu đồ 2: Đường phân tích độ nhạy của MAE_daily theo hệ số alpha (0.1, 0.2, 0.3, 0.5).
    Line Plot kèm vùng bóng ± std, đánh dấu mốc alpha = 0.2.
    """
    filepath = os.path.join(EVAL_DIR, "forecast_backtest_alpha_v2.csv")
    rows = read_csv_rows(filepath)

    scenario_meta = {
        "stable_noise": ("1. Chi tiêu ổn định có nhiễu (Stable)", "#2980b9", "o"),
        "upward_trend": ("2. Chi tiêu có xu hướng tăng (Upward Trend)", "#e74c3c", "s"),
        "volatile_outliers": ("3. Chi tiêu thất thường có outlier (Volatile)", "#8e44ad", "^"),
    }

    scenarios = {}
    for r in rows:
        sc = r["scenario"]
        if sc not in scenarios:
            scenarios[sc] = []
        scenarios[sc].append({
            "alpha": float(r["alpha"]),
            "mean": float(r["MAE_daily_mean"]) / 1e6,
            "std": float(r["MAE_daily_std"]) / 1e6,
        })

    fig, ax = plt.subplots(figsize=(10, 6))

    for sc_key, items in scenarios.items():
        items.sort(key=lambda x: x["alpha"])
        alphas = [x["alpha"] for x in items]
        means = [x["mean"] for x in items]
        stds = [x["std"] for x in items]

        label, color, marker = scenario_meta.get(sc_key, (sc_key, "#333333", "o"))

        # Line plot
        ax.plot(
            alphas,
            means,
            marker=marker,
            markersize=8,
            linewidth=2.2,
            label=label,
            color=color,
        )

        # Confidence ribbon (± std)
        lower_bound = [m - s for m, s in zip(means, stds)]
        upper_bound = [m + s for m, s in zip(means, stds)]
        ax.fill_between(alphas, lower_bound, upper_bound, color=color, alpha=0.15)

    # Mark chosen alpha = 0.2
    ax.axvline(
        x=0.2,
        color="#27ae60",
        linestyle="--",
        linewidth=2.0,
        label=r"Mốc tham số tối ưu đề xuất ($\alpha = 0.2$)",
    )

    # Highlight points at alpha = 0.2
    for sc_key, items in scenarios.items():
        pt_02 = next((x for x in items if abs(x["alpha"] - 0.2) < 1e-4), None)
        if pt_02:
            ax.scatter([0.2], [pt_02["mean"]], s=120, color="#27ae60", edgecolors="#1e8449", zorder=5)
            ax.annotate(
                f"{pt_02['mean']:.2f} tr",
                xy=(0.2, pt_02["mean"]),
                xytext=(8, -5 if sc_key == "upward_trend" else 8),
                textcoords="offset points",
                fontsize=9.5,
                fontweight="bold",
                color="#145a32",
                bbox=dict(boxstyle="round,pad=0.2", fc="#e8f8f5", ec="#a3e4d7", alpha=0.9),
            )

    ax.set_title(
        "PHÂN TÍCH ĐỘ NHẠY CỦA SAI SỐ DỰ BÁO MAE_DAILY THEO HỆ SỐ ALPHA",
        fontsize=13,
        fontweight="bold",
        pad=15,
    )
    ax.set_xlabel(r"Hệ số làm mịn EWMA ($\alpha$)", fontsize=11.5, fontweight="bold")
    ax.set_ylabel("MAE theo ngày (Triệu VNĐ)", fontsize=11.5, fontweight="bold")
    ax.set_xticks([0.1, 0.2, 0.3, 0.5])
    ax.grid(True, linestyle="--", alpha=0.55)

    ax.legend(
        loc="upper left",
        frameon=True,
        facecolor="#fdfefe",
        edgecolor="#bdc3c7",
        fontsize=10,
    )

    plt.tight_layout()
    out_path = os.path.join(CHARTS_DIR, "fig2_alpha_sensitivity_curve.png")
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Đã xuất {out_path}")


def plot_fig3_paired_bootstrap_ci():
    """
    Biểu đồ 3: Forest Plot biểu diễn hiệu số trung bình và khoảng tin cậy Bootstrap 95%
    của phép so sánh D vs A (Proposed vs Baseline) cho MAE_daily và MAE_end.
    """
    filepath = os.path.join(EVAL_DIR, "forecast_backtest_paired_v2.csv")
    rows = read_csv_rows(filepath)

    # Filter for D vs A
    filtered = [r for r in rows if r["comparison"] == "D vs A (Proposed vs Baseline)"]

    scenario_order = [
        ("volatile_outliers", "3. Thất thường/Outlier (Volatile)"),
        ("upward_trend", "2. Xu hướng tăng (Upward Trend)"),
        ("stable_noise", "1. Ổn định có nhiễu (Stable)"),
    ]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 5.5), sharey=True)
    fig.suptitle(
        "KIỂM ĐỊNH HIỆU SỐ THEO CẶP VÀ KHOẢNG TIN CẬY BOOTSTRAP 95%\n(Nhánh D: Đề xuất  vs  Nhánh A: Baseline)",
        fontsize=13,
        fontweight="bold",
        y=1.02,
    )

    for ax, metric, metric_title in [
        (ax1, "MAE_daily", "Hiệu số MAE_daily (Triệu VNĐ)"),
        (ax2, "MAE_end", "Hiệu số MAE_end (Triệu VNĐ)"),
    ]:
        ax.axvline(x=0, color="#7f8c8d", linestyle="--", linewidth=1.5, label="Ngưỡng tương đương (x = 0)")

        y_positions = range(len(scenario_order))
        for y_idx, (sc_key, _) in enumerate(scenario_order):
            item = next((r for r in filtered if r["scenario"] == sc_key and r["metric"] == metric), None)
            if not item:
                continue

            mean_diff = float(item["mean_diff"]) / 1e6
            ci_lower = float(item["ci_95_lower"]) / 1e6
            ci_upper = float(item["ci_95_upper"]) / 1e6
            win_rate = float(item["win_rate_pct"])

            is_benefit = mean_diff < 0
            point_color = "#27ae60" if is_benefit else "#c0392b"

            # Draw CI horizontal bar
            ax.plot([ci_lower, ci_upper], [y_idx, y_idx], color=point_color, linewidth=2.5, solid_capstyle="round")
            ax.plot([ci_lower, ci_lower], [y_idx - 0.08, y_idx + 0.08], color=point_color, linewidth=2)
            ax.plot([ci_upper, ci_upper], [y_idx - 0.08, y_idx + 0.08], color=point_color, linewidth=2)

            # Draw point estimate
            ax.plot(mean_diff, y_idx, marker="D", markersize=8, color=point_color, markeredgecolor="#1e8449" if is_benefit else "#922b21")

            # Annotate numerical text
            text_str = f"{mean_diff:+.3f}  [{ci_lower:.3f}, {ci_upper:.3f}]\nWin: {win_rate:.1f}%"
            ax.text(
                mean_diff,
                y_idx + 0.18,
                text_str,
                ha="center",
                va="bottom",
                fontsize=9.5,
                fontweight="bold",
                color=point_color,
                bbox=dict(boxstyle="round,pad=0.2", fc="#ffffff", ec=point_color, alpha=0.85, lw=0.8),
            )

        ax.set_title(metric_title, fontsize=11.5, fontweight="bold", pad=12)
        ax.set_yticks(range(len(scenario_order)))
        ax.set_yticklabels([label for _, label in scenario_order], fontsize=10.5, fontweight="medium")
        ax.grid(True, linestyle="--", alpha=0.45)
        ax.set_xlabel(r"$\Delta$ Sai số (Proposed - Baseline) [Triệu VNĐ]", fontsize=10.5, fontweight="bold")

        # Directional arrows at bottom
        ax.text(0.02, 0.03, "← Đề xuất (D) tốt hơn", transform=ax.transAxes, color="#27ae60", fontweight="bold", fontsize=9.5)
        ax.text(0.98, 0.03, "Baseline (A) tốt hơn →", transform=ax.transAxes, color="#c0392b", fontweight="bold", fontsize=9.5, ha="right")

    plt.tight_layout()
    out_path = os.path.join(CHARTS_DIR, "fig3_paired_bootstrap_ci.png")
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"[OK] Đã xuất {out_path}")


def main():
    print("Bắt đầu tạo các biểu đồ thực nghiệm đánh giá mô hình dòng tiền...")
    plot_fig1_ablation_mae()
    plot_fig2_alpha_sensitivity()
    plot_fig3_paired_bootstrap_ci()
    print("Hoàn tất xuất cả 3 biểu đồ vào thư mục:", CHARTS_DIR)


if __name__ == "__main__":
    main()

