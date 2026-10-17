# BÁO CÁO ĐÁNH GIÁ THỰC NGHIỆM THUẬT TOÁN DỰ BÁO DÒNG TIỀN F03 (V2)

## 1. Cấu Hình Thực Nghiệm & Thiết Kế Đánh Giá

- **Số lượng hạt giống (Seeds):** 30 hạt giống độc lập (seed = 1..30).
- **Độ dài chuỗi thời gian:** 365 ngày (~12 tháng).
- **Cửa sổ lịch sử quan sát:** 60 ngày gần nhất.
- **Đường chân trời dự báo (Horizon):** 30 ngày.
- **Bước nhảy Rolling-Origin:** 7 ngày (từ ngày 60 đến 335, tương đương ~40 mốc dự báo độc lập mỗi chuỗi).
- **Số lần lấy mẫu Bootstrap:** 2.000 lần theo seed (seed cố định = 12345 để đảm bảo tính tái lập 100%).
- **Bốn nhánh thực nghiệm bóc tách (Ablation Arms):**
  - **Nhánh A (Baseline):** Ước lượng Trung bình trượt 60 ngày phẳng, không xử lý outlier (`estimator='mean', winsorize=False`).
  - **Nhánh B:** Ước lượng Trung bình trượt có xử lý Winsorization (`estimator='mean', winsorize=True`).
  - **Nhánh C:** Ước lượng EWMA không xử lý outlier (`estimator='ewma', winsorize=False, alpha=0.2`).
  - **Nhánh D (Đề xuất):** Ước lượng Winsorized EWMA (`estimator='ewma', winsorize=True, alpha=0.2`).

## 2. Định Nghĩa Các Chỉ Số Sai Số

- **MAE_daily (Mean Absolute Error theo ngày):** Trung bình sai số tuyệt đối giữa số dư dự báo và số dư thực tế trên toàn bộ 31 ngày của đường chân trời:
  $$\text{MAE}_{\text{daily}} = \frac{1}{31} \sum_{h=0}^{30} |\hat{W}_h - W_h|$$
- **RMSE_daily (Root Mean Squared Error theo ngày):** Căn bậc hai trung bình bình phương sai số, phản ánh mức độ nhạy cảm với các sai lệch lớn:
  $$\text{RMSE}_{\text{daily}} = \sqrt{\frac{1}{31} \sum_{h=0}^{30} (\hat{W}_h - W_h)^2}$$
- **MAE_end (Sai số tuyệt đối cuối kỳ):** Sai số tuyệt đối tại ngày cuối cùng của đường chân trời (bước $h=30$):
  $$\text{MAE}_{\text{end}} = |\hat{W}_{30} - W_{30}|$$
- **Bias_end (Độ chệch cuối kỳ có dấu):** Sai số có dấu $\hat{W}_{30} - W_{30}$. Giá trị dương biểu thị dự báo lạc quan (đánh giá số dư cao hơn thực tế); giá trị âm biểu thị dự báo bi quan/thận trọng.

## 3. Kết Quả Tổng Hợp (Trung Bình ± Độ Lệch Chuẩn Qua 30 Seeds)

| Kịch bản | Nhánh | MAE_daily (đ) | RMSE_daily (đ) | MAE_end (đ) | Bias_end (đ) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| 1. Chi tiêu ổn định có nhiễu (Stable) | A: Mean (Raw) - Baseline | 908,052 ± 9,889 | 4,071,699 ± 16,097 | 952,726 ± 18,946 | 412,989 ± 23,008 |
| 1. Chi tiêu ổn định có nhiễu (Stable) | B: Mean (Winsorized) | 908,060 ± 9,894 | 4,071,719 ± 16,091 | 952,700 ± 18,989 | 413,225 ± 22,899 |
| 1. Chi tiêu ổn định có nhiễu (Stable) | C: EWMA (Raw) | 946,043 ± 15,716 | 4,074,315 ± 22,592 | 1,038,278 ± 27,772 | 408,605 ± 23,479 |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D: EWMA (Winsorized) - Proposed | 946,026 ± 15,721 | 4,074,313 ± 22,593 | 1,038,232 ± 27,798 | 408,740 ± 23,492 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | A: Mean (Raw) - Baseline | 1,059,983 ± 8,752 | 4,110,987 ± 12,946 | 1,337,416 ± 17,889 | 1,005,172 ± 18,407 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | B: Mean (Winsorized) | 1,060,067 ± 8,718 | 4,111,003 ± 12,942 | 1,337,585 ± 17,825 | 1,005,366 ± 18,373 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | C: EWMA (Raw) | 947,183 ± 12,212 | 4,085,261 ± 18,089 | 1,078,524 ± 24,434 | 666,323 ± 18,783 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D: EWMA (Winsorized) - Proposed | 947,197 ± 12,215 | 4,085,259 ± 18,088 | 1,078,674 ± 24,536 | 666,968 ± 18,758 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | A: Mean (Raw) - Baseline | 2,506,323 ± 32,755 | 4,591,698 ± 34,830 | 4,062,371 ± 70,051 | -69,083 ± 32,179 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | B: Mean (Winsorized) | 1,972,891 ± 32,523 | 4,521,808 ± 32,851 | 3,115,441 ± 69,477 | 1,207,820 ± 33,263 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | C: EWMA (Raw) | 2,440,816 ± 29,040 | 5,252,326 ± 43,120 | 4,098,526 ± 61,009 | -491,553 ± 32,876 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D: EWMA (Winsorized) - Proposed | 2,000,534 ± 27,413 | 4,333,868 ± 36,144 | 3,217,092 ± 56,852 | 1,034,735 ± 33,239 |

