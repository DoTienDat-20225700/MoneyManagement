# BÁO CÁO ĐÁNH GIÁ THỰC NGHIỆM THUẬT TOÁN DỰ BÁO DÒNG TIỀN F03 (V2)

## 1. Cấu Hình Thực Nghiệm & Thiết Kế Đánh Giá

- **Số seed mô phỏng cấu hình:** 10 hạt giống độc lập; split development. Số seed thực tế theo từng kịch bản được ghi ở mục 3.
- **Độ dài chuỗi mô phỏng:** 365 ngày.
- **Cửa sổ lịch sử quan sát:** 60 ngày gần nhất.
- **Đường chân trời dự báo (Horizon):** 30 ngày.
- **Bước nhảy Rolling-Origin:** 7 ngày, 40 cửa sổ chồng lấn mỗi chuỗi mô phỏng; horizon 30 ngày. Số cửa sổ của dữ liệu thực phụ thuộc độ dài chuỗi nhập.
- **Bootstrap 95% CI:** 2.000 lần lấy mẫu, random seed = 12345; mỗi seed là một đơn vị lấy mẫu độc lập. Chỉ số được tổng hợp qua các cửa sổ trong mỗi seed trước khi lấy sai khác theo cặp; không lấy mẫu riêng từng cửa sổ hoặc từng ngày.
  Các cửa sổ chồng lấn có phụ thuộc thời gian. CI phản ánh biến thiên giữa các chuỗi seed trong thiết kế này, không coi các cửa sổ là quan sát độc lập và không đại diện trực tiếp cho quần thể người dùng thực. Với dưới 2 seed, CI suy biến không đủ để kết luận ý nghĩa thống kê.
- **Tách dữ liệu:** seed phát triển 1000–1009; seed kiểm tra 0–29 (lần chạy này: [1000, 1001, 1002, 1003, 1004, 1005, 1006, 1007, 1008, 1009]). Chốt cấu hình trên development trước khi chạy test; không chọn lại cấu hình từ kết quả test. Alpha mỗi origin chỉ chọn từ lịch sử đến origin.
- **Chính sách thích nghi:** lưới ['0.02', '0.05', '0.1', '0.2', '0.3', '0.4', '0.5', '0.6'] + mean; tối thiểu 30 ngày; warm-up 21 ngày; MAE một bước trên mục tiêu thô; winsorize riêng từng fold. Warm-up được chọn bằng seed phát triển qua kiểm tra chuỗi tĩnh, không tối ưu theo seed kiểm tra. Lưới và ngưỡng tối thiểu được ấn định trước theo thiết kế.
- **Năm nhánh thực nghiệm bóc tách (Ablation Arms):**
  - **Nhánh A (Baseline):** Ước lượng Trung bình trượt 60 ngày phẳng, không xử lý outlier (`estimator='mean', winsorize=False`).
  - **Nhánh B:** Ước lượng Trung bình trượt có xử lý Winsorization (`estimator='mean', winsorize=True`).
  - **Nhánh C:** Ước lượng EWMA không xử lý outlier (`estimator='ewma', winsorize=False, alpha=0.2`).
  - **Nhánh D (Cố định):** Ước lượng Winsorized EWMA (`estimator='ewma', winsorize=True, alpha=0.2`).
  - **Nhánh E:** Mean/EWMA thích nghi + Winsorization; giữ mặc định ứng dụng là D.

## 2. Định Nghĩa Các Chỉ Số Sai Số

- **Quy ước origin:** Số dư tại origin là số dư cuối ngày; chỉ áp dụng sự kiện trong (origin, origin + horizon]. Step 0 bằng số dư quan sát và không được tính vào MAE_daily/RMSE_daily.
- **MAE_daily (Mean Absolute Error theo ngày):** Trung bình sai số tuyệt đối giữa số dư dự báo và số dư thực tế trên 30 ngày tương lai (h=1..30):
  $$\text{MAE}_{\text{daily}} = \frac{1}{30} \sum_{h=1}^{30} |\hat{W}_h - W_h|$$
- **RMSE_daily (Root Mean Squared Error theo ngày):** Căn bậc hai trung bình bình phương sai số, phản ánh mức độ nhạy cảm với các sai lệch lớn:
  $$\text{RMSE}_{\text{daily}} = \sqrt{\frac{1}{30} \sum_{h=1}^{30} (\hat{W}_h - W_h)^2}$$
- **MAE_end (Sai số tuyệt đối cuối kỳ):** Sai số tuyệt đối tại ngày cuối cùng của đường chân trời (bước $h=30$):
  $$\text{MAE}_{\text{end}} = |\hat{W}_{30} - W_{30}|$$
- **Bias_end (Độ chệch cuối kỳ có dấu):** Sai số có dấu $\hat{W}_{30} - W_{30}$. Giá trị dương biểu thị dự báo lạc quan (đánh giá số dư cao hơn thực tế); giá trị âm biểu thị dự báo bi quan/thận trọng.

## 3. Kết Quả Tổng Hợp (Trung Bình ± Độ Lệch Chuẩn Qua Các Seed)

Số seed theo từng kịch bản: 1. Chi tiêu ổn định có nhiễu (Stable): 10 seed; 2. Chi tiêu có xu hướng tăng (Upward Trend): 10 seed; 3. Chi tiêu thất thường có outlier (Volatile/Outlier): 10 seed; 4. Chi nhiều cuối tuần: 10 seed; 5. Thay đổi thói quen giữa chừng: 10 seed; 6. Chi tiêu thưa: 10 seed.

