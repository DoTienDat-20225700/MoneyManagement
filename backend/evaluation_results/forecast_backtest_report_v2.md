# BÁO CÁO ĐÁNH GIÁ THỰC NGHIỆM THUẬT TOÁN DỰ BÁO DÒNG TIỀN F03 (V2)

## 1. Cấu Hình Thực Nghiệm & Thiết Kế Đánh Giá

- **Số seed mô phỏng cấu hình:** 30 hạt giống độc lập; split test. Số seed thực tế theo từng kịch bản được ghi ở mục 3.
- **Độ dài chuỗi mô phỏng:** 365 ngày.
- **Cửa sổ lịch sử quan sát:** 60 ngày gần nhất.
- **Đường chân trời dự báo (Horizon):** 30 ngày.
- **Bước nhảy Rolling-Origin:** 7 ngày, 40 cửa sổ chồng lấn mỗi chuỗi mô phỏng; horizon 30 ngày. Số cửa sổ của dữ liệu thực phụ thuộc độ dài chuỗi nhập.
- **Bootstrap 95% CI:** 2.000 lần lấy mẫu, random seed = 12345; mỗi seed là một đơn vị lấy mẫu độc lập. Chỉ số được tổng hợp qua các cửa sổ trong mỗi seed trước khi lấy sai khác theo cặp; không lấy mẫu riêng từng cửa sổ hoặc từng ngày.
  Các cửa sổ chồng lấn có phụ thuộc thời gian. CI phản ánh biến thiên giữa các chuỗi seed trong thiết kế này, không coi các cửa sổ là quan sát độc lập và không đại diện trực tiếp cho quần thể người dùng thực. Với dưới 2 seed, CI suy biến không đủ để kết luận ý nghĩa thống kê.
- **Tách dữ liệu:** seed phát triển 1000–1009; seed kiểm tra 0–29 (lần chạy này: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29]). Chốt cấu hình trên development trước khi chạy test; không chọn lại cấu hình từ kết quả test. Alpha mỗi origin chỉ chọn từ lịch sử đến origin.
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

Số seed theo từng kịch bản: 1. Chi tiêu ổn định có nhiễu (Stable): 30 seed; 2. Chi tiêu có xu hướng tăng (Upward Trend): 30 seed; 3. Chi tiêu thất thường có outlier (Volatile/Outlier): 30 seed; 4. Chi nhiều cuối tuần: 30 seed; 5. Thay đổi thói quen giữa chừng: 30 seed; 6. Chi tiêu thưa: 30 seed.

| Kịch bản | Nhánh | MAE_daily (đ) | RMSE_daily (đ) | MAE_end (đ) | Bias_end (đ) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| 1. Chi tiêu ổn định có nhiễu (Stable) | A: Mean (Raw) - Baseline | 83,457.07 ± 10,506.94 | 109,466.31 ± 14,440.65 | 130,745.72 ± 21,916.33 | -1,091.93 ± 23,175.43 |
| 1. Chi tiêu ổn định có nhiễu (Stable) | B: Mean (Winsorized) | 83,476.13 ± 10,504.97 | 109,487.87 ± 14,439.62 | 130,762.90 ± 21,931.27 | -836.92 ± 23,081.16 |
| 1. Chi tiêu ổn định có nhiễu (Stable) | C: EWMA (Raw) | 127,491.54 ± 14,509.01 | 175,165.75 ± 20,088.74 | 226,139.71 ± 26,989.90 | -5,007.57 ± 23,034.43 |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D: EWMA (Winsorized) - Fixed | 127,485.14 ± 14,488.29 | 175,141.29 ± 20,072.86 | 226,113.27 ± 26,961.05 | -4,852.27 ± 23,051.20 |
| 1. Chi tiêu ổn định có nhiễu (Stable) | E: Adaptive Mean/EWMA (Winsorized) | 97,074.00 ± 15,750.09 | 133,485.27 ± 27,980.93 | 159,857.21 ± 30,485.65 | -1,379.12 ± 24,930.36 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | A: Mean (Raw) - Baseline | 273,113.80 ± 8,503.20 | 334,357.48 ± 11,347.17 | 590,907.27 ± 18,540.35 | 590,907.27 ± 18,540.35 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | B: Mean (Winsorized) | 273,220.66 ± 8,483.13 | 334,479.62 ± 11,323.32 | 591,115.91 ± 18,511.07 | 591,115.91 ± 18,511.07 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | C: EWMA (Raw) | 132,788.45 ± 10,621.01 | 187,037.19 ± 14,763.33 | 281,460.16 ± 21,465.30 | 252,432.20 ± 18,427.54 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D: EWMA (Winsorized) - Fixed | 132,832.96 ± 10,623.78 | 187,177.22 ± 14,719.03 | 281,671.23 ± 21,644.01 | 253,104.36 ± 18,377.11 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | E: Adaptive Mean/EWMA (Winsorized) | 160,469.59 ± 15,208.98 | 219,209.41 ± 18,326.42 | 347,279.54 ± 32,392.88 | 323,552.50 ± 28,403.07 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | A: Mean (Raw) - Baseline | 1,797,841.40 ± 29,896.87 | 2,418,486.49 ± 39,436.04 | 3,364,993.85 ± 66,299.45 | -482,795.58 ± 32,413.46 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | B: Mean (Winsorized) | 1,203,947.97 ± 29,535.23 | 2,118,427.07 ± 37,720.94 | 2,335,423.13 ± 65,698.20 | 794,568.82 ± 33,590.63 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | C: EWMA (Raw) | 2,210,374.51 ± 28,267.84 | 4,995,823.35 ± 41,669.29 | 4,330,019.71 ± 59,545.18 | -904,611.13 ± 32,253.16 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D: EWMA (Winsorized) - Fixed | 1,430,016.52 ± 27,454.48 | 2,782,629.77 ± 39,912.79 | 2,818,258.71 ± 57,188.89 | 622,131.85 ± 32,531.40 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | E: Adaptive Mean/EWMA (Winsorized) | 1,122,452.90 ± 74,125.47 | 2,200,109.46 ± 218,336.52 | 2,230,364.89 ± 154,855.54 | 1,166,163.69 ± 135,104.10 |
| 4. Chi nhiều cuối tuần | A: Mean (Raw) - Baseline | 156,451.09 ± 7,570.58 | 192,689.31 ± 8,626.15 | 217,158.89 ± 20,550.50 | -201,091.93 ± 23,175.43 |
| 4. Chi nhiều cuối tuần | B: Mean (Winsorized) | 156,451.09 ± 7,570.58 | 192,689.31 ± 8,626.15 | 217,158.89 ± 20,550.50 | -201,091.93 ± 23,175.43 |
| 4. Chi nhiều cuối tuần | C: EWMA (Raw) | 338,363.50 ± 11,521.59 | 406,946.06 ± 13,884.52 | 595,642.03 ± 21,490.04 | -591,565.43 ± 23,034.43 |
| 4. Chi nhiều cuối tuần | D: EWMA (Winsorized) - Fixed | 338,363.50 ± 11,521.59 | 406,946.06 ± 13,884.52 | 595,642.03 ± 21,490.04 | -591,565.43 ± 23,034.43 |
| 4. Chi nhiều cuối tuần | E: Adaptive Mean/EWMA (Winsorized) | 161,977.95 ± 13,566.31 | 212,614.59 ± 28,362.89 | 227,008.36 ± 28,384.28 | -182,287.23 ± 32,807.70 |
| 5. Thay đổi thói quen giữa chừng | A: Mean (Raw) - Baseline | 615,068.45 ± 12,951.81 | 1,393,959.58 ± 21,139.81 | 1,291,325.06 ± 29,388.23 | 1,198,908.07 ± 23,175.43 |
| 5. Thay đổi thói quen giữa chừng | B: Mean (Winsorized) | 615,561.58 ± 13,004.16 | 1,395,543.72 ± 21,249.66 | 1,292,289.60 ± 29,492.81 | 1,199,983.09 ± 23,150.90 |
| 5. Thay đổi thói quen giữa chừng | C: EWMA (Raw) | 311,835.70 ± 15,507.78 | 848,004.03 ± 29,217.73 | 706,026.84 ± 28,119.14 | 510,236.34 ± 23,034.43 |
| 5. Thay đổi thói quen giữa chừng | D: EWMA (Winsorized) - Fixed | 315,813.52 ± 15,531.99 | 855,981.13 ± 29,618.51 | 713,726.31 ± 28,322.07 | 518,050.54 ± 22,615.52 |
| 5. Thay đổi thói quen giữa chừng | E: Adaptive Mean/EWMA (Winsorized) | 273,681.51 ± 17,473.93 | 815,974.37 ± 28,643.07 | 629,713.86 ± 31,818.30 | 445,924.71 ± 33,160.48 |
| 6. Chi tiêu thưa | A: Mean (Raw) - Baseline | 582,077.05 ± 81,144.88 | 765,349.77 ± 120,434.26 | 906,642.19 ± 176,278.47 | -37,927.56 ± 142,403.66 |
| 6. Chi tiêu thưa | B: Mean (Winsorized) | 584,615.22 ± 81,347.88 | 769,418.84 ± 121,016.50 | 912,206.41 ± 177,704.96 | -28,305.79 ± 142,197.53 |
| 6. Chi tiêu thưa | C: EWMA (Raw) | 882,926.02 ± 101,234.59 | 1,229,300.90 ± 144,843.21 | 1,582,980.35 ± 189,545.77 | -96,756.96 ± 139,549.57 |
| 6. Chi tiêu thưa | D: EWMA (Winsorized) - Fixed | 882,665.86 ± 100,910.86 | 1,228,602.96 ± 143,806.78 | 1,582,868.26 ± 188,832.53 | -87,391.93 ± 138,451.43 |
| 6. Chi tiêu thưa | E: Adaptive Mean/EWMA (Winsorized) | 939,585.37 ± 208,068.19 | 1,432,353.03 ± 333,706.63 | 1,688,100.81 ± 415,892.12 | 118,633.42 ± 311,449.37 |