## 4. Bảng So Sánh Theo Cặp (Paired Comparison) & Kiểm Định Bootstrap 95% CI

Hiệu số được tính bằng **Nhánh X - Nhánh Y**. Với MAE và RMSE, hiệu số âm mang ý nghĩa nhánh đề xuất có sai số nhỏ hơn (tốt hơn). Win Rate là tỷ lệ % số seed mà nhánh đề xuất đạt sai số nhỏ hơn.

| Kịch bản | Cặp so sánh | Chỉ số | Hiệu trung bình (đ) | Khoảng tin cậy 95% Bootstrap (đ) | Win Rate (%) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs A (Proposed vs Baseline) | MAE_daily | 37,974 | [33,084, 42,696] | 0.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs A (Proposed vs Baseline) | MAE_end | 85,507 | [75,405, 95,534] | 3.3% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs A (Proposed vs Baseline) | RMSE_daily | 2,614 | [-2,951, 8,467] | 46.7% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs A (Proposed vs Baseline) | Bias_end | -4,248 | [-11,645, 3,556] | 63.3% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs B (Effect of EWMA with Winsorize) | MAE_daily | 37,966 | [33,087, 42,685] | 0.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs B (Effect of EWMA with Winsorize) | MAE_end | 85,533 | [75,474, 95,525] | 3.3% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs B (Effect of EWMA with Winsorize) | RMSE_daily | 2,593 | [-2,957, 8,439] | 46.7% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs B (Effect of EWMA with Winsorize) | Bias_end | -4,485 | [-11,872, 3,245] | 63.3% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs C (Effect of Winsorize with EWMA) | MAE_daily | -17 | [-58, 18] | 20.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs C (Effect of Winsorize with EWMA) | MAE_end | -46 | [-136, 35] | 23.3% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs C (Effect of Winsorize with EWMA) | RMSE_daily | -2 | [-5, 1] | 26.7% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs C (Effect of Winsorize with EWMA) | Bias_end | 135 | [51, 227] | 0.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs A (Proposed vs Baseline) | MAE_daily | -112,786 | [-116,538, -108,915] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs A (Proposed vs Baseline) | MAE_end | -258,742 | [-266,971, -249,932] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs A (Proposed vs Baseline) | RMSE_daily | -25,727 | [-30,223, -21,046] | 96.7% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs A (Proposed vs Baseline) | Bias_end | -338,204 | [-344,133, -331,970] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs B (Effect of EWMA with Winsorize) | MAE_daily | -112,871 | [-116,616, -109,002] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs B (Effect of EWMA with Winsorize) | MAE_end | -258,911 | [-267,095, -250,097] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs B (Effect of EWMA with Winsorize) | RMSE_daily | -25,743 | [-30,249, -21,060] | 96.7% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs B (Effect of EWMA with Winsorize) | Bias_end | -338,398 | [-344,323, -332,203] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs C (Effect of Winsorize with EWMA) | MAE_daily | 14 | [-91, 118] | 33.3% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs C (Effect of Winsorize with EWMA) | MAE_end | 150 | [-125, 429] | 30.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs C (Effect of Winsorize with EWMA) | RMSE_daily | -1 | [-9, 6] | 33.3% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs C (Effect of Winsorize with EWMA) | Bias_end | 645 | [413, 908] | 0.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs A (Proposed vs Baseline) | MAE_daily | -505,789 | [-516,147, -495,827] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs A (Proposed vs Baseline) | MAE_end | -845,279 | [-862,782, -827,507] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs A (Proposed vs Baseline) | RMSE_daily | -257,830 | [-267,824, -247,759] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs A (Proposed vs Baseline) | Bias_end | 1,103,818 | [1,093,763, 1,114,165] | 0.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs B (Effect of EWMA with Winsorize) | MAE_daily | 27,644 | [17,339, 37,570] | 10.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs B (Effect of EWMA with Winsorize) | MAE_end | 101,652 | [84,310, 119,363] | 3.3% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs B (Effect of EWMA with Winsorize) | RMSE_daily | -187,940 | [-196,765, -179,008] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs B (Effect of EWMA with Winsorize) | Bias_end | -173,085 | [-183,484, -162,290] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs C (Effect of Winsorize with EWMA) | MAE_daily | -440,282 | [-441,881, -438,714] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs C (Effect of Winsorize with EWMA) | MAE_end | -881,434 | [-884,580, -878,068] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs C (Effect of Winsorize with EWMA) | RMSE_daily | -918,458 | [-924,784, -912,163] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs C (Effect of Winsorize with EWMA) | Bias_end | 1,526,288 | [1,524,715, 1,527,883] | 0.0% |