| Kịch bản | Nhánh | MAE_daily (đ) | RMSE_daily (đ) | MAE_end (đ) | Bias_end (đ) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| 1. Chi tiêu ổn định có nhiễu (Stable) | A: Mean (Raw) - Baseline | 91,996.05 ± 20,863.24 | 121,085.63 ± 28,264.34 | 149,537.49 ± 45,209.11 | -10,110.53 ± 14,233.90 |
| 1. Chi tiêu ổn định có nhiễu (Stable) | B: Mean (Winsorized) | 91,988.24 ± 20,853.23 | 121,073.82 ± 28,251.98 | 149,521.05 ± 45,184.30 | -9,925.49 ± 14,184.81 |
| 1. Chi tiêu ổn định có nhiễu (Stable) | C: EWMA (Raw) | 128,389.89 ± 13,876.19 | 177,235.27 ± 17,842.22 | 229,551.92 ± 28,467.47 | -14,250.19 ± 33,559.35 |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D: EWMA (Winsorized) - Fixed | 128,256.51 ± 14,029.42 | 176,931.70 ± 17,879.75 | 229,292.49 ± 28,524.22 | -13,989.41 ± 33,533.88 |
| 1. Chi tiêu ổn định có nhiễu (Stable) | E: Adaptive Mean/EWMA (Winsorized) | 104,785.75 ± 19,735.60 | 142,791.50 ± 26,914.69 | 177,963.04 ± 44,879.65 | -17,285.27 ± 26,104.04 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | A: Mean (Raw) - Baseline | 270,677.37 ± 5,206.95 | 334,253.65 ± 6,044.05 | 583,692.40 ± 11,387.11 | 583,692.40 ± 11,387.11 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | B: Mean (Winsorized) | 270,762.98 ± 5,144.55 | 334,330.65 ± 6,064.68 | 583,866.27 ± 11,346.19 | 583,866.27 ± 11,346.19 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | C: EWMA (Raw) | 131,621.40 ± 8,595.56 | 186,002.77 ± 10,966.03 | 277,109.34 ± 14,667.83 | 245,038.11 ± 26,847.48 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D: EWMA (Winsorized) - Fixed | 131,488.54 ± 8,745.37 | 185,883.21 ± 11,058.88 | 276,943.43 ± 14,894.09 | 245,640.41 ± 26,707.79 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | E: Adaptive Mean/EWMA (Winsorized) | 156,573.42 ± 11,344.00 | 213,708.64 ± 14,487.97 | 336,199.38 ± 28,364.27 | 307,584.37 ± 39,045.64 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | A: Mean (Raw) - Baseline | 1,789,763.73 ± 32,252.91 | 2,404,918.21 ± 49,419.92 | 3,347,567.94 ± 87,832.33 | -495,387.45 ± 19,895.14 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | B: Mean (Winsorized) | 1,196,916.70 ± 32,107.87 | 2,104,180.52 ± 51,053.67 | 2,320,016.52 ± 87,548.51 | 779,734.68 ± 21,533.34 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | C: EWMA (Raw) | 2,195,779.53 ± 33,630.64 | 4,977,465.55 ± 37,629.21 | 4,293,651.24 ± 83,015.74 | -917,538.79 ± 46,940.19 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D: EWMA (Winsorized) - Fixed | 1,418,611.67 ± 30,324.25 | 2,764,784.20 ± 39,070.44 | 2,788,172.36 ± 74,316.36 | 606,232.71 ± 47,896.13 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | E: Adaptive Mean/EWMA (Winsorized) | 1,111,436.81 ± 56,953.21 | 2,163,905.61 ± 118,137.65 | 2,199,019.09 ± 116,326.82 | 1,131,576.30 ± 102,265.91 |
| 4. Chi nhiều cuối tuần | A: Mean (Raw) - Baseline | 163,723.79 ± 13,142.37 | 202,801.07 ± 18,605.50 | 232,266.34 ± 26,076.53 | -210,110.53 ± 14,233.90 |
| 4. Chi nhiều cuối tuần | B: Mean (Winsorized) | 163,723.79 ± 13,142.37 | 202,801.07 ± 18,605.50 | 232,266.34 ± 26,076.53 | -210,110.53 ± 14,233.90 |
| 4. Chi nhiều cuối tuần | C: EWMA (Raw) | 341,332.12 ± 15,042.91 | 411,268.37 ± 19,648.65 | 604,417.51 ± 34,083.86 | -600,808.05 ± 33,559.35 |
| 4. Chi nhiều cuối tuần | D: EWMA (Winsorized) - Fixed | 341,332.12 ± 15,042.91 | 411,268.37 ± 19,648.65 | 604,417.51 ± 34,083.86 | -600,808.05 ± 33,559.35 |
| 4. Chi nhiều cuối tuần | E: Adaptive Mean/EWMA (Winsorized) | 175,168.05 ± 14,930.09 | 232,610.71 ± 27,468.08 | 251,948.19 ± 27,682.06 | -205,849.39 ± 22,849.71 |
| 5. Thay đổi thói quen giữa chừng | A: Mean (Raw) - Baseline | 620,388.27 ± 19,755.05 | 1,398,800.83 ± 36,088.04 | 1,301,419.40 ± 39,987.11 | 1,189,889.47 ± 14,233.90 |
| 5. Thay đổi thói quen giữa chừng | B: Mean (Winsorized) | 620,841.00 ± 19,742.99 | 1,400,338.35 ± 36,206.07 | 1,302,294.33 ± 39,947.39 | 1,190,965.88 ± 14,261.39 |
| 5. Thay đổi thói quen giữa chừng | C: EWMA (Raw) | 314,920.92 ± 14,034.64 | 849,698.97 ± 28,360.69 | 714,367.44 ± 24,693.76 | 500,993.72 ± 33,559.35 |
| 5. Thay đổi thói quen giữa chừng | D: EWMA (Winsorized) - Fixed | 318,561.56 ± 14,353.47 | 857,613.19 ± 29,861.19 | 721,412.56 ± 24,905.96 | 508,559.06 ± 33,330.52 |
| 5. Thay đổi thói quen giữa chừng | E: Adaptive Mean/EWMA (Winsorized) | 281,122.54 ± 18,354.57 | 810,309.88 ± 29,010.71 | 643,846.33 ± 42,283.12 | 435,442.07 ± 35,977.34 |
| 6. Chi tiêu thưa | A: Mean (Raw) - Baseline | 566,487.94 ± 61,007.93 | 761,520.40 ± 89,908.06 | 899,868.96 ± 157,518.25 | 10,597.69 ± 149,073.93 |
| 6. Chi tiêu thưa | B: Mean (Winsorized) | 569,511.75 ± 61,359.59 | 765,877.17 ± 90,561.20 | 906,398.37 ± 159,860.29 | 18,499.21 ± 148,735.14 |
| 6. Chi tiêu thưa | C: EWMA (Raw) | 815,235.05 ± 89,593.12 | 1,117,687.23 ± 121,794.57 | 1,443,453.82 ± 154,486.05 | 42,771.30 ± 204,020.56 |
| 6. Chi tiêu thưa | D: EWMA (Winsorized) - Fixed | 815,574.52 ± 89,896.53 | 1,117,892.17 ± 121,540.63 | 1,446,428.56 ± 150,969.90 | 51,276.99 ± 200,591.11 |
| 6. Chi tiêu thưa | E: Adaptive Mean/EWMA (Winsorized) | 792,159.88 ± 103,223.14 | 1,200,501.41 ± 253,006.60 | 1,397,101.15 ± 215,870.12 | 248,913.26 ± 303,604.53 |

## 4. Bảng So Sánh Theo Cặp (Paired Comparison) & Kiểm Định Bootstrap 95% CI

Hiệu số được tính bằng **Nhánh X - Nhánh Y**. Với MAE và RMSE, hiệu số âm mang ý nghĩa nhánh đề xuất có sai số nhỏ hơn (tốt hơn). Win Rate là tỷ lệ % số seed mà nhánh đề xuất đạt sai số nhỏ hơn.