## 4. Bảng So Sánh Theo Cặp (Paired Comparison) & Kiểm Định Bootstrap 95% CI

Hiệu số được tính bằng **Nhánh X - Nhánh Y**. Với MAE và RMSE, hiệu số âm mang ý nghĩa nhánh đề xuất có sai số nhỏ hơn (tốt hơn). Win Rate là tỷ lệ % số seed mà nhánh đề xuất đạt sai số nhỏ hơn.

| Kịch bản | Cặp so sánh | Chỉ số | Hiệu trung bình (đ) | Khoảng tin cậy 95% Bootstrap (đ) | Win Rate (%) |
| :--- | :--- | :---: | :---: | :---: | :---: |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs A (Proposed vs Baseline) | MAE_daily | 44,028.07 | [38,614.18, 49,390.27] | 0.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs A (Proposed vs Baseline) | MAE_end | 95,367.54 | [84,068.55, 106,948.64] | 0.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs A (Proposed vs Baseline) | RMSE_daily | 65,674.97 | [57,971.01, 73,044.63] | 0.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs A (Proposed vs Baseline) | Bias_end | -3,760.33 | [-11,725.83, 3,173.85] | 43.3% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs B (Effect of EWMA with Winsorize) | MAE_daily | 44,009.01 | [38,602.09, 49,407.14] | 0.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs B (Effect of EWMA with Winsorize) | MAE_end | 95,350.37 | [84,007.97, 106,989.65] | 0.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs B (Effect of EWMA with Winsorize) | RMSE_daily | 65,653.42 | [57,945.61, 73,007.90] | 0.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs B (Effect of EWMA with Winsorize) | Bias_end | -4,015.35 | [-11,966.95, 2,955.66] | 43.3% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs C (Effect of Winsorize with EWMA) | MAE_daily | -6.41 | [-51.32, 41.73] | 23.3% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs C (Effect of Winsorize with EWMA) | MAE_end | -26.44 | [-120.21, 73.51] | 23.3% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs C (Effect of Winsorize with EWMA) | RMSE_daily | -24.46 | [-87.39, 37.36] | 23.3% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | D vs C (Effect of Winsorize with EWMA) | Bias_end | 155.30 | [72.13, 255.65] | 33.3% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | E vs A (Adaptive vs Mean) | MAE_daily | 13,616.93 | [9,294.35, 18,510.03] | 6.7% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | E vs A (Adaptive vs Mean) | MAE_end | 29,111.48 | [19,663.83, 39,631.52] | 13.3% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | E vs A (Adaptive vs Mean) | RMSE_daily | 24,018.95 | [15,830.97, 33,326.86] | 6.7% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | E vs A (Adaptive vs Mean) | Bias_end | -287.19 | [-7,603.86, 6,497.93] | 33.3% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | E vs D (Adaptive vs Fixed EWMA) | MAE_daily | -30,411.14 | [-35,248.43, -24,984.57] | 100.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | E vs D (Adaptive vs Fixed EWMA) | MAE_end | -66,256.06 | [-75,356.44, -55,560.84] | 100.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | E vs D (Adaptive vs Fixed EWMA) | RMSE_daily | -41,656.02 | [-49,476.48, -33,158.52] | 90.0% |
| 1. Chi tiêu ổn định có nhiễu (Stable) | E vs D (Adaptive vs Fixed EWMA) | Bias_end | 3,473.14 | [-3,463.06, 10,977.59] | 36.7% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs A (Proposed vs Baseline) | MAE_daily | -140,280.85 | [-143,771.81, -136,547.66] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs A (Proposed vs Baseline) | MAE_end | -309,236.04 | [-316,615.27, -301,761.70] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs A (Proposed vs Baseline) | RMSE_daily | -147,180.26 | [-151,942.64, -142,236.01] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs A (Proposed vs Baseline) | Bias_end | -337,802.92 | [-344,157.76, -332,232.19] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs B (Effect of EWMA with Winsorize) | MAE_daily | -140,387.70 | [-143,868.73, -136,685.77] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs B (Effect of EWMA with Winsorize) | MAE_end | -309,444.68 | [-316,850.63, -302,015.96] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs B (Effect of EWMA with Winsorize) | RMSE_daily | -147,302.40 | [-152,069.15, -142,335.32] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs B (Effect of EWMA with Winsorize) | Bias_end | -338,011.56 | [-344,341.77, -332,412.44] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs C (Effect of Winsorize with EWMA) | MAE_daily | 44.51 | [-72.23, 161.38] | 30.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs C (Effect of Winsorize with EWMA) | MAE_end | 211.07 | [-65.68, 487.08] | 26.7% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs C (Effect of Winsorize with EWMA) | RMSE_daily | 140.03 | [32.72, 260.73] | 26.7% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | D vs C (Effect of Winsorize with EWMA) | Bias_end | 672.15 | [447.58, 921.07] | 0.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | E vs A (Adaptive vs Mean) | MAE_daily | -112,644.21 | [-117,758.82, -107,453.88] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | E vs A (Adaptive vs Mean) | MAE_end | -243,627.73 | [-255,079.85, -232,451.65] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | E vs A (Adaptive vs Mean) | RMSE_daily | -115,148.07 | [-121,357.93, -109,021.23] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | E vs A (Adaptive vs Mean) | Bias_end | -267,354.78 | [-278,110.34, -256,689.59] | 100.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | E vs D (Adaptive vs Fixed EWMA) | MAE_daily | 27,636.63 | [23,702.65, 31,564.74] | 3.3% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | E vs D (Adaptive vs Fixed EWMA) | MAE_end | 65,608.31 | [57,517.58, 73,345.42] | 0.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | E vs D (Adaptive vs Fixed EWMA) | RMSE_daily | 32,032.19 | [27,457.17, 37,025.55] | 0.0% |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | E vs D (Adaptive vs Fixed EWMA) | Bias_end | 70,448.14 | [62,938.03, 78,385.48] | 0.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs A (Proposed vs Baseline) | MAE_daily | -367,824.88 | [-378,118.07, -357,739.70] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs A (Proposed vs Baseline) | MAE_end | -546,735.13 | [-564,870.34, -528,694.82] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs A (Proposed vs Baseline) | RMSE_daily | 364,143.28 | [349,748.70, 377,822.50] | 0.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs A (Proposed vs Baseline) | Bias_end | 1,104,927.43 | [1,094,328.82, 1,114,324.15] | 0.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs B (Effect of EWMA with Winsorize) | MAE_daily | 226,068.54 | [215,664.23, 235,993.67] | 0.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs B (Effect of EWMA with Winsorize) | MAE_end | 482,835.58 | [464,811.94, 500,702.62] | 0.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs B (Effect of EWMA with Winsorize) | RMSE_daily | 664,202.70 | [651,328.13, 676,441.23] | 0.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs B (Effect of EWMA with Winsorize) | Bias_end | -172,436.96 | [-183,335.44, -162,781.41] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs C (Effect of Winsorize with EWMA) | MAE_daily | -780,358.00 | [-781,946.13, -778,649.81] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs C (Effect of Winsorize with EWMA) | MAE_end | -1,511,761.00 | [-1,514,961.49, -1,508,440.82] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs C (Effect of Winsorize with EWMA) | RMSE_daily | -2,213,193.58 | [-2,217,757.83, -2,208,965.50] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | D vs C (Effect of Winsorize with EWMA) | Bias_end | 1,526,742.99 | [1,525,241.10, 1,528,352.66] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | E vs A (Adaptive vs Mean) | MAE_daily | -675,388.50 | [-695,386.78, -647,399.55] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | E vs A (Adaptive vs Mean) | MAE_end | -1,134,628.96 | [-1,175,851.10, -1,076,637.24] | 100.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | E vs A (Adaptive vs Mean) | RMSE_daily | -218,377.03 | [-272,240.50, -126,021.85] | 93.3% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | E vs A (Adaptive vs Mean) | Bias_end | 1,648,959.28 | [1,598,809.51, 1,686,057.46] | 0.0% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | E vs D (Adaptive vs Fixed EWMA) | MAE_daily | -307,563.62 | [-329,845.21, -274,867.94] | 96.7% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | E vs D (Adaptive vs Fixed EWMA) | MAE_end | -587,893.83 | [-632,781.97, -523,442.14] | 96.7% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | E vs D (Adaptive vs Fixed EWMA) | RMSE_daily | -582,520.31 | [-638,712.10, -486,526.48] | 96.7% |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | E vs D (Adaptive vs Fixed EWMA) | Bias_end | 544,031.84 | [495,511.07, 581,090.15] | 0.0% |
| 4. Chi nhiều cuối tuần | D vs A (Proposed vs Baseline) | MAE_daily | 181,912.40 | [177,871.49, 185,695.40] | 0.0% |
| 4. Chi nhiều cuối tuần | D vs A (Proposed vs Baseline) | MAE_end | 378,483.13 | [369,588.98, 386,848.92] | 0.0% |
| 4. Chi nhiều cuối tuần | D vs A (Proposed vs Baseline) | RMSE_daily | 214,256.75 | [209,362.85, 219,005.90] | 0.0% |
| 4. Chi nhiều cuối tuần | D vs A (Proposed vs Baseline) | Bias_end | -390,473.49 | [-398,428.62, -383,475.66] | 0.0% |
| 4. Chi nhiều cuối tuần | D vs B (Effect of EWMA with Winsorize) | MAE_daily | 181,912.40 | [177,871.49, 185,695.40] | 0.0% |
| 4. Chi nhiều cuối tuần | D vs B (Effect of EWMA with Winsorize) | MAE_end | 378,483.13 | [369,588.98, 386,848.92] | 0.0% |
| 4. Chi nhiều cuối tuần | D vs B (Effect of EWMA with Winsorize) | RMSE_daily | 214,256.75 | [209,362.85, 219,005.90] | 0.0% |
| 4. Chi nhiều cuối tuần | D vs B (Effect of EWMA with Winsorize) | Bias_end | -390,473.49 | [-398,428.62, -383,475.66] | 0.0% |
| 4. Chi nhiều cuối tuần | D vs C (Effect of Winsorize with EWMA) | MAE_daily | 0.00 | [0.00, 0.00] | 0.0% |
| 4. Chi nhiều cuối tuần | D vs C (Effect of Winsorize with EWMA) | MAE_end | 0.00 | [0.00, 0.00] | 0.0% |
| 4. Chi nhiều cuối tuần | D vs C (Effect of Winsorize with EWMA) | RMSE_daily | 0.00 | [0.00, 0.00] | 0.0% |
| 4. Chi nhiều cuối tuần | D vs C (Effect of Winsorize with EWMA) | Bias_end | 0.00 | [0.00, 0.00] | 0.0% |
| 4. Chi nhiều cuối tuần | E vs A (Adaptive vs Mean) | MAE_daily | 5,526.86 | [1,379.39, 10,189.81] | 33.3% |
| 4. Chi nhiều cuối tuần | E vs A (Adaptive vs Mean) | MAE_end | 9,849.46 | [347.74, 20,590.00] | 36.7% |
| 4. Chi nhiều cuối tuần | E vs A (Adaptive vs Mean) | RMSE_daily | 19,925.27 | [11,112.95, 29,590.37] | 26.7% |
| 4. Chi nhiều cuối tuần | E vs A (Adaptive vs Mean) | Bias_end | 18,804.70 | [10,067.28, 27,710.09] | 73.3% |
| 4. Chi nhiều cuối tuần | E vs D (Adaptive vs Fixed EWMA) | MAE_daily | -176,385.54 | [-180,540.92, -171,892.77] | 100.0% |
| 4. Chi nhiều cuối tuần | E vs D (Adaptive vs Fixed EWMA) | MAE_end | -368,633.67 | [-377,944.06, -358,781.90] | 100.0% |
| 4. Chi nhiều cuối tuần | E vs D (Adaptive vs Fixed EWMA) | RMSE_daily | -194,331.48 | [-203,356.50, -184,501.26] | 100.0% |
| 4. Chi nhiều cuối tuần | E vs D (Adaptive vs Fixed EWMA) | Bias_end | 409,278.20 | [398,586.95, 420,293.82] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | D vs A (Proposed vs Baseline) | MAE_daily | -299,254.93 | [-305,253.59, -293,199.48] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | D vs A (Proposed vs Baseline) | MAE_end | -577,598.74 | [-590,140.90, -565,595.50] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | D vs A (Proposed vs Baseline) | RMSE_daily | -537,978.45 | [-545,929.84, -529,195.20] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | D vs A (Proposed vs Baseline) | Bias_end | -680,857.53 | [-688,274.34, -674,349.65] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | D vs B (Effect of EWMA with Winsorize) | MAE_daily | -299,748.06 | [-305,748.55, -293,716.35] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | D vs B (Effect of EWMA with Winsorize) | MAE_end | -578,563.29 | [-591,100.33, -566,551.82] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | D vs B (Effect of EWMA with Winsorize) | RMSE_daily | -539,562.59 | [-547,509.81, -530,855.79] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | D vs B (Effect of EWMA with Winsorize) | Bias_end | -681,932.55 | [-689,430.67, -675,284.00] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | D vs C (Effect of Winsorize with EWMA) | MAE_daily | 3,977.83 | [3,549.43, 4,435.20] | 0.0% |
| 5. Thay đổi thói quen giữa chừng | D vs C (Effect of Winsorize with EWMA) | MAE_end | 7,699.47 | [6,878.27, 8,579.56] | 0.0% |
| 5. Thay đổi thói quen giữa chừng | D vs C (Effect of Winsorize with EWMA) | RMSE_daily | 7,977.10 | [7,228.71, 8,749.86] | 0.0% |
| 5. Thay đổi thói quen giữa chừng | D vs C (Effect of Winsorize with EWMA) | Bias_end | 7,814.19 | [6,980.39, 8,703.66] | 0.0% |
| 5. Thay đổi thói quen giữa chừng | E vs A (Adaptive vs Mean) | MAE_daily | -341,386.94 | [-347,156.79, -334,882.82] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | E vs A (Adaptive vs Mean) | MAE_end | -661,611.20 | [-672,419.73, -649,521.04] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | E vs A (Adaptive vs Mean) | RMSE_daily | -577,985.21 | [-585,817.03, -569,919.30] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | E vs A (Adaptive vs Mean) | Bias_end | -752,983.36 | [-764,871.66, -741,945.39] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | E vs D (Adaptive vs Fixed EWMA) | MAE_daily | -42,132.01 | [-47,309.98, -36,733.95] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | E vs D (Adaptive vs Fixed EWMA) | MAE_end | -84,012.45 | [-94,141.27, -73,910.83] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | E vs D (Adaptive vs Fixed EWMA) | RMSE_daily | -40,006.77 | [-46,426.59, -33,679.64] | 100.0% |
| 5. Thay đổi thói quen giữa chừng | E vs D (Adaptive vs Fixed EWMA) | Bias_end | -72,125.83 | [-81,344.53, -62,405.69] | 100.0% |
| 6. Chi tiêu thưa | D vs A (Proposed vs Baseline) | MAE_daily | 300,588.82 | [268,010.43, 333,722.42] | 0.0% |
| 6. Chi tiêu thưa | D vs A (Proposed vs Baseline) | MAE_end | 676,226.07 | [607,790.61, 749,423.26] | 0.0% |
| 6. Chi tiêu thưa | D vs A (Proposed vs Baseline) | RMSE_daily | 463,253.19 | [420,743.32, 509,541.86] | 0.0% |
| 6. Chi tiêu thưa | D vs A (Proposed vs Baseline) | Bias_end | -49,464.37 | [-100,189.31, 2,523.42] | 40.0% |
| 6. Chi tiêu thưa | D vs B (Effect of EWMA with Winsorize) | MAE_daily | 298,050.64 | [264,997.29, 331,629.52] | 0.0% |
| 6. Chi tiêu thưa | D vs B (Effect of EWMA with Winsorize) | MAE_end | 670,661.84 | [601,550.23, 745,157.29] | 0.0% |
| 6. Chi tiêu thưa | D vs B (Effect of EWMA with Winsorize) | RMSE_daily | 459,184.12 | [415,878.44, 506,430.28] | 0.0% |
| 6. Chi tiêu thưa | D vs B (Effect of EWMA with Winsorize) | Bias_end | -59,086.14 | [-109,459.87, -7,996.64] | 36.7% |
| 6. Chi tiêu thưa | D vs C (Effect of Winsorize with EWMA) | MAE_daily | -260.15 | [-1,530.02, 970.61] | 53.3% |
| 6. Chi tiêu thưa | D vs C (Effect of Winsorize with EWMA) | MAE_end | -112.09 | [-3,475.14, 3,428.09] | 56.7% |
| 6. Chi tiêu thưa | D vs C (Effect of Winsorize with EWMA) | RMSE_daily | -697.93 | [-2,587.71, 1,128.60] | 50.0% |
| 6. Chi tiêu thưa | D vs C (Effect of Winsorize with EWMA) | Bias_end | 9,365.03 | [5,673.15, 13,611.85] | 80.0% |
| 6. Chi tiêu thưa | E vs A (Adaptive vs Mean) | MAE_daily | 357,508.33 | [290,870.57, 430,456.94] | 0.0% |
| 6. Chi tiêu thưa | E vs A (Adaptive vs Mean) | MAE_end | 781,458.62 | [641,735.73, 933,445.49] | 0.0% |
| 6. Chi tiêu thưa | E vs A (Adaptive vs Mean) | RMSE_daily | 667,003.26 | [553,324.23, 786,359.91] | 0.0% |
| 6. Chi tiêu thưa | E vs A (Adaptive vs Mean) | Bias_end | 156,560.98 | [54,381.43, 258,709.08] | 30.0% |
| 6. Chi tiêu thưa | E vs D (Adaptive vs Fixed EWMA) | MAE_daily | 56,919.51 | [-5,366.97, 122,019.39] | 40.0% |
| 6. Chi tiêu thưa | E vs D (Adaptive vs Fixed EWMA) | MAE_end | 105,232.56 | [-21,733.07, 242,685.21] | 43.3% |
| 6. Chi tiêu thưa | E vs D (Adaptive vs Fixed EWMA) | RMSE_daily | 203,750.07 | [103,986.43, 306,871.92] | 20.0% |
| 6. Chi tiêu thưa | E vs D (Adaptive vs Fixed EWMA) | Bias_end | 206,025.35 | [119,680.80, 289,122.19] | 40.0% |