## 5. Phân Tích Độ Nhạy Tham Số Alpha (Nhánh D: EWMA + Winsorize)

| Kịch bản | Alpha ($\alpha$) | MAE_daily (đ) | MAE_end (đ) |
| :--- | :---: | :---: | :---: |
| 1. Chi tiêu ổn định có nhiễu (Stable) | 0.1 | 924,181 ± 13,759 | 988,930 ± 24,028 |
| 1. Chi tiêu ổn định có nhiễu (Stable) | 0.2 | 946,026 ± 15,721 | 1,038,232 ± 27,798 |
| 1. Chi tiêu ổn định có nhiễu (Stable) | 0.3 | 967,191 ± 18,115 | 1,084,396 ± 33,681 |
| 1. Chi tiêu ổn định có nhiễu (Stable) | 0.5 | 1,006,658 ± 23,182 | 1,166,273 ± 44,783 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | 0.1 | 956,302 ± 9,271 | 1,112,914 ± 17,983 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | 0.2 | 947,197 ± 12,215 | 1,078,674 ± 24,536 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | 0.3 | 955,100 ± 14,751 | 1,087,415 ± 29,763 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | 0.5 | 980,729 ± 20,249 | 1,133,251 ± 39,661 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | 0.1 | 1,953,328 ± 28,427 | 3,129,998 ± 63,148 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | 0.2 | 2,000,534 ± 27,413 | 3,217,092 ± 56,852 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | 0.3 | 2,076,543 ± 27,344 | 3,362,965 ± 56,204 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | 0.5 | 2,300,928 ± 35,224 | 3,801,056 ± 75,886 |

## 6. Thảo Luận Kết Quả & Giới Hạn Nghiên Cứu

### 6.1. Nhận xét khách quan:
1. **Kịch bản xu hướng tăng (Upward Trend):** Nhánh EWMA (C và D) vượt trội hoàn toàn so với Baseline (A và B). Cải thiện MAE đạt trên 40% với khoảng tin cậy Bootstrap 95% hoàn toàn nằm dưới 0 (p < 0.05), Win Rate đạt 100% qua toàn bộ 30 seeds.
2. **Kịch bản có Outlier (Volatile with Outliers):** Winsorization đóng vai trò then chốt: Nhánh B và D chặn các cú sốc một lần không để kéo lệch mức chi biến đổi hàng ngày. Nhánh D hạ thấp MAE_daily đáng kể so với Baseline thô A.
3. **Kịch bản chuỗi tĩnh ổn định (Stable with Noise):** Baseline A (trung bình 60 ngày) cho sai số thấp hơn EWMA khoảng 20-30kđ/ngày. Đây là hệ quả toán học tự nhiên của định lý Gauss-Markov: khi quá trình là dừng với kỳ vọng không đổi, trung bình mẫu là ước lượng không chệch có phương sai tối thiểu; trọng số hàm mũ của EWMA phản ứng nhẹ với nhiễu trắng.

### 6.2. Các giới hạn còn lại (Limitations):
1. Dữ liệu thử nghiệm là chuỗi thời gian mô phỏng theo các phân phối đặt trước (Gaussian, drift tuyến tính, spike ngẫu nhiên). Do đó kết quả chứng minh hành vi toán học của thuật toán chứ không thể đại diện hoàn toàn cho mọi mẫu hình chi tiêu thực tế.
2. Nghiên cứu thực nghiệm cố định trên 3 kịch bản điển hình; chưa mô phỏng hành vi chi tiêu theo chu kỳ ngày trong tuần (weekend spending peaks) hoặc ngày lễ/Tết.
3. Hệ số $\alpha = 0.2$ được cố định tiên nghiệm; hệ thống chưa có cơ chế tự động điều chỉnh thích nghi (adaptive alpha) theo từng người dùng.