| Kịch bản | Cặp so sánh | Chỉ số | Hiệu trung bình (đ) | Khoảng tin cậy 95% Bootstrap (đ) | Win Rate (%) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs A (Proposed vs Baseline) | MAE_daily | 36,260.46 | [25,271.57, 46,382.54] | 0.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs A (Proposed vs Baseline) | MAE_end | 79,755.00 | [60,159.59, 99,630.94] | 0.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs A (Proposed vs Baseline) | RMSE_daily | 55,846.07 | [45,097.17, 66,870.10] | 0.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs A (Proposed vs Baseline) | Bias_end | -3,878.88 | [-17,412.83, 12,034.05] | 40.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs B (Effect of EWMA with Winsorize) | MAE_daily | 36,268.27 | [25,306.40, 46,381.41] | 0.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs B (Effect of EWMA with Winsorize) | MAE_end | 79,771.44 | [60,185.99, 99,628.69] | 0.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs B (Effect of EWMA with Winsorize) | RMSE_daily | 55,857.88 | [45,124.23, 66,865.15] | 0.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs B (Effect of EWMA with Winsorize) | Bias_end | -4,063.92 | [-17,686.59, 11,824.37] | 30.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs C (Effect of Winsorize with EWMA) | MAE_daily | -133.38 | [-399.38, 0.07] | 30.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs C (Effect of Winsorize with EWMA) | MAE_end | -259.43 | [-776.84, 0.14] | 30.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs C (Effect of Winsorize with EWMA) | RMSE_daily | -303.56 | [-909.62, 0.08] | 30.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs C (Effect of Winsorize with EWMA) | Bias_end | 260.78 | [0.04, 780.20] | 40.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | E vs A (Adaptive vs Mean) | MAE_daily | 12,789.70 | [8,000.00, 18,069.05] | 0.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | E vs A (Adaptive vs Mean) | MAE_end | 28,425.55 | [18,720.86, 39,305.37] | 0.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | E vs A (Adaptive vs Mean) | RMSE_daily | 21,705.87 | [13,251.02, 32,101.09] | 0.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | E vs A (Adaptive vs Mean) | Bias_end | -7,174.74 | [-18,787.64, 4,799.85] | 40.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | E vs D (Adaptive vs Fixed EWMA) | MAE_daily | -23,470.76 | [-32,228.44, -15,157.39] | 90.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | E vs D (Adaptive vs Fixed EWMA) | MAE_end | -51,329.45 | [-69,146.82, -34,209.03] | 100.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | E vs D (Adaptive vs Fixed EWMA) | RMSE_daily | -34,140.20 | [-44,417.61, -25,643.73] | 100.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | E vs D (Adaptive vs Fixed EWMA) | Bias_end | -3,295.87 | [-17,340.15, 12,955.04] | 60.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs A (Proposed vs Baseline) | MAE_daily | -139,188.83 | [-144,263.50, -134,548.66] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs A (Proposed vs Baseline) | MAE_end | -306,748.97 | [-316,097.22, -298,002.79] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs A (Proposed vs Baseline) | RMSE_daily | -148,370.44 | [-153,962.38, -141,287.61] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs A (Proposed vs Baseline) | Bias_end | -338,052.00 | [-348,805.28, -325,379.83] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs B (Effect of EWMA with Winsorize) | MAE_daily | -139,274.44 | [-144,335.53, -134,636.20] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs B (Effect of EWMA with Winsorize) | MAE_end | -306,922.83 | [-316,178.78, -298,185.34] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs B (Effect of EWMA with Winsorize) | RMSE_daily | -148,447.44 | [-154,043.39, -141,383.97] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs B (Effect of EWMA with Winsorize) | Bias_end | -338,225.86 | [-348,940.69, -325,469.81] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs C (Effect of Winsorize with EWMA) | MAE_daily | -132.86 | [-393.26, 73.63] | 50.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs C (Effect of Winsorize with EWMA) | MAE_end | -165.91 | [-657.11, 242.91] | 40.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs C (Effect of Winsorize with EWMA) | RMSE_daily | -119.56 | [-442.15, 96.89] | 50.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs C (Effect of Winsorize with EWMA) | Bias_end | 602.29 | [202.78, 1,204.61] | 0.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | E vs A (Adaptive vs Mean) | MAE_daily | -114,103.95 | [-120,924.52, -106,473.45] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | E vs A (Adaptive vs Mean) | MAE_end | -247,493.02 | [-263,677.66, -229,029.78] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | E vs A (Adaptive vs Mean) | RMSE_daily | -120,545.01 | [-128,511.91, -111,688.37] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | E vs A (Adaptive vs Mean) | Bias_end | -276,108.03 | [-296,341.12, -252,026.31] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | E vs D (Adaptive vs Fixed EWMA) | MAE_daily | 25,084.88 | [20,296.07, 30,884.30] | 0.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | E vs D (Adaptive vs Fixed EWMA) | MAE_end | 59,255.95 | [48,580.76, 72,279.68] | 0.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | E vs D (Adaptive vs Fixed EWMA) | RMSE_daily | 27,825.42 | [22,989.01, 33,946.59] | 0.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | E vs D (Adaptive vs Fixed EWMA) | Bias_end | 61,943.97 | [46,685.65, 79,882.89] | 0.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs A (Proposed vs Baseline) | MAE_daily | -371,152.06 | [-387,571.16, -353,973.22] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs A (Proposed vs Baseline) | MAE_end | -559,395.57 | [-587,469.24, -530,621.12] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs A (Proposed vs Baseline) | RMSE_daily | 359,865.99 | [337,892.97, 382,763.50] | 0.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs A (Proposed vs Baseline) | Bias_end | 1,101,620.15 | [1,082,138.69, 1,122,627.14] | 0.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs B (Effect of EWMA with Winsorize) | MAE_daily | 221,694.97 | [205,567.39, 238,371.30] | 0.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs B (Effect of EWMA with Winsorize) | MAE_end | 468,155.84 | [440,571.01, 497,123.81] | 0.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs B (Effect of EWMA with Winsorize) | RMSE_daily | 660,603.69 | [638,613.53, 683,339.63] | 0.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs B (Effect of EWMA with Winsorize) | Bias_end | -173,501.97 | [-192,405.17, -152,060.65] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs C (Effect of Winsorize with EWMA) | MAE_daily | -777,167.86 | [-780,556.55, -773,849.09] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs C (Effect of Winsorize with EWMA) | MAE_end | -1,505,478.87 | [-1,512,902.78, -1,498,183.86] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs C (Effect of Winsorize with EWMA) | RMSE_daily | -2,212,681.35 | [-2,223,303.92, -2,201,982.31] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs C (Effect of Winsorize with EWMA) | Bias_end | 1,523,771.49 | [1,518,930.86, 1,528,282.95] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | E vs A (Adaptive vs Mean) | MAE_daily | -678,326.92 | [-703,694.81, -650,632.62] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | E vs A (Adaptive vs Mean) | MAE_end | -1,148,548.85 | [-1,193,501.65, -1,096,974.42] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | E vs A (Adaptive vs Mean) | RMSE_daily | -241,012.60 | [-283,575.28, -173,698.24] | 90.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | E vs A (Adaptive vs Mean) | Bias_end | 1,626,963.74 | [1,554,595.74, 1,682,323.92] | 0.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | E vs D (Adaptive vs Fixed EWMA) | MAE_daily | -307,174.86 | [-334,683.94, -274,260.56] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | E vs D (Adaptive vs Fixed EWMA) | MAE_end | -589,153.27 | [-637,183.88, -531,890.01] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | E vs D (Adaptive vs Fixed EWMA) | RMSE_daily | -600,878.59 | [-651,295.94, -523,825.99] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | E vs D (Adaptive vs Fixed EWMA) | Bias_end | 525,343.59 | [452,138.88, 585,439.31] | 0.0% |
| 4. Chi nhiều cuối tuần | D vs A (Proposed vs Baseline) | MAE_daily | 177,608.32 | [170,801.17, 184,514.19] | 0.0% |
| 4. Chi nhiều cuối tuần | D vs A (Proposed vs Baseline) | MAE_end | 372,151.16 | [358,148.74, 386,691.75] | 0.0% |
| 4. Chi nhiều cuối tuần | D vs A (Proposed vs Baseline) | RMSE_daily | 208,467.30 | [201,130.89, 215,620.37] | 0.0% |
| 4. Chi nhiều cuối tuần | D vs A (Proposed vs Baseline) | Bias_end | -390,697.52 | [-404,338.05, -374,838.23] | 0.0% |
| 4. Chi nhiều cuối tuần | D vs B (Effect of EWMA with Winsorize) | MAE_daily | 177,608.32 | [170,801.17, 184,514.19] | 0.0% |
| 4. Chi nhiều cuối tuần | D vs B (Effect of EWMA with Winsorize) | MAE_end | 372,151.16 | [358,148.74, 386,691.75] | 0.0% |
| 4. Chi nhiều cuối tuần | D vs B (Effect of EWMA with Winsorize) | RMSE_daily | 208,467.30 | [201,130.89, 215,620.37] | 0.0% |
| 4. Chi nhiều cuối tuần | D vs B (Effect of EWMA with Winsorize) | Bias_end | -390,697.52 | [-404,338.05, -374,838.23] | 0.0% |
| 4. Chi nhiều cuối tuần | D vs C (Effect of Winsorize with EWMA) | MAE_daily | 0.00 | [0.00, 0.00] | 0.0% |
| 4. Chi nhiều cuối tuần | D vs C (Effect of Winsorize with EWMA) | MAE_end | 0.00 | [0.00, 0.00] | 0.0% |
| 4. Chi nhiều cuối tuần | D vs C (Effect of Winsorize with EWMA) | RMSE_daily | 0.00 | [0.00, 0.00] | 0.0% |
| 4. Chi nhiều cuối tuần | D vs C (Effect of Winsorize with EWMA) | Bias_end | 0.00 | [0.00, 0.00] | 0.0% |
| 4. Chi nhiều cuối tuần | E vs A (Adaptive vs Mean) | MAE_daily | 11,444.26 | [3,032.42, 20,329.59] | 30.0% |
| 4. Chi nhiều cuối tuần | E vs A (Adaptive vs Mean) | MAE_end | 19,681.84 | [2,920.34, 36,634.47] | 30.0% |
| 4. Chi nhiều cuối tuần | E vs A (Adaptive vs Mean) | RMSE_daily | 29,809.64 | [12,893.87, 47,176.10] | 20.0% |
| 4. Chi nhiều cuối tuần | E vs A (Adaptive vs Mean) | Bias_end | 4,261.14 | [-10,448.85, 18,332.35] | 50.0% |
| 4. Chi nhiều cuối tuần | E vs D (Adaptive vs Fixed EWMA) | MAE_daily | -166,164.07 | [-175,128.30, -157,529.78] | 100.0% |
| 4. Chi nhiều cuối tuần | E vs D (Adaptive vs Fixed EWMA) | MAE_end | -352,469.32 | [-371,621.24, -331,850.34] | 100.0% |
| 4. Chi nhiều cuối tuần | E vs D (Adaptive vs Fixed EWMA) | RMSE_daily | -178,657.66 | [-194,261.32, -162,837.09] | 100.0% |
| 4. Chi nhiều cuối tuần | E vs D (Adaptive vs Fixed EWMA) | Bias_end | 394,958.66 | [371,712.94, 415,579.60] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | D vs A (Proposed vs Baseline) | MAE_daily | -301,826.71 | [-312,727.12, -290,230.10] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | D vs A (Proposed vs Baseline) | MAE_end | -580,006.84 | [-600,939.55, -555,150.44] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | D vs A (Proposed vs Baseline) | RMSE_daily | -541,187.64 | [-555,955.45, -526,121.82] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | D vs A (Proposed vs Baseline) | Bias_end | -681,330.41 | [-694,656.38, -666,027.22] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | D vs B (Effect of EWMA with Winsorize) | MAE_daily | -302,279.44 | [-313,126.41, -290,664.04] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | D vs B (Effect of EWMA with Winsorize) | MAE_end | -580,881.76 | [-601,773.00, -556,115.73] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | D vs B (Effect of EWMA with Winsorize) | RMSE_daily | -542,725.16 | [-557,333.22, -527,783.66] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | D vs B (Effect of EWMA with Winsorize) | Bias_end | -682,406.82 | [-695,677.25, -667,027.93] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | D vs C (Effect of Winsorize with EWMA) | MAE_daily | 3,640.64 | [2,908.63, 4,386.42] | 0.0% |
| 5. Thay đổi thói quen giữa chừng | D vs C (Effect of Winsorize with EWMA) | MAE_end | 7,045.12 | [5,625.77, 8,489.84] | 0.0% |
| 5. Thay đổi thói quen giữa chừng | D vs C (Effect of Winsorize with EWMA) | RMSE_daily | 7,914.22 | [6,597.01, 9,180.15] | 0.0% |
| 5. Thay đổi thói quen giữa chừng | D vs C (Effect of Winsorize with EWMA) | Bias_end | 7,565.34 | [6,246.05, 8,871.95] | 0.0% |
| 5. Thay đổi thói quen giữa chừng | E vs A (Adaptive vs Mean) | MAE_daily | -339,265.74 | [-349,591.17, -327,297.14] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | E vs A (Adaptive vs Mean) | MAE_end | -657,573.07 | [-678,855.21, -633,122.10] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | E vs A (Adaptive vs Mean) | RMSE_daily | -588,490.95 | [-601,019.06, -575,675.43] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | E vs A (Adaptive vs Mean) | Bias_end | -754,447.41 | [-775,001.74, -732,893.96] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | E vs D (Adaptive vs Fixed EWMA) | MAE_daily | -37,439.03 | [-48,015.94, -26,888.24] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | E vs D (Adaptive vs Fixed EWMA) | MAE_end | -77,566.23 | [-100,537.46, -56,318.30] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | E vs D (Adaptive vs Fixed EWMA) | RMSE_daily | -47,303.30 | [-54,321.00, -41,125.60] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | E vs D (Adaptive vs Fixed EWMA) | Bias_end | -73,116.99 | [-97,595.71, -48,854.07] | 100.0% |
| 6. Chi tiêu thưa | D vs A (Proposed vs Baseline) | MAE_daily | 249,086.58 | [186,116.51, 313,700.86] | 0.0% |
| 6. Chi tiêu thưa | D vs A (Proposed vs Baseline) | MAE_end | 546,559.60 | [406,981.55, 689,578.30] | 0.0% |
| 6. Chi tiêu thưa | D vs A (Proposed vs Baseline) | RMSE_daily | 356,371.77 | [270,380.65, 443,268.84] | 0.0% |
| 6. Chi tiêu thưa | D vs A (Proposed vs Baseline) | Bias_end | 40,679.30 | [-57,029.31, 138,125.60] | 20.0% |
| 6. Chi tiêu thưa | D vs B (Effect of EWMA with Winsorize) | MAE_daily | 246,062.77 | [180,982.28, 312,025.53] | 0.0% |
| 6. Chi tiêu thưa | D vs B (Effect of EWMA with Winsorize) | MAE_end | 540,030.19 | [395,318.63, 684,963.75] | 0.0% |
| 6. Chi tiêu thưa | D vs B (Effect of EWMA with Winsorize) | RMSE_daily | 352,015.00 | [264,635.41, 439,599.87] | 0.0% |
| 6. Chi tiêu thưa | D vs B (Effect of EWMA with Winsorize) | Bias_end | 32,777.78 | [-64,382.81, 130,774.79] | 20.0% |
| 6. Chi tiêu thưa | D vs C (Effect of Winsorize with EWMA) | MAE_daily | 339.46 | [-1,166.97, 1,660.76] | 30.0% |
| 6. Chi tiêu thưa | D vs C (Effect of Winsorize with EWMA) | MAE_end | 2,974.74 | [519.08, 5,918.52] | 20.0% |
| 6. Chi tiêu thưa | D vs C (Effect of Winsorize with EWMA) | RMSE_daily | 204.95 | [-1,171.12, 1,677.52] | 30.0% |
| 6. Chi tiêu thưa | D vs C (Effect of Winsorize with EWMA) | Bias_end | 8,505.69 | [2,452.58, 17,415.51] | 50.0% |
| 6. Chi tiêu thưa | E vs A (Adaptive vs Mean) | MAE_daily | 225,671.94 | [170,911.20, 280,861.54] | 0.0% |
| 6. Chi tiêu thưa | E vs A (Adaptive vs Mean) | MAE_end | 497,232.19 | [384,923.06, 602,448.04] | 0.0% |
| 6. Chi tiêu thưa | E vs A (Adaptive vs Mean) | RMSE_daily | 438,981.01 | [306,345.07, 587,771.03] | 0.0% |
| 6. Chi tiêu thưa | E vs A (Adaptive vs Mean) | Bias_end | 238,315.57 | [78,128.31, 389,084.36] | 10.0% |
| 6. Chi tiêu thưa | E vs D (Adaptive vs Fixed EWMA) | MAE_daily | -23,414.64 | [-84,112.83, 38,686.20] | 70.0% |
| 6. Chi tiêu thưa | E vs D (Adaptive vs Fixed EWMA) | MAE_end | -49,327.41 | [-176,243.43, 72,703.45] | 60.0% |
| 6. Chi tiêu thưa | E vs D (Adaptive vs Fixed EWMA) | RMSE_daily | 82,609.24 | [-57,252.41, 222,815.02] | 50.0% |
| 6. Chi tiêu thưa | E vs D (Adaptive vs Fixed EWMA) | Bias_end | 197,636.27 | [90,440.81, 289,497.21] | 20.0% |