## 5. Phân Tích Độ Nhạy Tham Số Alpha (Nhánh D: EWMA + Winsorize)

| Kịch bản | Alpha ($\alpha$) | MAE_daily (đ) | MAE_end (đ) |
| :--- | :---: | :---: | :---: |
| 1. Chi tiêu ổn định có nhiễu (Stable) | 0.1 | 101,802 ± 12,378 | 170,665 ± 23,294 |
| 1. Chi tiêu ổn định có nhiễu (Stable) | 0.2 | 127,485 ± 14,488 | 226,113 ± 26,961 |
| 1. Chi tiêu ổn định có nhiễu (Stable) | 0.3 | 151,926 ± 17,305 | 277,095 ± 33,701 |
| 1. Chi tiêu ổn định có nhiễu (Stable) | 0.5 | 196,947 ± 23,715 | 367,285 ± 46,986 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | 0.1 | 145,111 ± 7,917 | 323,783 ± 15,962 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | 0.2 | 132,833 ± 10,624 | 281,671 ± 21,644 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | 0.3 | 141,628 ± 12,764 | 290,556 ± 25,629 |
| 2. Chi tiêu có xu hướng tăng (Upward Trend) | 0.5 | 170,596 ± 18,934 | 340,795 ± 35,288 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | 0.1 | 1,296,778 ± 26,672 | 2,567,767 ± 60,571 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | 0.2 | 1,430,017 ± 27,454 | 2,818,259 ± 57,189 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | 0.3 | 1,549,604 ± 28,748 | 3,043,867 ± 57,763 |
| 3. Chi tiêu thất thường có outlier (Volatile/Outlier) | 0.5 | 1,751,801 ± 33,174 | 3,423,724 ± 65,608 |
| 4. Chi nhiều cuối tuần | 0.1 | 230,083 ± 8,335 | 378,004 ± 17,452 |
| 4. Chi nhiều cuối tuần | 0.2 | 338,364 ± 11,522 | 595,642 ± 21,490 |
| 4. Chi nhiều cuối tuần | 0.3 | 415,077 ± 15,079 | 745,977 ± 27,900 |
| 4. Chi nhiều cuối tuần | 0.5 | 398,466 ± 24,223 | 710,023 ± 45,094 |
| 5. Thay đổi thói quen giữa chừng | 0.1 | 352,426 ± 13,058 | 783,021 ± 23,818 |
| 5. Thay đổi thói quen giữa chừng | 0.2 | 315,814 ± 15,532 | 713,726 ± 28,322 |
| 5. Thay đổi thói quen giữa chừng | 0.3 | 318,434 ± 17,918 | 720,187 ± 33,869 |
| 5. Thay đổi thói quen giữa chừng | 0.5 | 345,956 ± 23,620 | 772,091 ± 46,140 |
| 6. Chi tiêu thưa | 0.1 | 718,447 ± 88,217 | 1,218,441 ± 179,782 |
| 6. Chi tiêu thưa | 0.2 | 882,666 ± 100,911 | 1,582,868 ± 188,833 |
| 6. Chi tiêu thưa | 0.3 | 1,040,977 ± 117,934 | 1,920,882 ± 219,218 |
| 6. Chi tiêu thưa | 0.5 | 1,339,096 ± 178,887 | 2,539,665 ± 345,321 |