## 5. Phân Tích Độ Nhạy Tham Số Alpha (Nhánh D: EWMA + Winsorize)

| Kịch bản | Alpha ($\alpha$) | MAE_daily (đ) | MAE_end (đ) |
| :--- | :---: | :---: | :---: |
| 1. Chi tiêu ổn định có nhiễu (Stable) | 0.1 | 105,283 ± 13,486 | 181,375 ± 32,085 |
| 1. Chi tiêu ổn định có nhiễu (Stable) | 0.2 | 128,257 ± 14,029 | 229,292 ± 28,524 |
| 1. Chi tiêu ổn định có nhiễu (Stable) | 0.3 | 152,435 ± 14,461 | 278,218 ± 26,411 |
| 1. Chi tiêu ổn định có nhiễu (Stable) | 0.5 | 203,603 ± 14,618 | 380,318 ± 29,039 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | 0.1 | 143,928 ± 7,203 | 319,607 ± 16,671 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | 0.2 | 131,489 ± 8,745 | 276,943 ± 14,894 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | 0.3 | 140,888 ± 10,443 | 287,163 ± 17,156 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | 0.5 | 174,401 ± 10,277 | 344,125 ± 19,614 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | 0.1 | 1,288,236 ± 28,397 | 2,546,348 ± 82,532 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | 0.2 | 1,418,612 ± 30,324 | 2,788,172 ± 74,316 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | 0.3 | 1,537,304 ± 35,129 | 3,013,060 ± 80,161 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | 0.5 | 1,739,370 ± 36,130 | 3,394,990 ± 76,099 |
| 4. Chi nhiều cuối tuần | 0.1 | 233,679 ± 10,881 | 385,167 ± 25,862 |
| 4. Chi nhiều cuối tuần | 0.2 | 341,332 ± 15,043 | 604,418 ± 34,084 |
| 4. Chi nhiều cuối tuần | 0.3 | 418,317 ± 20,146 | 755,914 ± 43,011 |
| 4. Chi nhiều cuối tuần | 0.5 | 399,502 ± 24,902 | 715,588 ± 52,630 |
| 5. Thay đổi thói quen giữa chừng | 0.1 | 359,901 ± 13,085 | 798,835 ± 26,810 |
| 5. Thay đổi thói quen giữa chừng | 0.2 | 318,562 ± 14,353 | 721,413 ± 24,906 |
| 5. Thay đổi thói quen giữa chừng | 0.3 | 322,624 ± 15,161 | 729,850 ± 24,161 |
| 5. Thay đổi thói quen giữa chừng | 0.5 | 357,498 ± 13,313 | 798,633 ± 24,974 |
| 6. Chi tiêu thưa | 0.1 | 673,335 ± 65,872 | 1,131,143 ± 110,227 |
| 6. Chi tiêu thưa | 0.2 | 815,575 ± 89,897 | 1,446,429 ± 150,970 |
| 6. Chi tiêu thưa | 0.3 | 958,673 ± 115,791 | 1,749,437 ± 219,703 |
| 6. Chi tiêu thưa | 0.5 | 1,237,626 ± 142,451 | 2,313,527 ± 283,652 |

## 6. Thảo Luận Kết Quả & Giới Hạn Nghiên Cứu

### 6.1. Nhận xét khách quan:

Cải thiện = (tham chiếu - nhánh đang xét) / tham chiếu × 100; giá trị âm nghĩa là nhánh đang xét có sai số cao hơn. A là baseline; B và C là các nhánh đối chiếu ablation. Kết luận dựa trên CI của hiệu nhánh đang xét - tham chiếu, không suy ra p-value. Bias_end là sai số có dấu nên không dùng dấu CI của Bias_end để kết luận tốt/kém.

- **1. Chi tiêu ổn định có nhiễu (Stable) — D vs A, MAE_daily:** Cải thiện: -39.42%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 36,260.46 đ; CI 95%: [25,271.57, 46,382.54] đ. Kết luận: kém hơn.
- **1. Chi tiêu ổn định có nhiễu (Stable) — D vs A, MAE_end:** Cải thiện: -53.33%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 79,755.00 đ; CI 95%: [60,159.59, 99,630.94] đ. Kết luận: kém hơn.
- **1. Chi tiêu ổn định có nhiễu (Stable) — D vs A, RMSE_daily:** Cải thiện: -46.12%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 55,846.07 đ; CI 95%: [45,097.17, 66,870.10] đ. Kết luận: kém hơn.
- **1. Chi tiêu ổn định có nhiễu (Stable) — D vs B, MAE_daily:** Cải thiện: -39.43%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 36,268.27 đ; CI 95%: [25,306.40, 46,381.41] đ. Kết luận: kém hơn.
- **1. Chi tiêu ổn định có nhiễu (Stable) — D vs B, MAE_end:** Cải thiện: -53.35%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 79,771.44 đ; CI 95%: [60,185.99, 99,628.69] đ. Kết luận: kém hơn.
- **1. Chi tiêu ổn định có nhiễu (Stable) — D vs B, RMSE_daily:** Cải thiện: -46.14%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 55,857.88 đ; CI 95%: [45,124.23, 66,865.15] đ. Kết luận: kém hơn.
- **1. Chi tiêu ổn định có nhiễu (Stable) — D vs C, MAE_daily:** Cải thiện: 0.10%; Win Rate: 30.0% (10 seed); hiệu trung bình D - tham chiếu: -133.38 đ; CI 95%: [-399.38, 0.07] đ. Kết luận: chưa kết luận được.
- **1. Chi tiêu ổn định có nhiễu (Stable) — D vs C, MAE_end:** Cải thiện: 0.11%; Win Rate: 30.0% (10 seed); hiệu trung bình D - tham chiếu: -259.43 đ; CI 95%: [-776.84, 0.14] đ. Kết luận: chưa kết luận được.
- **1. Chi tiêu ổn định có nhiễu (Stable) — D vs C, RMSE_daily:** Cải thiện: 0.17%; Win Rate: 30.0% (10 seed); hiệu trung bình D - tham chiếu: -303.56 đ; CI 95%: [-909.62, 0.08] đ. Kết luận: chưa kết luận được.
- **1. Chi tiêu ổn định có nhiễu (Stable) — E vs A, MAE_daily:** Cải thiện: -13.90%; Win Rate: 0.0% (10 seed); hiệu trung bình E - tham chiếu: 12,789.70 đ; CI 95%: [8,000.00, 18,069.05] đ. Kết luận: kém hơn.
- **1. Chi tiêu ổn định có nhiễu (Stable) — E vs A, MAE_end:** Cải thiện: -19.01%; Win Rate: 0.0% (10 seed); hiệu trung bình E - tham chiếu: 28,425.55 đ; CI 95%: [18,720.86, 39,305.37] đ. Kết luận: kém hơn.
- **1. Chi tiêu ổn định có nhiễu (Stable) — E vs A, RMSE_daily:** Cải thiện: -17.93%; Win Rate: 0.0% (10 seed); hiệu trung bình E - tham chiếu: 21,705.87 đ; CI 95%: [13,251.02, 32,101.09] đ. Kết luận: kém hơn.
- **1. Chi tiêu ổn định có nhiễu (Stable) — E vs D, MAE_daily:** Cải thiện: 18.30%; Win Rate: 90.0% (10 seed); hiệu trung bình E - tham chiếu: -23,470.76 đ; CI 95%: [-32,228.44, -15,157.39] đ. Kết luận: tốt hơn có ý nghĩa.
- **1. Chi tiêu ổn định có nhiễu (Stable) — E vs D, MAE_end:** Cải thiện: 22.39%; Win Rate: 100.0% (10 seed); hiệu trung bình E - tham chiếu: -51,329.45 đ; CI 95%: [-69,146.82, -34,209.03] đ. Kết luận: tốt hơn có ý nghĩa.
- **1. Chi tiêu ổn định có nhiễu (Stable) — E vs D, RMSE_daily:** Cải thiện: 19.30%; Win Rate: 100.0% (10 seed); hiệu trung bình E - tham chiếu: -34,140.20 đ; CI 95%: [-44,417.61, -25,643.73] đ. Kết luận: tốt hơn có ý nghĩa.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — D vs A, MAE_daily:** Cải thiện: 51.42%; Win Rate: 100.0% (10 seed); hiệu trung bình D - tham chiếu: -139,188.83 đ; CI 95%: [-144,263.50, -134,548.66] đ. Kết luận: tốt hơn có ý nghĩa.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — D vs A, MAE_end:** Cải thiện: 52.55%; Win Rate: 100.0% (10 seed); hiệu trung bình D - tham chiếu: -306,748.97 đ; CI 95%: [-316,097.22, -298,002.79] đ. Kết luận: tốt hơn có ý nghĩa.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — D vs A, RMSE_daily:** Cải thiện: 44.39%; Win Rate: 100.0% (10 seed); hiệu trung bình D - tham chiếu: -148,370.44 đ; CI 95%: [-153,962.38, -141,287.61] đ. Kết luận: tốt hơn có ý nghĩa.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — D vs B, MAE_daily:** Cải thiện: 51.44%; Win Rate: 100.0% (10 seed); hiệu trung bình D - tham chiếu: -139,274.44 đ; CI 95%: [-144,335.53, -134,636.20] đ. Kết luận: tốt hơn có ý nghĩa.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — D vs B, MAE_end:** Cải thiện: 52.57%; Win Rate: 100.0% (10 seed); hiệu trung bình D - tham chiếu: -306,922.83 đ; CI 95%: [-316,178.78, -298,185.34] đ. Kết luận: tốt hơn có ý nghĩa.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — D vs B, RMSE_daily:** Cải thiện: 44.40%; Win Rate: 100.0% (10 seed); hiệu trung bình D - tham chiếu: -148,447.44 đ; CI 95%: [-154,043.39, -141,383.97] đ. Kết luận: tốt hơn có ý nghĩa.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — D vs C, MAE_daily:** Cải thiện: 0.10%; Win Rate: 50.0% (10 seed); hiệu trung bình D - tham chiếu: -132.86 đ; CI 95%: [-393.26, 73.63] đ. Kết luận: chưa kết luận được.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — D vs C, MAE_end:** Cải thiện: 0.06%; Win Rate: 40.0% (10 seed); hiệu trung bình D - tham chiếu: -165.91 đ; CI 95%: [-657.11, 242.91] đ. Kết luận: chưa kết luận được.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — D vs C, RMSE_daily:** Cải thiện: 0.06%; Win Rate: 50.0% (10 seed); hiệu trung bình D - tham chiếu: -119.56 đ; CI 95%: [-442.15, 96.89] đ. Kết luận: chưa kết luận được.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — E vs A, MAE_daily:** Cải thiện: 42.15%; Win Rate: 100.0% (10 seed); hiệu trung bình E - tham chiếu: -114,103.95 đ; CI 95%: [-120,924.52, -106,473.45] đ. Kết luận: tốt hơn có ý nghĩa.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — E vs A, MAE_end:** Cải thiện: 42.40%; Win Rate: 100.0% (10 seed); hiệu trung bình E - tham chiếu: -247,493.02 đ; CI 95%: [-263,677.66, -229,029.78] đ. Kết luận: tốt hơn có ý nghĩa.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — E vs A, RMSE_daily:** Cải thiện: 36.06%; Win Rate: 100.0% (10 seed); hiệu trung bình E - tham chiếu: -120,545.01 đ; CI 95%: [-128,511.91, -111,688.37] đ. Kết luận: tốt hơn có ý nghĩa.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — E vs D, MAE_daily:** Cải thiện: -19.08%; Win Rate: 0.0% (10 seed); hiệu trung bình E - tham chiếu: 25,084.88 đ; CI 95%: [20,296.07, 30,884.30] đ. Kết luận: kém hơn.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — E vs D, MAE_end:** Cải thiện: -21.40%; Win Rate: 0.0% (10 seed); hiệu trung bình E - tham chiếu: 59,255.95 đ; CI 95%: [48,580.76, 72,279.68] đ. Kết luận: kém hơn.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — E vs D, RMSE_daily:** Cải thiện: -14.97%; Win Rate: 0.0% (10 seed); hiệu trung bình E - tham chiếu: 27,825.42 đ; CI 95%: [22,989.01, 33,946.59] đ. Kết luận: kém hơn.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — D vs A, MAE_daily:** Cải thiện: 20.74%; Win Rate: 100.0% (10 seed); hiệu trung bình D - tham chiếu: -371,152.06 đ; CI 95%: [-387,571.16, -353,973.22] đ. Kết luận: tốt hơn có ý nghĩa.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — D vs A, MAE_end:** Cải thiện: 16.71%; Win Rate: 100.0% (10 seed); hiệu trung bình D - tham chiếu: -559,395.57 đ; CI 95%: [-587,469.24, -530,621.12] đ. Kết luận: tốt hơn có ý nghĩa.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — D vs A, RMSE_daily:** Cải thiện: -14.96%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 359,865.99 đ; CI 95%: [337,892.97, 382,763.50] đ. Kết luận: kém hơn.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — D vs B, MAE_daily:** Cải thiện: -18.52%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 221,694.97 đ; CI 95%: [205,567.39, 238,371.30] đ. Kết luận: kém hơn.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — D vs B, MAE_end:** Cải thiện: -20.18%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 468,155.84 đ; CI 95%: [440,571.01, 497,123.81] đ. Kết luận: kém hơn.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — D vs B, RMSE_daily:** Cải thiện: -31.39%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 660,603.69 đ; CI 95%: [638,613.53, 683,339.63] đ. Kết luận: kém hơn.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — D vs C, MAE_daily:** Cải thiện: 35.39%; Win Rate: 100.0% (10 seed); hiệu trung bình D - tham chiếu: -777,167.86 đ; CI 95%: [-780,556.55, -773,849.09] đ. Kết luận: tốt hơn có ý nghĩa.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — D vs C, MAE_end:** Cải thiện: 35.06%; Win Rate: 100.0% (10 seed); hiệu trung bình D - tham chiếu: -1,505,478.87 đ; CI 95%: [-1,512,902.78, -1,498,183.86] đ. Kết luận: tốt hơn có ý nghĩa.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — D vs C, RMSE_daily:** Cải thiện: 44.45%; Win Rate: 100.0% (10 seed); hiệu trung bình D - tham chiếu: -2,212,681.35 đ; CI 95%: [-2,223,303.92, -2,201,982.31] đ. Kết luận: tốt hơn có ý nghĩa.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — E vs A, MAE_daily:** Cải thiện: 37.90%; Win Rate: 100.0% (10 seed); hiệu trung bình E - tham chiếu: -678,326.92 đ; CI 95%: [-703,694.81, -650,632.62] đ. Kết luận: tốt hơn có ý nghĩa.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — E vs A, MAE_end:** Cải thiện: 34.31%; Win Rate: 100.0% (10 seed); hiệu trung bình E - tham chiếu: -1,148,548.85 đ; CI 95%: [-1,193,501.65, -1,096,974.42] đ. Kết luận: tốt hơn có ý nghĩa.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — E vs A, RMSE_daily:** Cải thiện: 10.02%; Win Rate: 90.0% (10 seed); hiệu trung bình E - tham chiếu: -241,012.60 đ; CI 95%: [-283,575.28, -173,698.24] đ. Kết luận: tốt hơn có ý nghĩa.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — E vs D, MAE_daily:** Cải thiện: 21.65%; Win Rate: 100.0% (10 seed); hiệu trung bình E - tham chiếu: -307,174.86 đ; CI 95%: [-334,683.94, -274,260.56] đ. Kết luận: tốt hơn có ý nghĩa.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — E vs D, MAE_end:** Cải thiện: 21.13%; Win Rate: 100.0% (10 seed); hiệu trung bình E - tham chiếu: -589,153.27 đ; CI 95%: [-637,183.88, -531,890.01] đ. Kết luận: tốt hơn có ý nghĩa.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — E vs D, RMSE_daily:** Cải thiện: 21.73%; Win Rate: 100.0% (10 seed); hiệu trung bình E - tham chiếu: -600,878.59 đ; CI 95%: [-651,295.94, -523,825.99] đ. Kết luận: tốt hơn có ý nghĩa.
- **4. Chi nhiều cuối tuần — D vs A, MAE_daily:** Cải thiện: -108.48%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 177,608.32 đ; CI 95%: [170,801.17, 184,514.19] đ. Kết luận: kém hơn.
- **4. Chi nhiều cuối tuần — D vs A, MAE_end:** Cải thiện: -160.23%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 372,151.16 đ; CI 95%: [358,148.74, 386,691.75] đ. Kết luận: kém hơn.
- **4. Chi nhiều cuối tuần — D vs A, RMSE_daily:** Cải thiện: -102.79%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 208,467.30 đ; CI 95%: [201,130.89, 215,620.37] đ. Kết luận: kém hơn.
- **4. Chi nhiều cuối tuần — D vs B, MAE_daily:** Cải thiện: -108.48%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 177,608.32 đ; CI 95%: [170,801.17, 184,514.19] đ. Kết luận: kém hơn.
- **4. Chi nhiều cuối tuần — D vs B, MAE_end:** Cải thiện: -160.23%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 372,151.16 đ; CI 95%: [358,148.74, 386,691.75] đ. Kết luận: kém hơn.
- **4. Chi nhiều cuối tuần — D vs B, RMSE_daily:** Cải thiện: -102.79%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 208,467.30 đ; CI 95%: [201,130.89, 215,620.37] đ. Kết luận: kém hơn.
- **4. Chi nhiều cuối tuần — D vs C, MAE_daily:** Cải thiện: 0.00%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 0.00 đ; CI 95%: [0.00, 0.00] đ. Kết luận: chưa kết luận được.
- **4. Chi nhiều cuối tuần — D vs C, MAE_end:** Cải thiện: 0.00%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 0.00 đ; CI 95%: [0.00, 0.00] đ. Kết luận: chưa kết luận được.
- **4. Chi nhiều cuối tuần — D vs C, RMSE_daily:** Cải thiện: 0.00%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 0.00 đ; CI 95%: [0.00, 0.00] đ. Kết luận: chưa kết luận được.
- **4. Chi nhiều cuối tuần — E vs A, MAE_daily:** Cải thiện: -6.99%; Win Rate: 30.0% (10 seed); hiệu trung bình E - tham chiếu: 11,444.26 đ; CI 95%: [3,032.42, 20,329.59] đ. Kết luận: kém hơn.
- **4. Chi nhiều cuối tuần — E vs A, MAE_end:** Cải thiện: -8.47%; Win Rate: 30.0% (10 seed); hiệu trung bình E - tham chiếu: 19,681.84 đ; CI 95%: [2,920.34, 36,634.47] đ. Kết luận: kém hơn.
- **4. Chi nhiều cuối tuần — E vs A, RMSE_daily:** Cải thiện: -14.70%; Win Rate: 20.0% (10 seed); hiệu trung bình E - tham chiếu: 29,809.64 đ; CI 95%: [12,893.87, 47,176.10] đ. Kết luận: kém hơn.
- **4. Chi nhiều cuối tuần — E vs D, MAE_daily:** Cải thiện: 48.68%; Win Rate: 100.0% (10 seed); hiệu trung bình E - tham chiếu: -166,164.07 đ; CI 95%: [-175,128.30, -157,529.78] đ. Kết luận: tốt hơn có ý nghĩa.
- **4. Chi nhiều cuối tuần — E vs D, MAE_end:** Cải thiện: 58.32%; Win Rate: 100.0% (10 seed); hiệu trung bình E - tham chiếu: -352,469.32 đ; CI 95%: [-371,621.24, -331,850.34] đ. Kết luận: tốt hơn có ý nghĩa.
- **4. Chi nhiều cuối tuần — E vs D, RMSE_daily:** Cải thiện: 43.44%; Win Rate: 100.0% (10 seed); hiệu trung bình E - tham chiếu: -178,657.66 đ; CI 95%: [-194,261.32, -162,837.09] đ. Kết luận: tốt hơn có ý nghĩa.
- **5. Thay đổi thói quen giữa chừng — D vs A, MAE_daily:** Cải thiện: 48.65%; Win Rate: 100.0% (10 seed); hiệu trung bình D - tham chiếu: -301,826.71 đ; CI 95%: [-312,727.12, -290,230.10] đ. Kết luận: tốt hơn có ý nghĩa.
- **5. Thay đổi thói quen giữa chừng — D vs A, MAE_end:** Cải thiện: 44.57%; Win Rate: 100.0% (10 seed); hiệu trung bình D - tham chiếu: -580,006.84 đ; CI 95%: [-600,939.55, -555,150.44] đ. Kết luận: tốt hơn có ý nghĩa.
- **5. Thay đổi thói quen giữa chừng — D vs A, RMSE_daily:** Cải thiện: 38.69%; Win Rate: 100.0% (10 seed); hiệu trung bình D - tham chiếu: -541,187.64 đ; CI 95%: [-555,955.45, -526,121.82] đ. Kết luận: tốt hơn có ý nghĩa.
- **5. Thay đổi thói quen giữa chừng — D vs B, MAE_daily:** Cải thiện: 48.69%; Win Rate: 100.0% (10 seed); hiệu trung bình D - tham chiếu: -302,279.44 đ; CI 95%: [-313,126.41, -290,664.04] đ. Kết luận: tốt hơn có ý nghĩa.
- **5. Thay đổi thói quen giữa chừng — D vs B, MAE_end:** Cải thiện: 44.60%; Win Rate: 100.0% (10 seed); hiệu trung bình D - tham chiếu: -580,881.76 đ; CI 95%: [-601,773.00, -556,115.73] đ. Kết luận: tốt hơn có ý nghĩa.
- **5. Thay đổi thói quen giữa chừng — D vs B, RMSE_daily:** Cải thiện: 38.76%; Win Rate: 100.0% (10 seed); hiệu trung bình D - tham chiếu: -542,725.16 đ; CI 95%: [-557,333.22, -527,783.66] đ. Kết luận: tốt hơn có ý nghĩa.
- **5. Thay đổi thói quen giữa chừng — D vs C, MAE_daily:** Cải thiện: -1.16%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 3,640.64 đ; CI 95%: [2,908.63, 4,386.42] đ. Kết luận: kém hơn.
- **5. Thay đổi thói quen giữa chừng — D vs C, MAE_end:** Cải thiện: -0.99%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 7,045.12 đ; CI 95%: [5,625.77, 8,489.84] đ. Kết luận: kém hơn.
- **5. Thay đổi thói quen giữa chừng — D vs C, RMSE_daily:** Cải thiện: -0.93%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 7,914.22 đ; CI 95%: [6,597.01, 9,180.15] đ. Kết luận: kém hơn.
- **5. Thay đổi thói quen giữa chừng — E vs A, MAE_daily:** Cải thiện: 54.69%; Win Rate: 100.0% (10 seed); hiệu trung bình E - tham chiếu: -339,265.74 đ; CI 95%: [-349,591.17, -327,297.14] đ. Kết luận: tốt hơn có ý nghĩa.
- **5. Thay đổi thói quen giữa chừng — E vs A, MAE_end:** Cải thiện: 50.53%; Win Rate: 100.0% (10 seed); hiệu trung bình E - tham chiếu: -657,573.07 đ; CI 95%: [-678,855.21, -633,122.10] đ. Kết luận: tốt hơn có ý nghĩa.
- **5. Thay đổi thói quen giữa chừng — E vs A, RMSE_daily:** Cải thiện: 42.07%; Win Rate: 100.0% (10 seed); hiệu trung bình E - tham chiếu: -588,490.95 đ; CI 95%: [-601,019.06, -575,675.43] đ. Kết luận: tốt hơn có ý nghĩa.
- **5. Thay đổi thói quen giữa chừng — E vs D, MAE_daily:** Cải thiện: 11.75%; Win Rate: 100.0% (10 seed); hiệu trung bình E - tham chiếu: -37,439.03 đ; CI 95%: [-48,015.94, -26,888.24] đ. Kết luận: tốt hơn có ý nghĩa.
- **5. Thay đổi thói quen giữa chừng — E vs D, MAE_end:** Cải thiện: 10.75%; Win Rate: 100.0% (10 seed); hiệu trung bình E - tham chiếu: -77,566.23 đ; CI 95%: [-100,537.46, -56,318.30] đ. Kết luận: tốt hơn có ý nghĩa.
- **5. Thay đổi thói quen giữa chừng — E vs D, RMSE_daily:** Cải thiện: 5.52%; Win Rate: 100.0% (10 seed); hiệu trung bình E - tham chiếu: -47,303.30 đ; CI 95%: [-54,321.00, -41,125.60] đ. Kết luận: tốt hơn có ý nghĩa.
- **6. Chi tiêu thưa — D vs A, MAE_daily:** Cải thiện: -43.97%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 249,086.58 đ; CI 95%: [186,116.51, 313,700.86] đ. Kết luận: kém hơn.
- **6. Chi tiêu thưa — D vs A, MAE_end:** Cải thiện: -60.74%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 546,559.60 đ; CI 95%: [406,981.55, 689,578.30] đ. Kết luận: kém hơn.
- **6. Chi tiêu thưa — D vs A, RMSE_daily:** Cải thiện: -46.80%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 356,371.77 đ; CI 95%: [270,380.65, 443,268.84] đ. Kết luận: kém hơn.
- **6. Chi tiêu thưa — D vs B, MAE_daily:** Cải thiện: -43.21%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 246,062.77 đ; CI 95%: [180,982.28, 312,025.53] đ. Kết luận: kém hơn.
- **6. Chi tiêu thưa — D vs B, MAE_end:** Cải thiện: -59.58%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 540,030.19 đ; CI 95%: [395,318.63, 684,963.75] đ. Kết luận: kém hơn.
- **6. Chi tiêu thưa — D vs B, RMSE_daily:** Cải thiện: -45.96%; Win Rate: 0.0% (10 seed); hiệu trung bình D - tham chiếu: 352,015.00 đ; CI 95%: [264,635.41, 439,599.87] đ. Kết luận: kém hơn.
- **6. Chi tiêu thưa — D vs C, MAE_daily:** Cải thiện: -0.04%; Win Rate: 30.0% (10 seed); hiệu trung bình D - tham chiếu: 339.46 đ; CI 95%: [-1,166.97, 1,660.76] đ. Kết luận: chưa kết luận được.
- **6. Chi tiêu thưa — D vs C, MAE_end:** Cải thiện: -0.21%; Win Rate: 20.0% (10 seed); hiệu trung bình D - tham chiếu: 2,974.74 đ; CI 95%: [519.08, 5,918.52] đ. Kết luận: kém hơn.
- **6. Chi tiêu thưa — D vs C, RMSE_daily:** Cải thiện: -0.02%; Win Rate: 30.0% (10 seed); hiệu trung bình D - tham chiếu: 204.95 đ; CI 95%: [-1,171.12, 1,677.52] đ. Kết luận: chưa kết luận được.
- **6. Chi tiêu thưa — E vs A, MAE_daily:** Cải thiện: -39.84%; Win Rate: 0.0% (10 seed); hiệu trung bình E - tham chiếu: 225,671.94 đ; CI 95%: [170,911.20, 280,861.54] đ. Kết luận: kém hơn.
- **6. Chi tiêu thưa — E vs A, MAE_end:** Cải thiện: -55.26%; Win Rate: 0.0% (10 seed); hiệu trung bình E - tham chiếu: 497,232.19 đ; CI 95%: [384,923.06, 602,448.04] đ. Kết luận: kém hơn.
- **6. Chi tiêu thưa — E vs A, RMSE_daily:** Cải thiện: -57.65%; Win Rate: 0.0% (10 seed); hiệu trung bình E - tham chiếu: 438,981.01 đ; CI 95%: [306,345.07, 587,771.03] đ. Kết luận: kém hơn.
- **6. Chi tiêu thưa — E vs D, MAE_daily:** Cải thiện: 2.87%; Win Rate: 70.0% (10 seed); hiệu trung bình E - tham chiếu: -23,414.64 đ; CI 95%: [-84,112.83, 38,686.20] đ. Kết luận: chưa kết luận được.
- **6. Chi tiêu thưa — E vs D, MAE_end:** Cải thiện: 3.41%; Win Rate: 60.0% (10 seed); hiệu trung bình E - tham chiếu: -49,327.41 đ; CI 95%: [-176,243.43, 72,703.45] đ. Kết luận: chưa kết luận được.
- **6. Chi tiêu thưa — E vs D, RMSE_daily:** Cải thiện: -7.39%; Win Rate: 50.0% (10 seed); hiệu trung bình E - tham chiếu: 82,609.24 đ; CI 95%: [-57,252.41, 222,815.02] đ. Kết luận: chưa kết luận được.