## 6. Thảo Luận Kết Quả & Giới Hạn Nghiên Cứu

### 6.1. Nhận xét khách quan:

Cải thiện = (tham chiếu - nhánh đang xét) / tham chiếu × 100; giá trị âm nghĩa là nhánh đang xét có sai số cao hơn. A là baseline; B và C là các nhánh đối chiếu ablation. Kết luận dựa trên CI của hiệu nhánh đang xét - tham chiếu, không suy ra p-value. Bias_end là sai số có dấu nên không dùng dấu CI của Bias_end để kết luận tốt/kém.

- **1. Chi tiêu ổn định có nhiễu (Stable) — D vs A, MAE_daily:** Cải thiện: -52.76%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 44,028.07 đ; CI 95%: [38,614.18, 49,390.27] đ. Kết luận: kém hơn.
- **1. Chi tiêu ổn định có nhiễu (Stable) — D vs A, MAE_end:** Cải thiện: -72.94%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 95,367.54 đ; CI 95%: [84,068.55, 106,948.64] đ. Kết luận: kém hơn.
- **1. Chi tiêu ổn định có nhiễu (Stable) — D vs A, RMSE_daily:** Cải thiện: -60.00%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 65,674.97 đ; CI 95%: [57,971.01, 73,044.63] đ. Kết luận: kém hơn.
- **1. Chi tiêu ổn định có nhiễu (Stable) — D vs B, MAE_daily:** Cải thiện: -52.72%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 44,009.01 đ; CI 95%: [38,602.09, 49,407.14] đ. Kết luận: kém hơn.
- **1. Chi tiêu ổn định có nhiễu (Stable) — D vs B, MAE_end:** Cải thiện: -72.92%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 95,350.37 đ; CI 95%: [84,007.97, 106,989.65] đ. Kết luận: kém hơn.
- **1. Chi tiêu ổn định có nhiễu (Stable) — D vs B, RMSE_daily:** Cải thiện: -59.96%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 65,653.42 đ; CI 95%: [57,945.61, 73,007.90] đ. Kết luận: kém hơn.
- **1. Chi tiêu ổn định có nhiễu (Stable) — D vs C, MAE_daily:** Cải thiện: 0.01%; Win Rate: 23.3% (30 seed); hiệu trung bình D - tham chiếu: -6.41 đ; CI 95%: [-51.32, 41.73] đ. Kết luận: chưa kết luận được.
- **1. Chi tiêu ổn định có nhiễu (Stable) — D vs C, MAE_end:** Cải thiện: 0.01%; Win Rate: 23.3% (30 seed); hiệu trung bình D - tham chiếu: -26.44 đ; CI 95%: [-120.21, 73.51] đ. Kết luận: chưa kết luận được.
- **1. Chi tiêu ổn định có nhiễu (Stable) — D vs C, RMSE_daily:** Cải thiện: 0.01%; Win Rate: 23.3% (30 seed); hiệu trung bình D - tham chiếu: -24.46 đ; CI 95%: [-87.39, 37.36] đ. Kết luận: chưa kết luận được.
- **1. Chi tiêu ổn định có nhiễu (Stable) — E vs A, MAE_daily:** Cải thiện: -16.32%; Win Rate: 6.7% (30 seed); hiệu trung bình E - tham chiếu: 13,616.93 đ; CI 95%: [9,294.35, 18,510.03] đ. Kết luận: kém hơn.
- **1. Chi tiêu ổn định có nhiễu (Stable) — E vs A, MAE_end:** Cải thiện: -22.27%; Win Rate: 13.3% (30 seed); hiệu trung bình E - tham chiếu: 29,111.48 đ; CI 95%: [19,663.83, 39,631.52] đ. Kết luận: kém hơn.
- **1. Chi tiêu ổn định có nhiễu (Stable) — E vs A, RMSE_daily:** Cải thiện: -21.94%; Win Rate: 6.7% (30 seed); hiệu trung bình E - tham chiếu: 24,018.95 đ; CI 95%: [15,830.97, 33,326.86] đ. Kết luận: kém hơn.
- **1. Chi tiêu ổn định có nhiễu (Stable) — E vs D, MAE_daily:** Cải thiện: 23.85%; Win Rate: 100.0% (30 seed); hiệu trung bình E - tham chiếu: -30,411.14 đ; CI 95%: [-35,248.43, -24,984.57] đ. Kết luận: tốt hơn có ý nghĩa.
- **1. Chi tiêu ổn định có nhiễu (Stable) — E vs D, MAE_end:** Cải thiện: 29.30%; Win Rate: 100.0% (30 seed); hiệu trung bình E - tham chiếu: -66,256.06 đ; CI 95%: [-75,356.44, -55,560.84] đ. Kết luận: tốt hơn có ý nghĩa.
- **1. Chi tiêu ổn định có nhiễu (Stable) — E vs D, RMSE_daily:** Cải thiện: 23.78%; Win Rate: 90.0% (30 seed); hiệu trung bình E - tham chiếu: -41,656.02 đ; CI 95%: [-49,476.48, -33,158.52] đ. Kết luận: tốt hơn có ý nghĩa.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — D vs A, MAE_daily:** Cải thiện: 51.36%; Win Rate: 100.0% (30 seed); hiệu trung bình D - tham chiếu: -140,280.85 đ; CI 95%: [-143,771.81, -136,547.66] đ. Kết luận: tốt hơn có ý nghĩa.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — D vs A, MAE_end:** Cải thiện: 52.33%; Win Rate: 100.0% (30 seed); hiệu trung bình D - tham chiếu: -309,236.04 đ; CI 95%: [-316,615.27, -301,761.70] đ. Kết luận: tốt hơn có ý nghĩa.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — D vs A, RMSE_daily:** Cải thiện: 44.02%; Win Rate: 100.0% (30 seed); hiệu trung bình D - tham chiếu: -147,180.26 đ; CI 95%: [-151,942.64, -142,236.01] đ. Kết luận: tốt hơn có ý nghĩa.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — D vs B, MAE_daily:** Cải thiện: 51.38%; Win Rate: 100.0% (30 seed); hiệu trung bình D - tham chiếu: -140,387.70 đ; CI 95%: [-143,868.73, -136,685.77] đ. Kết luận: tốt hơn có ý nghĩa.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — D vs B, MAE_end:** Cải thiện: 52.35%; Win Rate: 100.0% (30 seed); hiệu trung bình D - tham chiếu: -309,444.68 đ; CI 95%: [-316,850.63, -302,015.96] đ. Kết luận: tốt hơn có ý nghĩa.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — D vs B, RMSE_daily:** Cải thiện: 44.04%; Win Rate: 100.0% (30 seed); hiệu trung bình D - tham chiếu: -147,302.40 đ; CI 95%: [-152,069.15, -142,335.32] đ. Kết luận: tốt hơn có ý nghĩa.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — D vs C, MAE_daily:** Cải thiện: -0.03%; Win Rate: 30.0% (30 seed); hiệu trung bình D - tham chiếu: 44.51 đ; CI 95%: [-72.23, 161.38] đ. Kết luận: chưa kết luận được.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — D vs C, MAE_end:** Cải thiện: -0.07%; Win Rate: 26.7% (30 seed); hiệu trung bình D - tham chiếu: 211.07 đ; CI 95%: [-65.68, 487.08] đ. Kết luận: chưa kết luận được.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — D vs C, RMSE_daily:** Cải thiện: -0.07%; Win Rate: 26.7% (30 seed); hiệu trung bình D - tham chiếu: 140.03 đ; CI 95%: [32.72, 260.73] đ. Kết luận: kém hơn.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — E vs A, MAE_daily:** Cải thiện: 41.24%; Win Rate: 100.0% (30 seed); hiệu trung bình E - tham chiếu: -112,644.21 đ; CI 95%: [-117,758.82, -107,453.88] đ. Kết luận: tốt hơn có ý nghĩa.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — E vs A, MAE_end:** Cải thiện: 41.23%; Win Rate: 100.0% (30 seed); hiệu trung bình E - tham chiếu: -243,627.73 đ; CI 95%: [-255,079.85, -232,451.65] đ. Kết luận: tốt hơn có ý nghĩa.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — E vs A, RMSE_daily:** Cải thiện: 34.44%; Win Rate: 100.0% (30 seed); hiệu trung bình E - tham chiếu: -115,148.07 đ; CI 95%: [-121,357.93, -109,021.23] đ. Kết luận: tốt hơn có ý nghĩa.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — E vs D, MAE_daily:** Cải thiện: -20.81%; Win Rate: 3.3% (30 seed); hiệu trung bình E - tham chiếu: 27,636.63 đ; CI 95%: [23,702.65, 31,564.74] đ. Kết luận: kém hơn.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — E vs D, MAE_end:** Cải thiện: -23.29%; Win Rate: 0.0% (30 seed); hiệu trung bình E - tham chiếu: 65,608.31 đ; CI 95%: [57,517.58, 73,345.42] đ. Kết luận: kém hơn.
- **2. Chi tiêu có xu hướng tăng (Upward Trend) — E vs D, RMSE_daily:** Cải thiện: -17.11%; Win Rate: 0.0% (30 seed); hiệu trung bình E - tham chiếu: 32,032.19 đ; CI 95%: [27,457.17, 37,025.55] đ. Kết luận: kém hơn.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — D vs A, MAE_daily:** Cải thiện: 20.46%; Win Rate: 100.0% (30 seed); hiệu trung bình D - tham chiếu: -367,824.88 đ; CI 95%: [-378,118.07, -357,739.70] đ. Kết luận: tốt hơn có ý nghĩa.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — D vs A, MAE_end:** Cải thiện: 16.25%; Win Rate: 100.0% (30 seed); hiệu trung bình D - tham chiếu: -546,735.13 đ; CI 95%: [-564,870.34, -528,694.82] đ. Kết luận: tốt hơn có ý nghĩa.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — D vs A, RMSE_daily:** Cải thiện: -15.06%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 364,143.28 đ; CI 95%: [349,748.70, 377,822.50] đ. Kết luận: kém hơn.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — D vs B, MAE_daily:** Cải thiện: -18.78%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 226,068.54 đ; CI 95%: [215,664.23, 235,993.67] đ. Kết luận: kém hơn.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — D vs B, MAE_end:** Cải thiện: -20.67%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 482,835.58 đ; CI 95%: [464,811.94, 500,702.62] đ. Kết luận: kém hơn.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — D vs B, RMSE_daily:** Cải thiện: -31.35%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 664,202.70 đ; CI 95%: [651,328.13, 676,441.23] đ. Kết luận: kém hơn.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — D vs C, MAE_daily:** Cải thiện: 35.30%; Win Rate: 100.0% (30 seed); hiệu trung bình D - tham chiếu: -780,358.00 đ; CI 95%: [-781,946.13, -778,649.81] đ. Kết luận: tốt hơn có ý nghĩa.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — D vs C, MAE_end:** Cải thiện: 34.91%; Win Rate: 100.0% (30 seed); hiệu trung bình D - tham chiếu: -1,511,761.00 đ; CI 95%: [-1,514,961.49, -1,508,440.82] đ. Kết luận: tốt hơn có ý nghĩa.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — D vs C, RMSE_daily:** Cải thiện: 44.30%; Win Rate: 100.0% (30 seed); hiệu trung bình D - tham chiếu: -2,213,193.58 đ; CI 95%: [-2,217,757.83, -2,208,965.50] đ. Kết luận: tốt hơn có ý nghĩa.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — E vs A, MAE_daily:** Cải thiện: 37.57%; Win Rate: 100.0% (30 seed); hiệu trung bình E - tham chiếu: -675,388.50 đ; CI 95%: [-695,386.78, -647,399.55] đ. Kết luận: tốt hơn có ý nghĩa.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — E vs A, MAE_end:** Cải thiện: 33.72%; Win Rate: 100.0% (30 seed); hiệu trung bình E - tham chiếu: -1,134,628.96 đ; CI 95%: [-1,175,851.10, -1,076,637.24] đ. Kết luận: tốt hơn có ý nghĩa.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — E vs A, RMSE_daily:** Cải thiện: 9.03%; Win Rate: 93.3% (30 seed); hiệu trung bình E - tham chiếu: -218,377.03 đ; CI 95%: [-272,240.50, -126,021.85] đ. Kết luận: tốt hơn có ý nghĩa.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — E vs D, MAE_daily:** Cải thiện: 21.51%; Win Rate: 96.7% (30 seed); hiệu trung bình E - tham chiếu: -307,563.62 đ; CI 95%: [-329,845.21, -274,867.94] đ. Kết luận: tốt hơn có ý nghĩa.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — E vs D, MAE_end:** Cải thiện: 20.86%; Win Rate: 96.7% (30 seed); hiệu trung bình E - tham chiếu: -587,893.83 đ; CI 95%: [-632,781.97, -523,442.14] đ. Kết luận: tốt hơn có ý nghĩa.
- **3. Chi tiêu thất thường có outlier (Volatile/Outlier) — E vs D, RMSE_daily:** Cải thiện: 20.93%; Win Rate: 96.7% (30 seed); hiệu trung bình E - tham chiếu: -582,520.31 đ; CI 95%: [-638,712.10, -486,526.48] đ. Kết luận: tốt hơn có ý nghĩa.
- **4. Chi nhiều cuối tuần — D vs A, MAE_daily:** Cải thiện: -116.27%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 181,912.40 đ; CI 95%: [177,871.49, 185,695.40] đ. Kết luận: kém hơn.
- **4. Chi nhiều cuối tuần — D vs A, MAE_end:** Cải thiện: -174.29%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 378,483.13 đ; CI 95%: [369,588.98, 386,848.92] đ. Kết luận: kém hơn.
- **4. Chi nhiều cuối tuần — D vs A, RMSE_daily:** Cải thiện: -111.19%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 214,256.75 đ; CI 95%: [209,362.85, 219,005.90] đ. Kết luận: kém hơn.
- **4. Chi nhiều cuối tuần — D vs B, MAE_daily:** Cải thiện: -116.27%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 181,912.40 đ; CI 95%: [177,871.49, 185,695.40] đ. Kết luận: kém hơn.
- **4. Chi nhiều cuối tuần — D vs B, MAE_end:** Cải thiện: -174.29%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 378,483.13 đ; CI 95%: [369,588.98, 386,848.92] đ. Kết luận: kém hơn.
- **4. Chi nhiều cuối tuần — D vs B, RMSE_daily:** Cải thiện: -111.19%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 214,256.75 đ; CI 95%: [209,362.85, 219,005.90] đ. Kết luận: kém hơn.
- **4. Chi nhiều cuối tuần — D vs C, MAE_daily:** Cải thiện: 0.00%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 0.00 đ; CI 95%: [0.00, 0.00] đ. Kết luận: chưa kết luận được.
- **4. Chi nhiều cuối tuần — D vs C, MAE_end:** Cải thiện: 0.00%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 0.00 đ; CI 95%: [0.00, 0.00] đ. Kết luận: chưa kết luận được.
- **4. Chi nhiều cuối tuần — D vs C, RMSE_daily:** Cải thiện: 0.00%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 0.00 đ; CI 95%: [0.00, 0.00] đ. Kết luận: chưa kết luận được.
- **4. Chi nhiều cuối tuần — E vs A, MAE_daily:** Cải thiện: -3.53%; Win Rate: 33.3% (30 seed); hiệu trung bình E - tham chiếu: 5,526.86 đ; CI 95%: [1,379.39, 10,189.81] đ. Kết luận: kém hơn.
- **4. Chi nhiều cuối tuần — E vs A, MAE_end:** Cải thiện: -4.54%; Win Rate: 36.7% (30 seed); hiệu trung bình E - tham chiếu: 9,849.46 đ; CI 95%: [347.74, 20,590.00] đ. Kết luận: kém hơn.
- **4. Chi nhiều cuối tuần — E vs A, RMSE_daily:** Cải thiện: -10.34%; Win Rate: 26.7% (30 seed); hiệu trung bình E - tham chiếu: 19,925.27 đ; CI 95%: [11,112.95, 29,590.37] đ. Kết luận: kém hơn.
- **4. Chi nhiều cuối tuần — E vs D, MAE_daily:** Cải thiện: 52.13%; Win Rate: 100.0% (30 seed); hiệu trung bình E - tham chiếu: -176,385.54 đ; CI 95%: [-180,540.92, -171,892.77] đ. Kết luận: tốt hơn có ý nghĩa.
- **4. Chi nhiều cuối tuần — E vs D, MAE_end:** Cải thiện: 61.89%; Win Rate: 100.0% (30 seed); hiệu trung bình E - tham chiếu: -368,633.67 đ; CI 95%: [-377,944.06, -358,781.90] đ. Kết luận: tốt hơn có ý nghĩa.
- **4. Chi nhiều cuối tuần — E vs D, RMSE_daily:** Cải thiện: 47.75%; Win Rate: 100.0% (30 seed); hiệu trung bình E - tham chiếu: -194,331.48 đ; CI 95%: [-203,356.50, -184,501.26] đ. Kết luận: tốt hơn có ý nghĩa.
- **5. Thay đổi thói quen giữa chừng — D vs A, MAE_daily:** Cải thiện: 48.65%; Win Rate: 100.0% (30 seed); hiệu trung bình D - tham chiếu: -299,254.93 đ; CI 95%: [-305,253.59, -293,199.48] đ. Kết luận: tốt hơn có ý nghĩa.
- **5. Thay đổi thói quen giữa chừng — D vs A, MAE_end:** Cải thiện: 44.73%; Win Rate: 100.0% (30 seed); hiệu trung bình D - tham chiếu: -577,598.74 đ; CI 95%: [-590,140.90, -565,595.50] đ. Kết luận: tốt hơn có ý nghĩa.
- **5. Thay đổi thói quen giữa chừng — D vs A, RMSE_daily:** Cải thiện: 38.59%; Win Rate: 100.0% (30 seed); hiệu trung bình D - tham chiếu: -537,978.45 đ; CI 95%: [-545,929.84, -529,195.20] đ. Kết luận: tốt hơn có ý nghĩa.
- **5. Thay đổi thói quen giữa chừng — D vs B, MAE_daily:** Cải thiện: 48.70%; Win Rate: 100.0% (30 seed); hiệu trung bình D - tham chiếu: -299,748.06 đ; CI 95%: [-305,748.55, -293,716.35] đ. Kết luận: tốt hơn có ý nghĩa.
- **5. Thay đổi thói quen giữa chừng — D vs B, MAE_end:** Cải thiện: 44.77%; Win Rate: 100.0% (30 seed); hiệu trung bình D - tham chiếu: -578,563.29 đ; CI 95%: [-591,100.33, -566,551.82] đ. Kết luận: tốt hơn có ý nghĩa.
- **5. Thay đổi thói quen giữa chừng — D vs B, RMSE_daily:** Cải thiện: 38.66%; Win Rate: 100.0% (30 seed); hiệu trung bình D - tham chiếu: -539,562.59 đ; CI 95%: [-547,509.81, -530,855.79] đ. Kết luận: tốt hơn có ý nghĩa.
- **5. Thay đổi thói quen giữa chừng — D vs C, MAE_daily:** Cải thiện: -1.28%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 3,977.83 đ; CI 95%: [3,549.43, 4,435.20] đ. Kết luận: kém hơn.
- **5. Thay đổi thói quen giữa chừng — D vs C, MAE_end:** Cải thiện: -1.09%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 7,699.47 đ; CI 95%: [6,878.27, 8,579.56] đ. Kết luận: kém hơn.
- **5. Thay đổi thói quen giữa chừng — D vs C, RMSE_daily:** Cải thiện: -0.94%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 7,977.10 đ; CI 95%: [7,228.71, 8,749.86] đ. Kết luận: kém hơn.
- **5. Thay đổi thói quen giữa chừng — E vs A, MAE_daily:** Cải thiện: 55.50%; Win Rate: 100.0% (30 seed); hiệu trung bình E - tham chiếu: -341,386.94 đ; CI 95%: [-347,156.79, -334,882.82] đ. Kết luận: tốt hơn có ý nghĩa.
- **5. Thay đổi thói quen giữa chừng — E vs A, MAE_end:** Cải thiện: 51.24%; Win Rate: 100.0% (30 seed); hiệu trung bình E - tham chiếu: -661,611.20 đ; CI 95%: [-672,419.73, -649,521.04] đ. Kết luận: tốt hơn có ý nghĩa.
- **5. Thay đổi thói quen giữa chừng — E vs A, RMSE_daily:** Cải thiện: 41.46%; Win Rate: 100.0% (30 seed); hiệu trung bình E - tham chiếu: -577,985.21 đ; CI 95%: [-585,817.03, -569,919.30] đ. Kết luận: tốt hơn có ý nghĩa.
- **5. Thay đổi thói quen giữa chừng — E vs D, MAE_daily:** Cải thiện: 13.34%; Win Rate: 100.0% (30 seed); hiệu trung bình E - tham chiếu: -42,132.01 đ; CI 95%: [-47,309.98, -36,733.95] đ. Kết luận: tốt hơn có ý nghĩa.
- **5. Thay đổi thói quen giữa chừng — E vs D, MAE_end:** Cải thiện: 11.77%; Win Rate: 100.0% (30 seed); hiệu trung bình E - tham chiếu: -84,012.45 đ; CI 95%: [-94,141.27, -73,910.83] đ. Kết luận: tốt hơn có ý nghĩa.
- **5. Thay đổi thói quen giữa chừng — E vs D, RMSE_daily:** Cải thiện: 4.67%; Win Rate: 100.0% (30 seed); hiệu trung bình E - tham chiếu: -40,006.77 đ; CI 95%: [-46,426.59, -33,679.64] đ. Kết luận: tốt hơn có ý nghĩa.
- **6. Chi tiêu thưa — D vs A, MAE_daily:** Cải thiện: -51.64%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 300,588.82 đ; CI 95%: [268,010.43, 333,722.42] đ. Kết luận: kém hơn.
- **6. Chi tiêu thưa — D vs A, MAE_end:** Cải thiện: -74.59%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 676,226.07 đ; CI 95%: [607,790.61, 749,423.26] đ. Kết luận: kém hơn.
- **6. Chi tiêu thưa — D vs A, RMSE_daily:** Cải thiện: -60.53%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 463,253.19 đ; CI 95%: [420,743.32, 509,541.86] đ. Kết luận: kém hơn.
- **6. Chi tiêu thưa — D vs B, MAE_daily:** Cải thiện: -50.98%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 298,050.64 đ; CI 95%: [264,997.29, 331,629.52] đ. Kết luận: kém hơn.
- **6. Chi tiêu thưa — D vs B, MAE_end:** Cải thiện: -73.52%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 670,661.84 đ; CI 95%: [601,550.23, 745,157.29] đ. Kết luận: kém hơn.
- **6. Chi tiêu thưa — D vs B, RMSE_daily:** Cải thiện: -59.68%; Win Rate: 0.0% (30 seed); hiệu trung bình D - tham chiếu: 459,184.12 đ; CI 95%: [415,878.44, 506,430.28] đ. Kết luận: kém hơn.
- **6. Chi tiêu thưa — D vs C, MAE_daily:** Cải thiện: 0.03%; Win Rate: 53.3% (30 seed); hiệu trung bình D - tham chiếu: -260.15 đ; CI 95%: [-1,530.02, 970.61] đ. Kết luận: chưa kết luận được.
- **6. Chi tiêu thưa — D vs C, MAE_end:** Cải thiện: 0.01%; Win Rate: 56.7% (30 seed); hiệu trung bình D - tham chiếu: -112.09 đ; CI 95%: [-3,475.14, 3,428.09] đ. Kết luận: chưa kết luận được.
- **6. Chi tiêu thưa — D vs C, RMSE_daily:** Cải thiện: 0.06%; Win Rate: 50.0% (30 seed); hiệu trung bình D - tham chiếu: -697.93 đ; CI 95%: [-2,587.71, 1,128.60] đ. Kết luận: chưa kết luận được.
- **6. Chi tiêu thưa — E vs A, MAE_daily:** Cải thiện: -61.42%; Win Rate: 0.0% (30 seed); hiệu trung bình E - tham chiếu: 357,508.33 đ; CI 95%: [290,870.57, 430,456.94] đ. Kết luận: kém hơn.
- **6. Chi tiêu thưa — E vs A, MAE_end:** Cải thiện: -86.19%; Win Rate: 0.0% (30 seed); hiệu trung bình E - tham chiếu: 781,458.62 đ; CI 95%: [641,735.73, 933,445.49] đ. Kết luận: kém hơn.
- **6. Chi tiêu thưa — E vs A, RMSE_daily:** Cải thiện: -87.15%; Win Rate: 0.0% (30 seed); hiệu trung bình E - tham chiếu: 667,003.26 đ; CI 95%: [553,324.23, 786,359.91] đ. Kết luận: kém hơn.
- **6. Chi tiêu thưa — E vs D, MAE_daily:** Cải thiện: -6.45%; Win Rate: 40.0% (30 seed); hiệu trung bình E - tham chiếu: 56,919.51 đ; CI 95%: [-5,366.97, 122,019.39] đ. Kết luận: chưa kết luận được.
- **6. Chi tiêu thưa — E vs D, MAE_end:** Cải thiện: -6.65%; Win Rate: 43.3% (30 seed); hiệu trung bình E - tham chiếu: 105,232.56 đ; CI 95%: [-21,733.07, 242,685.21] đ. Kết luận: chưa kết luận được.
- **6. Chi tiêu thưa — E vs D, RMSE_daily:** Cải thiện: -16.58%; Win Rate: 20.0% (30 seed); hiệu trung bình E - tham chiếu: 203,750.07 đ; CI 95%: [103,986.43, 306,871.92] đ. Kết luận: kém hơn.

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
| stable_noise | arm_A | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| stable_noise | arm_A | stress | 894 | 6 | 1 | 299 | 0.993 | 0.999 | -0.049 | 5.274 | 894 | 77 | 32 | 0 |
| stable_noise | arm_B | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| stable_noise | arm_B | stress | 894 | 6 | 1 | 299 | 0.993 | 0.999 | -0.049 | 5.274 | 894 | 77 | 32 | 0 |
| stable_noise | arm_C | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| stable_noise | arm_C | stress | 888 | 4 | 7 | 301 | 0.996 | 0.992 | 0.012 | 5.264 | 888 | 69 | 80 | 0 |
| stable_noise | arm_D | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| stable_noise | arm_D | stress | 888 | 4 | 7 | 301 | 0.996 | 0.992 | 0.012 | 5.264 | 888 | 69 | 80 | 0 |
| stable_noise | arm_E | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| stable_noise | arm_E | stress | 893 | 5 | 2 | 300 | 0.994 | 0.998 | -0.031 | 5.272 | 893 | 75 | 46 | 0 |
| upward_trend | arm_A | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| upward_trend | arm_A | stress | 902 | 0 | 33 | 265 | 1.000 | 0.965 | 0.211 | 4.615 | 902 | 3 | 185 | 0 |
| upward_trend | arm_B | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| upward_trend | arm_B | stress | 902 | 0 | 33 | 265 | 1.000 | 0.965 | 0.211 | 4.615 | 902 | 3 | 185 | 0 |
| upward_trend | arm_C | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| upward_trend | arm_C | stress | 923 | 7 | 12 | 258 | 0.992 | 0.987 | 0.061 | 4.665 | 923 | 28 | 84 | 0 |
| upward_trend | arm_D | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| upward_trend | arm_D | stress | 923 | 7 | 12 | 258 | 0.992 | 0.987 | 0.061 | 4.665 | 923 | 28 | 84 | 0 |
| upward_trend | arm_E | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| upward_trend | arm_E | stress | 922 | 4 | 13 | 261 | 0.996 | 0.986 | 0.088 | 4.663 | 922 | 24 | 104 | 0 |
| volatile_outliers | arm_A | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| volatile_outliers | arm_A | stress | 865 | 35 | 30 | 270 | 0.961 | 0.966 | -1.301 | 5.645 | 865 | 399 | 14 | 0 |
| volatile_outliers | arm_B | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| volatile_outliers | arm_B | stress | 865 | 35 | 30 | 270 | 0.961 | 0.966 | -0.657 | 5.645 | 865 | 341 | 17 | 0 |
| volatile_outliers | arm_C | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| volatile_outliers | arm_C | stress | 860 | 20 | 35 | 285 | 0.977 | 0.961 | -0.815 | 5.636 | 860 | 315 | 81 | 0 |
| volatile_outliers | arm_D | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| volatile_outliers | arm_D | stress | 859 | 16 | 36 | 289 | 0.982 | 0.960 | -0.428 | 5.633 | 859 | 292 | 89 | 0 |
| volatile_outliers | arm_E | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| volatile_outliers | arm_E | stress | 863 | 34 | 32 | 271 | 0.962 | 0.964 | -0.319 | 5.638 | 863 | 252 | 52 | 0 |
| weekend_spending | arm_A | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| weekend_spending | arm_A | stress | 898 | 3 | 16 | 283 | 0.997 | 0.982 | 0.249 | 4.963 | 898 | 31 | 255 | 0 |
| weekend_spending | arm_B | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| weekend_spending | arm_B | stress | 898 | 3 | 16 | 283 | 0.997 | 0.982 | 0.249 | 4.963 | 898 | 31 | 255 | 0 |
| weekend_spending | arm_C | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| weekend_spending | arm_C | stress | 908 | 15 | 6 | 271 | 0.984 | 0.993 | -0.148 | 4.975 | 908 | 170 | 55 | 0 |
| weekend_spending | arm_D | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| weekend_spending | arm_D | stress | 908 | 15 | 6 | 271 | 0.984 | 0.993 | -0.148 | 4.975 | 908 | 170 | 55 | 0 |
| weekend_spending | arm_E | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| weekend_spending | arm_E | stress | 899 | 4 | 15 | 282 | 0.996 | 0.984 | 0.230 | 4.964 | 899 | 36 | 245 | 0 |
| habit_shift | arm_A | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| habit_shift | arm_A | stress | 944 | 5 | 36 | 215 | 0.995 | 0.963 | 0.326 | 4.057 | 944 | 63 | 202 | 0 |
| habit_shift | arm_B | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| habit_shift | arm_B | stress | 944 | 5 | 36 | 215 | 0.995 | 0.963 | 0.326 | 4.057 | 944 | 63 | 202 | 0 |
| habit_shift | arm_C | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| habit_shift | arm_C | stress | 939 | 4 | 41 | 216 | 0.996 | 0.958 | 0.007 | 4.026 | 939 | 81 | 85 | 0 |
| habit_shift | arm_D | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| habit_shift | arm_D | stress | 939 | 4 | 41 | 216 | 0.996 | 0.958 | 0.007 | 4.026 | 939 | 81 | 85 | 0 |
| habit_shift | arm_E | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| habit_shift | arm_E | stress | 941 | 3 | 39 | 217 | 0.997 | 0.960 | -0.027 | 4.039 | 941 | 80 | 61 | 0 |
| sparse_spending | arm_A | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| sparse_spending | arm_A | stress | 618 | 64 | 80 | 438 | 0.906 | 0.885 | 0.283 | 4.736 | 618 | 12 | 66 | 0 |
| sparse_spending | arm_B | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| sparse_spending | arm_B | stress | 618 | 63 | 80 | 439 | 0.907 | 0.885 | 0.285 | 4.736 | 618 | 12 | 66 | 0 |
| sparse_spending | arm_C | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| sparse_spending | arm_C | stress | 622 | 78 | 76 | 424 | 0.889 | 0.891 | -0.027 | 4.772 | 622 | 51 | 50 | 0 |
| sparse_spending | arm_D | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| sparse_spending | arm_D | stress | 621 | 78 | 77 | 424 | 0.888 | 0.890 | -0.027 | 4.765 | 621 | 50 | 50 | 0 |
| sparse_spending | arm_E | risk | 0 | 0 | 0 | 1200 | N/A | N/A | N/A | N/A | 0 | 0 | 0 | 0 |
| sparse_spending | arm_E | stress | 609 | 54 | 89 | 448 | 0.919 | 0.872 | 0.005 | 4.670 | 609 | 40 | 49 | 0 |