### 6.2. Các giới hạn còn lại (Limitations):

- Chỉ có dữ liệu mô phỏng trong lần chạy này, chưa có kiểm chứng trên dữ liệu thực.
- Có 6 kịch bản mô phỏng trong lần chạy này; kết quả chỉ phản ánh các phân phối được mô phỏng, không bảo đảm khái quát cho hành vi chi tiêu khác.
- Các kịch bản mô phỏng hiện có chưa mô hình hóa ngày lễ/Tết; chỉ kịch bản weekend_spending mô hình hóa khác biệt cuối tuần.
- Các cửa sổ chồng lấn không làm tăng số đơn vị độc lập; CI theo seed chỉ phản ánh bất định giữa các seed dưới thiết kế hiện tại.
- Phân tích độ nhạy chỉ bao gồm các alpha [0.1, 0.2, 0.3, 0.5]; đây là phân tích nhạy của D, không dùng để chọn lại cấu hình E từ tập kiểm tra.
- E vẫn có MAE ngày cao hơn A ở chuỗi ổn định. Việc chọn ứng viên trên cửa sổ 60 ngày hữu hạn có chi phí chọn tham số và phương sai ước lượng alpha; đây là giải thích khả dĩ, không phải bằng chứng nhân quả. Không điều chỉnh lại thuật toán theo kết quả test này.

## 7. Phát hiện thiếu hụt tiền

CRITICAL ở đây là có số dư âm trong step 1..30. Precision = TP/(TP+FP), Recall = TP/(TP+FN); N/A khi mẫu số bằng 0. Timing = ngày âm đầu tiên dự báo - ngày âm đầu tiên thực tế (âm: sớm, dương: muộn), chỉ tính cho TP; Lead = số ngày từ origin đến ngày âm thực tế của TP. Các thống kê theo origin là mô tả, không coi cửa sổ chồng lấn là mẫu độc lập.

Cohort risk dùng số dư gốc; cohort stress đặt số dư tại mỗi origin về 1.000.000đ và giữ nguyên gia số tiền thực tế/tương lai. Stress là tình huống giả định có kiểm soát, không phải kết quả trên số dư quan sát. Already-negative đếm origin đã âm. Không gộp hai cohort.

| Kịch bản | Nhánh | Cohort | TP | FP | FN | TN | Precision | Recall | Timing (ngày) | Lead (ngày) | Số TP | Sớm | Muộn | Already-negative |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| stable_noise | arm_A | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| stable_noise | arm_A | stress | 299 | 1 | 0 | 100 | 0.997 | 1.000 | -0.067 | 5.301 | 299 | 27 | 7 | 0 |
| stable_noise | arm_B | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| stable_noise | arm_B | stress | 299 | 1 | 0 | 100 | 0.997 | 1.000 | -0.067 | 5.301 | 299 | 27 | 7 | 0 |
| stable_noise | arm_C | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| stable_noise | arm_C | stress | 295 | 1 | 4 | 100 | 0.997 | 0.987 | 0.007 | 5.278 | 295 | 22 | 24 | 0 |
| stable_noise | arm_D | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| stable_noise | arm_D | stress | 295 | 1 | 4 | 100 | 0.997 | 0.987 | 0.007 | 5.278 | 295 | 22 | 24 | 0 |
| stable_noise | arm_E | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| stable_noise | arm_E | stress | 298 | 1 | 1 | 100 | 0.997 | 0.997 | -0.054 | 5.295 | 298 | 26 | 11 | 0 |
| upward_trend | arm_A | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| upward_trend | arm_A | stress | 300 | 0 | 13 | 87 | 1.000 | 0.958 | 0.187 | 4.630 | 300 | 2 | 53 | 0 |
| upward_trend | arm_B | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| upward_trend | arm_B | stress | 300 | 0 | 13 | 87 | 1.000 | 0.958 | 0.187 | 4.630 | 300 | 2 | 53 | 0 |
| upward_trend | arm_C | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| upward_trend | arm_C | stress | 307 | 1 | 6 | 86 | 0.997 | 0.981 | 0.055 | 4.674 | 307 | 12 | 29 | 0 |
| upward_trend | arm_D | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| upward_trend | arm_D | stress | 307 | 1 | 6 | 86 | 0.997 | 0.981 | 0.055 | 4.674 | 307 | 12 | 29 | 0 |
| upward_trend | arm_E | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| upward_trend | arm_E | stress | 306 | 1 | 7 | 86 | 0.997 | 0.978 | 0.075 | 4.676 | 306 | 13 | 36 | 0 |
| volatile_outliers | arm_A | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| volatile_outliers | arm_A | stress | 289 | 11 | 10 | 90 | 0.963 | 0.967 | -1.360 | 5.716 | 289 | 134 | 5 | 0 |
| volatile_outliers | arm_B | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| volatile_outliers | arm_B | stress | 289 | 11 | 10 | 90 | 0.963 | 0.967 | -0.661 | 5.716 | 289 | 117 | 5 | 0 |
| volatile_outliers | arm_C | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| volatile_outliers | arm_C | stress | 287 | 5 | 12 | 96 | 0.983 | 0.960 | -0.854 | 5.700 | 287 | 112 | 26 | 0 |
| volatile_outliers | arm_D | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| volatile_outliers | arm_D | stress | 285 | 3 | 14 | 98 | 0.990 | 0.953 | -0.442 | 5.688 | 285 | 101 | 27 | 0 |
| volatile_outliers | arm_E | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| volatile_outliers | arm_E | stress | 289 | 11 | 10 | 90 | 0.963 | 0.967 | -0.353 | 5.716 | 289 | 90 | 21 | 0 |
| weekend_spending | arm_A | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| weekend_spending | arm_A | stress | 300 | 0 | 3 | 97 | 1.000 | 0.990 | 0.213 | 5.013 | 300 | 10 | 74 | 0 |
| weekend_spending | arm_B | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| weekend_spending | arm_B | stress | 300 | 0 | 3 | 97 | 1.000 | 0.990 | 0.213 | 5.013 | 300 | 10 | 74 | 0 |
| weekend_spending | arm_C | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| weekend_spending | arm_C | stress | 303 | 6 | 0 | 91 | 0.981 | 1.000 | -0.185 | 5.023 | 303 | 64 | 16 | 0 |
| weekend_spending | arm_D | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| weekend_spending | arm_D | stress | 303 | 6 | 0 | 91 | 0.981 | 1.000 | -0.185 | 5.023 | 303 | 64 | 16 | 0 |
| weekend_spending | arm_E | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| weekend_spending | arm_E | stress | 301 | 2 | 2 | 95 | 0.993 | 0.993 | 0.189 | 5.017 | 301 | 12 | 68 | 0 |
| habit_shift | arm_A | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| habit_shift | arm_A | stress | 312 | 3 | 11 | 74 | 0.990 | 0.966 | 0.311 | 4.032 | 312 | 23 | 66 | 0 |
| habit_shift | arm_B | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| habit_shift | arm_B | stress | 312 | 3 | 11 | 74 | 0.990 | 0.966 | 0.311 | 4.032 | 312 | 23 | 66 | 0 |
| habit_shift | arm_C | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| habit_shift | arm_C | stress | 312 | 3 | 11 | 74 | 0.990 | 0.966 | 0.038 | 4.032 | 312 | 28 | 34 | 0 |
| habit_shift | arm_D | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| habit_shift | arm_D | stress | 312 | 3 | 11 | 74 | 0.990 | 0.966 | 0.038 | 4.032 | 312 | 28 | 34 | 0 |
| habit_shift | arm_E | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| habit_shift | arm_E | stress | 312 | 3 | 11 | 74 | 0.990 | 0.966 | -0.019 | 4.032 | 312 | 33 | 25 | 0 |
| sparse_spending | arm_A | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| sparse_spending | arm_A | stress | 206 | 19 | 25 | 150 | 0.916 | 0.892 | 0.155 | 4.840 | 206 | 3 | 17 | 0 |
| sparse_spending | arm_B | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| sparse_spending | arm_B | stress | 206 | 19 | 25 | 150 | 0.916 | 0.892 | 0.155 | 4.840 | 206 | 3 | 17 | 0 |
| sparse_spending | arm_C | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| sparse_spending | arm_C | stress | 208 | 24 | 23 | 145 | 0.897 | 0.900 | 0.077 | 4.832 | 208 | 15 | 14 | 0 |
| sparse_spending | arm_D | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| sparse_spending | arm_D | stress | 208 | 24 | 23 | 145 | 0.897 | 0.900 | 0.077 | 4.832 | 208 | 15 | 14 | 0 |
| sparse_spending | arm_E | risk | 0 | 0 | 0 | 400 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| sparse_spending | arm_E | stress | 204 | 20 | 27 | 149 | 0.911 | 0.883 | 0.069 | 4.770 | 204 | 9 | 16 | 0 |
